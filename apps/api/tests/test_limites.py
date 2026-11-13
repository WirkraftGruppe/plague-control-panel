"""Límites de la API de tokens: cupo por IP y baldes de fallos del panel."""

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa

CLAVE = "clave-segura-123"
TOKEN = "/api/v1/auth/token/"
IP = "203.0.113.5"


class LimitesTokenTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        User.objects.create_user("emp", password=CLAVE, empresa=una_empresa())
        User.objects.create_user(
            "adm", password=CLAVE, rol=User.Rol.ADMINISTRADOR, empresa=una_empresa()
        )

    def _pedir(self, usuario="emp", clave=CLAVE, ip=IP, **extra):
        return self.client.post(
            TOKEN,
            {"username": usuario, "password": clave},
            content_type="application/json",
            REMOTE_ADDR=ip,
            **extra,
        )

    def _panel(self, usuario, clave, ip=IP):
        return self.client.post(
            "/panel/ingresar/",
            {"username": usuario, "password": clave},
            REMOTE_ADDR=ip,
        )

    @override_settings(INTENTOS_FALLIDOS_POR_IP=3)
    def test_cupo_del_token_es_independiente_del_panel(self):
        for i in range(3):
            self._panel(f"otro{i}", "mala")
        self.assertEqual(self._pedir().status_code, 200)
        codigos = [self._pedir(f"x{i}", "mala").status_code for i in range(10)]
        self.assertEqual(codigos[:9], [401] * 9)
        self.assertEqual(codigos[9], 429)
        # El panel de la misma IP sigue con su propio balde lleno, no con el del token.
        self.assertEqual(self._panel("adm", CLAVE).status_code, 429)
        self.assertEqual(self._panel("adm", CLAVE, "198.51.100.9").status_code, 302)

    @override_settings(NUM_PROXIES=0)
    def test_token_ignora_x_forwarded_for_sin_proxies(self):
        codigos = [
            self._pedir(f"x{i}", "mala", HTTP_X_FORWARDED_FOR=f"9.9.9.{i}").status_code
            for i in range(11)
        ]
        self.assertEqual(codigos[:10], [401] * 10)
        self.assertEqual(codigos[10], 429)

    @override_settings(NUM_PROXIES=1)
    def test_token_con_un_proxy_usa_la_ultima_ip(self):
        for i in range(10):
            self._pedir(f"x{i}", "mala", HTTP_X_FORWARDED_FOR=f"9.9.9.{i}, 7.7.7.7")
        bloqueado = self._pedir(HTTP_X_FORWARDED_FOR="9.9.9.9, 7.7.7.7")
        self.assertEqual(bloqueado.status_code, 429)
        otro = self._pedir(HTTP_X_FORWARDED_FOR="9.9.9.9, 7.7.7.8")
        self.assertEqual(otro.status_code, 200)

    def test_token_registra_fallos_en_los_baldes_de_usuario(self):
        for _ in range(5):
            self.assertEqual(self._pedir("EMP", "mala").status_code, 401)
        bloqueado = self._pedir("emp", CLAVE)
        self.assertEqual(bloqueado.status_code, 429)
        self.assertNotIn("access", bloqueado.json())
        self.assertEqual(self._pedir("emp", CLAVE, ip="198.51.100.9").status_code, 200)

    @override_settings(FALLOS_POR_USUARIO=3)
    def test_token_cuenta_en_el_cupo_global_por_usuario(self):
        for i in range(3):
            self._pedir("emp", "mala", ip=f"198.51.100.{i}")
        self.assertEqual(self._pedir("emp", CLAVE, ip="192.0.2.77").status_code, 429)

    def test_fallos_del_panel_bloquean_el_token_del_mismo_usuario(self):
        for _ in range(5):
            self._panel("emp", "mala")
        self.assertEqual(self._pedir("emp", CLAVE).status_code, 429)
