"""Cierra por sistema las visitas abiertas hace más de VISITA_ABIERTA_MAXIMO_HORAS."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import OperationalError
from django.utils import timezone

from apps.empresas.consultas import sin_filtro_empresa
from apps.visitas.models import Visita
from apps.visitas.services import cerrar_visita

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Cierra con cierre=sistema las visitas abiertas hace más de "
        "VISITA_ABIERTA_MAXIMO_HORAS (pensado para un cron diario)."
    )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=settings.VISITA_ABIERTA_MAXIMO_HORAS)
        # Cron de plataforma: recorre las visitas de todas las empresas.
        with sin_filtro_empresa():
            abiertas = list(
                Visita.objects.filter(
                    estado=Visita.Estado.ABIERTA, abierta_en__lt=limite
                ).order_by("abierta_en", "pk")
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
