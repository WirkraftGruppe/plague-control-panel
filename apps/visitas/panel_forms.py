"""Formularios del panel de Visitas."""

from django import forms
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.accounts.models import User
from apps.productos.models import Producto
from apps.productos.unidades import CHOICES as UNIDADES
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl

from .models import Revision, Visita
from .planillas import validar_datos
from .serializers import MAX_BYTES_FOTO
from .services import MAX_FOTOS, MAX_PRODUCTOS


class FormularioPuntosConServicio(forms.Form):
    """Puntos activos de un sitio, cada uno con el servicio que se le hará.

    Cada punto lleva un campo `servicio_<id>` con su servicio como valor inicial;
    los campos con `agrupado` los dibuja la plantilla de la tabla de puntos.
    """

    puntos = forms.ModelMultipleChoiceField(
        label="Puntos de control",
        queryset=PuntoControl.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, sitio, **kwargs):
        super().__init__(*args, **kwargs)
        self.sitio = sitio
        puntos = PuntoControl.objects.filter(sitio=sitio, activo=True)
        self.fields["puntos"].queryset = puntos
        self.fields["puntos"].agrupado = True
        self.puntos_activos = list(puntos)
        servicios = TipoServicio.objects.filter(activo=True).order_by("nombre")
        for punto in self.puntos_activos:
            campo = forms.ModelChoiceField(
                label=f"Servicio de {punto.nombre}",
                queryset=servicios,
                required=False,
                initial=punto.servicio_id,
            )
            campo.agrupado = True
            self.fields[f"servicio_{punto.pk}"] = campo

    def filas(self):
        """Una fila por punto: el punto, si está tildado y su campo de servicio."""
        tildados = {str(valor) for valor in self["puntos"].value() or []}
        return [
            {
                "punto": punto,
                "marcado": str(punto.pk) in tildados,
                "servicio": self[f"servicio_{punto.pk}"],
            }
            for punto in self.puntos_activos
        ]

    def clean(self):
        limpio = super().clean()
        for punto in limpio.get("puntos", []):
            if not limpio.get(f"servicio_{punto.pk}"):
                self.add_error(
                    f"servicio_{punto.pk}", "El punto no tiene servicio asignado."
                )
        return limpio

    def items(self):
        """Lista de `(punto, servicio)` de los puntos tildados, para los servicios."""
        return [
            (punto, self.cleaned_data[f"servicio_{punto.pk}"])
            for punto in self.cleaned_data["puntos"]
        ]


class FormularioTurno(FormularioPuntosConServicio):
    """Empleado activo, fecha y puntos con servicio para un turno pendiente."""

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


class FormularioManual(FormularioPuntosConServicio):
    """Carga manual de una visita; la planilla sale del esquema de cada servicio."""

    empleado = forms.ModelChoiceField(
        label="Empleado",
        queryset=User.objects.filter(rol=User.Rol.EMPLEADO, is_active=True).order_by(
            "username"
        ),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La hora actual como valor inicial y como tope del campo.
        ahora = timezone.localtime().strftime(FORMATO_FECHA_HORA)
        self.fields["realizada_en"].initial = ahora
        self.fields["realizada_en"].widget.attrs["max"] = ahora
        # Una pendiente con revisiones (evidencia migrada) no se completa a mano.
        pendientes = (
            Visita.objects.filter(sitio=self.sitio, estado=Visita.Estado.PENDIENTE)
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
        # Las planillas de todos los servicios; las del servicio no elegido se ignoran.
        self.servicios = {}
        servicios = TipoServicio.objects.filter(activo=True).prefetch_related("campos")
        for servicio in servicios.order_by("nombre"):
            self.servicios[servicio.pk] = servicio
            for ambito, prefijo in (
                ("punto", PREFIJO_DATOS),
                ("visita", PREFIJO_DATOS_VISITA),
            ):
                for campo in servicio.esquema_planilla(ambito):
                    nuevo = _campo_de_planilla(campo)
                    nuevo.required = False
                    nuevo.label = f"{servicio.nombre} · {campo['etiqueta']}"
                    self.fields[f"{prefijo}{servicio.pk}_{campo['clave']}"] = nuevo

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

    def _servicios_elegidos(self):
        """Servicios de los puntos tildados, sin repetir."""
        elegidos = {s.pk: self.servicios[s.pk] for _, s in self.items()}
        return list(elegidos.values())

    def _planillas(self, ambito, prefijo):
        """`{slug: valores}` de la planilla de cada servicio elegido."""
        return {
            s.slug: self._datos(s.esquema_planilla(ambito), f"{prefijo}{s.pk}_")
            for s in self._servicios_elegidos()
        }

    def datos_planilla(self):
        """Planilla de cada punto por servicio, con los tipos de `validar_datos`."""
        return self._planillas("punto", PREFIJO_DATOS)

    def datos_planilla_visita(self):
        """Planilla de ámbito visita por servicio."""
        return self._planillas("visita", PREFIJO_DATOS_VISITA)

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
        if any(n == "puntos" or n.startswith("servicio_") for n in self.errors):
            return limpio
        for ambito, prefijo in (
            ("punto", PREFIJO_DATOS),
            ("visita", PREFIJO_DATOS_VISITA),
        ):
            for servicio in self._servicios_elegidos():
                esquema = servicio.esquema_planilla(ambito)
                datos = self._datos(esquema, f"{prefijo}{servicio.pk}_")
                for clave, mensajes in validar_datos(esquema, datos).items():
                    campo = f"{prefijo}{servicio.pk}_{clave}"
                    for mensaje in mensajes:
                        self.add_error(campo if campo in self.fields else None, mensaje)
        return limpio
