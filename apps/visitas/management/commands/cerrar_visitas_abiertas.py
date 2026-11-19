"""Cierra por sistema las visitas abiertas que llevan demasiado tiempo.

Cierra las abiertas hace más de VISITA_ABIERTA_MAXIMO_HORAS, salvo las que
tuvieron actividad recibida dentro de ese plazo; y, sin excepción, toda abierta
hace más de VISITA_ABIERTA_TOPE_HORAS, aunque tenga actividad reciente.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import OperationalError
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.empresas.consultas import sin_filtro_empresa
from apps.visitas.models import PuntoNoRevisado, Revision, Visita
from apps.visitas.services import cerrar_visita

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Cierra con cierre=sistema las visitas abiertas hace más de "
        "VISITA_ABIERTA_MAXIMO_HORAS sin actividad reciente y toda abierta hace más "
        "de VISITA_ABIERTA_TOPE_HORAS (pensado para un cron diario)."
    )

    def handle(self, *args, **options):
        limite = timezone.now() - timedelta(hours=settings.VISITA_ABIERTA_MAXIMO_HORAS)
        # Una visita con actividad recibida dentro del plazo no se cierra: el
        # teléfono pudo trabajar sin conexión y sincronizar recién ahora.
        con_actividad = {"visita": OuterRef("pk"), "recibida_en__gte": limite}
        con_reporte = {"visita": OuterRef("pk"), "creado__gte": limite}
        tope = timedelta(hours=settings.VISITA_ABIERTA_TOPE_HORAS)
        limite_tope = timezone.now() - tope
        # Cron de plataforma: recorre las visitas de todas las empresas.
        with sin_filtro_empresa():
            sin_actividad = (
                Q(abierta_en__lt=limite, actualizado__lt=limite)
                & ~Q(Exists(Revision.objects.filter(**con_actividad)))
                & ~Q(Exists(PuntoNoRevisado.objects.filter(**con_reporte)))
            )
            abiertas = list(
                Visita.objects.filter(estado=Visita.Estado.ABIERTA)
                .filter(sin_actividad | Q(abierta_en__lt=limite_tope))
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
