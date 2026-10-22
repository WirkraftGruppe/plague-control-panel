"""Estado de vencimiento de los puntos de control y resumen por sitio."""

import datetime
from collections import defaultdict
from typing import NamedTuple

from django.db import models
from django.db.models import Count, Q

from .models import PuntoControl

UMBRAL_PROXIMA_DIAS = 7


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


class EstadoSitio(models.TextChoices):
    """Estado de un sitio por el mínimo vencimiento de sus puntos activos."""

    VENCIDOS = "vencidos", "Vencidos"
    SEMANA = "semana", "Esta semana"
    AL_DIA = "al_dia", "Al día"
    SIN_FECHAS = "sin_fechas", "Sin fechas"


# Chip de cada fila: el tono de panel.css y el texto en singular.
CHIP_ESTADO_SITIO = {
    EstadoSitio.VENCIDOS: ("danger", "Vencido"),
    EstadoSitio.SEMANA: ("warn", "Esta semana"),
    EstadoSitio.AL_DIA: ("ok", "Al día"),
    EstadoSitio.SIN_FECHAS: ("neutral", "Sin fechas"),
}


def estado_de_sitio(vencimiento, hoy):
    """Estado del sitio según su mínimo ``proximo_vencimiento``; nulo, sin fechas."""
    if vencimiento is None:
        return EstadoSitio.SIN_FECHAS
    if vencimiento < hoy:
        return EstadoSitio.VENCIDOS
    if vencimiento <= hoy + datetime.timedelta(days=UMBRAL_PROXIMA_DIAS):
        return EstadoSitio.SEMANA
    return EstadoSitio.AL_DIA


def condicion_de_estado(estado, hoy, campo="proximo_vencimiento"):
    """``Q`` equivalente a ``estado_de_sitio`` sobre una anotación con el mínimo."""
    limite = hoy + datetime.timedelta(days=UMBRAL_PROXIMA_DIAS)
    condiciones = {
        EstadoSitio.VENCIDOS: Q(**{f"{campo}__lt": hoy}),
        EstadoSitio.SEMANA: Q(**{f"{campo}__gte": hoy, f"{campo}__lte": limite}),
        EstadoSitio.AL_DIA: Q(**{f"{campo}__gt": limite}),
        EstadoSitio.SIN_FECHAS: Q(**{f"{campo}__isnull": True}),
    }
    return condiciones[estado]


def conteos_por_estado(sitios, hoy):
    """``{estado: cantidad}`` de un queryset con la anotación, en una agregación."""
    agregados = sitios.order_by().aggregate(
        **{
            e.value: Count("pk", filter=condicion_de_estado(e, hoy))
            for e in EstadoSitio
        }
    )
    return {EstadoSitio(clave): total for clave, total in agregados.items()}
