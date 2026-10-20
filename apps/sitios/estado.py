"""Estado de revisión de un punto de control respecto de los proyectos de su sitio."""

import datetime
from collections import defaultdict
from typing import NamedTuple

from django.db import models
from django.db.models import Max
from django.utils import timezone

from apps.proyectos.models import UMBRAL_PROXIMA_DIAS, Proyecto
from apps.visitas.models import Revision, Visita

from .models import PuntoControl


class EstadoPunto(models.TextChoices):
    AL_DIA = "al_dia", "Al día"
    PROXIMA = "proxima", "Próxima"
    VENCIDA = "vencida", "Vencida"
    SIN_REVISAR = "sin_revisar", "Sin revisar"


GRAVEDAD_PUNTO = {
    EstadoPunto.AL_DIA: 0,
    EstadoPunto.PROXIMA: 1,
    EstadoPunto.SIN_REVISAR: 2,
    EstadoPunto.VENCIDA: 3,
}

# Las revisiones de visitas canceladas no cuentan.
_VISITAS_QUE_CUENTAN = [Visita.Estado.ABIERTA, Visita.Estado.REALIZADA]


def peor_estado_punto(estados):
    """Devuelve el más grave de los estados; sin estados, ``al_dia``."""
    return max(estados, key=lambda e: GRAVEDAD_PUNTO[e], default=EstadoPunto.AL_DIA)


def _estado(ultima, frecuencia_dias, hoy):
    """Estado de un punto según su última revisión y la frecuencia del proyecto."""
    if ultima is None:
        return EstadoPunto.SIN_REVISAR
    if not frecuencia_dias:
        return EstadoPunto.AL_DIA
    vence = timezone.localtime(ultima).date() + datetime.timedelta(days=frecuencia_dias)
    if vence < hoy:
        return EstadoPunto.VENCIDA
    if vence <= hoy + datetime.timedelta(days=UMBRAL_PROXIMA_DIAS):
        return EstadoPunto.PROXIMA
    return EstadoPunto.AL_DIA


def estado_revision(punto, proyecto):
    """Estado del punto para un proyecto, a partir de su última revisión."""
    ultima = Revision.objects.filter(
        punto=punto,
        visita__proyecto=proyecto,
        visita__estado__in=_VISITAS_QUE_CUENTAN,
        visita__cuenta_como_servicio=True,
    ).aggregate(ultima=Max("realizada_en"))["ultima"]
    return _estado(ultima, proyecto.frecuencia_dias, timezone.localdate())


def estados_de_puntos(puntos):
    """Estado de cada punto: el peor entre los proyectos activos de su sitio.

    Devuelve ``{id_del_punto: estado}`` con dos consultas, sin importar cuántos
    puntos haya. Un sitio sin proyectos activos queda ``al_dia``.
    """
    puntos = list(puntos)
    if not puntos:
        return {}
    hoy = timezone.localdate()
    proyectos = defaultdict(list)
    for pk, sitio_id, frecuencia in Proyecto.objects.filter(
        sitio_id__in={p.sitio_id for p in puntos}, estado=Proyecto.Estado.ACTIVO
    ).values_list("pk", "sitio_id", "frecuencia_dias"):
        proyectos[sitio_id].append((pk, frecuencia))
    ultimas = {
        (fila["punto_id"], fila["visita__proyecto_id"]): fila["ultima"]
        for fila in Revision.objects.filter(
            punto_id__in=[p.pk for p in puntos],
            visita__proyecto_id__in=[
                pk for lista in proyectos.values() for pk, _ in lista
            ],
            visita__estado__in=_VISITAS_QUE_CUENTAN,
            visita__cuenta_como_servicio=True,
        )
        .values("punto_id", "visita__proyecto_id")
        .annotate(ultima=Max("realizada_en"))
    }
    return {
        punto.pk: peor_estado_punto(
            _estado(ultimas.get((punto.pk, proyecto_id)), frecuencia, hoy)
            for proyecto_id, frecuencia in proyectos[punto.sitio_id]
        )
        for punto in puntos
    }


class EstadoVencimiento(models.TextChoices):
    VENCIDA = "vencida", "Vencida"
    PROXIMA = "proxima", "Próxima"
    AL_DIA = "al_dia", "Al día"
    SIN_PROGRAMAR = "sin_programar", "Sin programar"


GRAVEDAD_VENCIMIENTO = {
    EstadoVencimiento.AL_DIA: 0,
    EstadoVencimiento.SIN_PROGRAMAR: 1,
    EstadoVencimiento.PROXIMA: 2,
    EstadoVencimiento.VENCIDA: 3,
}


class ResumenSitio(NamedTuple):
    """Peor estado por vencimiento y vencimiento más cercano de los puntos activos."""

    estado: str
    vencimiento: datetime.date | None


def estado_por_vencimiento(fecha, hoy):
    """Estado de un punto según su próximo vencimiento; sin fecha, ``sin_programar``."""
    if fecha is None:
        return EstadoVencimiento.SIN_PROGRAMAR
    if fecha < hoy:
        return EstadoVencimiento.VENCIDA
    if fecha <= hoy + datetime.timedelta(days=UMBRAL_PROXIMA_DIAS):
        return EstadoVencimiento.PROXIMA
    return EstadoVencimiento.AL_DIA


def estados_por_vencimiento(puntos, hoy):
    """``{id_del_punto: estado}`` según ``proximo_vencimiento``; sin consultas."""
    return {p.pk: estado_por_vencimiento(p.proximo_vencimiento, hoy) for p in puntos}


def resumen_de_sitios(sitios, hoy):
    """``{id_del_sitio: ResumenSitio}`` de los puntos activos, con una sola consulta.

    Un sitio sin puntos activos queda ``sin_programar`` y sin vencimiento.
    """
    ids = [s.pk if hasattr(s, "pk") else s for s in sitios]
    fechas = defaultdict(list)
    for sitio_id, fecha in PuntoControl.objects.filter(
        sitio_id__in=ids, activo=True
    ).values_list("sitio_id", "proximo_vencimiento"):
        fechas[sitio_id].append(fecha)
    resumen = {}
    for sitio_id in ids:
        lista = fechas[sitio_id]
        estado = max(
            (estado_por_vencimiento(f, hoy) for f in lista),
            key=lambda e: GRAVEDAD_VENCIMIENTO[e],
            default=EstadoVencimiento.SIN_PROGRAMAR,
        )
        resumen[sitio_id] = ResumenSitio(
            estado, min((f for f in lista if f), default=None)
        )
    return resumen
