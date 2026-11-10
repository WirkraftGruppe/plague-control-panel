"""Vistas del panel de Clientes."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.clientes.empresa import VistaDeEmpresaMixin
from apps.clientes.models import Cliente
from apps.clientes.panel_forms import ClienteForm
from apps.panel.listados import ListadoPanelMixin


class ClienteListadoView(
    VistaDeEmpresaMixin, AdministradorRequeridoMixin, ListadoPanelMixin
):
    """Listado con búsqueda por razón social o CUIT y filtro por activo."""

    model = Cliente
    template_name = "clientes/panel/listado.html"
    template_parcial = "clientes/panel/_listado.html"
    campos_busqueda = ("razon_social", "cuit")
    orden_permitido = ("razon_social", "cuit", "creado")

    def get_activo(self):
        valor = self.request.GET.get("activo", "")
        return valor if valor in ("1", "0") else ""

    def get_queryset(self):
        queryset = super().get_queryset()
        activo = self.get_activo()
        if activo:
            queryset = queryset.filter(activo=activo == "1")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        activo = self.get_activo()
        contexto["activo"] = activo
        if activo:
            separador = "&" if contexto["querystring"] else ""
            contexto["querystring"] += f"{separador}activo={activo}"
        return contexto


class ClienteAltaView(VistaDeEmpresaMixin, AdministradorRequeridoMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/panel/formulario.html"

    def get_success_url(self):
        messages.success(self.request, "Cliente creado.")
        return reverse("panel:clientes:ficha", args=[self.object.pk])


class ClienteEditarView(VistaDeEmpresaMixin, AdministradorRequeridoMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/panel/formulario.html"

    def get_success_url(self):
        messages.success(self.request, "Cliente actualizado.")
        return reverse("panel:clientes:ficha", args=[self.object.pk])


class ClienteFichaView(VistaDeEmpresaMixin, AdministradorRequeridoMixin, DetailView):
    model = Cliente
    template_name = "clientes/panel/ficha.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["sitios"] = self.object.sitios.order_by("nombre")
        return contexto


class ClienteBajaView(AdministradorRequeridoMixin, View):
    """GET pide confirmación; POST da de baja (activo=False) sin borrar."""

    def get(self, request, pk):
        cliente = get_object_or_404(Cliente.objects.de_empresa(request.empresa), pk=pk)
        return render(request, "clientes/panel/baja.html", {"cliente": cliente})

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente.objects.de_empresa(request.empresa), pk=pk)
        cliente.activo = False
        cliente.save(update_fields=["activo", "actualizado"])
        messages.success(request, "Cliente dado de baja.")
        return redirect("panel:clientes:ficha", pk=cliente.pk)
