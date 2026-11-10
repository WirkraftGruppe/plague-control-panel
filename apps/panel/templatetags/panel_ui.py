"""Filtros de interfaz compartidos por las plantillas del panel."""

from django import template
from django.utils import timezone

from apps.sitios.models import Sitio

register = template.Library()

TONOS = {
    # Semáforo por vencimiento
    "vencida": "danger",
    "proxima": "warn",
    "al_dia": "ok",
    "sin_programar": "neutral",
    # Estados de visita
    "realizada": "ok",
    "pendiente": "warn",
    "abierta": "warn",
    "cancelada": "neutral",
}


@register.filter
def tono_estado(valor):
    """Devuelve el tono (ok, warn, danger, neutral) de un estado."""
    return TONOS.get(str(valor), "neutral")


@register.simple_tag(takes_context=True)
def sitios_vencidos(context):
    """Cantidad de sitios activos con algún punto activo vencido, en una consulta.

    Cuenta solo los de la empresa de la petición. Sin un administrador autenticado
    con empresa devuelve 0 sin consultar.
    """
    solicitud = context.get("request")
    usuario = getattr(solicitud, "user", None)
    empresa = getattr(solicitud, "empresa", None)
    if not (usuario and usuario.is_authenticated and usuario.es_administrador):
        return 0
    if empresa is None:
        return 0
    return (
        Sitio.objects.de_empresa(empresa)
        .filter(
            activo=True,
            puntos__activo=True,
            puntos__proximo_vencimiento__lt=timezone.localdate(),
        )
        .distinct()
        .count()
    )
