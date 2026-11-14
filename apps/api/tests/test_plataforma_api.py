"""El usuario `plataforma` no obtiene ni renueva tokens de la API."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.pruebas import CLAVE_PLATAFORMA, crear_plataforma

TOKEN = "/api/v1/auth/token/"
RENOVAR = "/api/v1/auth/token/refresh/"


class PlataformaApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.plataforma = crear_plataforma()

    def _pedir(self, usuario, clave):
        return self.client.post(
            TOKEN,
            {"username": usuario, "password": clave},
            content_type="application/json",
        )

    def test_plataforma_no_obtiene_token(self):
        invalida = self._pedir("plataforma", "mala")
        correcta = self._pedir("plataforma", CLAVE_PLATAFORMA)
        self.assertEqual(invalida.status_code, 401)
        self.assertEqual(correcta.status_code, 401)
        self.assertEqual(correcta.json(), invalida.json())

    def test_plataforma_con_clave_correcta_cuenta_como_fallo(self):
        for _ in range(5):
            respuesta = self._pedir("plataforma", CLAVE_PLATAFORMA)
            self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(self._pedir("plataforma", CLAVE_PLATAFORMA).status_code, 429)

    def test_plataforma_no_renueva_token(self):
        refresco = RefreshToken.for_user(self.plataforma)
        respuesta = self.client.post(
            RENOVAR, {"refresh": str(refresco)}, content_type="application/json"
        )
        self.assertEqual(respuesta.status_code, 401)
