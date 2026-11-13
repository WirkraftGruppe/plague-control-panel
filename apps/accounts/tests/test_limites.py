"""Límites de fallos de ingreso al panel y al admin (ventana deslizante)."""

from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa

CLAVE = "clave-segura-123"
IP = "203.0.113.5"


class LimitesPanelTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user(
            "adm", password=CLAVE, rol=User.Rol.ADMINISTRADOR, empresa=una_empresa()
        )
        self.super = User.objects.create_superuser("root", password=CLAVE)

    def _ingresar(self, usuario, clave, ip=IP, url="/panel/ingresar/"):
        return self.client.post(
            url, {"username": usuario, "password": clave}, REMOTE_ADDR=ip
        )

    def _fallar(self, cantidad, usuario="adm", ip=IP):
        for _ in range(cantidad):
            self.assertEqual(self._ingresar(usuario, "mala", ip).status_code, 200)

    @override_settings(INTENTOS_FALLIDOS_POR_IP=4)
    def test_ip_con_fallos_no_bloquea_contrasena_correcta(self):
        for i in range(3):
            self._ingresar(f"otro{i}", "mala")
        respuesta = self._ingresar("adm", CLAVE)
        self.assertRedirects(respuesta, "/panel/", fetch_redirect_response=False)

    @override_settings(INTENTOS_FALLIDOS_POR_IP=4)
    def test_umbral_de_fallos_por_ip_bloquea(self):
        for i in range(4):
            self._ingresar(f"otro{i}", "mala")
        respuesta = self._ingresar("adm", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self._ingresar("adm", CLAVE, "198.51.100.1").status_code, 302)

    def test_variantes_unicode_del_usuario_comparten_cupo(self):
        variantes = ["adm", "ADM", "ａｄｍ", " Adm ", "ＡＤＭ"]
        for variante in variantes:
            self.assertEqual(self._ingresar(variante, "mala").status_code, 200)
        for variante in variantes:
            self.assertEqual(self._ingresar(variante, CLAVE).status_code, 429)

    def test_admin_login_tiene_el_mismo_limite(self):
        for _ in range(5):
            respuesta = self._ingresar("root", "mala", url="/admin/login/")
            self.assertEqual(respuesta.status_code, 200)
        respuesta = self._ingresar("root", CLAVE, url="/admin/login/")
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(self._ingresar("root", CLAVE).status_code, 429)

    def test_fallos_desde_otra_ip_no_bloquean_al_usuario(self):
        self._fallar(5)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 429)
        respuesta = self._ingresar("adm", CLAVE, "198.51.100.1")
        self.assertRedirects(respuesta, "/panel/", fetch_redirect_response=False)

    @override_settings(FALLOS_POR_USUARIO=3)
    def test_cupo_global_por_usuario_bloquea_desde_cualquier_ip(self):
        for i in range(3):
            self._fallar(1, ip=f"198.51.100.{i}")
        self.assertEqual(self._ingresar("adm", CLAVE, "192.0.2.77").status_code, 429)

    def test_bloqueo_no_evalua_la_contrasena(self):
        self._fallar(5)
        with mock.patch("django.contrib.auth.forms.authenticate") as autenticar:
            respuesta = self._ingresar("adm", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        autenticar.assert_not_called()

    def test_ingreso_exitoso_limpia_solo_el_balde_usuario_ip(self):
        self._fallar(4)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 302)
        self.client.logout()
        # Con el balde (usuario, IP) limpio caben otros 5 fallos antes del bloqueo.
        self._fallar(5)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 429)

    def test_empleado_sin_acceso_cuenta_como_fallo(self):
        User.objects.create_user("emp", password=CLAVE, empresa=una_empresa())
        for _ in range(5):
            self._ingresar("emp", CLAVE)
        self.assertEqual(self._ingresar("emp", CLAVE).status_code, 429)

    def test_ipv6_del_mismo_64_comparte_balde(self):
        direcciones = ["2001:db8:1:2::1", "2001:db8:1:2:ffff::9"]
        for i in range(5):
            self._fallar(1, ip=direcciones[i % 2])
        self.assertEqual(
            self._ingresar("adm", CLAVE, "2001:db8:1:2:abcd::7").status_code, 429
        )
        otra = self._ingresar("adm", CLAVE, "2001:db8:1:3::1")
        self.assertRedirects(otra, "/panel/", fetch_redirect_response=False)
