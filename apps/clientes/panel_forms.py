"""Formularios del panel de Clientes."""

from django import forms

from apps.clientes.empresa import FormularioDeEmpresa
from apps.clientes.models import Cliente


class ClienteForm(FormularioDeEmpresa):
    """Alta y edición de un cliente."""

    class Meta:
        model = Cliente
        fields = [
            "razon_social",
            "cuit",
            "contacto_nombre",
            "contacto_telefono",
            "contacto_email",
            "notas",
            "activo",
        ]
        widgets = {"notas": forms.Textarea(attrs={"rows": 4})}
