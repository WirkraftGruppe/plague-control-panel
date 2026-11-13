"""Serializers transversales de la API."""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.limites import normalizar_usuario


class TokenNormalizadoSerializer(TokenObtainPairSerializer):
    """Normaliza el usuario igual que el panel antes de autenticar."""

    @classmethod
    def get_token(cls, user):
        """No emite tokens a `plataforma` ni a un usuario de una empresa inactiva."""
        if user.es_plataforma:
            raise AuthenticationFailed(
                cls.default_error_messages["no_active_account"], "no_active_account"
            )
        if user.empresa is not None and not user.empresa.activo:
            raise AuthenticationFailed(
                "La empresa está inactiva.", code="empresa_inactiva"
            )
        return super().get_token(user)

    def validate(self, attrs):
        campo = self.username_field
        attrs[campo] = normalizar_usuario(attrs.get(campo))
        return super().validate(attrs)
