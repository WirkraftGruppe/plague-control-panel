"""Mapa de sitios: estado y vencimiento más cercano de los puntos de cada sitio."""

from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.sitios.estado import resumen_de_sitios
from apps.sitios.models import Sitio

ORIGEN_TESELAS = "https://tile.openstreetmap.org"


def _url(nombre, sitio):
    """URL de una ruta del panel para el sitio, o None mientras no exista."""
    try:
        return reverse(nombre, args=[sitio.pk])
    except NoReverseMatch:
        return None


def url_ficha(sitio):
    """URL de la ficha del sitio, o None mientras la ruta no exista."""
    return _url("panel:sitios:ficha", sitio)


def sitios_para_mapa(cliente=None, servicio=None, estado=None):
    """Sitios activos con coordenadas, en un número fijo de consultas.

    El color del sitio es el peor estado por vencimiento de sus puntos activos y
    `vencimiento` la fecha más próxima. `servicio` deja los sitios con algún punto
    activo de ese servicio.
    """
    sitios = Sitio.objects.filter(
        activo=True, latitud__isnull=False, longitud__isnull=False
    ).select_related("cliente")
    if cliente:
        sitios = sitios.filter(cliente_id=cliente)
    if servicio:
        sitios = sitios.filter(
            puntos__activo=True, puntos__servicio_id=servicio
        ).distinct()

    sitios = list(sitios)
    resumen = resumen_de_sitios(sitios, timezone.localdate())
    resultado = []
    for sitio in sitios:
        color, vencimiento = resumen[sitio.pk]
        if estado and color != estado:
            continue
        resultado.append(
            {
                "id": sitio.pk,
                "nombre": sitio.nombre,
                "cliente": sitio.cliente.razon_social,
                "lat": float(sitio.latitud),
                "lng": float(sitio.longitud),
                "estado": color.value,
                "vencimiento": vencimiento.isoformat() if vencimiento else None,
                "url_ficha": url_ficha(sitio),
                "url_nuevo_turno": _url("panel:visitas:nuevo_turno", sitio),
            }
        )
    return resultado
