"""Incidencias de ubicación: filtrar, ver la distancia y marcar como revisada."""

from unittest import mock

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.models import Visita
from apps.visitas.services import marcar_incidencia_revisada

from .test_models import crear_revision, crear_visita
from .test_services import espiar_bloqueos


class UbicacionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-ubi", password="x", rol=User.Rol.ADMINISTRADOR, empresa=una_empresa()
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _visita(self, **extra):
        ahora = timezone.now()
        datos = {
            "estado": Visita.Estado.REALIZADA,
            "abierta_en": ahora,
            "cerrada_en": ahora,
            "cierre": Visita.Cierre.ADMINISTRADOR,
            "origen": Visita.Origen.MANUAL,
            "motivo_manual": "Carga",
        }
        datos.update(extra)
        return crear_visita(**datos)

    def _pks(self, **parametros):
        respuesta = self.client.get(reverse("panel:visitas:listado"), parametros)
        self.assertEqual(respuesta.status_code, 200)
        return {v.pk for v in respuesta.context["visitas"]}

    def _ficha(self, visita):
        return self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))

    def _revisar(self, visita):
        return self.client.post(
            reverse("panel:visitas:revisar_incidencia", args=[visita.pk])
        )

    def test_se_puede_marcar_revisada_y_filtrar(self):
        en_visita = self._visita(incidencia_ubicacion=True, distancia_m=450)
        en_revision = self._visita()
        crear_revision(en_revision, incidencia_ubicacion=True, distancia_m=620)
        limpia = self._visita()
        crear_revision(limpia, distancia_m=10)
        self.assertEqual(
            self._pks(incidencia="ubicacion"), {en_visita.pk, en_revision.pk}
        )
        self.assertRedirects(
            self._revisar(en_revision),
            reverse("panel:visitas:ficha", args=[en_revision.pk]),
        )
        en_revision.refresh_from_db()
        self.assertEqual(en_revision.incidencia_revisada_por, self.admin)
        self.assertIsNotNone(en_revision.incidencia_revisada_en)
        # Revisada sale del filtro; sin incidencia de ubicación no se marca.
        self.assertEqual(self._pks(incidencia="ubicacion"), {en_visita.pk})
        self._revisar(limpia)
        limpia.refresh_from_db()
        self.assertIsNone(limpia.incidencia_revisada_en)
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(en_revision, self.admin)

    def test_ficha_muestra_distancia_y_boton(self):
        visita = self._visita(incidencia_ubicacion=True, distancia_m=450)
        crear_revision(visita, incidencia_ubicacion=True, distancia_m=620)
        respuesta = self._ficha(visita)
        self.assertContains(respuesta, "450 m")
        self.assertContains(respuesta, "620 m")
        self.assertContains(respuesta, "Marcar como revisada")
        self._revisar(visita)
        respuesta = self._ficha(visita)
        self.assertNotContains(respuesta, "Marcar como revisada")
        self.assertContains(respuesta, "Revisada por")
        # Solo la revisión está lejos: el botón también aparece.
        en_revision = self._visita()
        crear_revision(en_revision, incidencia_ubicacion=True, distancia_m=700)
        self.assertContains(self._ficha(en_revision), "Marcar como revisada")
        # Sin incidencia de ubicación ni general no hay botón.
        limpia = self._visita()
        crear_revision(limpia, distancia_m=12)
        respuesta = self._ficha(limpia)
        self.assertContains(respuesta, "12 m")
        self.assertNotContains(respuesta, "Marcar como revisada")

    def test_no_marca_revisada_una_visita_abierta(self):
        abierta = self._visita(
            estado=Visita.Estado.ABIERTA, cerrada_en=None, cierre="", incidencia=True
        )
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(abierta, self.admin)
        abierta.refresh_from_db()
        self.assertIsNone(abierta.incidencia_revisada_en)
        self.assertNotContains(self._ficha(abierta), "Marcar como revisada")

    def test_marcar_revisada_bloquea_la_fila(self):
        visita = self._visita(incidencia_ubicacion=True)
        with (
            espiar_bloqueos() as modelos,
            mock.patch(
                "apps.visitas.services.transaction.atomic", wraps=transaction.atomic
            ) as atomico,
        ):
            marcar_incidencia_revisada(visita, self.admin)
        self.assertEqual(modelos, [Visita])
        atomico.assert_called_once()
