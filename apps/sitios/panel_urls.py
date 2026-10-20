"""Rutas del panel de Sitios."""

from django.urls import path

from . import panel_views as vistas

app_name = "sitios"

urlpatterns = [
    path("", vistas.SitioListado.as_view(), name="listado"),
    path("nuevo/", vistas.SitioAlta.as_view(), name="alta"),
    path("geocodificar/", vistas.Geocodificar.as_view(), name="geocodificar"),
    path("<int:pk>/", vistas.SitioFicha.as_view(), name="ficha"),
    path("<int:pk>/editar/", vistas.SitioEdicion.as_view(), name="editar"),
    path("<int:pk>/puntos/nuevo/", vistas.PuntoAlta.as_view(), name="punto_alta"),
    path("<int:pk>/planos/nuevo/", vistas.PlanoAlta.as_view(), name="plano_alta"),
    path("planos/<int:pk>/imagen/", vistas.PlanoImagen.as_view(), name="plano_imagen"),
    path("puntos/<int:pk>/editar/", vistas.PuntoEdicion.as_view(), name="punto_editar"),
    path(
        "puntos/<int:pk>/desactivar/",
        vistas.PuntoDesactivar.as_view(),
        name="punto_desactivar",
    ),
    path("puntos/<int:pk>/qr.png", vistas.PuntoQRPng.as_view(), name="punto_qr_png"),
    path(
        "puntos/<int:pk>/regenerar-qr/",
        vistas.PuntoRegenerarQR.as_view(),
        name="punto_regenerar_qr",
    ),
    path(
        "puntos/<int:pk>/programacion/",
        vistas.PuntoProgramacion.as_view(),
        name="punto_programacion",
    ),
    path(
        "puntos/<int:pk>/posicion/",
        vistas.PuntoPosicion.as_view(),
        name="punto_posicion",
    ),
]
