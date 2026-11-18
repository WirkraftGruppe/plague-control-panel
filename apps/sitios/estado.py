"""Estado de vencimiento de los puntos de control y resumen por sitio."""

import datetime
from collections import defaultdict
from typing import NamedTuple

from django.db import models
from django.db.models import BooleanField, Count, Exists, ExpressionWrapper, OuterRef, Q

from .models import PuntoControl

# Tope de los días de aviso y valor de un punto sin frecuencia.
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


def dias_aviso(frecuencia_dias):
    """Días de aviso de un punto: ``ceil(frecuencia / 4)`` entre 1 y 7.

    Sin frecuencia (nula o 0) son 7. Si el aviso alcanza la frecuencia entera
    se usa ``frecuencia - 1``: con frecuencia 1, "próxima" solo el día que vence.
    """
    if not frecuencia_dias:
        return UMBRAL_PROXIMA_DIAS
    aviso = min(max(-(-frecuencia_dias // 4), 1), UMBRAL_PROXIMA_DIAS)
    return frecuencia_dias - 1 if aviso >= frecuencia_dias else aviso


def estado_por_vencimiento(fecha, hoy, frecuencia_dias=None):
    """Estado de un punto por vencimiento y frecuencia; sin fecha, sin_programar."""
    if fecha is None:
        return EstadoVencimiento.SIN_PROGRAMAR
    if fecha < hoy:
        return EstadoVencimiento.VENCIDA
    if fecha <= hoy + datetime.timedelta(days=dias_aviso(frecuencia_dias)):
        return EstadoVencimiento.PROXIMA
    return EstadoVencimiento.AL_DIA


def estados_por_vencimiento(puntos, hoy):
    """``{id_del_punto: estado}`` según vencimiento y frecuencia; sin consultas."""
    return {
        p.pk: estado_por_vencimiento(p.proximo_vencimiento, hoy, p.frecuencia_dias)
        for p in puntos
    }


def resumen_de_sitios(sitios, hoy, empresa):
    """``{id_del_sitio: ResumenSitio}`` de los puntos activos, con una sola consulta.

    Un sitio sin puntos activos queda ``sin_programar`` y sin vencimiento. Los puntos
    se acotan a ``empresa``, la de los sitios.
    """
    ids = [s.pk if hasattr(s, "pk") else s for s in sitios]
    fechas = defaultdict(list)
    for sitio_id, fecha, frecuencia in (
        PuntoControl.objects.de_empresa(empresa)
        .filter(sitio_id__in=ids, activo=True)
        .values_list("sitio_id", "proximo_vencimiento", "frecuencia_dias")
    ):
        fechas[sitio_id].append((fecha, frecuencia))
    resumen = {}
    for sitio_id in ids:
        lista = fechas[sitio_id]
        estado = max(
            (estado_por_vencimiento(f, hoy, fr) for f, fr in lista),
            key=lambda e: GRAVEDAD_VENCIMIENTO[e],
            default=EstadoVencimiento.SIN_PROGRAMAR,
        )
        resumen[sitio_id] = ResumenSitio(
            estado, min((f for f, _ in lista if f), default=None)
        )
    return resumen


class EstadoSitio(models.TextChoices):
    """Estado de un sitio por el peor estado de sus puntos activos."""

    VENCIDOS = "vencidos", "Vencidos"
    SEMANA = "semana", "Próxima"
    AL_DIA = "al_dia", "Al día"
    SIN_FECHAS = "sin_fechas", "Sin fechas"


# Chip de cada fila: el tono de panel.css y el texto en singular.
CHIP_ESTADO_SITIO = {
    EstadoSitio.VENCIDOS: ("danger", "Vencido"),
    EstadoSitio.SEMANA: ("warn", "Próxima"),
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


def estado_de_sitio_por_puntos(puntos, hoy):
    """Estado del sitio según sus puntos activos (``puntos`` ya filtrados)."""
    estados = set(estados_por_vencimiento(puntos, hoy).values())
    if EstadoVencimiento.VENCIDA in estados:
        return EstadoSitio.VENCIDOS
    if EstadoVencimiento.PROXIMA in estados:
        return EstadoSitio.SEMANA
    if EstadoVencimiento.AL_DIA in estados:
        return EstadoSitio.AL_DIA
    return EstadoSitio.SIN_FECHAS


# Tramos de frecuencia con los mismos días de aviso, como (desde, hasta, aviso).
# ``hasta`` nulo es sin tope; la frecuencia nula o 0 se trata aparte (7 días).
_TRAMOS_AVISO = [(1, 1, 0), (2, 4, 1), (5, 8, 2), (9, 12, 3)]
_TRAMOS_AVISO += [(13, 16, 4), (17, 20, 5), (21, 24, 6), (25, None, 7)]


def condicion_de_estado(estado, hoy):
    """``Q`` sobre un ``Sitio`` equivalente a ``estado_de_sitio_por_puntos``.

    Mira los puntos activos con ``Exists``; los días de aviso se resuelven por
    tramos de frecuencia, sin aritmética de fechas en SQL.
    """
    activos = PuntoControl.objects.filter(sitio=OuterRef("pk"), activo=True)
    vencido = Q(Exists(activos.filter(proximo_vencimiento__lt=hoy)))
    en_aviso = Q(Exists(activos.filter(_punto_en_aviso(hoy))))
    con_fecha = Q(Exists(activos.filter(proximo_vencimiento__isnull=False)))
    condiciones = {
        EstadoSitio.VENCIDOS: vencido,
        EstadoSitio.SEMANA: ~vencido & en_aviso,
        EstadoSitio.AL_DIA: ~vencido & ~en_aviso & con_fecha,
        EstadoSitio.SIN_FECHAS: ~con_fecha,
    }
    return condiciones[estado]


def _punto_en_aviso(hoy):
    """``Q`` sobre un punto: vence entre hoy y hoy + sus días de aviso."""

    def ventana(aviso):
        limite = hoy + datetime.timedelta(days=aviso)
        return Q(proximo_vencimiento__gte=hoy, proximo_vencimiento__lte=limite)

    sin_frecuencia = Q(frecuencia_dias__isnull=True) | Q(frecuencia_dias=0)
    q = sin_frecuencia & ventana(UMBRAL_PROXIMA_DIAS)
    for desde, hasta, aviso in _TRAMOS_AVISO:
        tramo = Q(frecuencia_dias__gte=desde)
        if hasta is not None:
            tramo &= Q(frecuencia_dias__lte=hasta)
        q |= tramo & ventana(aviso)
    return q


def conteos_por_estado(sitios, hoy):
    """``{estado: cantidad}`` de un queryset de sitios, en una agregación.

    Cada condición se anota antes de agregar: si el queryset ya trae un agregado,
    Django lo envuelve en una subconsulta y el ``Exists`` solo ve lo anotado.
    """
    anotados = sitios.order_by().annotate(
        **{
            f"_estado_{e.value}": ExpressionWrapper(
                condicion_de_estado(e, hoy), output_field=BooleanField()
            )
            for e in EstadoSitio
        }
    )
    agregados = anotados.aggregate(
        **{
            e.value: Count("pk", filter=Q(**{f"_estado_{e.value}": True}))
            for e in EstadoSitio
        }
    )
    return {EstadoSitio(clave): total for clave, total in agregados.items()}
