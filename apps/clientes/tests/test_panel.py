"""Tests del panel de Clientes."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.sitios.models import Sitio


class ClientePanelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        self.client.force_login(self.admin)

    def test_listado_busca_y_filtra_activo(self):
        Cliente.objects.create(
            razon_social="Molinos del Sur", cuit="20123456786", empresa=una_empresa()
        )
        Cliente.objects.create(
            razon_social="Frigorífico Norte", activo=False, empresa=una_empresa()
        )
        url = reverse("panel:clientes:listado")

        respuesta = self.client.get(url, {"q": "molinos"})
        self.assertContains(respuesta, "Molinos del Sur")
        self.assertNotContains(respuesta, "Frigorífico Norte")

        respuesta = self.client.get(url, {"q": "20123456786"})
        self.assertContains(respuesta, "Molinos del Sur")

        respuesta = self.client.get(url, {"activo": "0"})
        self.assertContains(respuesta, "Frigorífico Norte")
        self.assertNotContains(respuesta, "Molinos del Sur")

        respuesta = self.client.get(url, {"activo": "1"})
        self.assertContains(respuesta, "Molinos del Sur")
        self.assertNotContains(respuesta, "Frigorífico Norte")

    def test_baja_logica_no_borra(self):
        cliente = Cliente.objects.create(
            razon_social="Molinos del Sur", empresa=una_empresa()
        )
        url = reverse("panel:clientes:baja", args=[cliente.pk])

        self.assertContains(self.client.get(url), "Dar de baja")
        cliente.refresh_from_db()
        self.assertTrue(cliente.activo)

        respuesta = self.client.post(url)
        self.assertRedirects(
            respuesta,
            reverse("panel:clientes:ficha", args=[cliente.pk]),
            fetch_redirect_response=False,
        )
        cliente.refresh_from_db()
        self.assertFalse(cliente.activo)
        self.assertEqual(Cliente.objects.de_empresa(una_empresa()).count(), 1)

    def test_ficha_lista_sus_sitios(self):
        cliente = Cliente.objects.create(
            razon_social="Molinos del Sur", empresa=una_empresa()
        )
        otro = Cliente.objects.create(razon_social="Otro", empresa=una_empresa())
        Sitio.objects.create(cliente=cliente, nombre="Planta Chascomús")
        Sitio.objects.create(cliente=otro, nombre="Depósito Ajeno")

        respuesta = self.client.get(reverse("panel:clientes:ficha", args=[cliente.pk]))
        self.assertContains(respuesta, "Planta Chascomús")
        self.assertNotContains(respuesta, "Depósito Ajeno")

    def test_alta_y_edicion(self):
        respuesta = self.client.post(
            reverse("panel:clientes:alta"),
            {"razon_social": "Nuevo SA", "activo": "on"},
        )
        cliente = Cliente.objects.de_empresa(una_empresa()).get(razon_social="Nuevo SA")
        self.assertRedirects(
            respuesta,
            reverse("panel:clientes:ficha", args=[cliente.pk]),
            fetch_redirect_response=False,
        )
        self.client.post(
            reverse("panel:clientes:editar", args=[cliente.pk]),
            {"razon_social": "Nuevo SRL", "activo": "on"},
        )
        cliente.refresh_from_db()
        self.assertEqual(cliente.razon_social, "Nuevo SRL")

    def test_empleado_recibe_403(self):
        empleado = User.objects.create_user(
            "emp", password="clave-segura-123", empresa=una_empresa()
        )
        self.client.force_login(empleado)
        respuesta = self.client.get(reverse("panel:clientes:listado"))
        self.assertEqual(respuesta.status_code, 403)
