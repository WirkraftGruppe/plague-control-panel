"""Ayudas de los tests que entran al admin técnico."""

from django.contrib.auth import get_user_model

CLAVE_PLATAFORMA = "clave-plataforma-123"


def crear_plataforma(username="plataforma", password=CLAVE_PLATAFORMA, **campos):
    """Superusuario `plataforma` sin empresa: el único rol que entra a `/admin/`."""
    return get_user_model().objects.create_superuser(
        username=username, password=password, **campos
    )
