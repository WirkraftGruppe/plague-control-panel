"""Pruebas del catálogo de productos en el panel."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.productos.models import Producto


class ProductoPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-prod", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            username="emp-prod", password="x", rol=User.Rol.EMPLEADO
        )

    def test_empleado_no_accede(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse("panel:productos:listado"))
        self.assertEqual(respuesta.status_code, 403)

    def test_alta_edicion_y_desactivar(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(
            reverse("panel:productos:alta"),
            {
                "nombre_comercial": "Raticida X",
                "registro": "123",
                "unidad_base": "l",
                "contenido_por_envase": "5",
                "modo_unidad": "unica",
                "activo": "on",
            },
        )
        self.assertRedirects(respuesta, reverse("panel:productos:listado"))
        producto = Producto.objects.get(nombre_comercial="Raticida X")
        self.assertTrue(producto.activo)

        self.client.post(
            reverse("panel:productos:editar", args=[producto.pk]),
            {
                "nombre_comercial": "Raticida Y",
                "registro": "123",
                "unidad_base": "l",
                "contenido_por_envase": "5",
                "modo_unidad": "unica",
            },
        )
        producto.refresh_from_db()
        self.assertEqual(producto.nombre_comercial, "Raticida Y")
        self.assertFalse(producto.activo)

        respuesta = self.client.get(reverse("panel:productos:listado"))
        self.assertContains(respuesta, "Raticida Y")
        self.assertContains(respuesta, 'id="listado"')

    def test_listado_htmx_devuelve_solo_el_parcial(self):
        Producto.objects.create(nombre_comercial="Gel")
        self.client.force_login(self.admin)
        respuesta = self.client.get(
            reverse("panel:productos:listado"), HTTP_HX_REQUEST="true"
        )
        self.assertTemplateUsed(respuesta, "productos/panel/_listado.html")
        self.assertTemplateNotUsed(respuesta, "panel/base.html")
