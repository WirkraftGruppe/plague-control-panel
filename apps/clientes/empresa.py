"""Piezas comunes de formularios, vistas del panel y admin de los modelos de empresa."""

from django import forms
from django.views.generic.edit import ModelFormMixin

from apps.empresas.admin import AdminTodosMixin


class FormularioDeEmpresa(forms.ModelForm):
    """Formulario que fija la empresa de la instancia antes de validar.

    `empresa` no es un campo del formulario, así que Django la excluiría de la
    validación de restricciones: se la saca de las exclusiones para que un
    `UniqueConstraint(empresa, ...)` repetido dé error de formulario y no
    `IntegrityError`.
    """

    def __init__(self, *args, empresa, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        if self.instance._state.adding:
            self.instance.empresa = empresa

    def _get_validation_exclusions(self):
        exclusiones = super()._get_validation_exclusions()
        exclusiones.discard("empresa")
        return exclusiones


class VistaDeEmpresaMixin:
    """Vista del panel cuyo queryset es siempre el de `request.empresa`.

    Va primero en las bases: acota el queryset de la clase y, si la vista tiene
    formulario de modelo, le pasa la empresa. Un objeto de otra empresa da 404.
    """

    def get_queryset(self):
        return super().get_queryset().de_empresa(self.request.empresa)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if isinstance(self, ModelFormMixin):
            kwargs["empresa"] = self.request.empresa
        return kwargs


class AdminRaizMixin(AdminTodosMixin):
    """Admin de un modelo raíz: pide la empresa al crear y no deja cambiarla."""

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        return (*campos, "empresa") if obj is not None else campos

    def get_form(self, request, obj=None, change=False, **kwargs):
        formulario = super().get_form(request, obj, change=change, **kwargs)
        if "empresa" in formulario.base_fields:
            formulario.base_fields["empresa"].required = True
        return formulario


class AdminHijoMixin(AdminTodosMixin):
    """Admin de un modelo hijo: `save()` copia la empresa del padre."""

    def get_exclude(self, request, obj=None):
        return (*(super().get_exclude(request, obj) or ()), "empresa")
