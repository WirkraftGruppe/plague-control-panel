"""Vistas del panel de Productos: catálogo con alta y edición (sin borrado)."""

from django.contrib import messages
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, FormView, UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.panel.listados import ListadoPanelMixin

from . import services
from .models import MovimientoStock, Producto
from .panel_forms import MovimientoForm, ProductoForm


class ProductoListadoView(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = Producto
    template_name = "productos/panel/listado.html"
    template_parcial = "productos/panel/_listado.html"
    orden_permitido = ("nombre_comercial", "principio_activo", "registro", "activo")
    campos_busqueda = ("nombre_comercial", "principio_activo", "registro")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                stock_total=Coalesce(
                    Sum("movimientos__cantidad_base"),
                    Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=4),
                )
            )
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        for producto in contexto["object_list"]:
            producto.envases_total = services.envases(producto, producto.stock_total)
        return contexto


class ProductoFormularioMixin(AdministradorRequeridoMixin):
    model = Producto
    form_class = ProductoForm
    template_name = "productos/panel/formulario.html"
    success_url = reverse_lazy("panel:productos:listado")

    def form_valid(self, form):
        messages.success(self.request, "Producto guardado.")
        return super().form_valid(form)


class ProductoAltaView(ProductoFormularioMixin, CreateView):
    titulo = "Nuevo producto"


class ProductoEditarView(ProductoFormularioMixin, UpdateView):
    titulo = "Editar producto"


class ProductoFichaView(AdministradorRequeridoMixin, DetailView):
    """Ficha con stock, envases e historial de movimientos."""

    model = Producto
    template_name = "productos/panel/ficha.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        total = services.stock(self.object)
        contexto["stock"] = total
        contexto["envases"] = services.envases(self.object, total)
        contexto["movimientos"] = self.object.movimientos.select_related("usuario")[:50]
        return contexto


class MovimientoAltaView(AdministradorRequeridoMixin, FormView):
    """Alta de ingresos y ajustes; los movimientos no se editan ni se borran."""

    form_class = MovimientoForm
    template_name = "productos/panel/movimiento_formulario.html"

    @cached_property
    def producto(self):
        return get_object_or_404(Producto, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["producto"] = self.producto
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["producto"] = self.producto
        return contexto

    def form_valid(self, form):
        datos = form.cleaned_data
        if datos["tipo"] == MovimientoStock.Tipo.INGRESO:
            services.registrar_ingreso(
                self.producto,
                datos["cantidad"],
                datos["en_envases"],
                self.request.user,
                datos["nota"],
            )
        else:
            services.registrar_ajuste(
                self.producto, datos["cantidad"], self.request.user, datos["nota"]
            )
        messages.success(self.request, "Movimiento registrado.")
        return redirect("panel:productos:ficha", pk=self.producto.pk)
