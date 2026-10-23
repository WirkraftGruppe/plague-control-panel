"""Defectos del panel lateral de nuevo turno hallados en la prueba en navegador."""

import re
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .test_models import crear_visita

RUTA_JS = Path(__file__).resolve().parent.parent / "static/visitas/nuevo_turno.js"
HTMX = {"HX-Request": "true"}


class PanelLateralNavegadorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        visita = crear_visita()
        cls.sitio = visita.sitio
        cls.admin = User.objects.create_user(
            "adm-navegador", password="x", rol=User.Rol.ADMINISTRADOR
        )
        visita.delete()

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])

    def test_nuevo_turno_js_no_usa_htmx_onload(self):
        codigo = RUTA_JS.read_text(encoding="utf-8")
        self.assertNotIn("htmx.onLoad", codigo)
        self.assertTrue("htmx:load" in codigo or "htmx:afterSwap" in codigo)
        self.assertIn("readyState", codigo)

    def test_fecha_del_turno_en_formato_iso(self):
        patron = re.compile(
            r'<input[^>]*name="programada_para"[^>]*value="\d{4}-\d{2}-\d{2}"'
        )
        for cabeceras in ({}, HTMX):
            respuesta = self.client.get(self.url, headers=cabeceras)
            self.assertRegex(respuesta.content.decode(), patron)

    def test_pagina_completa_con_un_solo_titulo(self):
        html = self.client.get(self.url).content.decode()
        titulos = re.findall(r"<h[1-6][^>]*>\s*Nuevo turno\s*</h[1-6]>", html)
        self.assertEqual(len(titulos), 1)
