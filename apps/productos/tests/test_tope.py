"""Pruebas del tope de cantidad_base tras convertir."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.productos import services
from apps.productos.models import MovimientoStock, Producto
from apps.productos.panel_forms import MovimientoForm
from apps.productos.unidades import MAXIMO_CANTIDAD_BASE


class TopeCantidadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-tope", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.producto = Producto.objects.create(
            nombre_comercial="Cebo",
            unidad_base="l",
            contenido_por_envase=Decimal("1000"),
        )

    def test_ingreso_en_envases_desbordado_da_error_sin_movimiento(self):
        with self.assertRaises(ValidationError):
            services.registrar_ingreso(
                self.producto, Decimal("99999999"), True, self.admin
            )
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_formulario_de_movimiento_desbordado_da_error_en_cantidad(self):
        form = MovimientoForm(
            {"tipo": "ingreso", "cantidad": "99999999", "en_envases": "on"},
            producto=self.producto,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)

    def test_tope_exacto_se_acepta(self):
        movimiento = services.registrar_ajuste(
            self.producto, MAXIMO_CANTIDAD_BASE, self.admin
        )
        self.assertEqual(movimiento.cantidad_base, MAXIMO_CANTIDAD_BASE)
