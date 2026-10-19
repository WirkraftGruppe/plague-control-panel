"""Rutas del panel de gestión."""

from django.urls import include, path

from . import estado, views

app_name = "panel"

urlpatterns = [
    path("", views.InicioView.as_view(), name="inicio"),
    path("mapa/", views.MapaView.as_view(), name="mapa"),
    path("mapa/datos/", views.MapaDatosView.as_view(), name="mapa_datos"),
    path("ingresar/", views.IngresarView.as_view(), name="ingresar"),
    path("salir/", views.SalirView.as_view(), name="salir"),
    path(
        "sitios/<int:pk>/estado/", estado.EstadoSitioView.as_view(), name="estado_sitio"
    ),
    path("sitios/", include("apps.sitios.panel_urls")),
    path("clientes/", include("apps.clientes.panel_urls")),
    path("servicios/", include("apps.servicios.panel_urls")),
    path("proyectos/", include("apps.proyectos.panel_urls")),
    path("productos/", include("apps.productos.panel_urls")),
    path("visitas/", include("apps.visitas.panel_urls")),
    path("informes/", include("apps.informes.panel_urls")),
    path("usuarios/", include("apps.accounts.panel_urls")),
]
