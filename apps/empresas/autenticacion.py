"""Autenticación que conoce la empresa del usuario, en la sesión y en el JWT."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password


class BackendConEmpresa(ModelBackend):
    """`ModelBackend` que carga la empresa junto con el usuario (sin consulta extra)."""

    def get_user(self, user_id):
        modelo = get_user_model()
        try:
            usuario = modelo._default_manager.select_related("empresa").get(pk=user_id)
        except modelo.DoesNotExist:
            return None
        return usuario if self.user_can_authenticate(usuario) else None


class JWTAutenticacionEmpresa(JWTAuthentication):
    """JWT que da 401 con la empresa inactiva y fija `request.empresa`."""

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado is None:
            return None
        empresa = resultado[0].empresa
        if empresa is not None and not empresa.activo:
            raise AuthenticationFailed(
                "La empresa está inactiva.", code="empresa_inactiva"
            )
        request.empresa = empresa
        # `request` es el pedido de DRF: las vistas de Django leen el de abajo.
        request._request.empresa = empresa
        return resultado

    def get_user(self, validated_token):
        """Como el de simplejwt, pero con `select_related("empresa")`."""
        try:
            id_usuario = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError as error:
            raise InvalidToken(
                "El token no trae un identificador de usuario reconocible."
            ) from error
        try:
            usuario = self.user_model.objects.select_related("empresa").get(
                **{api_settings.USER_ID_FIELD: id_usuario}
            )
        except self.user_model.DoesNotExist as error:
            raise AuthenticationFailed(
                "Usuario no encontrado.", code="user_not_found"
            ) from error
        if api_settings.CHECK_USER_IS_ACTIVE and not usuario.is_active:
            raise AuthenticationFailed("Usuario inactivo.", code="user_inactive")
        if api_settings.CHECK_REVOKE_TOKEN:
            revocacion = validated_token.get(api_settings.REVOKE_TOKEN_CLAIM)
            if revocacion != get_md5_hash_password(usuario.password):
                raise AuthenticationFailed(
                    "La contraseña del usuario cambió.", code="password_changed"
                )
        return usuario
