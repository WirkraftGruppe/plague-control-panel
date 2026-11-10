"""Token: el usuario se normaliza igual que en el panel y los baldes lo cuentan bien."""

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa

CLAVE = "clave-segura-123"
TOKEN = "/api/v1/auth/token/"


class TokenNormalizadoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def _pedir(self, usuario, clave=CLAVE):
        return self.client.post(
            TOKEN,
            {"username": usuario, "password": clave},
            content_type="application/json",
        )

    def test_usuario_con_mayusculas_obtiene_token(self):
        User.objects.create_user("emp", password=CLAVE, empresa=una_empresa())
        respuesta = self._pedir("  EMP ")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("access", respuesta.json())

    @override_settings(FALLOS_POR_USUARIO=2, FALLOS_POR_USUARIO_E_IP=50)
    def test_usuario_numerico_cuenta_en_su_balde(self):
        User.objects.create_user("12345678", password=CLAVE, empresa=una_empresa())
        self.assertEqual(self._pedir(12345678, "mala").status_code, 401)
        self.assertEqual(self._pedir(12345678, "mala").status_code, 401)
        # Los fallos cayeron en el balde de "12345678", no en el de "": pedirlo
        # como texto, con la clave correcta, ya está bloqueado.
        self.assertEqual(self._pedir("12345678").status_code, 429)
        # Y otro usuario distinto no queda afectado.
        User.objects.create_user("otro", password=CLAVE, empresa=una_empresa())
        self.assertEqual(self._pedir("otro").status_code, 200)
