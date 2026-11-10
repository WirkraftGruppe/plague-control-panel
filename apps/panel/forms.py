"""Formularios del panel."""

from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html

from apps.accounts.limites import normalizar_usuario


class FormularioIngreso(AuthenticationForm):
    """Login del panel: solo entran administradores."""

    def clean_username(self):
        return normalizar_usuario(self.cleaned_data["username"])

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.es_plataforma:
            raise ValidationError(
                format_html(
                    'Las cuentas de plataforma ingresan por <a href="{}">{}</a>.',
                    reverse("admin:index"),
                    reverse("admin:index"),
                ),
                code="plataforma",
            )
        if not user.es_administrador:
            raise ValidationError(
                "Esta cuenta no tiene acceso al panel.", code="sin_acceso"
            )
        if user.empresa is None or not user.empresa.activo:
            raise ValidationError(
                "La empresa de esta cuenta no está activa.", code="empresa_inactiva"
            )
