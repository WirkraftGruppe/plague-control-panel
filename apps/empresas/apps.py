from django.apps import AppConfig


class EmpresasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.empresas"
    verbose_name = "Empresas"

    def ready(self):
        """Registra la extensión de OpenAPI de `JWTAutenticacionEmpresa`."""
        from . import esquema  # noqa: F401
