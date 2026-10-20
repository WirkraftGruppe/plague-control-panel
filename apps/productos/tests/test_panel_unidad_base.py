"""Pruebas del bloqueo del cambio de unidad base con movimientos."""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.productos import services
from apps.productos.models import Producto
from apps.productos.panel_forms import ProductoForm


class UnidadBaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-ub", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.producto = Producto.objects.create(
            nombre_comercial="Gel", unidad_base="l", contenido_por_envase=Decimal("5")
        )

    def _form(self, unidad):
        return ProductoForm(
            {
                "nombre_comercial": "Gel",
                "unidad_base": unidad,
                "contenido_por_envase": "5",
                "modo_unidad": "unica",
                "activo": "on",
            },
            instance=self.producto,
        )

    def test_cambiar_unidad_base_con_movimientos_da_error(self):
        services.registrar_ingreso(self.producto, Decimal("1"), False, self.admin)
        form = self._form("kg")
        self.assertFalse(form.is_valid())
        self.assertIn(
            "No se puede cambiar la unidad base de un producto con "
            "movimientos de stock.",
            form.errors["unidad_base"],
        )

    def test_sin_movimientos_se_puede_cambiar(self):
        self.assertTrue(self._form("kg").is_valid())
