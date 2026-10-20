"""Formularios del panel de Productos."""

from django import forms
from django.core.exceptions import ValidationError

from .models import MovimientoStock, Producto
from .unidades import validar_cantidad_base


class ProductoForm(forms.ModelForm):
    """Alta y edición del producto; `activo` permite retirarlo del catálogo."""

    class Meta:
        model = Producto
        fields = [
            "nombre_comercial",
            "principio_activo",
            "registro",
            "presentacion",
            "unidad_dosis_por_defecto",
            "unidad_base",
            "contenido_por_envase",
            "modo_unidad",
            "activo",
        ]

    def clean_unidad_base(self):
        unidad = self.cleaned_data["unidad_base"]
        if (
            self.instance.pk
            and unidad != self.instance.unidad_base
            and self.instance.movimientos.exists()
        ):
            raise ValidationError(
                "No se puede cambiar la unidad base de un producto con "
                "movimientos de stock."
            )
        return unidad


class MovimientoForm(forms.Form):
    """Alta de un ingreso (en envases o unidad base) o de un ajuste con signo."""

    tipo = forms.ChoiceField(
        label="Tipo",
        choices=[
            (MovimientoStock.Tipo.INGRESO, "Ingreso"),
            (MovimientoStock.Tipo.AJUSTE, "Ajuste"),
        ],
    )
    cantidad = forms.DecimalField(
        label="Cantidad",
        max_digits=14,
        decimal_places=4,
        help_text="Ingreso: mayor que cero. Ajuste: con signo (negativa resta).",
    )
    en_envases = forms.BooleanField(label="La cantidad está en envases", required=False)
    nota = forms.CharField(label="Nota", max_length=200, required=False)

    def __init__(self, *args, producto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto

    def clean(self):
        datos = super().clean()
        tipo, cantidad = datos.get("tipo"), datos.get("cantidad")
        if cantidad is None:
            return datos
        if tipo == MovimientoStock.Tipo.INGRESO and cantidad <= 0:
            self.add_error("cantidad", "El ingreso debe ser mayor que cero.")
        if tipo == MovimientoStock.Tipo.AJUSTE:
            if cantidad == 0:
                self.add_error("cantidad", "El ajuste no puede ser cero.")
            if datos.get("en_envases"):
                self.add_error("en_envases", "El ajuste se carga en unidad base.")
        if "cantidad" not in self.errors:
            total = cantidad
            if self.producto is not None and datos.get("en_envases"):
                total = cantidad * self.producto.contenido_por_envase
            try:
                validar_cantidad_base(total)
            except ValidationError as error:
                self.add_error("cantidad", error)
        return datos
