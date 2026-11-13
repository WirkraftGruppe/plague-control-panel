"""Rutas de API de Sitios (montadas en la raíz de `/api/v1/`)."""

from django.urls import path

from . import api_views

app_name = "sitios"

urlpatterns = [
    path(
        "qr/<str:codigo>/resolver/",
        api_views.ResolverQRView.as_view(),
        name="qr-resolver",
    ),
    path(
        "planos/<int:pk>/imagen/",
        api_views.PlanoImagenView.as_view(),
        name="plano-imagen",
    ),
    path("sitios/", api_views.AltaSitioView.as_view(), name="alta-sitio"),
    path(
        "sitios/<int:pk>/puntos/",
        api_views.AltaPuntoView.as_view(),
        name="alta-punto",
    ),
    path(
        "puntos/<int:pk>/ubicacion/",
        api_views.UbicacionPuntoView.as_view(),
        name="ubicacion-punto",
    ),
    path("me/puntos/", api_views.MisPuntosView.as_view(), name="mis-puntos"),
]
