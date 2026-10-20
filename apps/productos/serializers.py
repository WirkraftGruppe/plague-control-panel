"""Serializers de Productos para la API."""

from rest_framework import serializers

from . import unidades
from .models import Producto


class ProductoSerializer(serializers.ModelSerializer):
    """Representación de solo lectura de un producto del catálogo."""

    unidades_permitidas = serializers.SerializerMethodField()

    def get_unidades_permitidas(self, producto) -> list[str]:
        """Unidades en que se puede cargar la cantidad aplicada."""
        return unidades.unidades_permitidas(producto)

    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre_comercial",
            "principio_activo",
            "registro",
            "presentacion",
            "unidad_dosis_por_defecto",
            "unidad_base",
            "modo_unidad",
            "unidades_permitidas",
        ]
        read_only_fields = fields
