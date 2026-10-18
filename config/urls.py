"""Rutas raíz del proyecto."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("panel/", include("apps.panel.urls")),
    path("api/v1/", include("apps.api.urls")),
    # /q/<uuid>/: la página que abren los QR impresos.
    path("", include("apps.sitios.publico_urls")),
    # Sin sitio público: la raíz lleva al login del panel (destino fijo, sin parámetros).
    path("", RedirectView.as_view(pattern_name="panel:ingresar", permanent=False)),
]
