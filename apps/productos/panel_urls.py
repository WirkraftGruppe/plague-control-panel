"""Rutas del panel de Productos."""

from django.urls import path

from . import panel_views

app_name = "productos"

urlpatterns = [
    path("", panel_views.ProductoListadoView.as_view(), name="listado"),
    path("nuevo/", panel_views.ProductoAltaView.as_view(), name="alta"),
    path("<int:pk>/", panel_views.ProductoFichaView.as_view(), name="ficha"),
    path(
        "<int:pk>/movimientos/nuevo/",
        panel_views.MovimientoAltaView.as_view(),
        name="movimiento_alta",
    ),
    path("<int:pk>/editar/", panel_views.ProductoEditarView.as_view(), name="editar"),
]
