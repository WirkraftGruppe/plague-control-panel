import uuid

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

    empresa = models.ForeignKey(
        Empresa, verbose_name="empresa", on_delete=models.PROTECT, related_name="+"
    )

    objects = EmpresaQuerySet.as_manager()
    todos = models.Manager()

    class Meta:
        abstract = True

    def validate_unique(self, exclude=None):
        with sin_filtro_empresa():
            super().validate_unique(exclude)

    def validate_constraints(self, exclude=None):
        with sin_filtro_empresa():
            super().validate_constraints(exclude)
