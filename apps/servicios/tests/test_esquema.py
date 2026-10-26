"""Pruebas del esquema de planilla de un tipo de servicio."""

from django.test import TestCase

from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import CampoPlanilla, TipoServicio


class EsquemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tipo = TipoServicio.objects.create(
            nombre="Esquema", slug="esquema", empresa=una_empresa()
        )
        for orden, clave, activo in ((2, "b", True), (1, "a", True), (3, "c", False)):
            CampoPlanilla.objects.create(
                tipo_servicio=cls.tipo,
                orden=orden,
                etiqueta=clave.upper(),
                clave=clave,
                tipo=CampoPlanilla.Tipo.TEXTO,
                activo=activo,
            )

    def test_omite_inactivos_y_ordena(self):
        claves = [c["clave"] for c in self.tipo.esquema_planilla()]
        self.assertEqual(claves, ["a", "b"])

    def test_usa_el_prefetch(self):
        tipo = TipoServicio.objects.prefetch_related("campos").get(pk=self.tipo.pk)
        with self.assertNumQueries(0):
            esquema = tipo.esquema_planilla()
        self.assertEqual(len(esquema), 2)
