import logging
from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, F, Max, OuterRef, Q
from django.utils import timezone
from simple_history.utils import update_change_reason

from apps.productos import unidades
from apps.productos.models import Producto
from apps.productos.services import registrar_consumo
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.imagenes import procesar_imagen
from apps.visitas.models import (
    Foto,
    ItemTurno,
    ProductoAplicado,
    PuntoNoRevisado,
    Revision,
    Visita,
)
from apps.visitas.planillas import validar_datos
from apps.visitas.ubicacion import verificar

# Topes de una revisión desde la app; los comparte el serializer de la API.
MAX_FOTOS = 2
MAX_PRODUCTOS = 30
TOLERANCIA_FUTURO = timedelta(minutes=10)
MENSAJE_QR_INVALIDO = "El código QR no corresponde a este sitio."
MENSAJE_SIN_SERVICIO = "El punto no tiene servicio asignado."
MENSAJE_SERVICIO_DE_BAJA = "El servicio de este punto está dado de baja."
MENSAJE_PUNTO_NO_REPORTABLE = "El punto no corresponde a este sitio."
MOTIVO_UBICACION_FIJADA = "Ubicación fijada por el primer escaneo"

logger = logging.getLogger(__name__)


class RevisionDuplicada(Exception):
    """El `cliente_uuid` ya fue registrado; `revision` es la revisión existente."""

    def __init__(self, revision):
        super().__init__("La revisión ya fue registrada.")
        self.revision = revision


class VisitaNoEncontrada(ValidationError):
    """La visita no existe o es de otro empleado: la API responde 404 en ambos casos."""

    def __init__(self):
        super().__init__({"visita": "La visita no existe."})


class VisitaYaCerrada(ValidationError):
    """La visita ya estaba cerrada y no por el mismo empleado: la API responde 409."""

    def __init__(self):
        super().__init__("La visita ya fue cerrada.")


class VisitaNoAbierta(ValidationError):
    """La visita propia no está abierta: la app reenvía `abrir` y reintenta."""

    def __init__(self, mensaje="La visita no está abierta.", campo="visita"):
        error = ValidationError(mensaje, code="visita_no_abierta")
        super().__init__(error if campo is None else {campo: error})


def validar_hora_cliente(valor, campo):
    """Valida una hora que manda el teléfono: ni futura ni con demasiado atraso.

    Futura más allá de `TOLERANCIA_FUTURO`: error común. Con más de
    `ATRASO_MAXIMO_APP_HORAS` de atraso: error con `code="atraso_excedido"`. La
    carga manual del administrador sigue con `ATRASO_MAXIMO_HORAS`.
    """
    ahora = timezone.now()
    if valor > ahora + TOLERANCIA_FUTURO:
        raise ValidationError({campo: ["La fecha no puede ser futura."]})
    horas = settings.ATRASO_MAXIMO_APP_HORAS
    if valor < ahora - timedelta(hours=horas):
        mensaje = (
            f"Tiene más de {horas} horas de atraso. Avise al administrador para "
            "que la cargue como manual."
        )
        raise ValidationError({campo: ValidationError(mensaje, code="atraso_excedido")})


@contextmanager
def _transaccion_con_archivos():
    """Transacción que, si falla, borra los archivos de las fotos ya escritas.

    Entrega la lista donde el cuerpo anota las fotos guardadas. La transacción
    revierte la base, no los archivos.
    """
    guardadas, confirmada = [], False
    try:
        with transaction.atomic():
            yield guardadas
        confirmada = True
    finally:
        if not confirmada:
            _borrar_archivos(guardadas)


def _resolver_punto(sitio_id, qr_codigo, empresa_id):
    """Punto activo del sitio (de la empresa) que tiene ese QR; si no, error genérico.

    Mismo mensaje para QR ajeno, punto o sitio inactivo y cliente dado de baja: no
    se revela el motivo.
    """
    try:
        codigo = UUID(str(qr_codigo))
    except ValueError:
        raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
    punto = (
        PuntoControl.objects.de_empresa(empresa_id)
        .select_related("sitio__cliente")
        .filter(qr_codigo=codigo, activo=True, sitio_id=sitio_id)
        .first()
    )
    if punto is None or not punto.sitio.activo or not punto.sitio.cliente.activo:
        raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
    return punto


def _servicio_con_campos(pk, empresa_id):
    """Servicio de la empresa con sus campos de planilla precargados."""
    return (
        TipoServicio.objects.de_empresa(empresa_id)
        .prefetch_related("campos")
        .get(pk=pk)
    )


def _id_producto(item):
    """Id entero del producto de un ítem, o None si no es utilizable."""
    try:
        return int(item.get("producto"))
    except (TypeError, ValueError, AttributeError):
        return None


def _error_de_unidad(producto, unidad):
    """Mensaje si `unidad` no se admite para el producto (None si es válida)."""
    if unidad in unidades.unidades_permitidas(producto):
        return None
    if producto.modo_unidad == "unica" and unidad in unidades.UNIDADES:
        if unidades.magnitud_de(unidad) == unidades.magnitud_de(producto.unidad_base):
            return f"Este producto solo admite la unidad {producto.unidad_base}."
    permitidas = ", ".join(unidades.unidades_permitidas(producto))
    return f"La unidad no corresponde al producto: use {permitidas}."


def _errores_de_cantidad(aplicado, producto):
    """Valida unidad y cantidad del aplicado y fija `cantidad_base`.

    Devuelve los errores por campo (vacío si todo está bien).
    """
    errores = {}
    mensaje = _error_de_unidad(producto, aplicado.unidad)
    if mensaje:
        errores["unidad"] = [mensaje]
    if aplicado.cantidad is not None and aplicado.cantidad <= 0:
        errores["cantidad"] = ["La cantidad debe ser mayor que cero."]
    if not errores:
        aplicado.cantidad_base = unidades.convertir(
            aplicado.cantidad, aplicado.unidad, producto.unidad_base
        )
        if aplicado.cantidad_base <= 0:
            errores["cantidad"] = ["La cantidad es demasiado chica para el producto."]
        else:
            try:
                unidades.validar_cantidad_base(aplicado.cantidad_base)
            except ValidationError as error:
                errores["cantidad"] = error.messages
    return errores


def _armar_productos(productos_aplicados, empresa_id):
    """Valida cada producto aplicado; devuelve (instancias sin guardar, errores).

    Los errores van anidados, `{posición: {campo: [mensajes]}}`, con
    posición desde cero. Busca todos los productos del pedido, del catálogo de la
    empresa, en una sola consulta y calcula `cantidad_base` en la unidad base del
    producto.
    """
    ids = {_id_producto(item) for item in productos_aplicados} - {None}
    catalogo = (
        Producto.objects.de_empresa(empresa_id)
        .filter(pk__in=ids, activo=True)
        .in_bulk()
    )
    errores, instancias = {}, []
    for posicion, item in enumerate(productos_aplicados):
        producto = catalogo.get(_id_producto(item))
        if producto is None:
            errores[posicion] = {"producto": ["No existe o está inactivo."]}
            continue
        aplicado = ProductoAplicado(
            producto=producto,
            lote=item.get("lote") or "",
            dosis=item.get("dosis"),
            unidad_dosis=item.get("unidad_dosis") or "",
            unidad=item.get("unidad") or "",
            cantidad=item.get("cantidad"),
        )
        try:
            # El producto ya se leyó del catálogo: no se vuelve a consultar.
            aplicado.full_clean(
                exclude=["revision", "producto", "cantidad_base", "movimiento"]
            )
            campos = {}
        except ValidationError as error:
            campos = dict(error.message_dict)
        if "unidad" not in campos and "cantidad" not in campos:
            campos.update(_errores_de_cantidad(aplicado, producto))
        if campos:
            errores[posicion] = campos
        else:
            instancias.append(aplicado)
    return instancias, errores


def _validar_coordenadas(latitud, longitud, obligatorias=False):
    """Errores por campo si la latitud o la longitud faltan (si son obligatorias)
    o están fuera de rango."""
    errores = {}
    for clave, valor, limite in (
        ("latitud", latitud, 90),
        ("longitud", longitud, 180),
    ):
        if valor is None and obligatorias:
            errores[clave] = ["Este campo es obligatorio."]
            continue
        try:
            fuera = valor is not None and not -limite <= valor <= limite
        except TypeError:
            fuera = True
        if fuera:
            errores[clave] = [f"Debe estar entre -{limite} y {limite}."]
    return errores


def _errores_planilla(esquema, datos):
    """Mensajes de la planilla contra su esquema (lista vacía si es válida)."""
    return [
        mensaje if clave == "datos" else f"{clave}: {mensaje}"
        for clave, mensajes in validar_datos(esquema, datos).items()
        for mensaje in mensajes
    ]


def _validar_evidencia(esquema, datos, productos_aplicados, empresa_id):
    """Valida planilla y productos; devuelve (errores por campo, productos armados)."""
    errores = {}
    errores_datos = _errores_planilla(esquema, datos)
    if errores_datos:
        errores["datos"] = errores_datos
    errores_productos, aplicados = _validar_productos(productos_aplicados, empresa_id)
    errores.update(errores_productos)
    return errores, aplicados


def _validar_productos(productos_aplicados, empresa_id):
    """Valida los productos aplicados; devuelve (errores por campo, armados)."""
    errores = {}
    if len(productos_aplicados) > MAX_PRODUCTOS:
        errores["productos_aplicados"] = [
            f"Se permiten hasta {MAX_PRODUCTOS} productos por revisión."
        ]
        return errores, []
    aplicados, errores_productos = _armar_productos(productos_aplicados, empresa_id)
    for posicion, campos in errores_productos.items():
        for campo, mensajes in campos.items():
            errores[f"productos_aplicados.{posicion}.{campo}"] = mensajes
    return errores, aplicados


def _borrar_archivos(fotos):
    """Borra del almacenamiento los archivos de fotos de una operación fallida."""
    for foto in fotos:
        try:
            foto.imagen.storage.delete(foto.imagen.name)
        except Exception:  # noqa: BLE001
            # No debe tapar la excepción original que se está propagando.
            logger.exception("No se pudo borrar un archivo de foto.")


def _pendiente_para(sitio, empleado, punto=None, hasta=None):
    """Pendiente propia (la más antigua) y si hay una de otro empleado.

    Sin bloquear filas. Con `punto`, la de otro empleado cuenta solo si su turno
    tiene un ítem de ese punto. Con `hasta` (una fecha), la propia debe estar sin
    programar o programada para esa fecha o antes.
    """
    pendientes = Visita.objects.de_empresa(sitio.empresa_id).filter(
        sitio=sitio, estado=Visita.Estado.PENDIENTE
    )
    # Una pendiente con revisiones no se reutiliza.
    sin_revisiones = ~Exists(
        Revision.objects.de_empresa(sitio.empresa_id).filter(visita=OuterRef("pk"))
    )
    propias = pendientes.filter(sin_revisiones, empleado=empleado)
    if hasta is not None:
        propias = propias.filter(
            Q(programada_para__isnull=True) | Q(programada_para__lte=hasta)
        )
    propia = propias.order_by(F("programada_para").asc(nulls_last=True), "pk").first()
    de_otro = pendientes.exclude(empleado=empleado)
    if punto is not None:
        de_otro = de_otro.filter(
            Exists(
                ItemTurno.objects.de_empresa(sitio.empresa_id).filter(
                    visita=OuterRef("pk"), punto=punto
                )
            )
        )
    return propia, de_otro.exists()


def visita_destino(*, empleado, sitio, hasta=None):
    """Visita a la que irá el próximo escaneo del empleado en el sitio, o `None`.

    No bloquea filas. Es la abierta propia del sitio (la de menor `pk`); si no hay
    y el empleado no es administrador, la pendiente más antigua sin revisiones
    (con `hasta`, solo las programadas para esa fecha o antes, o sin programar).
    """
    abierta = (
        Visita.objects.de_empresa(sitio.empresa_id)
        .filter(sitio=sitio, empleado=empleado, estado=Visita.Estado.ABIERTA)
        .order_by("pk")
        .first()
    )
    if abierta is not None or empleado.es_administrador:
        return abierta
    return _pendiente_para(sitio, empleado, hasta=hasta)[0]


def servicio_para_punto(*, visita, punto):
    """Servicio de un punto en una visita: `(servicio | None, en_turno)`.

    Si la visita tiene un ítem para el punto, es el de ese ítem y `en_turno` es
    `True`. Si no (o sin visita), es el servicio del punto y `en_turno` es `False`.
    El servicio llega con sus `campos` precargados.
    """
    item = None
    if visita is not None:
        item = (
            ItemTurno.objects.de_empresa(visita.empresa_id)
            .filter(visita=visita, punto=punto)
            .first()
        )
    servicio_id = item.servicio_id if item is not None else punto.servicio_id
    if servicio_id is None:
        return None, False
    return _servicio_con_campos(servicio_id, punto.empresa_id), item is not None


def _errores_de_items(sitio_id, items, empresa_id):
    """Errores de los ítems `(punto, servicio)` de un turno o carga manual.

    Exige al menos uno, puntos activos del sitio sin repetir y servicios activos,
    unos y otros de la empresa del sitio.
    """
    if not items:
        return {"puntos": ["Elija al menos un punto de control."]}
    errores = {}
    puntos = [punto for punto, _ in items]
    if any(not p.activo or p.sitio_id != sitio_id for p in puntos):
        errores["puntos"] = ["Los puntos deben ser activos y del sitio."]
    elif len({p.pk for p in puntos}) != len(puntos):
        errores["puntos"] = ["Un punto no puede repetirse."]
    if any(servicio is None or not servicio.activo for _, servicio in items):
        errores["servicios"] = ["Cada punto necesita un servicio activo."]
    elif any(servicio.empresa_id != empresa_id for _, servicio in items):
        errores["servicios"] = ["Los servicios deben ser de la empresa del sitio."]
    if "puntos" not in errores and any(p.empresa_id != empresa_id for p in puntos):
        errores["puntos"] = ["Los puntos deben ser de la empresa del sitio."]
    return errores


def crear_turno(*, sitio, empleado, programada_para, items, asignada_por):
    """Crea un turno pendiente para un empleado y devuelve la `Visita`.

    `items` es una lista de `(punto, servicio)`: los puntos que debe revisar, cada
    uno con el servicio que se le hará. Exige al menos un ítem, puntos activos del
    sitio, servicios activos, un empleado activo y un sitio y cliente activos.
    Levanta `ValidationError` con errores por campo.
    """
    errores = _errores_de_items(sitio.pk, items, sitio.empresa_id)
    if not (sitio.activo and sitio.cliente.activo):
        errores["sitio"] = ["El sitio o el cliente están de baja."]
    if not (empleado.is_active and empleado.es_empleado):
        errores["empleado"] = ["Debe ser un empleado activo."]
    elif empleado.empresa_id != sitio.empresa_id:
        errores["empleado"] = ["El empleado debe ser de la empresa del sitio."]
    if errores:
        raise ValidationError(errores)
    with transaction.atomic():
        visita = Visita.objects.create(
            sitio=sitio,
            empleado=empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.PENDIENTE,
            programada_para=programada_para,
            asignada_por=asignada_por,
        )
        ItemTurno.objects.bulk_create(
            ItemTurno(
                visita=visita,
                punto=punto,
                servicio=servicio,
                empresa_id=visita.empresa_id,
            )
            for punto, servicio in items
        )
    return visita


def abrir_visita(
    *,
    empleado,
    qr_codigo,
    latitud=None,
    longitud=None,
    precision_m=None,
    abierta_en=None,
):
    """Abre la jornada del empleado en el sitio del QR; devuelve `(visita, creada)`.

    `latitud` y `longitud` (opcionales) verifican la ubicación: la distancia al punto
    queda en la visita y nunca se rechaza. `precision_m` se guarda tal cual. La
    visita de un administrador no cuenta como servicio (`cuenta_como_servicio` queda
    en `False`, según su rol al abrir): no toma pendientes ni marca
    `incidencia_asignacion`.

    Es idempotente: si el empleado ya tiene una visita abierta en el sitio la
    devuelve con `creada=False`. Si tiene un turno pendiente, abre el más antiguo. Si
    no, crea una visita nueva sin ítems, con `incidencia_asignacion` cuando otro
    empleado tiene un turno pendiente en el sitio. Levanta `ValidationError` si
    `qr_codigo` no es el de un punto activo de un sitio y cliente activos, antes de
    tomar locks y de crear nada.

    `abierta_en` es la hora en que el empleado abrió sin conexión: se valida con
    `validar_hora_cliente` y se guarda `min(abierta_en, ahora)`; con una visita ya
    abierta no se evalúa ni se toca. Al reabrir o crear se guarda la hora de
    recepción (`abierta_recibida_en`). Con ella solo se reabren pendientes sin
    programar o programadas hasta `localdate(abierta_en)`; si no hay ninguna se
    crea una visita nueva.
    """
    with transaction.atomic():
        try:
            punto = (
                PuntoControl.objects.de_empresa(empleado.empresa_id)
                .select_related("sitio__cliente")
                .get(qr_codigo=UUID(str(qr_codigo)), activo=True)
            )
        except (PuntoControl.DoesNotExist, ValueError):
            raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
        sitio = punto.sitio
        if not (sitio.activo and sitio.cliente.activo):
            raise ValidationError({"qr_codigo": MENSAJE_QR_INVALIDO})
        # Orden de bloqueo: Sitio -> Visita -> PuntoControl.
        # Serializa las aperturas del mismo sitio: no quedan dos abiertas.
        Sitio.objects.de_empresa(sitio.empresa_id).select_for_update(of=("self",)).get(
            pk=sitio.pk
        )
        # visita_destino no bloquea filas: se bloquean antes las visitas propias del
        # sitio que pueden ser el destino (abiertas o pendientes).
        propias = list(
            Visita.objects.de_empresa(sitio.empresa_id)
            .select_for_update()
            .filter(
                sitio=sitio,
                empleado=empleado,
                estado__in=[Visita.Estado.ABIERTA, Visita.Estado.PENDIENTE],
            )
        )
        # Con una abierta se devuelve tal cual: `abierta_en` no se evalúa.
        abierta = next((v for v in propias if v.estado == Visita.Estado.ABIERTA), None)
        if abierta is not None:
            return abierta, False
        if abierta_en is not None:
            validar_hora_cliente(abierta_en, "abierta_en")
        hasta = None if abierta_en is None else timezone.localdate(abierta_en)
        destino = visita_destino(empleado=empleado, sitio=sitio, hasta=hasta)
        if destino is not None and destino.estado == Visita.Estado.ABIERTA:
            return destino, False
        propia = destino
        hay_de_otro = (
            not empleado.es_administrador and _pendiente_para(sitio, empleado, punto)[1]
        )
        distancia, incidencia_ubicacion = verificar(punto, latitud, longitud)
        ahora = timezone.now()
        apertura = ahora if abierta_en is None else min(abierta_en, ahora)
        if propia is not None:
            propia.distancia_m = distancia
            propia.precision_m = precision_m
            propia.incidencia_ubicacion = incidencia_ubicacion
            propia.estado = Visita.Estado.ABIERTA
            propia.abierta_en = apertura
            propia.abierta_recibida_en = ahora
            propia.origen = Visita.Origen.APP
            propia.motivo_manual = ""
            propia.cuenta_como_servicio = True
            propia.save()
            return propia, True
        visita = Visita.objects.create(
            sitio=sitio,
            empleado=empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=apertura,
            abierta_recibida_en=ahora,
            incidencia_asignacion=hay_de_otro,
            distancia_m=distancia,
            precision_m=precision_m,
            incidencia_ubicacion=incidencia_ubicacion,
            cuenta_como_servicio=not empleado.es_administrador,
        )
        return visita, True


def _fijar_ubicacion_por_escaneo(punto, revision, usuario):
    """El primer escaneo de un punto sin coordenadas las fija, sea cual sea el rol.

    Bloquea el punto; con precisión peor que `PRECISION_MAXIMA_M`, o con
    incidencia de ubicación (revisión lejos de la referencia), no fija nada y la
    revisión igual se registra. Si el sitio no tiene coordenadas no hay incidencia
    y el primer escaneo fija. Deja al usuario en el historial del punto.
    """
    if revision.incidencia_ubicacion:
        return
    precision = revision.precision_m
    if precision is None or precision > settings.PRECISION_MAXIMA_M:
        return
    bloqueado = (
        PuntoControl.objects.de_empresa(punto.empresa_id)
        .select_for_update(no_key=True)
        .get(pk=punto.pk)
    )
    if bloqueado.latitud is not None and bloqueado.longitud is not None:
        return
    bloqueado.latitud = revision.latitud
    bloqueado.longitud = revision.longitud
    bloqueado.ubicacion_fijada_por = usuario
    bloqueado.ubicacion_fijada_en = timezone.now()
    bloqueado._history_user = usuario
    bloqueado._change_reason = MOTIVO_UBICACION_FIJADA
    bloqueado.save(
        update_fields=[
            "latitud",
            "longitud",
            "ubicacion_fijada_por",
            "ubicacion_fijada_en",
        ]
    )


def _guardar_fotos_y_productos(revision, fotos, aplicados, guardadas, usuario):
    """Guarda fotos y productos aplicados y descuenta el stock de cada uno."""
    for orden, archivo in enumerate(fotos):
        foto = Foto(revision=revision, imagen=archivo, orden=orden)
        try:
            foto.save()
        except ValidationError as error:
            raise ValidationError({"fotos": error.messages})
        guardadas.append(foto)
    for aplicado in aplicados:
        aplicado.revision = revision
        aplicado.save()
        aplicado.movimiento = registrar_consumo(
            aplicado.producto, aplicado.cantidad_base, usuario
        )
        aplicado.save(update_fields=["movimiento"])


def actualizar_vencimiento(punto):
    """Recalcula `proximo_vencimiento` del punto desde su revisión más reciente.

    Cuentan las revisiones de visitas abiertas o realizadas que cuentan como
    servicio; la fecha es la de la última más la `frecuencia_dias` del punto. Sin
    frecuencia o sin revisiones que cuenten no cambia nada, y una revisión anterior
    a la última no pisa la fecha. Bloquea el punto.
    """
    bloqueado = (
        PuntoControl.objects.de_empresa(punto.empresa_id)
        .select_for_update(no_key=True)
        .get(pk=punto.pk)
    )
    if not bloqueado.frecuencia_dias:
        return bloqueado
    ultima = (
        Revision.objects.de_empresa(bloqueado.empresa_id)
        .filter(
            punto=bloqueado,
            visita__estado__in=[Visita.Estado.ABIERTA, Visita.Estado.REALIZADA],
            visita__cuenta_como_servicio=True,
        )
        .aggregate(ultima=Max("realizada_en"))["ultima"]
    )
    if ultima is None:
        return bloqueado
    vence = timezone.localdate(ultima) + timedelta(days=bloqueado.frecuencia_dias)
    if bloqueado.proximo_vencimiento != vence:
        bloqueado.proximo_vencimiento = vence
        bloqueado.save(update_fields=["proximo_vencimiento"])
    return bloqueado


def _pk_enviado(enviado):
    """Id entero del servicio que mandó el cliente, o `None` si no es utilizable."""
    try:
        return int(getattr(enviado, "pk", enviado))
    except (TypeError, ValueError):
        return None


def _servicio_enviado(enviado, empresa_id):
    """Servicio activo de la empresa que mandó el cliente; si no, error."""
    pk = _pk_enviado(enviado)
    servicio = None
    if pk is not None:
        servicio = (
            TipoServicio.objects.de_empresa(empresa_id)
            .prefetch_related("campos")
            .filter(pk=pk, activo=True)
            .first()
        )
    if servicio is None:
        raise ValidationError({"servicio": "El servicio no existe o está de baja."})
    return servicio


def _servicio_de_la_revision(visita, punto, enviado=None):
    """Servicio, `fuera_de_turno` e `incidencia_servicio` de un punto en la visita.

    El servicio es el del ítem del turno para ese punto; si no hay ítem, el del
    punto (y la revisión queda fuera de turno). Sin ninguno de los dos, error. Si
    el cliente mandó otro (`enviado`), se usa ese, activo y de la empresa, con
    `incidencia_servicio`; vale también cuando el servidor no tenía servicio o el
    suyo estaba de baja.
    """
    servicio, en_turno = servicio_para_punto(visita=visita, punto=punto)
    if enviado is not None and (
        servicio is None or _pk_enviado(enviado) != servicio.pk
    ):
        return _servicio_enviado(enviado, punto.empresa_id), not en_turno, True
    if servicio is None:
        raise ValidationError({"qr_codigo": MENSAJE_SIN_SERVICIO})
    if not servicio.activo:
        raise ValidationError({"qr_codigo": MENSAJE_SERVICIO_DE_BAJA})
    return servicio, not en_turno, False


def _guardar_revision(
    *,
    visita,
    empleado,
    qr_codigo,
    cliente_uuid,
    realizada_en,
    latitud,
    longitud,
    precision_m,
    datos,
    productos_aplicados,
    fotos,
    observaciones,
    incidencia,
    incidencia_detalle,
    guardadas,
    servicio_enviado=None,
):
    """Valida y crea la revisión dentro de la transacción del llamador."""
    punto = _resolver_punto(visita.sitio_id, qr_codigo, visita.empresa_id)
    servicio, fuera_de_turno, incidencia_servicio = _servicio_de_la_revision(
        visita, punto, servicio_enviado
    )
    errores = _validar_coordenadas(latitud, longitud, obligatorias=True)
    esquema = servicio.esquema_planilla("punto")
    errores_evidencia, aplicados = _validar_evidencia(
        esquema, datos, productos_aplicados, visita.empresa_id
    )
    errores.update(errores_evidencia)
    if len(fotos) > MAX_FOTOS:
        errores["fotos"] = [f"Se permiten hasta {MAX_FOTOS} fotos por revisión."]
    ahora = timezone.now()
    try:
        validar_hora_cliente(realizada_en, "realizada_en")
    except ValidationError as error:
        errores.update(error.error_dict)
    if errores:
        raise ValidationError(errores)

    distancia, incidencia_ubicacion = verificar(punto, latitud, longitud)
    revision = Revision.objects.create(
        visita=visita,
        punto=punto,
        servicio=servicio,
        fuera_de_turno=fuera_de_turno,
        incidencia_servicio=incidencia_servicio,
        orden=visita.revisiones.count() + 1,
        realizada_en=realizada_en,
        recibida_en=ahora,
        cliente_uuid=cliente_uuid,
        latitud=latitud,
        longitud=longitud,
        precision_m=precision_m,
        distancia_m=distancia,
        incidencia_ubicacion=incidencia_ubicacion,
        datos=datos,
        esquema_planilla=esquema,
        observaciones=observaciones,
        incidencia=incidencia,
        incidencia_detalle=incidencia_detalle,
    )
    _guardar_fotos_y_productos(revision, fotos, aplicados, guardadas, empleado)
    _fijar_ubicacion_por_escaneo(punto, revision, empleado)
    actualizar_vencimiento(punto)
    return revision


def _duplicada(cliente_uuid, empresa_id):
    """Revisión de la empresa con ese `cliente_uuid` (la de otra empresa no cuenta)."""
    return (
        Revision.objects.de_empresa(empresa_id)
        .select_related("visita")
        .filter(cliente_uuid=cliente_uuid)
        .first()
    )


def registrar_revision(
    *,
    visita,
    empleado,
    qr_codigo,
    cliente_uuid,
    realizada_en,
    latitud,
    longitud,
    precision_m,
    datos,
    productos_aplicados,
    fotos,
    observaciones="",
    incidencia=False,
    incidencia_detalle="",
    servicio=None,
):
    """Registra el escaneo de un punto en una visita abierta y devuelve la `Revision`.

    `visita` es la instancia o el id; `qr_codigo` es el del punto (el servidor lo
    resuelve y exige que sea de un punto activo del sitio de la visita);
    `productos_aplicados` es una lista de dicts con `producto` como id; `fotos`, una
    lista de archivos. El servidor decide el servicio: el del ítem del turno para el
    punto o, fuera del turno, el del punto (sin servicio, error); si el cliente manda
    otro `servicio` (id), debe ser un servicio activo de la empresa y la revisión
    queda con `incidencia_servicio`. Valida
    coordenadas, de 0 a `MAX_FOTOS` fotos, planilla de ámbito `punto` del servicio y
    el atraso. Actualiza el vencimiento del punto (`actualizar_vencimiento`). Guarda
    la distancia al punto sin rechazar por ella.
    Si el punto no tiene ubicación, la primera revisión con precisión de a lo sumo
    `PRECISION_MAXIMA_M` y sin incidencia de ubicación la fija (ver
    `_fijar_ubicacion_por_escaneo`). Todo ocurre en una transacción (y sin fotos
    huérfanas si falla).
    Levanta `RevisionDuplicada` si el `cliente_uuid` ya existe y `ValidationError`
    con errores por campo; `VisitaNoEncontrada` si la visita no existe o es ajena y
    `VisitaNoAbierta` si no está abierta. No debe llamarse dentro de otro `atomic`.
    """
    if cliente_uuid is None:
        raise ValidationError({"cliente_uuid": "Este campo es obligatorio."})
    try:
        with _transaccion_con_archivos() as guardadas:
            existente = _duplicada(cliente_uuid, empleado.empresa_id)
            if existente:
                raise RevisionDuplicada(existente)
            try:
                # Se filtra por empleado al bloquear: la fila ajena no se toca.
                visita_bd = (
                    Visita.objects.de_empresa(empleado.empresa_id)
                    .select_for_update()
                    .get(pk=getattr(visita, "pk", visita), empleado=empleado)
                )
            except (Visita.DoesNotExist, TypeError, ValueError):
                raise VisitaNoEncontrada()
            if visita_bd.estado != Visita.Estado.ABIERTA:
                raise VisitaNoAbierta()
            return _guardar_revision(
                visita=visita_bd,
                empleado=empleado,
                qr_codigo=qr_codigo,
                cliente_uuid=cliente_uuid,
                realizada_en=realizada_en,
                latitud=latitud,
                longitud=longitud,
                precision_m=precision_m,
                datos=datos,
                productos_aplicados=productos_aplicados,
                fotos=fotos,
                observaciones=observaciones,
                incidencia=incidencia,
                incidencia_detalle=incidencia_detalle,
                guardadas=guardadas,
                servicio_enviado=servicio,
            )
    except IntegrityError:
        # Carrera: otro pedido con el mismo `cliente_uuid` ganó.
        existente = _duplicada(cliente_uuid, empleado.empresa_id)
        if existente:
            raise RevisionDuplicada(existente)
        raise


class NoRevisadoDuplicado(Exception):
    """El `cliente_uuid` ya fue registrado; `reporte` es el reporte existente."""

    def __init__(self, reporte):
        super().__init__("El reporte ya fue registrado.")
        self.reporte = reporte


def _no_revisado_duplicado(cliente_uuid, empresa_id):
    """Reporte de la empresa con ese `cliente_uuid` (el de otra empresa no cuenta)."""
    return (
        PuntoNoRevisado.objects.de_empresa(empresa_id)
        .select_related("visita")
        .filter(cliente_uuid=cliente_uuid)
        .first()
    )


def _punto_a_reportar(visita, punto):
    """Punto activo del sitio de la visita que aún no fue reportado en ella."""
    encontrado = (
        PuntoControl.objects.de_empresa(visita.empresa_id)
        .filter(pk=getattr(punto, "pk", punto), sitio_id=visita.sitio_id, activo=True)
        .first()
    )
    if encontrado is None:
        raise ValidationError({"punto": MENSAJE_PUNTO_NO_REPORTABLE})
    if visita.no_revisados.filter(punto=encontrado).exists():
        raise ValidationError({"punto": "El punto ya fue reportado en esta visita."})
    return encontrado


def registrar_no_revisado(
    *,
    empleado,
    visita_pk,
    punto,
    motivo,
    detalle="",
    latitud=None,
    longitud=None,
    precision_m=None,
    foto=None,
    cliente_uuid,
    reportado_en=None,
):
    """Registra que un punto de la visita abierta no se pudo revisar.

    `punto` es la instancia o el id. No crea una `Revision`, no actualiza el
    vencimiento ni cambia `cerrar_visita`. Bloquea en el orden Sitio -> Visita,
    acotando por la empresa y el empleado: una visita ajena o de otra empresa da
    `VisitaNoEncontrada`. La foto se reduce con `procesar_imagen`. Levanta
    `NoRevisadoDuplicado` si el `cliente_uuid` ya existe (también en la carrera),
    `VisitaNoAbierta` si la visita no está abierta y `ValidationError` si el punto
    no se puede reportar. `reportado_en` es la hora del teléfono (se valida con
    `validar_hora_cliente`); por defecto, ahora. No debe llamarse dentro de otro
    `atomic`.
    """
    if cliente_uuid is None:
        raise ValidationError({"cliente_uuid": "Este campo es obligatorio."})
    empresa_id = empleado.empresa_id
    try:
        with _transaccion_con_archivos() as guardadas:
            existente = _no_revisado_duplicado(cliente_uuid, empresa_id)
            if existente:
                raise NoRevisadoDuplicado(existente)
            if reportado_en is not None:
                validar_hora_cliente(reportado_en, "reportado_en")
            try:
                sitio_id = (
                    Visita.objects.de_empresa(empresa_id)
                    .filter(pk=visita_pk, empleado=empleado)
                    .values_list("sitio_id", flat=True)
                    .get()
                )
                Sitio.objects.de_empresa(empresa_id).select_for_update(
                    of=("self",)
                ).get(pk=sitio_id)
                visita = (
                    Visita.objects.de_empresa(empresa_id)
                    .select_for_update()
                    .get(pk=visita_pk, empleado=empleado)
                )
            except (Visita.DoesNotExist, TypeError, ValueError):
                raise VisitaNoEncontrada()
            if visita.estado != Visita.Estado.ABIERTA:
                raise VisitaNoAbierta()
            if (
                reportado_en is not None
                and visita.abierta_en
                and reportado_en < visita.abierta_en
            ):
                raise ValidationError(
                    {
                        "reportado_en": [
                            "La hora del reporte no puede ser anterior a la apertura."
                        ]
                    }
                )
            errores = _validar_coordenadas(latitud, longitud)
            if motivo not in PuntoNoRevisado.Motivo.values:
                errores["motivo"] = ["Motivo inválido."]
            if errores:
                raise ValidationError(errores)
            punto = _punto_a_reportar(visita, punto)
            distancia, _ = verificar(punto, latitud, longitud)
            reporte = PuntoNoRevisado(
                visita=visita,
                punto=punto,
                motivo=motivo,
                detalle=detalle,
                latitud=latitud,
                longitud=longitud,
                precision_m=precision_m,
                distancia_m=distancia,
                cliente_uuid=cliente_uuid,
                reportado_en=reportado_en or timezone.now(),
            )
            if foto:
                try:
                    contenido = procesar_imagen(foto)
                except ValidationError as error:
                    raise ValidationError({"foto": error.messages})
                reporte.foto.save("foto.jpg", contenido, save=False)
                # `_borrar_archivos` espera objetos con `imagen`.
                guardadas.append(SimpleNamespace(imagen=reporte.foto))
            reporte.save()
            return reporte
    except IntegrityError:
        # Carrera: otro pedido con el mismo `cliente_uuid` ganó.
        existente = _no_revisado_duplicado(cliente_uuid, empresa_id)
        if existente:
            raise NoRevisadoDuplicado(existente)
        raise


def condicion_incidencia_sin_revisar():
    """`Q` sobre `Visita`: incidencia pendiente de revisar.

    Cuenta la incidencia declarada y la visita realizada con puntos no revisados o
    con alguna revisión de un servicio distinto del asignado.
    """
    con_reportes = Exists(PuntoNoRevisado.objects.filter(visita=OuterRef("pk")))
    con_servicio = Exists(
        Revision.objects.filter(visita=OuterRef("pk"), incidencia_servicio=True)
    )
    realizada = Q(estado=Visita.Estado.REALIZADA)
    return Q(incidencia_revisada_en__isnull=True) & (
        Q(incidencia=True)
        | (realizada & Q(con_reportes))
        | (realizada & Q(con_servicio))
    )


def _cerrar_sin_revisiones(visita):
    """Cierre por sistema de una visita sin revisiones.

    Si venía asignada vuelve a pendiente; si no, queda cancelada.
    """
    if visita.asignada_por_id:
        visita.estado = Visita.Estado.PENDIENTE
        visita.abierta_en = None
        visita.abierta_recibida_en = None
        visita.cierre = ""
    else:
        visita.estado = Visita.Estado.CANCELADA
        visita.cierre = Visita.Cierre.SISTEMA
    visita.full_clean()
    visita.save()
    return visita


def _errores_planilla_visita(esquemas, datos):
    """Mensajes de la planilla de visita por servicio: `datos = {slug: {clave: valor}}`.

    Valida cada servicio presente con su esquema y rechaza los servicios ajenos.
    """
    if not isinstance(datos, dict):
        return ["Debe ser un objeto con la planilla de cada servicio."]
    errores = []
    for slug, esquema in esquemas.items():
        errores += [
            f"{slug}: {m}" for m in _errores_planilla(esquema, datos.get(slug, {}))
        ]
    errores += [
        f"{slug}: El servicio no figura en la visita."
        for slug in datos
        if slug not in esquemas
    ]
    return errores


def cerrar_visita(
    visita,
    *,
    quien,
    cierre,
    datos=None,
    observaciones=None,
    incidencia=None,
    incidencia_detalle=None,
    cerrada_en=None,
):
    """Cierra la visita abierta; devuelve la copia cerrada.

    La instancia recibida no se modifica: todo ocurre sobre una copia bloqueada.
    Exige al menos una revisión o un reporte de punto no revisado; sin ninguno de
    los dos, el cierre por sistema aplica `_cerrar_sin_revisiones`. Con solo
    reportes la visita queda realizada y no toca ningún vencimiento. `datos` es la
    planilla de ámbito `visita` (se valida, salvo en el cierre por sistema). `datos`
    va por servicio, `{slug: {clave: valor}}`, con un servicio por cada uno de los
    ítems y las revisiones de la visita; el
    esquema de cada uno queda copiado en `esquema_planilla`. `cerrada_en` es la hora
    de cierre: por defecto ahora, o la de la última revisión en el cierre por
    sistema. Bloquea en el orden Sitio -> Visita. Cerrar de nuevo por el mismo
    empleado es idempotente; si la cerró el sistema o un administrador, levanta
    `VisitaYaCerrada`. El empleado sobre una visita pendiente o cancelada recibe
    `VisitaNoAbierta`. El cierre del empleado guarda `cerrada_recibida_en` (hora del
    servidor); los demás cierres la dejan nula. Si el empleado manda `cerrada_en`,
    se valida con `validar_hora_cliente` y no puede ser anterior a `abierta_en`.
    """
    if cierre not in Visita.Cierre.values:
        raise ValidationError({"cierre": "Tipo de cierre inválido."})
    with transaction.atomic():
        # El sitio se lee sin bloquear solo para saber cuál bloquear primero;
        # el estado se evalúa recién con la visita bloqueada.
        empresa_id = visita.empresa_id
        sitio_id = (
            Visita.objects.de_empresa(empresa_id)
            .values_list("sitio_id", flat=True)
            .get(pk=visita.pk)
        )
        Sitio.objects.de_empresa(empresa_id).select_for_update(of=("self",)).get(
            pk=sitio_id
        )
        visita_bd = (
            Visita.objects.de_empresa(empresa_id).select_for_update().get(pk=visita.pk)
        )

        if cierre == Visita.Cierre.EMPLEADO and (
            quien is None or quien.pk != visita_bd.empleado_id
        ):
            raise ValidationError("Solo el empleado de la visita puede cerrarla.")
        if cierre == Visita.Cierre.ADMINISTRADOR and not (
            quien is not None and quien.es_administrador
        ):
            raise ValidationError("Solo un administrador puede cerrar de este modo.")
        if visita_bd.estado == Visita.Estado.REALIZADA:
            if cierre == visita_bd.cierre == Visita.Cierre.EMPLEADO:
                return visita_bd
            raise VisitaYaCerrada()
        if visita_bd.estado != Visita.Estado.ABIERTA:
            mensaje = "Solo se puede cerrar una visita abierta."
            if cierre == Visita.Cierre.EMPLEADO:
                raise VisitaNoAbierta(mensaje, campo=None)
            raise ValidationError(mensaje)
        revisiones = visita_bd.revisiones.all()
        if cierre != Visita.Cierre.ADMINISTRADOR:
            # Cuentan las recibidas durante esta jornada (hora del servidor, no la
            # del teléfono): la evidencia heredada de una migración no.
            revisiones = revisiones.filter(recibida_en__gte=visita_bd.abierta_en)
        ultima = revisiones.order_by("-realizada_en", "-id").first()
        ultimo_reporte = None
        if ultima is None:
            # Sin revisiones, los reportes de puntos no revisados bastan para cerrar.
            ultimo_reporte = visita_bd.no_revisados.order_by(
                "-reportado_en", "-id"
            ).first()
            if ultimo_reporte is None:
                if cierre != Visita.Cierre.SISTEMA:
                    raise ValidationError(
                        "La visita necesita al menos una revisión o un punto "
                        "reportado como no revisado."
                    )
                return _cerrar_sin_revisiones(visita_bd)
        if (
            visita_bd.origen == Visita.Origen.MANUAL
            and not (visita_bd.motivo_manual or "").strip()
        ):
            raise ValidationError("Una visita manual exige el motivo.")

        if cerrada_en is None:
            sistema = cierre == Visita.Cierre.SISTEMA
            if not sistema:
                cerrada_en = timezone.now()
            else:
                cerrada_en = (
                    ultima.realizada_en if ultima else ultimo_reporte.reportado_en
                )
        elif cierre == Visita.Cierre.EMPLEADO:
            validar_hora_cliente(cerrada_en, "cerrada_en")
            if visita_bd.abierta_en and cerrada_en < visita_bd.abierta_en:
                raise ValidationError(
                    {
                        "cerrada_en": [
                            "La hora de cierre no puede ser anterior a la apertura."
                        ]
                    }
                )
        if cerrada_en > timezone.now() + TOLERANCIA_FUTURO:
            raise ValidationError("La fecha de cierre no puede ser futura.")
        servicios = (
            TipoServicio.objects.de_empresa(empresa_id)
            .filter(Q(items_turno__visita=visita_bd) | Q(revisiones__visita=visita_bd))
            .prefetch_related("campos")
            .distinct()
            .order_by("pk")
        )
        esquema = {s.slug: s.esquema_planilla("visita") for s in servicios}
        if datos is not None:
            visita_bd.datos = datos
        if cierre != Visita.Cierre.SISTEMA:
            errores = _errores_planilla_visita(esquema, visita_bd.datos)
            if errores:
                raise ValidationError({"datos": errores})
        for campo, valor in (
            ("observaciones", observaciones),
            ("incidencia", incidencia),
            ("incidencia_detalle", incidencia_detalle),
        ):
            if valor is not None:
                setattr(visita_bd, campo, valor)
        visita_bd.esquema_planilla = esquema
        visita_bd.estado = Visita.Estado.REALIZADA
        visita_bd.cierre = cierre
        visita_bd.cerrada_en = cerrada_en
        if cierre == Visita.Cierre.EMPLEADO:
            visita_bd.cerrada_recibida_en = timezone.now()
        visita_bd.full_clean()
        visita_bd.save()
    return visita_bd


def registrar_visita_manual(
    *,
    sitio,
    empleado,
    administrador,
    motivo,
    realizada_en,
    items,
    datos,
    productos_aplicados,
    fotos,
    pendiente=None,
    confirmar_atraso=False,
    datos_visita=None,
    observaciones="",
    incidencia=False,
    incidencia_detalle="",
):
    """Registra una visita cargada a mano por un administrador y la devuelve.

    `items` es una lista de `(punto, servicio)`: crea una revisión por cada uno, con
    ese servicio. `datos` y `datos_visita` son las planillas por servicio,
    `{slug: {clave: valor}}`, de ámbito `punto` (la misma para todas las revisiones
    del servicio) y `visita`. Las fotos y los productos quedan en la revisión del
    primer punto por `orden`. Cierra la visita con `cierre=administrador` y
    `cerrada_en` igual a `realizada_en`. Crea la visita, con un ítem por cada
    `(punto, servicio)`, o completa `pendiente` (sin revisiones previas), con
    `origen=manual`: una revisión de un punto sin ítem en la pendiente queda fuera de
    turno. Una carga con más de `ATRASO_MAXIMO_HORAS` de atraso exige
    `confirmar_atraso` y deja la confirmación en el historial; una hora más de
    `TOLERANCIA_FUTURO` posterior a la actual se rechaza, como una fecha anterior al
    alta del sitio (al minuto, la resolución del formulario) y un sitio o cliente de
    baja. Si la pendiente era de otro empleado, la reasignación queda en el
    historial. Actualiza el vencimiento de cada punto. Todo ocurre en una
    transacción; si algo falla no queda nada, tampoco los archivos. Levanta
    `ValidationError` con errores por campo. No debe llamarse dentro de otro
    `atomic`.
    """
    if realizada_en > timezone.now() + TOLERANCIA_FUTURO:
        raise ValidationError(
            {
                "realizada_en": (
                    "La fecha y hora de la visita no puede ser posterior a la "
                    "hora actual."
                )
            }
        )
    with _transaccion_con_archivos() as guardadas:
        errores = {}
        if not (motivo or "").strip():
            errores["motivo"] = ["El motivo de la carga manual es obligatorio."]
        if not (sitio.activo and sitio.cliente.activo):
            errores["sitio"] = ["El sitio o el cliente están de baja."]
        if realizada_en < sitio.creado.replace(second=0, microsecond=0):
            errores["realizada_en"] = [
                "La fecha no puede ser anterior al alta del sitio."
            ]
        if not (empleado.is_active and empleado.es_empleado):
            errores["empleado"] = ["Debe ser un empleado activo."]
        elif empleado.empresa_id != sitio.empresa_id:
            errores["empleado"] = ["El empleado debe ser de la empresa del sitio."]
        horas = settings.ATRASO_MAXIMO_HORAS
        atrasada = realizada_en < timezone.now() - timedelta(hours=horas)
        if atrasada and not confirmar_atraso:
            errores["confirmar_atraso"] = [
                f"La visita tiene más de {horas} horas de atraso: "
                "confirme la carga para continuar."
            ]
        items = sorted(items, key=lambda i: (i[0].orden, i[0].pk))
        errores.update(_errores_de_items(sitio.pk, items, sitio.empresa_id))
        servicios = {}
        for _, servicio in items:
            if servicio is not None and servicio.empresa_id == sitio.empresa_id:
                servicios[servicio.slug] = _servicio_con_campos(
                    servicio.pk, sitio.empresa_id
                )
        datos = datos or {}
        esquemas_punto = {s: v.esquema_planilla("punto") for s, v in servicios.items()}
        errores_datos = _errores_planilla_visita(esquemas_punto, datos)
        if errores_datos:
            errores["datos"] = errores_datos
        errores_productos, aplicados = _validar_productos(
            productos_aplicados, sitio.empresa_id
        )
        errores.update(errores_productos)
        if len(fotos) > MAX_FOTOS:
            errores["fotos"] = [f"Se permiten hasta {MAX_FOTOS} fotos por revisión."]
        visita = None
        if pendiente is not None:
            # Orden Sitio -> Visita, como en `abrir_visita` y `cerrar_visita`.
            Sitio.objects.de_empresa(sitio.empresa_id).select_for_update(
                of=("self",)
            ).get(pk=sitio.pk)
            visita = (
                Visita.objects.de_empresa(sitio.empresa_id)
                .select_for_update()
                .get(pk=pendiente.pk)
            )
            if visita.sitio_id != sitio.pk or visita.estado != Visita.Estado.PENDIENTE:
                errores["pendiente"] = ["La visita no es una pendiente del sitio."]
            elif visita.revisiones.exists():
                errores["pendiente"] = [
                    "La pendiente ya tiene revisiones: no se completa a mano."
                ]
        if errores:
            raise ValidationError(errores)

        if visita is None:
            visita = Visita(sitio=sitio)
        if visita.empleado_id not in (None, empleado.pk):
            visita._change_reason = (
                f"Reasignada en carga manual por {administrador.get_username()}"
            )
        visita.empleado = empleado
        visita.origen = Visita.Origen.MANUAL
        visita.motivo_manual = motivo.strip()
        visita.asignada_por = administrador
        visita.cuenta_como_servicio = True
        visita.estado = Visita.Estado.ABIERTA
        visita.abierta_en = realizada_en
        visita.save()
        if pendiente is None:
            ItemTurno.objects.bulk_create(
                ItemTurno(
                    visita=visita,
                    punto=punto,
                    servicio=servicio,
                    empresa_id=visita.empresa_id,
                )
                for punto, servicio in items
            )
        con_item = set(visita.items.values_list("punto_id", flat=True))

        ahora = timezone.now()
        for orden, (punto, servicio) in enumerate(items, start=1):
            revision = Revision.objects.create(
                visita=visita,
                punto=punto,
                servicio=servicio,
                fuera_de_turno=punto.pk not in con_item,
                orden=orden,
                realizada_en=realizada_en,
                recibida_en=ahora,
                datos=datos.get(servicio.slug, {}),
                esquema_planilla=esquemas_punto[servicio.slug],
            )
            if orden == 1:
                _guardar_fotos_y_productos(
                    revision, fotos, aplicados, guardadas, administrador
                )
        resultado = cerrar_visita(
            visita,
            quien=administrador,
            cierre=Visita.Cierre.ADMINISTRADOR,
            datos=datos_visita,
            observaciones=observaciones,
            incidencia=incidencia,
            incidencia_detalle=incidencia_detalle,
            cerrada_en=realizada_en,
        )
        for punto, _ in items:
            actualizar_vencimiento(punto)
        if atrasada:
            update_change_reason(
                resultado,
                f"Carga manual atrasada confirmada por {administrador.get_username()}",
            )
    return resultado


def marcar_incidencia_revisada(visita, administrador):
    """Registra quién y cuándo revisó la incidencia de una visita; devuelve la copia.

    Vale para la incidencia declarada y para la de ubicación (en la visita o en
    alguna de sus revisiones), para los puntos no revisados y para las revisiones con
    un servicio distinto del asignado: comparten la marca de revisión. Bloquea la
    fila para que dos administradores no la revisen a la vez.
    """
    with transaction.atomic():
        visita = (
            Visita.objects.de_empresa(visita.empresa_id)
            .select_for_update()
            .get(pk=visita.pk)
        )
        if visita.estado != Visita.Estado.REALIZADA:
            raise ValidationError("La incidencia se revisa con la visita cerrada.")
        con_ubicacion = (
            visita.incidencia_ubicacion
            or visita.revisiones.filter(incidencia_ubicacion=True).exists()
        )
        con_reportes = visita.no_revisados.exists()
        con_servicio = visita.revisiones.filter(incidencia_servicio=True).exists()
        if not (visita.incidencia or con_ubicacion or con_reportes or con_servicio):
            raise ValidationError("La visita no tiene incidencia para revisar.")
        if visita.incidencia_revisada_en is not None:
            raise ValidationError("La incidencia ya fue revisada.")
        visita.incidencia_revisada_por = administrador
        visita.incidencia_revisada_en = timezone.now()
        visita.save(
            update_fields=[
                "incidencia_revisada_por",
                "incidencia_revisada_en",
                "actualizado",
            ]
        )
    return visita
