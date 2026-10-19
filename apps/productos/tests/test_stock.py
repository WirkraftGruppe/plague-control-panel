"""Pruebas del stock: suma de movimientos con signo."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import User
from apps.productos import services
from apps.productos.models import MovimientoStock, Producto


class StockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(
            username="admin-stock", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def crear_producto(self, **kwargs):
        datos = {
            "nombre_comercial": "Cebo",
            "unidad_base": "l",
            "contenido_por_envase": Decimal("5"),
        }
        datos.update(kwargs)
        return Producto.objects.create(**datos)

    def test_ingreso_de_3_envases_de_5_l_suma_15_l(self):
        producto = self.crear_producto()
        movimiento = services.registrar_ingreso(
            producto, Decimal("3"), True, self.usuario, "compra"
        )
        self.assertEqual(movimiento.cantidad_base, Decimal("15"))
        self.assertEqual(movimiento.tipo, MovimientoStock.Tipo.INGRESO)
        self.assertEqual(services.stock(producto), Decimal("15"))

    def test_stock_puede_quedar_negativo(self):
        producto = self.crear_producto()
        services.registrar_ingreso(producto, Decimal("2"), False, self.usuario)
        consumo = services.registrar_consumo(producto, Decimal("3.5"), self.usuario)
        self.assertEqual(consumo.cantidad_base, Decimal("-3.5"))
        self.assertEqual(services.stock(producto), Decimal("-1.5"))

    def test_contenido_por_envase_debe_ser_positivo(self):
        producto = self.crear_producto(contenido_por_envase=Decimal("0"))
        with self.assertRaises(ValidationError):
            producto.full_clean()

    def test_stock_sin_movimientos_es_cero(self):
        self.assertEqual(services.stock(self.crear_producto()), Decimal("0"))

    def test_ingreso_y_ajuste_validan_la_cantidad(self):
        producto = self.crear_producto()
        with self.assertRaises(ValueError):
            services.registrar_ingreso(producto, Decimal("0"), False, self.usuario)
        with self.assertRaises(ValueError):
            services.registrar_ajuste(producto, Decimal("0"), self.usuario)

    def test_envases_a_dos_decimales_sin_ceros_sobrantes(self):
        producto = self.crear_producto()
        self.assertEqual(str(services.envases(producto, Decimal("15"))), "3")
        self.assertEqual(str(services.envases(producto, Decimal("7.5"))), "1.5")
        self.assertEqual(str(services.envases(producto, Decimal("-7.5"))), "-1.5")
