"""Serializers de la API de la empresa."""

from rest_framework import serializers


class EmpresaSerializer(serializers.Serializer):
    """Datos de la empresa para la app: nombre y URL absoluta del logo."""

    nombre = serializers.CharField(read_only=True)
    logo = serializers.URLField(read_only=True, allow_null=True)
