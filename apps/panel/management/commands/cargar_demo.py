"""Carga datos de demostración: clientes, sitios, plano, puntos y 90 días de visitas."""

import logging
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.demo import exigir_entorno_demo, limpiar_datos_demo
from apps.panel.demo_datos import (
    CADENCIA_HISTORIA_DIAS,
    CASTELLI,
    CHASCOMUS,
    CLAVE_DEMO,
    CLIENTES,
    DESFASES,
    DIAS_DE_HISTORIA,
    FRECUENCIAS,
    INCIDENCIAS_UBICACION,
    MARCA_DEMO,
    PRODUCTOS,
    SITIO_CON_ABIERTO,
    SITIO_CON_PENDIENTE,
    SITIOS,
    SUFIJO_PRODUCTO,
    TELEFONO_FICTICIO,
    TIPOS,
    VENCIMIENTOS,
)
from apps.panel.demo_historia import GeneradorHistoria
from apps.panel.demo_imagenes import plano_esquematico, posicion_en_plano
from apps.productos.models import Producto
from apps.productos.services import registrar_ingreso
from apps.servicios.models import TipoServicio
from apps.sitios import services as servicios_sitio
from apps.sitios.models import Plano, PuntoControl, Sitio

logger = logging.getLogger(__name__)

# Los sitios se corren unos cientos de metros dentro de su localidad.
PASO_SITIO = Decimal("0.004")
PASO_PUNTO = Decimal("0.0003")


class Command(BaseCommand):
    help = (
        "Carga datos de demostración (4 clientes, 6 sitios con sus puntos, un plano, "
        "servicios y vencimientos por punto, turnos pendientes, abiertos y realizados "
        "con unos 90 días de revisiones, fotos y productos). "
        "Borra y recrea solo los datos marcados como demo (notas que empiezan con "
        "'[demo]', productos con sufijo ' (demo)' y el formato viejo 'Cliente Demo "
        "N'); no toca nada sin marca. Regenera los QR de los puntos demo. Solo corre "
        "con DEBUG, DJANGO_ENV=development y SQLite (sin DATABASE_URL). Crea "
        "demo-admin (administrador) y demo-empleado (empleado) con la contraseña "
        f"{CLAVE_DEMO}: existen solo en desarrollo."
    )

    def handle(self, *args, **opciones):
        exigir_entorno_demo("cargar_demo")
        # La transacción revierte la base, no los archivos ya escritos.
        self._archivos = []
        try:
            with transaction.atomic():
                administrador, empleado = self._usuarios()
                borrados = limpiar_datos_demo()
                if not TipoServicio.objects.exists():
                    call_command("loaddata", "tipos_servicio", verbosity=0)
                sitios = self._crear_sitios()
                self._crear_historia(sitios, administrador, empleado)
        except Exception:
            self._borrar_archivos()
            raise
        self.stdout.write(f"Demo lista ({borrados} sitios anteriores reemplazados).")

    def _borrar_archivos(self):
        """Borra del almacenamiento los archivos de una corrida fallida."""
        for almacenamiento, nombre in self._archivos:
            try:
                almacenamiento.delete(nombre)
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo borrar un archivo de la demo.")

    def _usuarios(self):
        """Crea los usuarios demo y devuelve (administrador, empleado).

        Uno que ya existía con otro rol u otra contraseña no se modifica: se avisa
        por stderr y la contraseña solo se informa de los recién creados.
        """
        usuarios = []
        for nombre, rol in (
            ("demo-admin", User.Rol.ADMINISTRADOR),
            ("demo-empleado", User.Rol.EMPLEADO),
        ):
            usuario, creado = User.objects.get_or_create(
                username=nombre, defaults={"rol": rol}
            )
            if creado:
                usuario.set_password(CLAVE_DEMO)
                usuario.save()
                self.stdout.write(f"Usuario creado: {nombre}, contraseña {CLAVE_DEMO}.")
            elif usuario.rol != rol or not usuario.check_password(CLAVE_DEMO):
                self.stderr.write(
                    f"El usuario {nombre} ya existía con otro rol u otra "
                    "contraseña: no se modificó."
                )
            usuarios.append(usuario)
        return tuple(usuarios)

    def _crear_sitios(self):
        """Clientes de la Carta, sus sitios y puntos; el primer sitio lleva plano."""
        clientes = {
            razon: Cliente.objects.create(razon_social=razon, notas=MARCA_DEMO)
            for razon in CLIENTES
        }
        sitios = []
        for numero, datos in enumerate(SITIOS):
            razon, nombre, direccion, localidad, sector, puntos = datos
            lat, lng = CASTELLI if localidad == "Castelli" else CHASCOMUS
            desvio = PASO_SITIO * (numero // 2)
            sitio = Sitio.objects.create(
                cliente=clientes[razon],
                nombre=nombre,
                direccion=direccion,
                localidad=localidad,
                sector=sector,
                latitud=lat + desvio,
                longitud=lng - desvio,
                contacto_en_sitio="Encargado (demostración)",
                telefono_en_sitio=TELEFONO_FICTICIO,
                horario_acceso="Lunes a viernes de 8 a 17",
                notas=MARCA_DEMO,
            )
            self._crear_puntos(sitio, puntos, con_plano=numero == 0)
            sitios.append(sitio)
        return sitios

    def _crear_puntos(self, sitio, nombres, con_plano):
        """Puntos del sitio, con su ubicación y, si lleva plano, sus marcadores."""
        puntos = [sitio.puntos.get(nombre="General")]
        for orden, nombre in enumerate(nombres, start=1):
            puntos.append(sitio.puntos.create(nombre=nombre, orden=orden))
        plano = None
        if con_plano:
            plano = Plano(
                sitio=sitio,
                nombre="Planta general",
                imagen=plano_esquematico([punto.nombre for punto in puntos]),
            )
            plano.save()
            self._archivos.append((plano.imagen.storage, plano.imagen.name))
        for numero, punto in enumerate(puntos):
            # Cada punto, apenas corrido del anterior para que el mapa los distinga.
            servicios_sitio.fijar_ubicacion(
                punto,
                sitio.latitud + PASO_PUNTO * (numero % 3),
                sitio.longitud + PASO_PUNTO * (numero // 3),
            )
            if plano is not None:
                x, y = posicion_en_plano(numero, len(puntos))
                servicios_sitio.ubicar_en_plano(punto, plano, x, y)

    def _crear_productos(self, administrador):
        """Productos demo, cada uno con su ingreso inicial de stock en envases."""
        productos = []
        for datos in PRODUCTOS:
            nombre, principio, presentacion, unidad_dosis, registro = datos[:5]
            base, contenido, modo, envases = datos[5:]
            producto = Producto.objects.create(
                nombre_comercial=f"{nombre}{SUFIJO_PRODUCTO}",
                principio_activo=principio,
                presentacion=presentacion,
                unidad_dosis_por_defecto=unidad_dosis,
                registro=registro,
                unidad_base=base,
                contenido_por_envase=contenido,
                modo_unidad=modo,
            )
            registrar_ingreso(producto, envases, True, administrador, "Stock inicial")
            productos.append(producto)
        return productos

    def _tipos(self):
        """Tipos de servicio reales por slug; los que faltan se crean sin pisar."""
        return [
            TipoServicio.objects.get_or_create(slug=slug, defaults={"nombre": nombre})[
                0
            ]
            for slug, nombre in TIPOS.items()
        ]

    def _programar_puntos(self, numero, puntos, tipos):
        """Servicio, frecuencia y vencimiento de cada punto: de todo un poco.

        Devuelve los ítems `(punto, servicio)`. Los puntos se actualizan por
        `update()` para no pasar por el recálculo del vencimiento.
        """
        hoy = timezone.localdate()
        items = []
        for indice, punto in enumerate(puntos):
            segundo = (numero >= 4) != (indice % 3 == 2)
            servicio = tipos[1 if segundo else 0]
            dias = VENCIMIENTOS[(numero + indice) % len(VENCIMIENTOS)]
            programado = dias is not None
            PuntoControl.objects.filter(pk=punto.pk).update(
                servicio=servicio,
                frecuencia_dias=FRECUENCIAS[indice % 3] if programado else None,
                proximo_vencimiento=hoy + timedelta(days=dias) if programado else None,
            )
            punto.servicio = servicio
            items.append((punto, servicio))
        return items

    def _crear_historia(self, sitios, administrador, empleado):
        """Servicios por punto, jornadas quincenales de unos 90 días y turnos."""
        tipos = self._tipos()
        generador = GeneradorHistoria(
            empleado,
            administrador,
            self._crear_productos(administrador),
            self._archivos,
        )
        hoy = timezone.localdate()
        antiguo = timezone.now() - timedelta(days=DIAS_DE_HISTORIA + 3)
        for numero, sitio in enumerate(sitios):
            puntos = list(sitio.puntos.filter(activo=True))
            items = self._programar_puntos(numero, puntos, tipos)
            dias = range(DESFASES[numero], DIAS_DE_HISTORIA, CADENCIA_HISTORIA_DIAS)
            for jornada, atras in enumerate(dias):
                lejanos = INCIDENCIAS_UBICACION.get((numero, jornada), set())
                generador.jornada(sitio, items, hoy - timedelta(days=atras), lejanos)
            if numero == SITIO_CON_PENDIENTE:
                generador.pendiente(sitio, items, hoy + timedelta(days=3))
            if numero == SITIO_CON_ABIERTO:
                generador.abierto(sitio, items, hoy)
        Cliente.objects.filter(notas=MARCA_DEMO).update(creado=antiguo)
        Sitio.objects.filter(notas=MARCA_DEMO).update(creado=antiguo)
