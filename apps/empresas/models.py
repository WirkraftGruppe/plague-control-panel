import uuid

from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ObjectDoesNotExist,
    ValidationError,
)
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

    # La base la exige; `blank=True` porque `save()` copia la empresa del padre y
    # hay altas de hijos que validan antes de eso.
    empresa = models.ForeignKey(
        Empresa,
        verbose_name="empresa",
        on_delete=models.PROTECT,
        related_name="+",
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

    @classmethod
    def from_db(cls, db, field_names, values):
        """Recuerda la empresa con la que se cargó el registro (sin consulta extra)."""
        instancia = super().from_db(db, field_names, values)
        if "empresa_id" in instancia.__dict__:
            instancia._empresa_original = instancia.__dict__["empresa_id"]
        return instancia

    # Empresa guardada en la base; `None` en las altas y en los registros sin empresa.
    _empresa_original = None

    def _empresa_cambiada(self):
        """Indica si se intenta cambiar la empresa ya fijada de un registro guardado."""
        if self._state.adding:
            return False
        if self._empresa_original is None or "empresa_id" not in self.__dict__:
            return False
        return self.empresa_id != self._empresa_original

    def save(self, *args, **kwargs):
        campos = kwargs.get("update_fields")
        if (campos is None or "empresa" in campos or "empresa_id" in campos) and (
            self._empresa_cambiada()
        ):
            raise ValueError(
                f"La empresa de {type(self).__name__} no se puede cambiar "
                "después del alta."
            )
        sin_empresa = self.empresa_id is None
        self._heredar_empresa()
        if sin_empresa and self.empresa_id is not None and campos is not None:
            kwargs["update_fields"] = {*campos, "empresa"}
        super().save(*args, **kwargs)
        self._empresa_original = self.empresa_id

    def _empresa_de(self, nombre):
        """Empresa de la FK `nombre`; `None` si el objeto referido no existe."""
        try:
            return getattr(self, nombre).empresa_id
        except ObjectDoesNotExist:
            return None

    def clean(self):
        """Rechaza el cambio de empresa y las referencias a otra empresa.

        Usa la empresa efectiva: la propia o, si falta, la del padre (que `save()`
        copiará). Los campos sin empresa fijada no se comparan.
        """
        super().clean()
        if self._empresa_cambiada():
            raise ValidationError(
                {NON_FIELD_ERRORS: "La empresa no se puede cambiar después del alta."}
            )
        errores = {}
        efectiva = self.empresa_id
        padre = self.padre_de_empresa
        if padre and getattr(self, f"{padre}_id") is not None:
            empresa_padre = self._empresa_de(padre)
            if efectiva is None:
                efectiva = empresa_padre
            elif empresa_padre is not None and empresa_padre != efectiva:
                errores[padre] = "Pertenece a otra empresa."
        if efectiva is not None:
            for nombre in self.referencias_de_empresa:
                if getattr(self, f"{nombre}_id") is None:
                    continue
                empresa_referido = self._empresa_de(nombre)
                if empresa_referido is not None and empresa_referido != efectiva:
                    errores[nombre] = "Pertenece a otra empresa."
        if errores:
            raise ValidationError(errores)

    def validate_unique(self, exclude=None):
        with sin_filtro_empresa():
            super().validate_unique(exclude)

    def validate_constraints(self, exclude=None):
        with sin_filtro_empresa():
            super().validate_constraints(exclude)
