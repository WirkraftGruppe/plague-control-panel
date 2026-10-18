"""Vistas públicas de los sitios."""

from django.shortcuts import render


def qr(request, codigo):
    """Aterrizaje de un QR en el navegador: no consulta la base ni usa el código."""
    return render(request, "sitios/publico/qr.html")
