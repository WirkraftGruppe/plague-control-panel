"""Pruebas del choque de slug en una carrera de altas de TipoServicio."""

from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.empresas.pruebas import crear_empresa
from apps.servicios.models import TipoServicio


class SlugConcurrenteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = crear_empresa("Empresa Carrera")

    def test_choque_de_slug_reintenta_con_sufijo(self):
        """Si otro alta ganó la carrera por el slug, se reintenta con `-2`."""
        TipoServicio.objects.create(empresa=self.empresa, nombre="Roedores")
        original = TipoServicio._slug_libre
        llamadas = []

        def simulado(instancia):
            llamadas.append(1)
            if len(llamadas) == 1:
                return "roedores"  # ya tomado: simula la carrera
            return original(instancia)

        with patch.object(
            TipoServicio, "_slug_libre", autospec=True, side_effect=simulado
        ):
            nuevo = TipoServicio.objects.create(empresa=self.empresa, nombre="Roedores")
        self.assertEqual(nuevo.slug, "roedores-2")
        self.assertEqual(len(llamadas), 2)

    def test_slug_explicito_repetido_no_se_reintenta(self):
        TipoServicio.objects.create(empresa=self.empresa, nombre="Roedores")
        with self.assertRaises(IntegrityError), transaction.atomic():
            TipoServicio.objects.create(
                empresa=self.empresa, nombre="Otro", slug="roedores"
            )
