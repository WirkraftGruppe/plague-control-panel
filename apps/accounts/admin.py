from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CuentaAdmin(UserAdmin):
    """Admin de usuarios con los campos de rol y teléfono."""

    list_display = ("username", "first_name", "last_name", "rol", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("", {"fields": ("rol", "telefono")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("", {"fields": ("rol", "telefono")}),)

    def get_fieldsets(self, request, obj=None):
        """Titula la sección propia con el nombre de la empresa vigente en settings."""
        secciones = list(super().get_fieldsets(request, obj))
        secciones[-1] = (settings.NOMBRE_EMPRESA, secciones[-1][1])
        return secciones
