"""Formularios del panel de usuarios; no exponen contraseña ni permisos de Django."""

from django import forms
from django.contrib.auth import get_user_model, password_validation

User = get_user_model()

CAMPOS = ["username", "first_name", "last_name", "email", "telefono", "rol"]


class UsuarioEdicionForm(forms.ModelForm):
    """Edición de datos y rol; no toca la contraseña.

    El rol `plataforma` no se ofrece: un administrador no puede crear ni promover
    cuentas del operador de la plataforma. Si recibe `empresa`, la fija en la
    instancia antes de validar (la empresa no es un campo del formulario).
    """

    class Meta:
        model = User
        fields = CAMPOS

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa is not None:
            self.instance.empresa = empresa
        self.fields["rol"].choices = [
            opcion for opcion in User.Rol.choices if opcion[0] != User.Rol.PLATAFORMA
        ]


class UsuarioAltaForm(UsuarioEdicionForm):
    """Alta con doble contraseña validada con los validadores de Django."""

    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label="Repetir contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    password_validation.validate_password(p1, self.instance)
                except forms.ValidationError as error:
                    self.add_error("password2", error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario
