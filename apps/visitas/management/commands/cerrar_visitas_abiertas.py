"""Cierra por sistema las abiertas hace más de VISITA_ABIERTA_MAXIMO_HORAS.

No cierra las que tuvieron actividad recibida dentro de ese plazo.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import OperationalError
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.empresas.consultas import sin_filtro_empresa
from apps.visitas.models import PuntoNoRevisado, Revision, Visita
from apps.visitas.services import cerrar_visita

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Cierra con cierre=sistema las visitas abiertas hace más de "
        "VISITA_ABIERTA_MAXIMO_HORAS (pensado para un cron diario)."
    )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=settings.VISITA_ABIERTA_MAXIMO_HORAS)
        # Una visita con actividad recibida dentro del plazo no se cierra: el
        # teléfono pudo trabajar sin conexión y sincronizar recién ahora.
        con_actividad = {"visita": OuterRef("pk"), "recibida_en__gte": limite}
        con_reporte = {"visita": OuterRef("pk"), "creado__gte": limite}
        # Cron de plataforma: recorre las visitas de todas las empresas.
        with sin_filtro_empresa():
            abiertas = list(
                Visita.objects.filter(
                    estado=Visita.Estado.ABIERTA,
                    abierta_en__lt=limite,
                    actualizado__lt=limite,
                )
                .exclude(Exists(Revision.objects.filter(**con_actividad)))
                .exclude(Exists(PuntoNoRevisado.objects.filter(**con_reporte)))
                .order_by("abierta_en", "pk")
            )
        cerradas = 0
        for visita in abiertas:
            try:
                cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
            except ValidationError:
                logger.exception("No se pudo cerrar la visita %s.", visita.pk)
                continue
            except OperationalError:
                # Bloqueo no disponible o interbloqueo: queda para la próxima corrida.
                logger.exception("Falla de base al cerrar la visita %s.", visita.pk)
                continue
            cerradas += 1
        self.stdout.write(f"Visitas cerradas por sistema: {cerradas}")
