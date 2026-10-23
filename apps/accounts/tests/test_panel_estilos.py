"""Estilos del panel de usuarios: sin estilos en línea."""

import re

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


class FiltrosUsuariosTests(TestCase):
    def test_filtros_usan_clase_del_sistema(self):
        admin = User.objects.create_user(
            username="admin-filt", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(admin)
        html = self.client.get(reverse("panel:usuarios:listado")).content.decode()
        fila = re.search(r'<form class="filtros[^"]*".*?</form>', html, re.S).group(0)
        self.assertIn('id="filtro-rol"', fila)
        self.assertIn('id="filtro-activo"', fila)
        self.assertEqual(fila.count('class="campo"'), 2)
