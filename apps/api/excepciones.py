"""Manejador de excepciones: todo error sale como `{"detalle", "campos"}`."""

import logging

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as ErrorDeDjango
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

DETALLE_VALIDACION = "Hay datos inválidos."
DETALLE_INTERNO = "Error interno del servidor."


def _como_lista(valor):
    if isinstance(valor, (list, tuple)):
        return [str(item) for item in valor]
    return [str(valor)]


def _aplanar(datos, ruta, campos, generales):
    """Aplana errores anidados en `campos` con claves con punto (`a.0.b`).

    Los `non_field_errors` de primer nivel van a `generales` (el `detalle`); los
    anidados, a `campos` bajo su ruta (`productos_aplicados.0`).
    """
    if isinstance(datos, dict):
        for clave, valor in datos.items():
            if clave == "non_field_errors":
                if ruta:
                    campos.setdefault(ruta, []).extend(_como_lista(valor))
                else:
                    generales.extend(_como_lista(valor))
            else:
                _aplanar(
                    valor, f"{ruta}.{clave}" if ruta else str(clave), campos, generales
                )
    elif isinstance(datos, (list, tuple)) and any(
        isinstance(item, (dict, list, tuple)) for item in datos
    ):
        for indice, item in enumerate(datos):
            _aplanar(
                item, f"{ruta}.{indice}" if ruta else str(indice), campos, generales
            )
    elif ruta:
        campos.setdefault(ruta, []).extend(_como_lista(datos))
    else:
        generales.extend(_como_lista(datos))


def _detalle_legible(exc, respuesta):
    """Texto del error sin el repr de `ErrorDetail` ni estructuras anidadas."""
    detalle = respuesta.data.get("detail") if isinstance(respuesta.data, dict) else None
    if detalle is None or isinstance(detalle, (dict, list, tuple)):
        detalle = getattr(exc, "default_detail", "")
    return str(detalle)


def manejar_excepcion(exc, contexto):
    """Respuesta uniforme; las excepciones no previstas no exponen su texto."""
    if isinstance(exc, ErrorDeDjango):
        if hasattr(exc, "error_dict"):
            errores = dict(exc.message_dict)
            if NON_FIELD_ERRORS in errores:
                errores["non_field_errors"] = errores.pop(NON_FIELD_ERRORS)
        else:
            errores = exc.messages
        exc = ValidationError(errores)
    respuesta = exception_handler(exc, contexto)
    if respuesta is None:
        logger.exception("Excepción no controlada en la API", exc_info=exc)
        return Response(
            {"detalle": DETALLE_INTERNO, "campos": {}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    campos = {}
    if isinstance(exc, ValidationError):
        generales = []
        _aplanar(respuesta.data, "", campos, generales)
        detalle = " ".join(generales) or DETALLE_VALIDACION
    else:
        detalle = _detalle_legible(exc, respuesta)
    respuesta.data = {"detalle": detalle, "campos": campos}
    return respuesta
