"""Pestañas del catálogo en el listado de servicios."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.servicios.models import TipoServicio


class CatalogoServiciosTests(TestCase):
    def test_listado_muestra_pestanas_con_servicios_activa(self):
        admin = User.objects.create_user(
            username="admin-cat-s", password="x", rol=User.Rol.ADMINISTRADOR
        )
        TipoServicio.objects.create(nombre="Roedores", slug="roedores-cat")
        self.client.force_login(admin)
        respuesta = self.client.get(reverse("panel:servicios:listado"))
        self.assertContains(respuesta, '<nav class="pestanas" aria-label="Catálogo">')
        self.assertContains(
            respuesta,
            f'<a href="{reverse("panel:servicios:listado")}" '
            'aria-current="page">Servicios</a>',
        )
        self.assertContains(
            respuesta, f'<a href="{reverse("panel:productos:listado")}">Productos</a>'
        )
        self.assertContains(respuesta, "Roedores")
