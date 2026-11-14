"""Vistas transversales de la API: raíz y tokens JWT."""

import math
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.defaults import page_not_found
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.limites import (
    _baldes,
    _fallos_vigentes,
    baldes_llenos,
    limpiar_usuario_ip,
    registrar_fallo,
)
from apps.accounts.red import ip_del_cliente
from apps.empresas.consultas import empresa_de

from .serializers import TokenNormalizadoSerializer


class IpDelClienteMixin:
    """Identifica al cliente con `ip_del_cliente` y no con `X-Forwarded-For` crudo."""

    def get_ident(self, request):
        return ip_del_cliente(request)


class ThrottleToken(IpDelClienteMixin, AnonRateThrottle):
    """Limita los pedidos anónimos de obtener tokens, por IP."""

    scope = "token"


class ThrottleRenovacion(IpDelClienteMixin, AnonRateThrottle):
    """Cupo propio para renovar tokens, aparte del de obtenerlos."""

    scope = "renovacion"
    rate = "30/min"


class RenovacionSerializer(TokenRefreshSerializer):
    """Rechaza renovar si el usuario no existe o cambió su contraseña."""

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        usuario = (
            get_user_model()
            .objects.select_related("empresa")
            .filter(
                **{
                    api_settings.USER_ID_FIELD: refresh.payload.get(
                        api_settings.USER_ID_CLAIM
                    )
                }
            )
            .first()
        )
        reclamo = refresh.payload.get(api_settings.REVOKE_TOKEN_CLAIM)
        if usuario is None or reclamo != get_md5_hash_password(usuario.password):
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )
        if usuario.es_plataforma:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )
        if usuario.empresa is not None and not usuario.empresa.activo:
            raise AuthenticationFailed("La empresa está inactiva.", "empresa_inactiva")
        return super().validate(attrs)


def segundos_de_espera(request, usuario):
    """Segundos hasta que el balde de usuario lleno libere un lugar (`Retry-After`)."""
    ahora = time.time()
    esperas = []
    for clave, maximo, ventana in _baldes(request, usuario)[1:]:
        fallos = sorted(_fallos_vigentes(clave, ventana, ahora))
        if len(fallos) >= maximo:
            esperas.append(fallos[len(fallos) - maximo] + ventana - ahora)
    return max(1, math.ceil(max(esperas, default=settings.VENTANA_MINUTOS * 60)))


def no_encontrado(request, exception):
    """404 JSON de la API bajo `/api/`; el resto, la página HTML de Django."""
    if request.path.startswith("/api/"):
        return JsonResponse({"detalle": "No encontrado.", "campos": {}}, status=404)
    return page_not_found(request, exception)


RAIZ = inline_serializer(
    "Raiz",
    {
        "usuario": inline_serializer(
            "RaizUsuario",
            {
                "id": serializers.IntegerField(),
                "nombre_completo": serializers.CharField(),
                "username": serializers.CharField(),
            },
        ),
        "empresa": inline_serializer(
            "RaizEmpresa",
            {"id": serializers.IntegerField(), "nombre": serializers.CharField()},
            allow_null=True,
        ),
        "rol": serializers.CharField(),
    },
)


class RaizView(APIView):
    """Con los permisos por defecto: anónimo 401, autenticado ve quién es."""

    @extend_schema(responses=RAIZ)
    def get(self, request):
        usuario = request.user
        empresa = empresa_de(request)
        return Response(
            {
                "usuario": {
                    "id": usuario.pk,
                    "nombre_completo": usuario.get_full_name() or usuario.username,
                    "username": usuario.username,
                },
                "empresa": (
                    {"id": empresa.pk, "nombre": empresa.nombre}
                    if empresa is not None
                    else None
                ),
                "rol": usuario.rol,
            }
        )


TOKENS = inline_serializer(
    "Tokens",
    {"access": serializers.CharField(), "refresh": serializers.CharField()},
)
RESPUESTAS_DE_CONTRATO = {
    415: OpenApiResponse(description="El cuerpo no es JSON (`Content-Type`)."),
    429: OpenApiResponse(description="Demasiados intentos; reintentar más tarde."),
}


@extend_schema(
    summary="Obtener tokens",
    description="Intercambia usuario y contraseña por un par de tokens JWT.",
    responses={
        200: TOKENS,
        400: OpenApiResponse(description="Falta el usuario o la contraseña."),
        401: OpenApiResponse(description="Credenciales inválidas o cuenta inactiva."),
        **RESPUESTAS_DE_CONTRATO,
    },
)
class ObtenerToken(TokenObtainPairView):
    """Obtiene el token; comparte con el panel los baldes de fallos por usuario."""

    serializer_class = TokenNormalizadoSerializer
    parser_classes = [JSONParser]
    throttle_classes = [ThrottleToken]

    def post(self, request, *args, **kwargs):
        usuario = (
            request.data.get("username", "") if hasattr(request.data, "get") else ""
        )
        usuario = "" if usuario is None else str(usuario)
        if baldes_llenos(request, usuario, solo_usuario=True):
            raise Throttled(wait=segundos_de_espera(request, usuario))
        try:
            respuesta = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            registrar_fallo(request, usuario, solo_usuario=True)
            raise
        limpiar_usuario_ip(request, usuario)
        return respuesta


@extend_schema(
    summary="Renovar el token de acceso",
    description=(
        "Entrega un nuevo token de acceso y un nuevo token de renovación; el "
        "token de renovación enviado queda invalidado, así que hay que guardar "
        "el nuevo. Falla si el usuario ya no existe o cambió su contraseña."
    ),
    responses={
        200: TOKENS,
        401: OpenApiResponse(description="Token de renovación inválido o vencido."),
        415: RESPUESTAS_DE_CONTRATO[415],
        429: RESPUESTAS_DE_CONTRATO[429],
    },
)
class RenovarToken(TokenRefreshView):
    serializer_class = RenovacionSerializer
    parser_classes = [JSONParser]
    throttle_classes = [ThrottleRenovacion]
