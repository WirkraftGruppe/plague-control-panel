from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from apps.empresas.admin import AdminTodosMixin

from .models import User


class ReglaRolEmpresaMixin:
    """Regla del admin: `plataforma` sin empresa; los demás roles, con empresa."""

    def clean(self):
        datos = super().clean()
        rol, empresa = datos.get("rol"), datos.get("empresa")
        if rol == User.Rol.PLATAFORMA and empresa:
            self.add_error("empresa", "El rol plataforma no pertenece a una empresa.")
        elif rol and rol != User.Rol.PLATAFORMA and not empresa:
            self.add_error("empresa", "Este rol exige una empresa.")
        return datos


class CuentaAltaForm(ReglaRolEmpresaMixin, AdminUserCreationForm):
    """Alta de cuenta en el admin con la regla de rol y empresa."""


class CuentaEdicionForm(ReglaRolEmpresaMixin, UserChangeForm):
    """Edición de cuenta en el admin con la regla de rol y empresa."""


@admin.register(User)
class CuentaAdmin(AdminTodosMixin, UserAdmin):
    """Admin de usuarios con los campos de rol, empresa y teléfono."""

    form = CuentaEdicionForm
    add_form = CuentaAltaForm
    list_display = (
        "username",
        "first_name",
        "last_name",
        "rol",
        "empresa",
        "is_active",
    )
    list_filter = ("rol", "empresa", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("", {"fields": ("rol", "empresa", "telefono")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("", {"fields": ("rol", "empresa", "telefono")}),
    )
