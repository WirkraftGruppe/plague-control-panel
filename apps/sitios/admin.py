from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.template.response import TemplateResponse
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin

from . import services
from .models import Plano, PuntoControl, Sitio


class _AdministradorMixin:
    """Requisitos comunes del admin: rol administrador, confirmación y sin revert."""

    def history_form_view(self, request, object_id, version_id, extra_context=None):
        """Prohíbe revertir desde el historial: solo se consulta."""
        if request.method == "POST":
            raise PermissionDenied
        return super().history_form_view(request, object_id, version_id, extra_context)

    def _es_administrador_activo(self, request):
        return request.user.is_active and getattr(
            request.user, "es_administrador", False
        )

    def _pedir_confirmacion(self, request, queryset, accion, titulo, consecuencia):
        opts = self.model._meta
        return TemplateResponse(
            request,
            "admin/sitios/sitio/confirmar_accion.html",
            {
                "title": titulo,
                "consecuencia": consecuencia,
                "objetos": queryset,
                "accion": accion,
                "url_listado": reverse(
                    f"admin:{opts.app_label}_{opts.model_name}_changelist"
                ),
                "opts": opts,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                **self.admin_site.each_context(request),
            },
        )


@admin.register(Sitio)
class SitioAdmin(_AdministradorMixin, SimpleHistoryAdmin):
    list_display = ("nombre", "cliente", "localidad", "sector", "activo")
    search_fields = ("nombre", "direccion", "localidad", "cliente__razon_social")
    list_filter = ("sector", "activo")
    actions = ["suprimir_datos"]

    def has_suprimir_datos_permission(self, request):
        return self._es_administrador_activo(request) and self.has_delete_permission(
            request
        )

    @admin.action(
        description="Suprimir datos (Ley 25.326): borra el sitio y todo su historial",
        permissions=["suprimir_datos"],
    )
    def suprimir_datos(self, request, queryset):
        if "confirmado" not in request.POST:
            return self._pedir_confirmacion(
                request,
                queryset,
                "suprimir_datos",
                "Suprimir datos (Ley 25.326)",
                "Se borrarán estos sitios y todo su historial de cambios. "
                "No se puede deshacer.",
            )
        suprimidos, con_visitas = services.suprimir_sitios(list(queryset))
        self.message_user(
            request, f"Se suprimieron los datos de {suprimidos} sitio(s)."
        )
        if con_visitas:
            nombres = ", ".join(sitio.nombre for sitio in con_visitas)
            self.message_user(
                request,
                f"No se suprimieron por tener visitas asociadas: {nombres}.",
                level=messages.WARNING,
            )


class PuntoControlAdminForm(forms.ModelForm):
    """Avisa en el formulario si se desactiva el último punto activo del sitio."""

    class Meta:
        model = PuntoControl
        fields = "__all__"

    def clean(self):
        datos = super().clean()
        if (
            self.instance.pk
            and "activo" in self.changed_data
            and not datos.get("activo")
        ):
            activos = list(
                PuntoControl.objects.select_for_update()
                .filter(sitio_id=self.instance.sitio_id, activo=True)
                .values_list("pk", flat=True)
            )
            if activos == [self.instance.pk]:
                self.add_error(
                    "activo", "No se puede desactivar el último punto activo."
                )
        return datos


@admin.register(PuntoControl)
class PuntoControlAdmin(_AdministradorMixin, SimpleHistoryAdmin):
    form = PuntoControlAdminForm
    list_display = ("nombre", "sitio", "sector", "orden", "activo")
    search_fields = ("nombre", "sector", "sitio__nombre")
    list_filter = ("activo",)
    readonly_fields = (
        "qr_codigo",
        "precision_m",
        "ubicacion_fijada_por",
        "ubicacion_fijada_en",
    )
    actions = ["regenerar_qr"]

    def get_readonly_fields(self, request, obj=None):
        """Al editar, el sitio y la foto no se cambian desde el admin."""
        campos = super().get_readonly_fields(request, obj)
        return (*campos, "sitio", "foto") if obj else campos

    def save_model(self, request, obj, form, change):
        """Coordenadas corregidas limpian la marca de escaneo; baja por el servicio."""
        if {"latitud", "longitud"} & set(form.changed_data):
            obj.ubicacion_fijada_por = None
            obj.ubicacion_fijada_en = None
            obj.precision_m = None
        if not change or "activo" not in form.changed_data or obj.activo:
            return super().save_model(request, obj, form, change)
        # El formulario ya rechazó el último punto activo; si el servicio lo
        # rechaza igual, la excepción hace fallar la petición.
        obj.activo = True
        with transaction.atomic():
            super().save_model(request, obj, form, change)
            services.desactivar_punto(obj)

    def has_regenerar_qr_permission(self, request):
        return self._es_administrador_activo(request) and self.has_change_permission(
            request
        )

    @admin.action(
        description="Regenerar código QR (invalida la etiqueta impresa)",
        permissions=["regenerar_qr"],
    )
    def regenerar_qr(self, request, queryset):
        if "confirmado" not in request.POST:
            return self._pedir_confirmacion(
                request,
                queryset,
                "regenerar_qr",
                "Regenerar código QR",
                "La etiqueta QR impresa de estos puntos dejará de funcionar "
                "y habrá que imprimir una nueva.",
            )
        try:
            cantidad = services.regenerar_qr_lote(list(queryset))
        except ValidationError as error:
            self.message_user(request, " ".join(error.messages), level=messages.ERROR)
            return
        self.message_user(request, f"Se regeneró el código QR de {cantidad} punto(s).")


@admin.register(Plano)
class PlanoAdmin(_AdministradorMixin, SimpleHistoryAdmin):
    list_display = ("nombre", "sitio", "orden", "ancho_px", "alto_px", "activo")
    search_fields = ("nombre", "sitio__nombre")
    list_filter = ("activo",)
    readonly_fields = ("ancho_px", "alto_px")

    def get_readonly_fields(self, request, obj=None):
        """Al editar, el plano no se cambia de sitio."""
        campos = super().get_readonly_fields(request, obj)
        return (*campos, "sitio") if obj else campos
