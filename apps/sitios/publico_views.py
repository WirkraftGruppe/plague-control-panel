"""Vistas públicas de los sitios."""

from django.shortcuts import render


def qr(request, codigo):
    """Aterrizaje de un QR en el navegador: no consulta la base ni usa el código."""
    respuesta = render(request, "sitios/publico/qr.html")
    respuesta["X-Robots-Tag"] = "noindex, nofollow"
    return respuesta
