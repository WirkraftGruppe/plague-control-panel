import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .consultas import EmpresaQuerySet, sin_filtro_empresa


def ruta_logo(instancia, nombre):
    """Ruta de almacenamiento: UUID aleatorio, nunca el nombre original."""
    return f"empresas/logos/{uuid.uuid4().hex}.png"


class Empresa(models.Model):
    """Empresa de control de plagas que usa la plataforma; dueña de sus datos."""

    nombre = models.CharField("nombre", max_length=150)
    logo = models.ImageField("logo", upload_to=ruta_logo, blank=True)
    correo_contacto = models.EmailField("correo de contacto", blank=True)
    activo = models.BooleanField("activa", default=True)
    creado = models.DateTimeField("creada", auto_now_add=True)
    modificado = models.DateTimeField("modificada", auto_now=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ModeloDeEmpresa(models.Model):
    """Base de los modelos que pertenecen a una empresa.

    `objects` (el manager por defecto) exige `.de_empresa(empresa)` para evaluarse;
    `todos` no filtra y es solo para el admin y los comandos.
    """

    # Nula en esta fase: T14 la vuelve obligatoria.
    empresa = models.ForeignKey(
        Empresa,
        verbose_name="empresa",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    # Nombre de la FK al padre de la que el hijo copia la empresa (vacío en las raíces).
    padre_de_empresa = ""
    # Nombres de las FK que deben ser de la misma empresa que el objeto.
    referencias_de_empresa = ()

    objects = EmpresaQuerySet.as_manager()
    todos = models.Manager()

    class Meta:
        abstract = True

    def _heredar_empresa(self):
        """Copia la empresa del padre si falta; lanza `ValueError` si difiere."""
        if not self.padre_de_empresa:
            return
        if getattr(self, f"{self.padre_de_empresa}_id") is None:
            return
        padre = getattr(self, self.padre_de_empresa)
        if self.empresa_id is None:
            self.empresa_id = padre.empresa_id
        elif padre.empresa_id is not None and padre.empresa_id != self.empresa_id:
            raise ValueError(
                f"La empresa de {type(self).__name__} difiere de la de su padre "
                f"({self.padre_de_empresa})."
            )

    def save(self, *args, **kwargs):
        sin_empresa = self.empresa_id is None
        self._heredar_empresa()
        campos = kwargs.get("update_fields")
        if sin_empresa and self.empresa_id is not None and campos is not None:
            kwargs["update_fields"] = {*campos, "empresa"}
        super().save(*args, **kwargs)

    def clean(self):
        """Rechaza referencias a objetos de otra empresa si ambas están fijadas."""
        super().clean()
        if self.empresa_id is None:
            return
        errores = {}
        for nombre in self.referencias_de_empresa:
            if getattr(self, f"{nombre}_id") is None:
                continue
            referido = getattr(self, nombre)
            if (
                referido.empresa_id is not None
                and referido.empresa_id != self.empresa_id
            ):
                errores[nombre] = "Pertenece a otra empresa."
        if errores:
            raise ValidationError(errores)

    def validate_unique(self, exclude=None):
        with sin_filtro_empresa():
            super().validate_unique(exclude)

    def validate_constraints(self, exclude=None):
        with sin_filtro_empresa():
            super().validate_constraints(exclude)
