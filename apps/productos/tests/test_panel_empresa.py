"""El panel de Productos resuelve todo por la empresa del administrador."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.empresas.models import Empresa
from apps.productos.models import MovimientoStock, Producto


class ProductosPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre="Empresa A")
        cls.empresa_b = Empresa.objects.create(nombre="Empresa B")
        cls.admin_a = User.objects.create_user(
            "adm-a",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=cls.empresa_a,
        )
        cls.propio = Producto.objects.create(
            nombre_comercial="Cebo propio", empresa=cls.empresa_a
        )
        cls.ajeno = Producto.objects.create(
            nombre_comercial="Gel ajeno", empresa=cls.empresa_b
        )

    def setUp(self):
        self.client.force_login(self.admin_a)

    def test_listado_solo_de_la_empresa(self):
        respuesta = self.client.get(reverse("panel:productos:listado"))
        self.assertContains(respuesta, "Cebo propio")
        self.assertNotContains(respuesta, "Gel ajeno")

    def test_rutas_de_producto_de_otra_empresa_dan_404(self):
        for nombre in ("ficha", "editar", "movimiento_alta"):
            url = reverse(f"panel:productos:{nombre}", args=[self.ajeno.pk])
            self.assertEqual(self.client.get(url).status_code, 404, nombre)
        url = reverse("panel:productos:movimiento_alta", args=[self.ajeno.pk])
        datos = {"tipo": "ingreso", "cantidad": "5"}
        self.assertEqual(self.client.post(url, datos).status_code, 404)
        self.assertFalse(MovimientoStock.todos.filter(producto=self.ajeno).exists())
        url = reverse("panel:productos:ficha", args=[self.propio.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
