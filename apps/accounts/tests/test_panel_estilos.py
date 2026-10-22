"""Estilos del panel de usuarios: sin estilos en línea."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class EstilosPanelTests(TestCase):
    def test_listado_de_usuarios_sin_style_en_linea(self):
        admin = User.objects.create_user(
            username="admin-est", password="x", rol=User.Rol.ADMINISTRADOR
        )
        User.objects.create_user(
            username="emp-est", password="x", rol=User.Rol.EMPLEADO, is_active=False
        )
        self.client.force_login(admin)
        respuesta = self.client.get(reverse("panel:usuarios:listado"))
        self.assertNotContains(respuesta, 'style="')
        self.assertContains(respuesta, "formulario-en-linea")
