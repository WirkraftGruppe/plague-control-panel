"""Pestañas del catálogo en el listado de productos."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.productos.models import Producto


class CatalogoProductosTests(TestCase):
    def test_listado_muestra_pestanas_con_productos_activa_y_stock(self):
        admin = User.objects.create_user(
            username="admin-cat-p", password="x", rol=User.Rol.ADMINISTRADOR
        )
        Producto.objects.create(nombre_comercial="Raticida Cat")
        self.client.force_login(admin)
        respuesta = self.client.get(reverse("panel:productos:listado"))
        self.assertContains(respuesta, '<nav class="pestanas" aria-label="Catálogo">')
        self.assertContains(
            respuesta,
            f'<a href="{reverse("panel:productos:listado")}" '
            'aria-current="page">Productos</a>',
        )
        self.assertContains(
            respuesta, f'<a href="{reverse("panel:servicios:listado")}">Servicios</a>'
        )
        self.assertContains(respuesta, "Raticida Cat")
        self.assertContains(respuesta, "Stock")
