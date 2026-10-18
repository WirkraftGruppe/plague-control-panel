"""Modelos de Clientes."""

from django.core.validators import RegexValidator
from django.db import models

from apps.clientes.validators import validar_cuit


class Cliente(models.Model):
    """Empresa o persona a la que la empresa presta servicios."""

    razon_social = models.CharField("razón social", max_length=200)
    cuit = models.CharField(
        "CUIT",
        max_length=11,
        blank=True,
        validators=[
            RegexValidator(r"^\d{11}$", "El CUIT debe tener 11 dígitos, sin guiones."),
            validar_cuit,
        ],
    )
    contacto_nombre = models.CharField("nombre de contacto", max_length=150, blank=True)
    contacto_telefono = models.CharField(
        "teléfono de contacto", max_length=30, blank=True
    )
    contacto_email = models.EmailField("email de contacto", blank=True)
    notas = models.TextField("notas", blank=True)
    activo = models.BooleanField("activo", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["razon_social"]

    def __str__(self):
        return self.razon_social
