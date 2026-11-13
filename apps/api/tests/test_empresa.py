"""Tokens de la API: una empresa inactiva no obtiene ni renueva tokens."""

from django.core.cache import cache
from django.test import TestCase

from apps.accounts.models import User
from apps.empresas.models import Empresa

CLAVE = "clave-segura-123"
TOKEN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"


class TokenEmpresaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.empresa = Empresa.objects.create(nombre="Empresa A")
        User.objects.create_user("emp", password=CLAVE, empresa=self.empresa)

    def _pedir(self):
        return self.client.post(
            TOKEN,
            {"username": "emp", "password": CLAVE},
            content_type="application/json",
        )

    def _desactivar(self):
        Empresa.objects.filter(pk=self.empresa.pk).update(activo=False)

    def test_token_con_empresa_inactiva_no_se_emite(self):
        self._desactivar()
        respuesta = self._pedir()
        self.assertEqual(respuesta.status_code, 401)
        self.assertNotIn("access", respuesta.json())

    def test_renovacion_con_empresa_inactiva_da_401(self):
        refresh = self._pedir().json()["refresh"]
        self._desactivar()
        respuesta = self.client.post(
            REFRESH, {"refresh": refresh}, content_type="application/json"
        )
        self.assertEqual(respuesta.status_code, 401)
