from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from apps.empresas.admin import AdminTodosMixin

from .models import User


class ReglaRolEmpresaMixin:
    """Regla del admin: `plataforma` sin empresa; los demás roles, con empresa."""

    def clean(self):
        datos = super().clean()
        rol = datos.get("rol")
        if "empresa" in self.fields:
            empresa = datos.get("empresa")
        else:
            # Empresa de solo lectura: rige la de la instancia.
            empresa = self.instance.empresa_id
        # Con la empresa de solo lectura el error va al campo del rol.
        campo = "empresa" if "empresa" in self.fields else "rol"
        if rol == User.Rol.PLATAFORMA and empresa:
            self.add_error(campo, "El rol plataforma no pertenece a una empresa.")
        elif rol and rol != User.Rol.PLATAFORMA and not empresa:
            self.add_error(campo, "Este rol exige una empresa.")
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

    def get_readonly_fields(self, request, obj=None):
        """La empresa de un usuario que ya la tiene no se cambia al editar."""
        campos = super().get_readonly_fields(request, obj)
        if obj is not None and obj.empresa_id:
            campos = (*campos, "empresa")
        return campos
