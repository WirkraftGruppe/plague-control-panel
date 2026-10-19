"""Configuración de apps propias del proyecto."""

from django.contrib.admin.apps import AdminConfig


class AdminDetachConfig(AdminConfig):
    """Reemplaza el sitio de admin por uno restringido a superusuarios."""

    default_site = "config.admin.SitioAdministracion"
