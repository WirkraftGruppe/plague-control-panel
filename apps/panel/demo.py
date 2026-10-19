"""Guardas compartidas por los comandos de demostración."""

import os

from django.conf import settings
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.models import Q

from apps.clientes.models import Cliente
from apps.panel.demo_datos import (
    MARCA_DEMO,
    PATRON_CLIENTE_VIEJO,
    SLUG_TIPO_VIEJO,
    SUFIJO_PRODUCTO,
)
from apps.productos.models import MovimientoStock, Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.sitios.services import suprimir_sitio
from apps.visitas.models import ProductoAplicado, Revision, Visita

LOTE_HISTORIAL = 500


def _es_sqlite(config):
    """True solo si la base es SQLite: un HOST local puede ser un túnel a producción."""
    return config.get("ENGINE", "").endswith("sqlite3")


def exigir_entorno_demo(comando="cargar_demo"):
    """Lanza `CommandError` si el entorno no es de desarrollo local con SQLite.

    Exige DEBUG activo, `DJANGO_ENV=development` y SQLite, para que un comando de
    demostración nunca toque una base remota.
    """
    if not settings.DEBUG:
        raise CommandError(f"{comando} solo se puede ejecutar con DEBUG activo.")
    if os.environ.get("DJANGO_ENV") != "development":
        raise CommandError(f"{comando} exige DJANGO_ENV=development.")
    if not _es_sqlite(connection.settings_dict):
        raise CommandError(
            f"{comando} solo corre contra SQLite (DJANGO_ENV=development sin "
            "DATABASE_URL)."
        )


def _borrar_historial(modelo, ids):
    """Borra las filas `Historical*` de los objetos ya eliminados (por lotes)."""
    ids = list(ids)
    for inicio in range(0, len(ids), LOTE_HISTORIAL):
        modelo.history.filter(id__in=ids[inicio : inicio + LOTE_HISTORIAL]).delete()


def _clientes_demo():
    return Cliente.objects.filter(
        Q(notas__startswith=MARCA_DEMO) | Q(razon_social__regex=PATRON_CLIENTE_VIEJO)
    )


def _sitios_demo():
    """Sitios marcados y los de un cliente demo del formato viejo (sin marca)."""
    viejos = Q(
        cliente__razon_social__regex=PATRON_CLIENTE_VIEJO,
        cliente__notas="",
    )
    return Sitio.objects.filter(Q(notas__startswith=MARCA_DEMO) | viejos)


def limpiar_datos_demo():
    """Borra solo los datos de demo y devuelve cuántos sitios se eliminaron.

    Orden: visitas, proyectos, planos y puntos con sus sitios, clientes y
    productos demo, respetando los PROTECT. Los archivos de plano y foto salen
    por las señales de borrado al confirmar la transacción y las filas
    `Historical*` se borran a mano. Un cliente demo que conserva un sitio sin
    marca, o un producto ya aplicado en una visita ajena, no se toca.
    """
    with transaction.atomic():
        sitios = list(_sitios_demo())
        proyectos = Proyecto.objects.filter(sitio__in=sitios)
        visitas = Visita.objects.filter(proyecto__in=proyectos)
        ids_visitas = list(visitas.values_list("pk", flat=True))
        ids_revisiones = list(
            Revision.objects.filter(visita__in=ids_visitas).values_list("pk", flat=True)
        )
        ids_aplicados = list(
            ProductoAplicado.objects.filter(revision__in=ids_revisiones).values_list(
                "pk", flat=True
            )
        )
        ids_movimientos = list(
            ProductoAplicado.objects.filter(
                revision__in=ids_revisiones, movimiento__isnull=False
            ).values_list("movimiento_id", flat=True)
        )
        visitas.delete()
        # Los consumos van después de sus aplicados: el movimiento es PROTECT.
        MovimientoStock.objects.filter(pk__in=ids_movimientos).delete()
        _borrar_historial(Visita, ids_visitas)
        _borrar_historial(Revision, ids_revisiones)
        _borrar_historial(ProductoAplicado, ids_aplicados)
        proyectos.delete()
        for sitio in sitios:
            # Borra también el historial de sitio, proyectos, puntos y planos.
            suprimir_sitio(sitio)
        _clientes_demo().filter(sitios__isnull=True).delete()
        productos = Producto.objects.filter(
            nombre_comercial__endswith=SUFIJO_PRODUCTO, productoaplicado__isnull=True
        )
        MovimientoStock.objects.filter(producto__in=productos).delete()
        productos.delete()
        TipoServicio.objects.filter(
            slug=SLUG_TIPO_VIEJO, proyectos__isnull=True
        ).delete()
    return len(sitios)
