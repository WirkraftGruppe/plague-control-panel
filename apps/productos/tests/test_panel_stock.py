"""Pruebas de la ficha de producto y del alta de movimientos en el panel."""

from decimal import Decimal

from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import User
from apps.productos import services
from apps.productos.models import MovimientoStock, Producto


class FichaProductoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-ficha", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            username="emp-ficha", password="x", rol=User.Rol.EMPLEADO
        )
        cls.producto = Producto.objects.create(
            nombre_comercial="Cebo",
            unidad_base="l",
            contenido_por_envase=Decimal("5"),
        )

    def test_ficha_muestra_3_envases(self):
        services.registrar_ingreso(self.producto, Decimal("15"), False, self.admin)
        self.client.force_login(self.admin)
        respuesta = self.client.get(
            reverse("panel:productos:ficha", args=[self.producto.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["envases"], Decimal("3"))
        self.assertContains(respuesta, "15 l")
        self.assertContains(respuesta, "<dd>3 (de 5 l)</dd>", html=True)

    def test_ficha_marca_stock_negativo(self):
        services.registrar_consumo(self.producto, Decimal("2"), self.admin)
        self.client.force_login(self.admin)
        respuesta = self.client.get(
            reverse("panel:productos:ficha", args=[self.producto.pk])
        )
        self.assertContains(respuesta, "etiqueta-danger")
        self.assertContains(respuesta, "Stock negativo")

    def test_ajuste_negativo_resta(self):
        services.registrar_ingreso(self.producto, Decimal("10"), False, self.admin)
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("panel:productos:movimiento_alta", args=[self.producto.pk]),
            {"tipo": "ajuste", "cantidad": "-4", "nota": "derrame"},
        )
        self.assertRedirects(
            respuesta, reverse("panel:productos:ficha", args=[self.producto.pk])
        )
        self.assertEqual(services.stock(self.producto), Decimal("6"))
        movimiento = MovimientoStock.objects.get(tipo="ajuste")
        self.assertEqual(movimiento.usuario, self.admin)

    def test_ingreso_en_envases_desde_el_panel(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("panel:productos:movimiento_alta", args=[self.producto.pk]),
            {"tipo": "ingreso", "cantidad": "2", "en_envases": "on"},
        )
        self.assertEqual(services.stock(self.producto), Decimal("10"))

    def test_ingreso_en_envases_desbordado_muestra_error_sin_movimiento(self):
        producto = Producto.objects.create(
            nombre_comercial="Concentrado",
            unidad_base="l",
            contenido_por_envase=Decimal("5000"),
        )
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("panel:productos:movimiento_alta", args=[producto.pk]),
            {"tipo": "ingreso", "cantidad": "9999999", "en_envases": "on"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_ingreso_no_positivo_se_rechaza(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("panel:productos:movimiento_alta", args=[self.producto.pk]),
            {"tipo": "ingreso", "cantidad": "0"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_empleado_no_accede(self):
        self.client.force_login(self.empleado)
        for nombre in ("ficha", "movimiento_alta"):
            url = reverse(f"panel:productos:{nombre}", args=[self.producto.pk])
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {}).status_code, 403)

    def test_no_hay_rutas_para_editar_ni_borrar_movimientos(self):
        for nombre in ("movimiento_editar", "movimiento_borrar", "movimiento_eliminar"):
            with self.assertRaises(NoReverseMatch):
                reverse(f"panel:productos:{nombre}", args=[self.producto.pk, 1])

    def test_listado_muestra_stock_y_enlaza_a_la_ficha(self):
        services.registrar_ingreso(self.producto, Decimal("15"), False, self.admin)
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("panel:productos:listado"))
        self.assertContains(
            respuesta, reverse("panel:productos:ficha", args=[self.producto.pk])
        )
        self.assertContains(respuesta, "15 l")
