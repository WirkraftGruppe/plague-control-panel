"""Rutas de API de Visitas (se montan en la raíz de la API)."""

from django.urls import path

from . import api_views

app_name = "visitas"

urlpatterns = [
    path("me/visitas/", api_views.MisVisitasView.as_view(), name="mis-visitas"),
    path("visitas/abrir/", api_views.AbrirVisitaView.as_view(), name="abrir"),
    path(
        "visitas/<int:pk>/cerrar/", api_views.CerrarVisitaView.as_view(), name="cerrar"
    ),
    path(
        "visitas/<int:pk>/no-revisados/",
        api_views.ReportarNoRevisadoView.as_view(),
        name="no-revisados",
    ),
    path("revisiones/", api_views.CrearRevisionView.as_view(), name="revision"),
    path("me/historial/", api_views.HistorialView.as_view(), name="historial"),
    path("fotos/<uuid:codigo>/", api_views.FotoView.as_view(), name="foto"),
]
