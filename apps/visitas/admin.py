from django.contrib import admin
from django.core.exceptions import PermissionDenied
from simple_history.admin import SimpleHistoryAdmin

from apps.accounts.models import User

from .models import Foto, ProductoAplicado, Revision, Visita

CAMPOS_EVIDENCIA = (
    "sitio",
    "empleado",
    "origen",
    "motivo_manual",
    "datos",
    "estado",
    "abierta_en",
    "cerrada_en",
    "cierre",
    "esquema_planilla",
)

CAMPOS_PLANIFICACION = ("programada_para", "asignada_por")

# Los fija el servicio de revisión de incidencias, nunca se editan a mano.
CAMPOS_REVISION = ("incidencia_revisada_por", "incidencia_revisada_en")

# Campos que llena el servicio al abrir la visita: nunca se editan a mano.
CAMPOS_DE_LA_APP = (
    "incidencia_asignacion",
    "distancia_m",
    "precision_m",
    "incidencia_ubicacion",
    "cuenta_como_servicio",
)

CAMPOS_VISITA = (
    (
        "sitio",
        "empleado",
        "origen",
        "motivo_manual",
        "programada_para",
        "asignada_por",
        "estado",
        "abierta_en",
        "cerrada_en",
        "cierre",
        "datos",
        "esquema_planilla",
        "observaciones",
        "incidencia",
        "incidencia_detalle",
    )
    + CAMPOS_DE_LA_APP
    + CAMPOS_REVISION
)

# La planilla de la visita la llena el cierre, no el admin, mientras sigue pendiente.
CAMPOS_REGISTRO_APP = ("datos",)


def _visita_cerrada(visita):
    """Una visita ya no pendiente es evidencia: no se modifica."""
    return visita is not None and visita.estado != Visita.Estado.PENDIENTE


class SoloLectura:
    """La evidencia de una revisión no se agrega, cambia ni borra desde el admin."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class FotoInline(SoloLectura, admin.TabularInline):
    model = Foto
    extra = 0
    fields = ("imagen", "tomada_en", "orden")


class ProductoAplicadoInline(SoloLectura, admin.TabularInline):
    model = ProductoAplicado
    extra = 0
    fields = ("producto", "lote", "dosis", "unidad_dosis", "cantidad", "unidad")


class RevisionInline(SoloLectura, admin.TabularInline):
    model = Revision
    extra = 0
    show_change_link = True
    fields = (
        "punto",
        "orden",
        "realizada_en",
        "recibida_en",
        "cliente_uuid",
        "latitud",
        "longitud",
        "precision_m",
        "distancia_m",
        "incidencia_ubicacion",
    )


@admin.register(Visita)
class VisitaAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "sitio",
        "empleado",
        "origen",
        "estado",
        "programada_para",
        "cerrada_en",
        "incidencia",
    )
    list_filter = ("estado", "origen", "incidencia")
    search_fields = ("sitio__nombre", "empleado__username")
    raw_id_fields = ("sitio",)
    fields = CAMPOS_VISITA
    readonly_fields = (
        ("estado", "abierta_en", "cerrada_en", "cierre", "esquema_planilla")
        + CAMPOS_DE_LA_APP
        + CAMPOS_REVISION
    )
    inlines = (RevisionInline,)

    def get_form(self, request, obj=None, **kwargs):
        """Una visita nueva o pendiente se asigna solo a empleados.

        La regla es de `Visita.clean`; esto solo acota las opciones del campo.
        """
        form = super().get_form(request, obj, **kwargs)
        if "empleado" in form.base_fields and (
            obj is None or obj.estado == Visita.Estado.PENDIENTE
        ):
            form.base_fields["empleado"].queryset = User.objects.filter(
                rol=User.Rol.EMPLEADO
            )
        return form

    def get_inlines(self, request, obj):
        """Las revisiones solo se ven fuera de pendiente (en el alta tampoco)."""
        if obj is None or obj.estado == Visita.Estado.PENDIENTE:
            return ()
        return super().get_inlines(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if _visita_cerrada(obj):
            return (
                CAMPOS_EVIDENCIA
                + CAMPOS_PLANIFICACION
                + CAMPOS_DE_LA_APP
                + CAMPOS_REVISION
            )
        base = super().get_readonly_fields(request, obj)
        if obj is None or obj.estado == Visita.Estado.PENDIENTE:
            return base + CAMPOS_REGISTRO_APP
        return base

    def has_delete_permission(self, request, obj=None):
        return False

    def history_form_view(self, request, object_id, version_id, extra_context=None):
        """Revertir desde el historial reescribiría evidencia: solo se permite ver."""
        if request.method == "POST":
            raise PermissionDenied
        return super().history_form_view(request, object_id, version_id, extra_context)


@admin.register(Revision)
class RevisionAdmin(SoloLectura, SimpleHistoryAdmin):
    list_display = ("id", "visita", "punto", "orden", "realizada_en")
    list_filter = ("punto__sitio",)
    search_fields = ("visita__sitio__nombre", "punto__nombre")
    inlines = (FotoInline, ProductoAplicadoInline)

    def history_form_view(self, request, object_id, version_id, extra_context=None):
        """Revertir desde el historial reescribiría evidencia: solo se permite ver."""
        if request.method == "POST":
            raise PermissionDenied
        return super().history_form_view(request, object_id, version_id, extra_context)


@admin.register(Foto)
class FotoAdmin(SoloLectura, admin.ModelAdmin):
    list_display = ("id", "revision", "tomada_en", "orden")


@admin.register(ProductoAplicado)
class ProductoAplicadoAdmin(SoloLectura, admin.ModelAdmin):
    list_display = (
        "id",
        "revision",
        "producto",
        "lote",
        "dosis",
        "unidad_dosis",
        "cantidad",
        "unidad",
    )
