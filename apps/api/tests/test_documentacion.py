"""Esquema OpenAPI y documentación: solo con sesión o token, sin orígenes externos."""

import re

from django.test import TestCase

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa


class DocumentacionTests(TestCase):
    def test_schema_y_docs_rechazan_anonimos(self):
        for ruta in ("/api/v1/schema/", "/api/v1/docs/"):
            self.assertIn(self.client.get(ruta).status_code, (401, 403), ruta)

    def test_docs_con_sesion_sin_origenes_externos(self):
        admin = User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        self.client.force_login(admin)
        respuesta = self.client.get("/api/v1/docs/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(re.findall(r"https?://", respuesta.content.decode()), [])
