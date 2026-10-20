"""Rutas del panel de Visitas."""

from django.urls import path

from . import panel_views

app_name = "visitas"

urlpatterns = [
    path("", panel_views.ListadoVisitas.as_view(), name="listado"),
    path("<int:pk>/", panel_views.FichaVisita.as_view(), name="ficha"),
    path(
        "<int:pk>/revisar-incidencia/",
        panel_views.RevisarIncidencia.as_view(),
        name="revisar_incidencia",
    ),
    path("fotos/<uuid:codigo>/", panel_views.FotoVisita.as_view(), name="foto"),
    path(
        "sitios/<int:sitio_pk>/turnos/nuevo/",
        panel_views.NuevoTurnoView.as_view(),
        name="nuevo_turno",
    ),
    path(
        "sitios/<int:sitio_pk>/cargar/",
        panel_views.CargarVisitaView.as_view(),
        name="cargar",
    ),
]
