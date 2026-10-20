"""Formularios del panel de Sitios."""

from django import forms

from apps.servicios.models import TipoServicio

from .models import Plano, PuntoControl, Sitio


class SitioForm(forms.ModelForm):
    """Alta y edición de un sitio; lat y lng se cargan a mano."""

    class Meta:
        model = Sitio
        fields = [
            "cliente",
            "nombre",
            "direccion",
            "localidad",
            "latitud",
            "longitud",
            "sector",
            "contacto_en_sitio",
            "telefono_en_sitio",
            "horario_acceso",
            "responsable",
            "notas",
            "activo",
        ]
        widgets = {
            "notas": forms.Textarea(attrs={"rows": 3}),
        }


class PuntoForm(forms.ModelForm):
    """Alta y edición de un punto; el plano se limita a los del propio sitio."""

    class Meta:
        model = PuntoControl
        fields = [
            "nombre",
            "sector",
            "orden",
            "activo",
            "plano",
            "x",
            "y",
            "qr_impreso_el",
            "latitud",
            "longitud",
        ]
        widgets = {
            "qr_impreso_el": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }

    def __init__(self, *args, sitio, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.sitio = sitio
        self.fields["plano"].queryset = sitio.planos.filter(activo=True)
        self.fields["orden"].required = False

    def clean_latitud(self):
        return _en_rango(self.cleaned_data["latitud"], 90, "La latitud")

    def clean_longitud(self):
        return _en_rango(self.cleaned_data["longitud"], 180, "La longitud")

    def clean(self):
        datos = super().clean()
        x, y, plano = datos.get("x"), datos.get("y"), datos.get("plano")
        if (x is None) != (y is None):
            raise forms.ValidationError("La posición necesita x e y.")
        if x is not None and plano is None:
            raise forms.ValidationError("Para ubicar el punto elija un plano.")
        return datos


class PuntoAltaForm(PuntoForm):
    """Alta: sin coordenadas; la ubicación se toma del primer escaneo."""

    class Meta(PuntoForm.Meta):
        fields = [c for c in PuntoForm.Meta.fields if c not in ("latitud", "longitud")]


def _en_rango(valor, limite, nombre):
    if valor is not None and abs(valor) > limite:
        raise forms.ValidationError(f"{nombre} debe estar entre -{limite} y {limite}.")
    return valor


class PlanoForm(forms.ModelForm):
    """Subida de un plano: ``Plano.clean`` valida JPG, PNG o PDF y lo convierte."""

    class Meta:
        model = Plano
        fields = ["nombre", "imagen", "orden"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["orden"].required = False


class PosicionForm(forms.Form):
    """Posición del marcador en el plano, en fracción del ancho y del alto."""

    x = forms.DecimalField(min_value=0, max_value=1, max_digits=5, decimal_places=4)
    y = forms.DecimalField(min_value=0, max_value=1, max_digits=5, decimal_places=4)
    plano = forms.ModelChoiceField(
        queryset=Plano.objects.filter(activo=True), required=False
    )


class ProgramacionForm(forms.Form):
    """Servicio, frecuencia y próximo vencimiento de un punto (edición en línea)."""

    servicio = forms.ModelChoiceField(
        TipoServicio.objects.filter(activo=True), required=False
    )
    frecuencia_dias = forms.IntegerField(
        min_value=1, max_value=3650, required=False, label="Frecuencia (días)"
    )
    proximo_vencimiento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
