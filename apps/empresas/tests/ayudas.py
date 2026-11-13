"""Ayudas de los tests de todas las apps: una empresa común por test."""

from apps.empresas.models import Empresa

NOMBRE_EMPRESA_DE_PRUEBA = "Empresa de prueba"


def una_empresa():
    """La empresa de prueba del test en curso (se crea la primera vez)."""
    return Empresa.objects.get_or_create(nombre=NOMBRE_EMPRESA_DE_PRUEBA)[0]
