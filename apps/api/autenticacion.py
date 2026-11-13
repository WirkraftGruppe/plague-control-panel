"""Autenticación de sesión de la API que exige una empresa activa."""

from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SesionAutenticacionEmpresa(SessionAuthentication):
    """Rechaza la sesión sin empresa (`plataforma`) o con empresa inactiva."""

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado is None:
            return None
        empresa = resultado[0].empresa
        if empresa is None or not empresa.activo:
            raise AuthenticationFailed(
                "La sesión no pertenece a una empresa activa.",
                code="empresa_inactiva",
            )
        return resultado
