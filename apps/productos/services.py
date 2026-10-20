"""Reglas de stock de Productos: el stock es la suma de sus movimientos."""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Sum

from .models import MovimientoStock
from .unidades import validar_cantidad_base


def stock(producto):
    """Stock actual en unidad base (puede ser negativo)."""
    total = producto.movimientos.aggregate(total=Sum("cantidad_base"))["total"]
    return total or Decimal("0")


def envases(producto, cantidad_base):
    """Envases equivalentes a `cantidad_base`, a 2 decimales sin ceros sobrantes."""
    valor = (cantidad_base / producto.contenido_por_envase).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return valor.normalize() if valor else Decimal("0")


def _crear(producto, tipo, cantidad_base, usuario, nota):
    return MovimientoStock.objects.create(
        producto=producto,
        tipo=tipo,
        cantidad_base=cantidad_base,
        usuario=usuario,
        nota=nota,
    )


def registrar_ingreso(producto, cantidad, en_envases, usuario, nota=""):
    """Suma stock; con `en_envases` la cantidad se multiplica por el contenido."""
    cantidad = Decimal(cantidad)
    if cantidad <= 0:
        raise ValueError("El ingreso debe ser mayor que cero.")
    if en_envases:
        cantidad *= producto.contenido_por_envase
    validar_cantidad_base(cantidad)
    return _crear(producto, MovimientoStock.Tipo.INGRESO, cantidad, usuario, nota)


def registrar_ajuste(producto, cantidad_base, usuario, nota=""):
    """Corrige el stock con una cantidad con signo distinta de cero."""
    cantidad_base = Decimal(cantidad_base)
    if cantidad_base == 0:
        raise ValueError("El ajuste no puede ser cero.")
    validar_cantidad_base(cantidad_base)
    return _crear(producto, MovimientoStock.Tipo.AJUSTE, cantidad_base, usuario, nota)


def registrar_consumo(producto, cantidad_base, usuario, nota=""):
    """Descuenta stock: crea un movimiento negativo y lo devuelve."""
    cantidad_base = Decimal(cantidad_base)
    if cantidad_base <= 0:
        raise ValueError("El consumo debe ser mayor que cero.")
    return _crear(producto, MovimientoStock.Tipo.CONSUMO, -cantidad_base, usuario, nota)
