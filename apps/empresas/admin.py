from django.contrib import admin

from .models import Empresa


def _manager_sin_filtro(modelo):
    """`todos` si el modelo es de empresa; si no, su manager por defecto (`User`)."""
    return getattr(modelo, "todos", None) or modelo._default_manager


class AdminTodosMixin:
    """Admin de modelos de empresa: lista y ofrece todos los registros, sin guardia."""

    def get_queryset(self, request):
        consulta = _manager_sin_filtro(self.model).get_queryset()
        orden = self.get_ordering(request)
        return consulta.order_by(*orden) if orden else consulta

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if "queryset" not in kwargs:
            modelo = db_field.remote_field.model
            kwargs["queryset"] = _manager_sin_filtro(modelo).all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo_contacto", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "correo_contacto")
