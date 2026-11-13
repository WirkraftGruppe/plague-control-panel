"""Vistas de API de Productos."""

import hashlib
import json

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permisos import EsAdministrador, EsEmpleado
from apps.empresas.consultas import empresa_de

from .models import Producto
from .serializers import ProductoSerializer


class CatalogoView(APIView):
    """Catálogo completo de productos activos, sin paginar y con ETag."""

    permission_classes = [EsEmpleado | EsAdministrador]

    @extend_schema(
        summary="Catálogo de productos activos",
        description=(
            "Lista completa y sin paginar de los productos activos. "
            "Devuelve un `ETag`; con `If-None-Match` igual responde 304 sin cuerpo."
        ),
        responses={
            200: ProductoSerializer(many=True),
            304: OpenApiResponse(description="El catálogo no cambió."),
        },
    )
    def get(self, request):
        """Devuelve los productos activos o 304 si el ETag del cliente coincide."""
        productos = Producto.objects.de_empresa(empresa_de(request)).filter(activo=True)
        datos = ProductoSerializer(productos, many=True).data
        contenido = json.dumps(datos, sort_keys=True, ensure_ascii=False)
        etag = '"%s"' % hashlib.sha256(contenido.encode("utf-8")).hexdigest()
        if request.headers.get("If-None-Match") == etag:
            respuesta = Response(status=304)
        else:
            respuesta = Response(datos)
        respuesta["ETag"] = etag
        return respuesta
