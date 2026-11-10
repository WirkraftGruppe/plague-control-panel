from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.empresas.pruebas import crear_empresa
from apps.servicios.models import TipoServicio


class SlugPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = crear_empresa("Empresa A")
        cls.b = crear_empresa("Empresa B")

    def test_mismo_slug_en_dos_empresas(self):
        en_a = TipoServicio.objects.create(empresa=self.a, nombre="Roedores")
        en_b = TipoServicio.objects.create(empresa=self.b, nombre="Roedores")
        self.assertEqual(en_a.slug, "roedores")
        self.assertEqual(en_b.slug, "roedores")
        with self.assertRaises(IntegrityError), transaction.atomic():
            TipoServicio.objects.create(empresa=self.a, nombre="Otro", slug="roedores")

    def test_mismo_nombre_en_una_empresa_da_slugs_distintos(self):
        primero = TipoServicio.objects.create(empresa=self.a, nombre="Roedores")
        segundo = TipoServicio.objects.create(empresa=self.a, nombre="Roedores")
        tercero = TipoServicio.objects.create(empresa=self.a, nombre="Roedores")
        self.assertEqual(
            [primero.slug, segundo.slug, tercero.slug],
            ["roedores", "roedores-2", "roedores-3"],
        )
