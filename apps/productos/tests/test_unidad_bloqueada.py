"""Pruebas del bloqueo de unidad base y modo de unidad con movimientos."""

from decimal import Decimal

from django.contrib.admin.sites import site
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.productos import services
from apps.productos.models import Producto
from apps.productos.panel_forms import ProductoForm


class UnidadBloqueadaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = una_empresa()
        cls.admin = User.objects.create_user(
            username="admin-ubl",
            password="x",
            rol=User.Rol.ADMINISTRADOR,
            empresa=cls.empresa,
        )
        cls.producto = Producto.objects.create(
            nombre_comercial="Gel",
            unidad_base="l",
            contenido_por_envase=Decimal("5"),
            empresa=cls.empresa,
        )

    def _form(self, modo):
        return ProductoForm(
            {
                "nombre_comercial": "Gel",
                "unidad_base": "l",
                "contenido_por_envase": "5",
                "modo_unidad": modo,
                "dosis_variable": "on",
                "activo": "on",
            },
            instance=Producto.objects.de_empresa(self.empresa).get(pk=self.producto.pk),
            empresa=self.empresa,
        )

    def test_modo_unidad_con_movimientos_da_error(self):
        otro = next(
            valor
            for valor, _ in Producto._meta.get_field("modo_unidad").choices
            if valor != self.producto.modo_unidad
        )
        self.assertTrue(self._form(otro).is_valid())
        services.registrar_ingreso(self.producto, Decimal("1"), False, self.admin)
        form = self._form(otro)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "No se puede cambiar el modo de unidad de un producto con "
            "movimientos de stock.",
            form.errors["modo_unidad"],
        )

    def test_admin_unidades_de_solo_lectura_con_movimientos(self):
        admin_producto = site._registry[Producto]
        peticion = RequestFactory().get("/admin/")
        peticion.user = User(rol=User.Rol.PLATAFORMA, is_superuser=True, is_staff=True)
        antes = admin_producto.get_readonly_fields(peticion, self.producto)
        self.assertNotIn("modo_unidad", antes)
        services.registrar_ingreso(self.producto, Decimal("1"), False, self.admin)
        despues = admin_producto.get_readonly_fields(peticion, self.producto)
        self.assertIn("unidad_base", despues)
        self.assertIn("modo_unidad", despues)
