"""Vistas del panel de Servicios: tipos de servicio y editor de planillas."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    TemplateView,
    UpdateView,
    View,
)

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.panel.listados import ListadoPanelMixin

from .models import CampoPlanilla, TipoServicio
from .panel_forms import CampoPlanillaForm, TipoServicioForm


class TipoServicioListadoView(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = TipoServicio
    template_name = "servicios/panel/listado.html"
    template_parcial = "servicios/panel/_listado.html"
    orden_permitido = ("nombre", "activo")
    campos_busqueda = ("nombre",)


class TipoServicioFormularioMixin(AdministradorRequeridoMixin):
    model = TipoServicio
    form_class = TipoServicioForm
    template_name = "servicios/panel/servicio_formulario.html"
    success_url = reverse_lazy("panel:servicios:listado")

    def form_valid(self, form):
        messages.success(self.request, "Servicio guardado.")
        return super().form_valid(form)


class TipoServicioAltaView(TipoServicioFormularioMixin, CreateView):
    titulo = "Nuevo servicio"


class TipoServicioEditarView(TipoServicioFormularioMixin, UpdateView):
    titulo = "Editar servicio"


class CamposView(AdministradorRequeridoMixin, DetailView):
    """Editor de la planilla: todos los campos del tipo, activos o no."""

    model = TipoServicio
    template_name = "servicios/panel/campos.html"
    context_object_name = "tipo"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["campos"] = self.object.campos.all()
        return contexto


class CampoFormularioMixin(AdministradorRequeridoMixin, FormView):
    form_class = CampoPlanillaForm
    template_name = "servicios/panel/campo_formulario.html"
    titulo = ""

    def get_tipo_servicio(self):
        raise NotImplementedError

    def get_instancia(self):
        return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tipo_servicio"] = self.get_tipo_servicio()
        kwargs["instance"] = self.get_instancia()
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["tipo"] = self.get_tipo_servicio()
        return contexto

    def get_success_url(self):
        return reverse("panel:servicios:campos", args=[self.get_tipo_servicio().pk])

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Campo guardado.")
        return super().form_valid(form)


class CampoAltaView(CampoFormularioMixin):
    titulo = "Nuevo campo"

    def get_tipo_servicio(self):
        return get_object_or_404(TipoServicio, pk=self.kwargs["pk"])


class CampoEditarView(CampoFormularioMixin):
    titulo = "Editar campo"

    def get_instancia(self):
        if not hasattr(self, "_campo"):
            self._campo = get_object_or_404(
                CampoPlanilla.objects.select_related("tipo_servicio"),
                pk=self.kwargs["pk"],
            )
        return self._campo

    def get_tipo_servicio(self):
        return self.get_instancia().tipo_servicio


class CampoDesactivarView(AdministradorRequeridoMixin, TemplateView):
    """Confirma por GET y desactiva por POST; no hay borrado."""

    template_name = "servicios/panel/campo_desactivar.html"

    def get_campo(self):
        return get_object_or_404(
            CampoPlanilla.objects.select_related("tipo_servicio"),
            pk=self.kwargs["pk"],
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        campo = self.get_campo()
        contexto["campo"] = campo
        contexto["cancelar_url"] = reverse(
            "panel:servicios:campos", args=[campo.tipo_servicio_id]
        )
        return contexto

    def post(self, request, *args, **kwargs):
        campo = self.get_campo()
        campo.activo = False
        campo.save(update_fields=["activo"])
        messages.success(request, "Campo desactivado.")
        return redirect("panel:servicios:campos", pk=campo.tipo_servicio_id)


class CampoReactivarView(AdministradorRequeridoMixin, View):
    """Solo POST: el campo vuelve al esquema; su clave ya le pertenecía."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        campo = get_object_or_404(CampoPlanilla, pk=kwargs["pk"])
        campo.activo = True
        campo.save(update_fields=["activo"])
        messages.success(request, "Campo reactivado.")
        return redirect("panel:servicios:campos", pk=campo.tipo_servicio_id)
