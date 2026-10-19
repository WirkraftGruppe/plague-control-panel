"""Context processors del proyecto."""

from django.conf import settings


def empresa(request):
    """Expone el nombre de la empresa a las plantillas (provisorio)."""
    return {"NOMBRE_EMPRESA": settings.NOMBRE_EMPRESA}
