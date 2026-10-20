"""Unidades de medida de los productos y conversión entre ellas (sin `float`)."""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError

VOLUMEN = "volumen"
MASA = "masa"
CONTEO = "conteo"

# código -> (magnitud, factor a la unidad de referencia de la magnitud: l, kg, unidad)
UNIDADES = {
    "ml": (VOLUMEN, Decimal("0.001")),
    "l": (VOLUMEN, Decimal("1")),
    "gal": (VOLUMEN, Decimal("3.785411784")),
    "g": (MASA, Decimal("0.001")),
    "kg": (MASA, Decimal("1")),
    "lb": (MASA, Decimal("0.45359237")),
    "unidad": (CONTEO, Decimal("1")),
}

CHOICES = [(codigo, codigo) for codigo in UNIDADES]

CUANTO = Decimal("0.0001")

# Mayor valor que cabe en MovimientoStock.cantidad_base (14 dígitos, 4 decimales)
MAXIMO_CANTIDAD_BASE = Decimal("9999999999.9999")


def validar_cantidad_base(valor):
    """Lanza `ValidationError` si `valor` (en unidad base) no cabe en el campo."""
    if abs(Decimal(valor)) > MAXIMO_CANTIDAD_BASE:
        raise ValidationError(
            "La cantidad es demasiado grande: supera el máximo de "
            f"{MAXIMO_CANTIDAD_BASE} en unidad base."
        )


def magnitud_de(unidad):
    """Magnitud (volumen, masa o conteo) de una unidad; `ValueError` si no existe."""
    if unidad not in UNIDADES:
        raise ValueError(f"Unidad desconocida: {unidad}")
    return UNIDADES[unidad][0]


def unidades_de(magnitud):
    """Códigos de las unidades de una magnitud, en el orden del diccionario."""
    return [codigo for codigo, (mag, _) in UNIDADES.items() if mag == magnitud]


def convertir(cantidad, desde, hacia):
    """Convierte `cantidad` entre unidades de la misma magnitud, a 4 decimales."""
    if magnitud_de(desde) != magnitud_de(hacia):
        raise ValueError(f"No se puede convertir {desde} a {hacia}: distinta magnitud.")
    resultado = Decimal(cantidad) * UNIDADES[desde][1] / UNIDADES[hacia][1]
    return resultado.quantize(CUANTO, rounding=ROUND_HALF_UP)


def unidades_permitidas(producto):
    """Unidades en que se puede cargar la cantidad de un producto."""
    if producto.modo_unidad == "equivalentes":
        return unidades_de(magnitud_de(producto.unidad_base))
    return [producto.unidad_base]
