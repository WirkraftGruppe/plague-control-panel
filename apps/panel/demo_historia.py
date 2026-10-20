"""Historia de visitas de la demostración: jornadas quincenales de unos 90 días.

Los servicios de visitas rechazan fechas viejas, así que las jornadas se crean
por el ORM con `full_clean()` y las fechas de creación se retrotraen con
`.update()`.
"""

import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from apps.panel.demo_datos import ESQUEMA_PUNTO
from apps.panel.demo_imagenes import foto_de_demostracion
from apps.productos.services import registrar_consumo
from apps.productos.unidades import convertir, unidades_permitidas
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita
from apps.visitas.ubicacion import verificar

METROS_POR_GRADO = 111_000
CENTESIMAS = Decimal("0.000001")


def datos_de_planilla(esquema, semilla, fecha):
    """Valores válidos para cada campo del esquema, variados según la semilla."""
    datos = {}
    for campo in esquema:
        opciones = campo.get("opciones") or []
        tipo = campo["tipo"]
        if tipo == "texto":
            valor = "Sin novedades"
        elif tipo == "numero":
            valor = semilla % 5 + 1
        elif tipo == "booleano":
            valor = semilla % 4 != 0
        elif tipo == "fecha":
            valor = fecha.isoformat()
        elif tipo == "opcion_multiple":
            valor = [opciones[semilla % len(opciones)]] if opciones else []
        else:
            valor = opciones[semilla % len(opciones)] if opciones else None
        datos[campo["clave"]] = valor
    return datos


def _coordenada(valor, desvio_m, sentido):
    """Coordenada corrida unos `desvio_m` metros hacia `sentido` (1 o -1)."""
    return (valor + Decimal(desvio_m * sentido) / METROS_POR_GRADO).quantize(CENTESIMAS)


class GeneradorHistoria:
    """Crea las jornadas realizadas y la visita pendiente de cada proyecto."""

    def __init__(self, empleado, administrador, productos, archivos):
        self.empleado = empleado
        self.administrador = administrador
        self.productos = productos
        self.archivos = archivos  # (almacenamiento, nombre) de cada foto escrita
        self.semilla = 0

    def _fotos(self, revision, cantidad):
        for orden in range(cantidad):
            self.semilla += 1
            foto = Foto(
                revision=revision,
                imagen=foto_de_demostracion(self.semilla),
                tomada_en=revision.realizada_en,
                orden=orden,
            )
            foto.save()
            self.archivos.append((foto.imagen.storage, foto.imagen.name))

    def _producto_aplicado(self, revision, numero):
        producto = self.productos[numero % len(self.productos)]
        permitidas = unidades_permitidas(producto)
        unidad = permitidas[numero % len(permitidas)]
        cantidad = Decimal(numero % 4 + 1)
        aplicado = ProductoAplicado(
            revision=revision,
            producto=producto,
            lote=f"LOTE-DEMO-{numero % 7 + 1:03d}",
            dosis=Decimal("2.500"),
            unidad_dosis=producto.unidad_dosis_por_defecto or "g",
            unidad=unidad,
            cantidad=cantidad,
            cantidad_base=convertir(cantidad, unidad, producto.unidad_base),
        )
        aplicado.full_clean(exclude=["movimiento"])
        aplicado.save()
        aplicado.movimiento = registrar_consumo(
            producto, aplicado.cantidad_base, self.empleado
        )
        aplicado.save(update_fields=["movimiento"])

    def _revision(self, visita, punto, esquema, orden, momento, lejos, numero):
        """Revisión de un punto: cerca de él o, con `lejos`, a más del máximo."""
        desvio = settings.DISTANCIA_MAXIMA_M * 2 if lejos else 12
        latitud = _coordenada(punto.latitud, desvio, 1)
        longitud = _coordenada(punto.longitud, desvio // 2, -1)
        distancia, incidencia_ubicacion = verificar(punto, latitud, longitud)
        con_plaga = numero % 17 == 0
        revision = Revision(
            visita=visita,
            punto=punto,
            orden=orden,
            realizada_en=momento,
            recibida_en=momento + timedelta(minutes=1),
            cliente_uuid=uuid.uuid4(),
            latitud=latitud,
            longitud=longitud,
            precision_m=Decimal("8.0"),
            distancia_m=distancia,
            incidencia_ubicacion=incidencia_ubicacion,
            esquema_planilla=esquema,
            datos=datos_de_planilla(esquema, numero, momento.date()),
            observaciones="Revisión de demostración.",
            incidencia=con_plaga,
            incidencia_detalle="Actividad en la zona; se reforzó el control."
            if con_plaga
            else "",
        )
        revision.full_clean()
        revision.save()
        self._fotos(revision, 2 if numero % 5 == 0 else 1)
        if numero % 3 == 0:
            # `numero` es múltiplo de 3: se divide para recorrer todos los productos.
            self._producto_aplicado(revision, numero // 3)
        return revision

    def jornada(self, proyecto, puntos, fecha, lejanos):
        """Jornada realizada ese día, con una revisión por punto activo."""
        inicio = timezone.make_aware(datetime.combine(fecha, time(9, 0)))
        tipo = proyecto.tipo_servicio
        esquema_visita = tipo.esquema_planilla("visita")
        esquema_punto = tipo.esquema_planilla("punto") or ESQUEMA_PUNTO
        visita = Visita(
            proyecto=proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.REALIZADA,
            cierre=Visita.Cierre.EMPLEADO,
            abierta_en=inicio,
            cerrada_en=inicio + timedelta(minutes=8 * len(puntos) + 5),
            datos=datos_de_planilla(esquema_visita, fecha.toordinal(), fecha),
            esquema_planilla=esquema_visita,
            precision_m=Decimal("8.00"),
            incidencia_ubicacion=bool(lejanos),
        )
        visita.full_clean()
        visita.save()
        distancias = []
        for orden, punto in enumerate(puntos, start=1):
            self.semilla += 1
            momento = inicio + timedelta(minutes=8 * orden)
            revision = self._revision(
                visita,
                punto,
                esquema_punto,
                orden,
                momento,
                orden - 1 in lejanos,
                self.semilla,
            )
            distancias.append(revision.distancia_m or 0)
        # La distancia de la visita es la de su revisión más lejana.
        visita.distancia_m = max(distancias)
        if lejanos:
            visita.observaciones = "Revisión fuera de la ubicación del punto."
        Visita.objects.filter(pk=visita.pk).update(
            distancia_m=visita.distancia_m,
            observaciones=visita.observaciones,
            creado=visita.abierta_en,
            actualizado=visita.cerrada_en,
        )
        return visita

    def pendiente(self, proyecto, fecha):
        """Visita programada para `fecha`, asignada por el administrador."""
        visita = Visita(
            proyecto=proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.PENDIENTE,
            programada_para=fecha,
            asignada_por=self.administrador,
        )
        visita.full_clean()
        visita.save()
        return visita
