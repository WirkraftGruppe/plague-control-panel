"""Etiquetas de plantilla del panel de Visitas."""

from django import template

from apps.visitas.models import Visita

register = template.Library()


@register.simple_tag(takes_context=True)
def incidencias_sin_revisar(context):
    """Visitas con incidencia sin revisar, como el filtro del listado de turnos.

    Sin un administrador autenticado en la petición (login, plantillas sueltas)
    devuelve 0 sin consultar la base.
    """
    usuario = getattr(context.get("request"), "user", None)
    if not (usuario and usuario.is_authenticated and usuario.es_administrador):
        return 0
    return Visita.objects.filter(
        incidencia=True, incidencia_revisada_en__isnull=True
    ).count()
