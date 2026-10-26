"""Esquema OpenAPI: exige autenticación y publica las rutas de dominio."""

import shutil
import tempfile

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa

RUTAS_DE_DOMINIO = (
    "/api/v1/productos/",
    "/api/v1/qr/{codigo}/resolver/",
    "/api/v1/me/visitas/",
    "/api/v1/visitas/abrir/",
    "/api/v1/revisiones/",
    "/api/v1/visitas/{id}/cerrar/",
    "/api/v1/me/historial/",
    "/api/v1/fotos/{codigo}/",
    "/api/v1/planos/{id}/imagen/",
    "/api/v1/me/puntos/",
)


MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="schema-api-test-")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class SchemaTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_schema_requiere_auth_y_lista_endpoints(self):
        """Anónimo recibe 401; con usuario, 200 y las rutas de dominio."""
        self.assertEqual(APIClient().get("/api/v1/schema/").status_code, 401)

        usuario = User.objects.create_user(
            "emp",
            password="clave-segura-123",
            rol=User.Rol.EMPLEADO,
            empresa=una_empresa(),
        )
        api = APIClient()
        api.force_authenticate(usuario)
        respuesta = api.get("/api/v1/schema/", {"format": "json"})
        self.assertEqual(respuesta.status_code, 200)
        rutas = respuesta.json()["paths"]
        for ruta in RUTAS_DE_DOMINIO:
            self.assertIn(ruta, rutas)

    def test_token_documenta_cuerpo_y_415(self):
        """El token declara 200 con sus tokens, 401, 415 y 429; la renovación, 415."""
        usuario = User.objects.create_user(
            "emp",
            password="clave-segura-123",
            rol=User.Rol.EMPLEADO,
            empresa=una_empresa(),
        )
        api = APIClient()
        api.force_authenticate(usuario)
        rutas = api.get("/api/v1/schema/", {"format": "json"}).json()["paths"]
        obtener = rutas["/api/v1/auth/token/"]["post"]
        self.assertTrue(set(obtener["responses"]) >= {"200", "401", "415", "429"})
        cuerpo = obtener["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertIn("$ref", cuerpo)
        renovar = rutas["/api/v1/auth/token/refresh/"]["post"]
        self.assertIn("415", renovar["responses"])
        self.assertTrue(renovar["description"])
        # La rotación devuelve también un refresh nuevo: el 200 debe exigir ambos.
        esquema = renovar["responses"]["200"]["content"]["application/json"]["schema"]
        nombre = esquema["$ref"].rsplit("/", 1)[-1]
        componente = api.get("/api/v1/schema/", {"format": "json"}).json()[
            "components"
        ]["schemas"][nombre]
        self.assertTrue({"access", "refresh"} <= set(componente["required"]))
