"""El panel de Clientes resuelve todo por la empresa del administrador."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa


class ClientesPorEmpresaTests(TestCase):
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
        cls.propio = Cliente.objects.create(
            razon_social="Molinos propios", empresa=cls.empresa_a
        )
        cls.ajeno = Cliente.objects.create(
            razon_social="Frigorifico ajeno", empresa=cls.empresa_b
        )

    def setUp(self):
        self.client.force_login(self.admin_a)

    def test_listado_solo_de_la_empresa(self):
        respuesta = self.client.get(reverse("panel:clientes:listado"))
        self.assertContains(respuesta, "Molinos propios")
        self.assertNotContains(respuesta, "Frigorifico ajeno")

    def test_rutas_de_cliente_de_otra_empresa_dan_404(self):
        for nombre in ("ficha", "editar", "baja"):
            url = reverse(f"panel:clientes:{nombre}", args=[self.ajeno.pk])
            self.assertEqual(self.client.get(url).status_code, 404, nombre)
        url = reverse("panel:clientes:editar", args=[self.ajeno.pk])
        self.assertEqual(
            self.client.post(url, {"razon_social": "Cambio"}).status_code, 404
        )
        url = reverse("panel:clientes:baja", args=[self.ajeno.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.ajeno.refresh_from_db()
        self.assertTrue(self.ajeno.activo)
        self.assertEqual(self.ajeno.razon_social, "Frigorifico ajeno")
        url = reverse("panel:clientes:ficha", args=[self.propio.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_alta_asigna_la_empresa(self):
        respuesta = self.client.post(
            reverse("panel:clientes:alta"), {"razon_social": "Nuevo", "activo": "on"}
        )
        self.assertEqual(respuesta.status_code, 302)
        nuevo = Cliente.todos.get(razon_social="Nuevo")
        self.assertEqual(nuevo.empresa_id, self.empresa_a.pk)
