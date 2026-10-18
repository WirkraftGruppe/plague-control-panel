"""Rutas públicas de los sitios: aterrizaje del QR de un punto de control."""

from django.urls import path

from . import publico_views

app_name = "publico"

urlpatterns = [
    path("q/<uuid:codigo>/", publico_views.qr, name="qr"),
]
