"""Postproceso del esquema OpenAPI: respuestas 401 y 429 comunes."""

ESQUEMA_ERROR = {
    "type": "object",
    "properties": {
        "detalle": {"type": "string"},
        "campos": {
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
    },
    "required": ["detalle", "campos"],
}
REF_ERROR = {"$ref": "#/components/schemas/Error"}
RESPUESTA_401 = {
    "description": "Falta autenticación o es inválida.",
    "content": {"application/json": {"schema": REF_ERROR}},
}
RESPUESTA_429 = {
    "description": "Demasiados pedidos; reintentar tras `Retry-After`.",
    "headers": {
        "Retry-After": {
            "description": "Segundos de espera antes de reintentar.",
            "schema": {"type": "integer"},
        }
    },
    "content": {"application/json": {"schema": REF_ERROR}},
}


def _con_throttle(vista):
    return bool(getattr(vista, "throttle_scope", None)) or any(
        getattr(clase, "scope", None) for clase in vista.throttle_classes
    )


def agregar_respuestas_comunes(result, generator, request, public):
    """Agrega 401 a toda operación con seguridad y 429 a las que tienen throttle.

    No pisa lo que `extend_schema` ya declaró.
    """
    vistas = {
        (ruta, metodo.lower()): vista
        for ruta, _regex, metodo, vista in generator._get_paths_and_endpoints()
    }
    for ruta, operaciones in result.get("paths", {}).items():
        for metodo, operacion in operaciones.items():
            respuestas = operacion.setdefault("responses", {})
            if any(operacion.get("security") or []):
                respuestas.setdefault("401", RESPUESTA_401)
            vista = vistas.get((ruta, metodo))
            if vista is not None and _con_throttle(vista):
                respuestas.setdefault("429", RESPUESTA_429)
    result.setdefault("components", {}).setdefault("schemas", {}).setdefault(
        "Error", ESQUEMA_ERROR
    )
    return result
