from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as UserManagerBase
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class UserManager(UserManagerBase):
    """`create_superuser` crea `plataforma` salvo que reciba un `rol` explícito."""

    use_in_migrations = False

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if "rol" not in extra_fields and extra_fields.get("empresa") is not None:
            raise ValueError(
                "Un superusuario con empresa necesita un rol de empresa explícito "
                "(administrador o empleado): el rol plataforma no tiene empresa."
            )
        extra_fields.setdefault("rol", "plataforma")
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Usuario del sistema. `rol` decide el acceso al panel y a la API."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        EMPLEADO = "empleado", "Empleado"
        PLATAFORMA = "plataforma", "Plataforma"

    rol = models.CharField(
        "rol", max_length=15, choices=Rol.choices, default=Rol.EMPLEADO
    )
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    # Nula solo para el rol plataforma, que no pertenece a ninguna empresa.
    empresa = models.ForeignKey(
        "empresas.Empresa",
        verbose_name="empresa",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
    )

    objects = UserManager()

    history = HistoricalRecords(excluded_fields=["password", "last_login"])

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(rol="plataforma", empresa__isnull=True)
                    | (~models.Q(rol="plataforma") & models.Q(empresa__isnull=False))
                ),
                name="usuario_empresa_segun_rol",
                violation_error_message=(
                    "El rol plataforma no tiene empresa; los demás roles la exigen."
                ),
            )
        ]

    @property
    def es_administrador(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_empleado(self):
        return self.rol == self.Rol.EMPLEADO

    @property
    def es_plataforma(self):
        return self.rol == self.Rol.PLATAFORMA

    def clean(self):
        """Administrador y empleado exigen empresa; plataforma no puede tenerla."""
        super().clean()
        if self.rol == self.Rol.PLATAFORMA:
            if self.empresa_id is not None:
                raise ValidationError(
                    {"empresa": "El rol plataforma no puede tener empresa."}
                )
        elif self.empresa_id is None:
            raise ValidationError(
                {"empresa": "Los administradores y empleados exigen una empresa."}
            )

    def save(self, *args, **kwargs):
        """Guarda sin historial cuando solo se actualiza `last_login` (cada login)."""
        update_fields = kwargs.get("update_fields")
        solo_last_login = update_fields is not None and set(update_fields) == {
            "last_login"
        }
        # Solo se borra la marca si la puso este método, no el llamador.
        puso_marca = solo_last_login and not hasattr(self, "skip_history_when_saving")
        if puso_marca:
            self.skip_history_when_saving = True
        try:
            super().save(*args, **kwargs)
        finally:
            if puso_marca:
                del self.skip_history_when_saving
