"""Formularios del panel de Visitas."""

from django import forms
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.accounts.models import User
from apps.productos.models import Producto
from apps.productos.unidades import CHOICES as UNIDADES
from apps.sitios.models import PuntoControl

from .models import Revision, Visita
from .planillas import validar_datos
from .serializers import MAX_BYTES_FOTO
from .services import MAX_FOTOS, MAX_PRODUCTOS


class FormularioAsignar(forms.Form):
    """Empleado activo y fecha para una visita pendiente."""

    empleado = forms.ModelChoiceField(
        label="Empleado",
        queryset=User.objects.filter(rol=User.Rol.EMPLEADO, is_active=True).order_by(
            "username"
        ),
    )
    programada_para = forms.DateField(
        label="Fecha programada",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_programada_para(self):
        fecha = self.cleaned_data["programada_para"]
        if fecha < timezone.localdate():
            raise forms.ValidationError("La fecha no puede ser anterior a hoy.")
        return fecha


PREFIJO_DATOS = "datos_"
PREFIJO_DATOS_VISITA = "datosv_"
FORMATO_FECHA_HORA = "%Y-%m-%dT%H:%M"


class VariosArchivosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class VariosArchivosField(forms.FileField):
    """Campo de archivos múltiples; entrega la lista de archivos válidos."""

    widget = VariosArchivosInput

    def clean(self, data, initial=None):
        archivos = data if isinstance(data, (list, tuple)) else [data]
        return [
            super(VariosArchivosField, self).clean(archivo, initial)
            for archivo in archivos
            if archivo
        ]


class ProductoConUnidadField(forms.ModelChoiceField):
    """Muestra la unidad base del producto para elegir la unidad de la cantidad."""

    def label_from_instance(self, producto):
        return f"{producto} ({producto.unidad_base})"


class FormularioProductoManual(forms.Form):
    """Un producto aplicado: siempre del catálogo y activo.

    La unidad de la cantidad debe ser una de las del producto (lo valida el servicio);
    la de la dosis es texto libre, por ejemplo la `unidad_dosis_por_defecto`.
    """

    producto = ProductoConUnidadField(
        label="Producto", queryset=Producto.objects.filter(activo=True)
    )
    lote = forms.CharField(label="Lote", max_length=60)
    dosis = forms.DecimalField(label="Dosis", max_digits=10, decimal_places=3)
    unidad_dosis = forms.CharField(
        label="Unidad de la dosis", max_length=20, help_text="Por ejemplo: ml/l."
    )
    cantidad = forms.DecimalField(label="Cantidad", max_digits=10, decimal_places=3)
    unidad = forms.ChoiceField(
        label="Unidad de la cantidad",
        choices=[("", "---------"), *UNIDADES],
        help_text="Una de las unidades del producto.",
    )


FormSetProductos = forms.formset_factory(
    FormularioProductoManual,
    extra=3,
    max_num=MAX_PRODUCTOS,
    validate_max=True,
)


def _campo_de_planilla(campo):
    """Campo de formulario que corresponde a un campo del esquema de la planilla."""
    tipo = campo["tipo"]
    opciones = [(str(i), str(op)) for i, op in enumerate(campo.get("opciones") or [])]
    comunes = {
        "label": campo["etiqueta"],
        "help_text": campo.get("ayuda", ""),
        "required": bool(campo.get("obligatorio")) and tipo != "booleano",
    }
    if tipo == "numero":
        return forms.FloatField(**comunes)
    if tipo == "booleano":
        return forms.BooleanField(**comunes)
    if tipo == "fecha":
        return forms.DateField(
            widget=forms.DateInput(attrs={"type": "date"}), **comunes
        )
    if tipo == "opcion":
        return forms.ChoiceField(choices=[("", "---------")] + opciones, **comunes)
    if tipo == "opcion_multiple":
        return forms.MultipleChoiceField(choices=opciones, **comunes)
    return forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), **comunes)


class FormularioManual(forms.Form):
    """Carga manual de una visita; la planilla sale del esquema del servicio."""

    empleado = forms.ModelChoiceField(
        label="Empleado",
        queryset=User.objects.filter(rol=User.Rol.EMPLEADO, is_active=True).order_by(
            "username"
        ),
    )
    puntos = forms.ModelMultipleChoiceField(
        label="Puntos revisados",
        queryset=PuntoControl.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    pendiente = forms.ModelChoiceField(
        label="Completar una visita pendiente",
        queryset=Visita.objects.none(),
        required=False,
        empty_label="Crear una visita nueva",
    )
    motivo = forms.CharField(
        label="Motivo de la carga manual", widget=forms.Textarea(attrs={"rows": 2})
    )
    realizada_en = forms.DateTimeField(
        label="Fecha y hora de la visita",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format=FORMATO_FECHA_HORA
        ),
        input_formats=[FORMATO_FECHA_HORA, "%Y-%m-%d %H:%M"],
    )
    confirmar_atraso = forms.BooleanField(
        label="Confirmo cargar una visita con atraso",
        required=False,
    )
    observaciones = forms.CharField(
        label="Observaciones", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    incidencia = forms.BooleanField(label="Hubo una incidencia", required=False)
    incidencia_detalle = forms.CharField(
        label="Detalle de la incidencia",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    fotos = VariosArchivosField(
        label=f"Fotos (hasta {MAX_FOTOS})",
        required=False,
        widget=VariosArchivosInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
    )

    def __init__(self, *args, proyecto, **kwargs):
        super().__init__(*args, **kwargs)
        self.proyecto = proyecto
        # La hora actual como valor inicial y como tope del campo.
        ahora = timezone.localtime().strftime(FORMATO_FECHA_HORA)
        self.fields["realizada_en"].initial = ahora
        self.fields["realizada_en"].widget.attrs["max"] = ahora
        self.esquema = proyecto.tipo_servicio.esquema_planilla("punto")
        self.esquema_visita = proyecto.tipo_servicio.esquema_planilla("visita")
        self.fields["puntos"].queryset = PuntoControl.objects.filter(
            sitio_id=proyecto.sitio_id, activo=True
        )
        # Una pendiente con revisiones (evidencia migrada) no se completa a mano.
        pendientes = (
            Visita.objects.filter(proyecto=proyecto, estado=Visita.Estado.PENDIENTE)
            .exclude(Exists(Revision.objects.filter(visita=OuterRef("pk"))))
            .order_by("programada_para", "pk")
        )
        self.fields["pendiente"].queryset = pendientes
        self.fields["pendiente"].label_from_instance = lambda v: (
            f"Pendiente {v.pk} de {v.empleado}"
            + (
                f", programada para {v.programada_para:%d/%m/%Y}"
                if v.programada_para
                else ""
            )
        )
        for campo in self.esquema:
            self.fields[PREFIJO_DATOS + campo["clave"]] = _campo_de_planilla(campo)
        for campo in self.esquema_visita:
            self.fields[PREFIJO_DATOS_VISITA + campo["clave"]] = _campo_de_planilla(
                campo
            )

    def clean_fotos(self):
        fotos = self.cleaned_data["fotos"]
        if len(fotos) > MAX_FOTOS:
            raise forms.ValidationError(
                f"Se permiten hasta {MAX_FOTOS} fotos por visita."
            )
        if any(foto.size > MAX_BYTES_FOTO for foto in fotos):
            raise forms.ValidationError(
                f"Cada foto puede pesar hasta {MAX_BYTES_FOTO // (1024 * 1024)} MB."
            )
        return fotos

    def datos_planilla(self):
        """Valores de la planilla de cada punto, con los tipos de `validar_datos`."""
        return self._datos(self.esquema, PREFIJO_DATOS)

    def datos_planilla_visita(self):
        """Valores de la planilla de ámbito visita."""
        return self._datos(self.esquema_visita, PREFIJO_DATOS_VISITA)

    def _datos(self, esquema, prefijo):
        datos = {}
        for campo in esquema:
            clave, tipo = campo["clave"], campo["tipo"]
            valor = self.cleaned_data.get(prefijo + clave)
            if tipo == "booleano":
                datos[clave] = bool(valor)
            elif tipo in ("opcion", "opcion_multiple"):
                opciones = campo.get("opciones") or []
                indices = [valor] if tipo == "opcion" and valor else valor
                if indices:
                    elegidas = [opciones[int(i)] for i in indices]
                    datos[clave] = (
                        elegidas if tipo == "opcion_multiple" else elegidas[0]
                    )
            elif tipo == "fecha":
                if valor:
                    datos[clave] = valor.isoformat()
            elif valor not in (None, ""):
                datos[clave] = valor
        return datos

    def clean(self):
        limpio = super().clean()
        for esquema, prefijo, datos in (
            (self.esquema, PREFIJO_DATOS, self.datos_planilla),
            (self.esquema_visita, PREFIJO_DATOS_VISITA, self.datos_planilla_visita),
        ):
            if self.errors.keys() & {prefijo + c["clave"] for c in esquema}:
                continue
            for clave, mensajes in validar_datos(esquema, datos()).items():
                campo = prefijo + clave
                for mensaje in mensajes:
                    self.add_error(campo if campo in self.fields else None, mensaje)
        return limpio
