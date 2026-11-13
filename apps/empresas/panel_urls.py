"""Rutas del panel de la empresa (`/panel/empresa/`)."""

from django.urls import path

from . import panel_views

app_name = "empresas"

urlpatterns = [
    path("", panel_views.EmpresaEditarView.as_view(), name="editar"),
    path("logo/", panel_views.EmpresaLogoView.as_view(), name="logo"),
]
