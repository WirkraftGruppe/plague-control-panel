"""Etiquetas de plantilla del panel de Visitas."""

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
