"""Pruebas de las unidades de medida y su conversión."""

from decimal import Decimal

from django.test import SimpleTestCase

from apps.productos import unidades
from apps.productos.models import Producto


class UnidadesTests(SimpleTestCase):
    def test_dos_litros_son_0_5283_galones(self):
        self.assertEqual(
            unidades.convertir(Decimal("2"), "l", "gal"), Decimal("0.5283")
        )

    def test_otra_magnitud_lanza_error(self):
        with self.assertRaises(ValueError):
            unidades.convertir(Decimal("1"), "l", "kg")

    def test_conteo_solo_admite_unidad(self):
        self.assertEqual(unidades.unidades_de("conteo"), ["unidad"])
        with self.assertRaises(ValueError):
            unidades.convertir(Decimal("1"), "unidad", "g")

    def test_conversion_redondea_half_up_a_4_decimales(self):
        self.assertEqual(
            unidades.convertir(Decimal("1"), "lb", "kg"), Decimal("0.4536")
        )
        self.assertEqual(
            unidades.convertir(Decimal("1500"), "ml", "l"), Decimal("1.5000")
        )

    def test_unidades_permitidas_segun_modo(self):
        unica = Producto(unidad_base="l", modo_unidad="unica")
        equivalentes = Producto(unidad_base="l", modo_unidad="equivalentes")
        self.assertEqual(unidades.unidades_permitidas(unica), ["l"])
        self.assertEqual(unidades.unidades_permitidas(equivalentes), ["ml", "l", "gal"])
