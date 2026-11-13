"""Integración de robustez-listados: 404 JSON bajo /api/ y esquema con sesión."""

from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.accounts.pruebas import crear_plataforma
from apps.empresas.tests.ayudas import una_empresa

ESQUEMA = "/api/v1/schema/"


class IntegracionRobustezTests(TestCase):
    def _administrador(self, empresa):
        return User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=empresa,
        )

    @override_settings(DEBUG=False)
    def test_ruta_inexistente_bajo_api_da_404_json(self):
        respuesta = self.client.get("/api/v1/no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertEqual(respuesta.json(), {"detalle": "No encontrado.", "campos": {}})

    @override_settings(DEBUG=False)
    def test_ruta_inexistente_fuera_de_api_da_html(self):
        respuesta = self.client.get("/no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("text/html", respuesta["Content-Type"])

    def test_esquema_con_sesion_de_plataforma_se_rechaza(self):
        self.client.force_login(crear_plataforma())
        self.assertIn(self.client.get(ESQUEMA).status_code, (401, 403))

    def test_esquema_con_sesion_de_empresa_inactiva_se_rechaza(self):
        empresa = una_empresa()
        self.client.force_login(self._administrador(empresa))
        empresa.activo = False
        empresa.save()
        self.assertIn(self.client.get(ESQUEMA).status_code, (401, 403))

    def test_esquema_con_sesion_de_empresa_activa_responde(self):
        self.client.force_login(self._administrador(una_empresa()))
        respuesta = self.client.get(ESQUEMA)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Retry-After", respuesta.content)
