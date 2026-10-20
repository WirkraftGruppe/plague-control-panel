"""Rutas del panel de Servicios ; ninguna ruta borra servicios ni campos."""

from django.urls import path

from . import panel_views

app_name = "servicios"

urlpatterns = [
    path("", panel_views.TipoServicioListadoView.as_view(), name="listado"),
    path(
        "nuevo/",
        panel_views.TipoServicioAltaView.as_view(),
        name="servicio_alta",
    ),
    path(
        "<int:pk>/editar/",
        panel_views.TipoServicioEditarView.as_view(),
        name="servicio_editar",
    ),
    path("<int:pk>/campos/", panel_views.CamposView.as_view(), name="campos"),
    path(
        "<int:pk>/campos/nuevo/",
        panel_views.CampoAltaView.as_view(),
        name="campo_alta",
    ),
    path(
        "campos/<int:pk>/editar/",
        panel_views.CampoEditarView.as_view(),
        name="campo_editar",
    ),
    path(
        "campos/<int:pk>/desactivar/",
        panel_views.CampoDesactivarView.as_view(),
        name="campo_desactivar",
    ),
    path(
        "campos/<int:pk>/reactivar/",
        panel_views.CampoReactivarView.as_view(),
        name="campo_reactivar",
    ),
]
