from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from . import unidades


class Producto(models.Model):
    """Producto del catálogo; las aplicaciones de las visitas siempre apuntan acá."""

    nombre_comercial = models.CharField("nombre comercial", max_length=150)
    principio_activo = models.CharField("principio activo", max_length=150, blank=True)
    registro = models.CharField(
        "registro",
        max_length=60,
        blank=True,
        help_text="Número de registro ANMAT/SENASA del producto.",
    )
    presentacion = models.CharField("presentación", max_length=100, blank=True)
    unidad_dosis_por_defecto = models.CharField(
        "unidad de dosis por defecto",
        max_length=20,
        blank=True,
        help_text="Por ejemplo: ml/l.",
    )
    unidad_base = models.CharField(
        "unidad base",
        max_length=10,
        choices=unidades.CHOICES,
        default="unidad",
        help_text="Unidad en que se lleva el stock.",
    )
    contenido_por_envase = models.DecimalField(
        "contenido por envase",
        max_digits=12,
        decimal_places=4,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0.0001"))],
        help_text="Cantidad de unidad base que trae cada envase.",
    )
    modo_unidad = models.CharField(
        "modo de unidad",
        max_length=12,
        choices=[
            ("unica", "Solo la unidad base"),
            ("equivalentes", "Unidades equivalentes"),
        ],
        default="unica",
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre_comercial"]

    def __str__(self):
        return self.nombre_comercial


class MovimientoStock(models.Model):
    """Entrada o salida de stock de un producto, en unidad base y con signo."""

    class Tipo(models.TextChoices):
        INGRESO = "ingreso", "Ingreso"
        AJUSTE = "ajuste", "Ajuste"
        CONSUMO = "consumo", "Consumo"

    producto = models.ForeignKey(
        Producto,
        verbose_name="producto",
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    cantidad_base = models.DecimalField(
        "cantidad en unidad base", max_digits=14, decimal_places=4
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="usuario",
        on_delete=models.PROTECT,
        related_name="movimientos_stock",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    nota = models.CharField("nota", max_length=200, blank=True)

    class Meta:
        verbose_name = "movimiento de stock"
        verbose_name_plural = "movimientos de stock"
        ordering = ["-creado", "-id"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad_base} de {self.producto}"
