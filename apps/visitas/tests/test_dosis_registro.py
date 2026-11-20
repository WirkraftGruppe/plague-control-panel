"""Dosis de un producto aplicado: la define el producto salvo que sea variable."""

from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.empresas.tests.ayudas import una_empresa
from apps.productos.models import Producto
from apps.visitas.models import ProductoAplicado
from apps.visitas.services import abrir_visita
from apps.visitas.tests.test_turnos import BaseTurnoTests


class DosisRegistroTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.visita, _ = abrir_visita(
            empleado=self.empleado, qr_codigo=self.general.qr_codigo
        )

    def producto_con(self, **campos):
        return Producto.objects.create(
            nombre_comercial="Concentrado",
            unidad_base="ml",
            modo_unidad="equivalentes",
            empresa=una_empresa(),
            **campos,
        )

    def aplicar(self, producto, **cambios):
        item = {"producto": producto.pk, "lote": "L1", "cantidad": "10", "unidad": "ml"}
        item.update(cambios)
        self.revisar(self.visita, self.general, productos_aplicados=[item])
        return ProductoAplicado.objects.de_empresa(una_empresa()).get()

    def test_sin_dosis_variable_y_sin_dosis_guarda_habitual(self):
        producto = self.producto_con(
            dosis_habitual=Decimal("5"), unidad_dosis_habitual="ml/l"
        )
        aplicado = self.aplicar(producto)
        self.assertEqual((aplicado.dosis, aplicado.unidad_dosis), (5, "ml/l"))

    def test_sin_dosis_variable_ignora_dosis_enviada(self):
        producto = self.producto_con(
            dosis_habitual=Decimal("5"), unidad_dosis_habitual="ml/l"
        )
        aplicado = self.aplicar(producto, dosis="9", unidad_dosis="g/l")
        self.assertEqual((aplicado.dosis, aplicado.unidad_dosis), (5, "ml/l"))

    def test_sin_dosis_habitual_guarda_nada(self):
        aplicado = self.aplicar(self.producto_con(), dosis="9", unidad_dosis="g/l")
        self.assertEqual((aplicado.dosis, aplicado.unidad_dosis), (None, ""))

    def test_con_dosis_variable_guarda_la_enviada(self):
        producto = self.producto_con(
            dosis_variable=True,
            dosis_habitual=Decimal("5"),
            unidad_dosis_habitual="ml/l",
        )
        aplicado = self.aplicar(producto, dosis="9", unidad_dosis="g/l")
        self.assertEqual((aplicado.dosis, aplicado.unidad_dosis), (9, "g/l"))

    def test_con_dosis_variable_sin_dosis_guarda_habitual(self):
        producto = self.producto_con(
            dosis_variable=True,
            dosis_habitual=Decimal("5"),
            unidad_dosis_habitual="ml/l",
        )
        aplicado = self.aplicar(producto)
        self.assertEqual((aplicado.dosis, aplicado.unidad_dosis), (5, "ml/l"))

    def test_lote_sigue_obligatorio_en_la_posicion_del_producto(self):
        producto = self.producto_con(dosis_variable=True)
        bueno = {"producto": producto.pk, "lote": "L1", "cantidad": "1", "unidad": "ml"}
        malo = dict(bueno, lote="")
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(self.visita, self.general, productos_aplicados=[bueno, malo])
        self.assertIn("productos_aplicados.1.lote", contexto.exception.message_dict)
