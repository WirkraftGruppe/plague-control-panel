"""Vistas transversales de la API: raíz y tokens JWT."""

from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
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

from apps.accounts.limites import baldes_llenos, limpiar_usuario_ip, registrar_fallo
from apps.accounts.red import ip_del_cliente

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
        if usuario.empresa is not None and not usuario.empresa.activo:
            raise AuthenticationFailed("La empresa está inactiva.", "empresa_inactiva")
        return super().validate(attrs)


class RaizView(APIView):
    """Con los permisos por defecto: anónimo 401, autenticado ve su rol."""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response({"usuario": request.user.username, "rol": request.user.rol})


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
            raise Throttled()
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
