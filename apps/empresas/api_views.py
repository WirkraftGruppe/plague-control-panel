"""Vistas de la API de la empresa: sus datos y su logo."""

from django.http import FileResponse
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permisos import EsAdministrador, EsEmpleado

from .consultas import empresa_de
from .serializers import EmpresaSerializer


class IgnorarAccept(BaseContentNegotiation):
    """Usa siempre el primer renderer: la imagen no depende del `Accept`."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class MiEmpresaView(APIView):
    """Nombre y logo de la empresa del usuario."""

    permission_classes = [EsEmpleado | EsAdministrador]

    @extend_schema(
        summary="Datos de mi empresa",
        responses={200: EmpresaSerializer},
    )
    def get(self, request):
        """Devuelve el nombre y la URL absoluta del logo (`null` si no hay)."""
        empresa = empresa_de(request)
        logo = None
        if empresa.logo:
            logo = request.build_absolute_uri(
                reverse("api:empresas:logo", args=[empresa.pk])
            )
        return Response({"nombre": empresa.nombre, "logo": logo})


class LogoView(APIView):
    """Sirve el logo de la empresa del usuario."""

    permission_classes = [EsEmpleado | EsAdministrador]
    content_negotiation_class = IgnorarAccept

    @extend_schema(
        summary="Descargar el logo de mi empresa",
        responses={
            (200, "image/png"): OpenApiTypes.BINARY,
            404: OpenApiResponse(description="Sin logo o de otra empresa."),
        },
    )
    def get(self, request, pk):
        """Devuelve el PNG; 404 si `pk` no es la empresa del usuario o no hay logo."""
        empresa = empresa_de(request)
        if empresa is None or empresa.pk != pk or not empresa.logo:
            raise NotFound("El logo no existe.")
        try:
            archivo = empresa.logo.open("rb")
        except FileNotFoundError:
            raise NotFound("El logo no existe.") from None
        respuesta = FileResponse(archivo, content_type="image/png")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta
