"""Raíz con usuario y empresa, y `code` público de los 401 por empresa inactiva."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.pruebas import crear_plataforma
from apps.api.excepciones import manejar_excepcion
from apps.empresas.models import Empresa

CLAVE = "clave-segura-123"
RAIZ = "/api/v1/"
TOKEN = "/api/v1/auth/token/"
REFRESH = "/api/v1/auth/token/refresh/"


def _bearer(usuario):
    return {
        "HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(usuario).access_token}"
    }


class RaizTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa A")

    def test_devuelve_usuario_y_empresa(self):
        usuario = User.objects.create_user(
            "ana",
            password=CLAVE,
            empresa=self.empresa,
            first_name="Ana",
            last_name="Pérez",
        )
        respuesta = self.client.get(RAIZ, **_bearer(usuario))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json(),
            {
                "usuario": {
                    "id": usuario.pk,
                    "nombre_completo": "Ana Pérez",
                    "username": "ana",
                },
                "empresa": {"id": self.empresa.pk, "nombre": "Empresa A"},
                "rol": "empleado",
            },
        )

    def test_sin_nombre_usa_username(self):
        usuario = User.objects.create_user(
            "sinnombre", password=CLAVE, empresa=self.empresa
        )
        cuerpo = self.client.get(RAIZ, **_bearer(usuario)).json()
        self.assertEqual(cuerpo["usuario"]["nombre_completo"], "sinnombre")

    def test_usuario_sin_empresa_da_200_con_empresa_null(self):
        plataforma = crear_plataforma()
        respuesta = self.client.get(RAIZ, **_bearer(plataforma))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNone(respuesta.json()["empresa"])
        self.assertEqual(respuesta.json()["rol"], "plataforma")


class CodigoErrorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.empresa = Empresa.objects.create(nombre="Empresa A")
        self.usuario = User.objects.create_user(
            "emp", password=CLAVE, empresa=self.empresa
        )

    def _pedir_token(self):
        return self.client.post(
            TOKEN,
            {"username": "emp", "password": CLAVE},
            content_type="application/json",
        )

    def _desactivar(self):
        Empresa.objects.filter(pk=self.empresa.pk).update(activo=False)

    def test_token_con_empresa_inactiva_trae_code(self):
        self._desactivar()
        respuesta = self._pedir_token()
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "empresa_inactiva")

    def test_renovacion_con_empresa_inactiva_trae_code(self):
        refresh = self._pedir_token().json()["refresh"]
        self._desactivar()
        respuesta = self.client.post(
            REFRESH, {"refresh": refresh}, content_type="application/json"
        )
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "empresa_inactiva")

    def test_ruta_con_token_vigente_y_empresa_inactiva_trae_code(self):
        cabecera = _bearer(self.usuario)
        self._desactivar()
        respuesta = self.client.get(RAIZ, **cabecera)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["code"], "empresa_inactiva")
        self.assertEqual(respuesta.json()["detalle"], "La empresa está inactiva.")

    def test_otros_codigos_de_autenticacion_no_traen_code(self):
        sin_contexto = {}
        cambio = manejar_excepcion(
            AuthenticationFailed("Cambió.", code="password_changed"), sin_contexto
        )
        invalido = manejar_excepcion(InvalidToken("Token inválido."), sin_contexto)
        self.assertEqual(cambio.status_code, 401)
        self.assertNotIn("code", cambio.data)
        self.assertEqual(invalido.status_code, 401)
        self.assertNotIn("code", invalido.data)
        respuesta = self.client.get(RAIZ, HTTP_AUTHORIZATION="Bearer basura")
        self.assertEqual(respuesta.status_code, 401)
        self.assertNotIn("code", respuesta.json())

    def test_esquema_de_error_documenta_code(self):
        esquema = self.client.get(
            "/api/v1/schema/?format=json", **_bearer(self.usuario)
        )
        self.assertEqual(esquema.status_code, 200)
        propiedades = esquema.json()["components"]["schemas"]["Error"]["properties"]
        self.assertEqual(propiedades["code"]["enum"], ["empresa_inactiva"])
