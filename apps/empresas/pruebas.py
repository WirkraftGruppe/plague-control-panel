"""Ayudas para los tests de las apps que dependen de una empresa."""

from .models import Empresa


def crear_empresa(nombre="Empresa de prueba", **campos):
    """Crea una empresa activa para un test."""
    return Empresa.objects.create(nombre=nombre, **campos)
