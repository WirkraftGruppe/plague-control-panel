"""Formularios del panel de la empresa."""

from django import forms
from django.core.files.uploadedfile import UploadedFile

from .logos import procesar_logo
from .models import Empresa


class EmpresaForm(forms.ModelForm):
    """Nombre, logo y correo de contacto de la empresa del administrador."""

    # No es `ImageField`: abriría el archivo con todos los plugins de Pillow
    # antes de `procesar_logo`, que solo acepta JPEG y PNG.
    logo = forms.FileField(
        label="Logo",
        required=False,
        help_text="JPG o PNG de hasta 2 MB. Se guarda como PNG de hasta 1000 px.",
    )

    class Meta:
        model = Empresa
        fields = ["nombre", "logo", "correo_contacto"]

    def clean_logo(self):
        archivo = self.cleaned_data.get("logo")
        if not isinstance(archivo, UploadedFile):
            # Sin subida (queda el logo actual) o casilla "Limpiar" (se borra).
            return archivo
        return procesar_logo(archivo)
