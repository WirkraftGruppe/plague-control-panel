"""Cantidad con unidad y consumo de stock al registrar una revisión por la API."""

import json
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.productos.models import MovimientoStock, Producto
from apps.productos.services import registrar_ingreso, stock
from apps.visitas.models import ProductoAplicado, Revision
from apps.visitas.tests.test_api import ApiVisitasBase


class StockRevisionApiTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta()
        self.galones = Producto.objects.create(
            nombre_comercial="Concentrado en galones",
            unidad_base="gal",
            modo_unidad="equivalentes",
        )
        registrar_ingreso(self.galones, Decimal("10"), False, self.empleado)

    def _item(self, producto=None, **cambios):
        item = {
            "producto": (producto or self.galones).pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad_dosis": "ml/l",
            "cantidad": "2",
            "unidad": "l",
        }
        item.update(cambios)
        return item

    def _enviar(self, items, **cambios):
        return self._post(self.visita, productos_aplicados=json.dumps(items), **cambios)

    def _consumos(self):
        return MovimientoStock.objects.filter(tipo=MovimientoStock.Tipo.CONSUMO)

    def test_dos_litros_en_producto_en_galones_guarda_0_5283_y_descuenta(self):
        r = self._enviar([self._item()])
        self.assertEqual(r.status_code, 201, r.content)
        aplicado = ProductoAplicado.objects.get()
        self.assertEqual(aplicado.cantidad_base, Decimal("0.5283"))
        self.assertEqual((aplicado.cantidad, aplicado.unidad), (Decimal("2"), "l"))
        self.assertEqual(aplicado.unidad_dosis, "ml/l")
        self.assertEqual(aplicado.movimiento.cantidad_base, Decimal("-0.5283"))
        self.assertEqual(aplicado.movimiento.usuario, self.empleado)
        self.assertEqual(stock(self.galones), Decimal("9.4717"))
        item = r.data["productos"][0]
        self.assertEqual(item["unidad_dosis"], "ml/l")
        self.assertEqual(item["cantidad_base"], "0.5283")

    def _comprobar_400_en_unidad(self, producto, unidad):
        r = self._enviar([self._item(producto, unidad=unidad)])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("productos_aplicados.0.unidad", r.data["campos"])
        self.assertFalse(Revision.objects.exists())
        self.assertFalse(self._consumos().exists())

    def test_modo_unica_con_otra_unidad_da_400_en_el_producto(self):
        unica = Producto.objects.create(
            nombre_comercial="Solo litros", unidad_base="l", modo_unidad="unica"
        )
        self._comprobar_400_en_unidad(unica, "ml")

    def test_unidad_de_otra_magnitud_da_400(self):
        self._comprobar_400_en_unidad(self.galones, "kg")

    def test_foto_invalida_no_deja_movimiento(self):
        falsa = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        r = self._enviar([self._item()], fotos=[falsa])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(ProductoAplicado.objects.exists())
        self.assertFalse(self._consumos().exists())
        self.assertEqual(stock(self.galones), Decimal("10"))

    def test_cantidad_es_obligatoria(self):
        sin_cantidad = self._item()
        del sin_cantidad["cantidad"]
        r = self._enviar([sin_cantidad, self._item(cantidad="0")])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("productos_aplicados.0.cantidad", r.data["campos"])
        self.assertIn("productos_aplicados.1.cantidad", r.data["campos"])
        self.assertFalse(Revision.objects.exists())
