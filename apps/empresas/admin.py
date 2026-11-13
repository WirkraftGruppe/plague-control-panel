from django import forms
from django.contrib import admin
from django.core.exceptions import NON_FIELD_ERRORS
from django.core.files.uploadedfile import UploadedFile

from .logos import procesar_logo
from .models import Empresa


def _manager_sin_filtro(modelo):
    """`todos` si el modelo es de empresa; si no, su manager por defecto (`User`)."""
    return getattr(modelo, "todos", None) or modelo._default_manager


class ErroresGeneralesMixin:
    """Formulario del admin: los errores de campos ausentes pasan a errores generales.

    `Model.clean()` puede marcar un campo (el padre, una referencia a `User`) que
    el admin muestra de solo lectura o no incluye; `add_error` lo rechazaría con
    `ValueError` y daría un 500. Acá el error va al formulario, con el nombre del
    campo en el texto.
    """

    def _update_errors(self, errors):
        if hasattr(errors, "error_dict"):
            reconducidos = {}
            for campo, lista in errors.error_dict.items():
                if campo == NON_FIELD_ERRORS or campo in self.fields:
                    reconducidos.setdefault(campo, []).extend(lista)
                    continue
                nombre = self._etiqueta_de(campo)
                for error in lista:
                    mensajes = " ".join(error.messages)
                    reconducidos.setdefault(NON_FIELD_ERRORS, []).append(
                        forms.ValidationError(f"{nombre}: {mensajes}")
                    )
            errors = forms.ValidationError(reconducidos)
        super()._update_errors(errors)

    def _etiqueta_de(self, campo):
        try:
            return str(self._meta.model._meta.get_field(campo).verbose_name)
        except Exception:  # noqa: BLE001
            return campo

    def _get_validation_exclusions(self):
        """`empresa` entra en las restricciones si la instancia la tiene."""
        exclusiones = super()._get_validation_exclusions()
        if getattr(self.instance, "empresa_id", None) is not None:
            exclusiones.discard("empresa")
        return exclusiones


class AdminFormularioMixin:
    """Admin cuyo formulario reconduce los errores de campos ausentes."""

    def get_form(self, request, obj=None, change=False, **kwargs):
        base = kwargs.pop("form", None) or self.form
        if not issubclass(base, ErroresGeneralesMixin):
            base = type(base.__name__, (ErroresGeneralesMixin, base), {})
        return super().get_form(request, obj, change=change, form=base, **kwargs)


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


class EmpresaAdminForm(forms.ModelForm):
    """Formulario del admin de empresas: el logo se procesa como en el panel."""

    class Meta:
        model = Empresa
        fields = "__all__"

    def clean_logo(self):
        archivo = self.cleaned_data.get("logo")
        if not isinstance(archivo, UploadedFile):
            # Sin subida (queda el logo actual) o casilla "Limpiar" (se borra).
            return archivo
        return procesar_logo(archivo)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    form = EmpresaAdminForm
    list_display = ("nombre", "correo_contacto", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "correo_contacto")
