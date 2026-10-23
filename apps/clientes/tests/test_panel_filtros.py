"""Filtro por estado del listado de clientes: el activo se marca."""

import re

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User


class FiltrosClientesTests(TestCase):
    def setUp(self):
        admin = User.objects.create_user(
            "adm-filtros", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(admin)

    def _marcados(self, parametros):
        html = self.client.get(
            reverse("panel:clientes:listado"), parametros
        ).content.decode()
        nav = re.search(r'<nav class="filtros[^"]*".*?</nav>', html, re.S).group(0)
        return re.findall(r'aria-current="page"[^>]*>\s*([^<]+?)\s*</a>', nav)

    def test_filtro_activo_marcado(self):
        self.assertEqual(self._marcados({"activo": "1"}), ["Activos"])
        self.assertEqual(self._marcados({"activo": "0"}), ["Inactivos"])
        self.assertEqual(self._marcados({}), ["Todos"])
