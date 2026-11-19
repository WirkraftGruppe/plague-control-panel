"""Etiquetas de plantilla del panel de Visitas."""

from datetime import timedelta

from django import template

from apps.visitas.models import Visita
from apps.visitas.services import condicion_incidencia_sin_revisar

register = template.Library()


@register.simple_tag(takes_context=True)
def incidencias_sin_revisar(context):
    """Visitas de la empresa con incidencia sin revisar, como el filtro del listado.

    Sin un administrador autenticado en la petición (login, plantillas sueltas)
    devuelve 0 sin consultar la base.
    """
    usuario = getattr(context.get("request"), "user", None)
    if not (usuario and usuario.is_authenticated and usuario.es_administrador):
        return 0
    empresa = getattr(context.get("request"), "empresa", None)
    if empresa is None:
        return 0
    return (
        Visita.objects.de_empresa(empresa)
        .filter(condicion_incidencia_sin_revisar())
        .count()
    )


UMBRAL_LLEGADA = timedelta(minutes=10)


@register.filter
def con_incidencia_servicio(revisiones):
    """Indica si alguna revisión cargada tiene un servicio distinto del asignado."""
    return any(revision.incidencia_servicio for revision in revisiones)


@register.filter
def llegada_tardia(revision):
    """Hora de llegada al servidor si difiere más de 10 min de la del teléfono.

    Devuelve `None` en caso contrario, para que la plantilla no muestre nada, y en
    las visitas de origen manual: su hora de recepción es la de la carga.
    """
    if revision.visita.origen == Visita.Origen.MANUAL:
        return None
    if abs(revision.recibida_en - revision.realizada_en) > UMBRAL_LLEGADA:
        return revision.recibida_en
    return None


@register.filter
def llegada_diferida(declarada, recibida):
    """Hora de recepción si difiere más de 10 min de la declarada; si no, `None`.

    Tolera horas nulas (visitas anteriores a la hora de recepción o sin cerrar).
    """
    if declarada is None or recibida is None:
        return None
    if abs(recibida - declarada) > UMBRAL_LLEGADA:
        return recibida
    return None
