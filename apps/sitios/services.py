"""Servicios de Sitios: supresión de datos, QR y ubicación de los puntos."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError

from .models import Plano, PuntoControl, Sitio

TOPE_REGENERAR_QR = 20


def suprimir_sitio(sitio):
    """Suprime el sitio y su historial (Ley 25.326).

    Si el sitio tiene visitas, ``ProtectedError`` se propaga y no se borra nada.
    """
    with transaction.atomic():
        pk = sitio.pk
        sitio.delete()
        Sitio.history.filter(id=pk).delete()
        PuntoControl.history.filter(sitio_id=pk).delete()
        Plano.history.filter(sitio_id=pk).delete()


def suprimir_sitios(sitios):
    """Suprime cada sitio por separado.

    Devuelve ``(suprimidos, con_visitas)``: la cantidad suprimida y la lista de
    sitios que no se pudieron suprimir por tener visitas.
    """
    suprimidos = 0
    con_visitas = []
    for sitio in sitios:
        try:
            suprimir_sitio(sitio)
        except ProtectedError:
            con_visitas.append(sitio)
        else:
            suprimidos += 1
    return suprimidos, con_visitas


def regenerar_qr(punto):
    """Genera un nuevo ``qr_codigo`` del punto (invalida la etiqueta impresa).

    Deja el motivo en el historial.
    """
    punto.qr_codigo = uuid.uuid4()
    punto.qr_impreso_el = None
    punto._change_reason = "Regeneración de QR"
    punto.save(update_fields=["qr_codigo", "qr_impreso_el"])
    return punto.qr_codigo


def regenerar_qr_lote(puntos):
    """Regenera el QR de varios puntos; rechaza el lote si supera ``TOPE_REGENERAR_QR``.

    Devuelve la cantidad de puntos regenerados.
    """
    if len(puntos) > TOPE_REGENERAR_QR:
        raise ValidationError(
            f"No se pueden regenerar más de {TOPE_REGENERAR_QR} códigos QR a la vez "
            f"(se seleccionaron {len(puntos)})."
        )
    with transaction.atomic():
        for punto in puntos:
            regenerar_qr(punto)
    return len(puntos)


def _bloquear_punto(punto):
    """Relee el punto bloqueando la fila (dentro de un ``atomic``), con su sitio."""
    return (
        PuntoControl.objects.select_for_update(no_key=True, of=("self",))
        .select_related("sitio__cliente")
        .get(pk=punto.pk)
    )


def fijar_ubicacion(punto, latitud, longitud):
    """Fija lat/lng del punto (clic en el mapa) y deja el motivo en el historial."""
    with transaction.atomic():
        bloqueado = _bloquear_punto(punto)
        bloqueado.latitud = latitud
        bloqueado.longitud = longitud
        bloqueado.ubicacion_fijada_por = None
        bloqueado.ubicacion_fijada_en = None
        bloqueado.precision_m = None
        bloqueado._change_reason = "Ubicación fijada en el mapa"
        bloqueado.save(
            update_fields=[
                "latitud",
                "longitud",
                "ubicacion_fijada_por",
                "ubicacion_fijada_en",
                "precision_m",
            ]
        )
    punto.latitud, punto.longitud = bloqueado.latitud, bloqueado.longitud


def mover_en_plano(punto, x, y):
    """Guarda la posición del marcador en el plano (fracción 0 a 1)."""
    punto.x = x
    punto.y = y
    punto._change_reason = "Marcador movido en el plano"
    punto.save(update_fields=["x", "y"])


def ubicar_en_plano(punto, plano, x, y):
    """Ubica el punto en un plano de su mismo sitio, con x e y entre 0 y 1."""
    if plano.sitio_id != punto.sitio_id:
        raise ValidationError("El plano es de otro sitio.")
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise ValidationError("La posición debe estar entre 0 y 1.")
    punto.plano = plano
    punto.x = x
    punto.y = y
    punto._change_reason = "Punto ubicado en el plano"
    punto.save(update_fields=["plano", "x", "y"])


def desactivar_punto(punto):
    """Da de baja el punto: conserva sus revisiones, pero deja de pedirse.

    Rechaza desactivar el último punto activo: el sitio se quedaría sin QR vigente.
    """
    with transaction.atomic():
        activos = list(
            PuntoControl.objects.select_for_update()
            .filter(sitio_id=punto.sitio_id, activo=True)
            .values_list("pk", flat=True)
        )
        if activos == [punto.pk]:
            raise ValidationError("No se puede desactivar el último punto activo.")
        punto.activo = False
        punto._change_reason = "Punto desactivado"
        punto.save(update_fields=["activo"])


def _exigir_precision(precision_m):
    """El modo campo solo fija coordenadas con una precisión de GPS suficiente."""
    if precision_m is None or precision_m > settings.PRECISION_MAXIMA_M:
        raise ValidationError(
            "La precisión del GPS debe ser de "
            f"{settings.PRECISION_MAXIMA_M} m o mejor para fijar la ubicación."
        )


def _exigir_activo(sitio):
    if not sitio.activo or not sitio.cliente.activo:
        raise ValidationError("El sitio o su cliente están inactivos.")


def crear_sitio_en_campo(
    *,
    administrador,
    cliente,
    nombre,
    direccion,
    localidad,
    latitud,
    longitud,
    precision_m,
):
    """Alta de un sitio (con su punto General) hecha por un administrador en campo."""
    if not cliente.activo:
        raise ValidationError("El cliente está inactivo.")
    _exigir_precision(precision_m)
    sitio = Sitio(
        cliente=cliente,
        nombre=nombre,
        direccion=direccion,
        localidad=localidad,
        latitud=latitud,
        longitud=longitud,
        precision_m=precision_m,
    )
    sitio._history_user = administrador
    sitio._change_reason = "Alta en campo desde la app"
    sitio.save()
    return sitio


def crear_punto_en_campo(
    *,
    administrador,
    sitio,
    nombre,
    sector,
    latitud=None,
    longitud=None,
    precision_m=None,
    foto=None,
):
    """Alta de un punto hecha por un administrador; con coordenadas exige precisión."""
    _exigir_activo(sitio)
    if latitud is not None or longitud is not None:
        _exigir_precision(precision_m)
    ultimo = sitio.puntos.order_by("-orden").values_list("orden", flat=True).first()
    punto = PuntoControl(
        sitio=sitio,
        nombre=nombre,
        sector=sector,
        orden=(ultimo or 0) + 1,
        latitud=latitud,
        longitud=longitud,
        precision_m=precision_m if latitud is not None else None,
        foto=foto,
    )
    punto._history_user = administrador
    punto._change_reason = "Alta en campo desde la app"
    punto.save()
    return punto


def fijar_ubicacion_en_campo(*, administrador, punto, latitud, longitud, precision_m):
    """Fija lat/lng del punto desde el GPS de un administrador."""
    _exigir_precision(precision_m)
    with transaction.atomic():
        bloqueado = _bloquear_punto(punto)
        _exigir_activo(bloqueado.sitio)
        if not bloqueado.activo:
            raise ValidationError("El punto está inactivo.")
        bloqueado.latitud = latitud
        bloqueado.longitud = longitud
        bloqueado.precision_m = precision_m
        bloqueado.ubicacion_fijada_por = None
        bloqueado.ubicacion_fijada_en = None
        bloqueado._history_user = administrador
        bloqueado._change_reason = "Ubicación fijada en campo desde la app"
        bloqueado.save(
            update_fields=[
                "latitud",
                "longitud",
                "precision_m",
                "ubicacion_fijada_por",
                "ubicacion_fijada_en",
            ]
        )
    punto.latitud, punto.longitud = bloqueado.latitud, bloqueado.longitud
    punto.precision_m = bloqueado.precision_m


def actualizar_programacion(
    punto, servicio, frecuencia_dias, proximo_vencimiento, usuario
):
    """Guarda servicio, frecuencia y vencimiento del punto, con motivo en el historial.

    Editar la frecuencia no recalcula el vencimiento.
    """
    with transaction.atomic():
        bloqueado = _bloquear_punto(punto)
        bloqueado.servicio = servicio
        bloqueado.frecuencia_dias = frecuencia_dias
        bloqueado.proximo_vencimiento = proximo_vencimiento
        bloqueado._change_reason = "Programación editada"
        bloqueado._history_user = usuario
        bloqueado.save(
            update_fields=["servicio", "frecuencia_dias", "proximo_vencimiento"]
        )
    punto.servicio = servicio
    punto.frecuencia_dias = frecuencia_dias
    punto.proximo_vencimiento = proximo_vencimiento
    return punto
