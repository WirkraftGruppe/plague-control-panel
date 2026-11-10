"""El admin técnico solo admite al operador de la plataforma."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.pruebas import crear_plataforma
from apps.empresas.pruebas import crear_empresa
from apps.visitas.tests.test_models import crear_visita


class AdminPlataformaTests(TestCase):
    def test_administrador_sin_superuser_no_entra_al_admin(self):
        usuario = get_user_model().objects.create_user(
            "jefe",
            password="clave-larga-123",
            rol="administrador",
            is_staff=True,
            empresa=crear_empresa(),
        )
        self.client.force_login(usuario)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])

    def test_superusuario_con_rol_administrador_no_entra_al_admin(self):
        usuario = get_user_model().objects.create_superuser(
            "root",
            password="clave-larga-123",
            rol="administrador",
            empresa=crear_empresa(),
        )
        self.client.force_login(usuario)
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/login/", r["Location"])

    def test_plataforma_entra_al_admin(self):
        self.client.force_login(crear_plataforma())
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_alta_de_usuario_exige_empresa_segun_rol(self):
        self.client.force_login(crear_plataforma())
        empresa = crear_empresa()
        url = reverse("admin:accounts_user_add")
        base = {
            "password1": "clave-larga-123",
            "password2": "clave-larga-123",
            "telefono": "",
        }
        # Un administrador sin empresa y una plataforma con empresa se rechazan.
        for nombre, rol, empresa_id in (
            ("sin-empresa", "administrador", ""),
            ("con-empresa", "plataforma", empresa.pk),
        ):
            r = self.client.post(
                url, {**base, "username": nombre, "rol": rol, "empresa": empresa_id}
            )
            self.assertEqual(r.status_code, 200, nombre)
            self.assertIn("empresa", r.context["adminform"].form.errors, nombre)
            self.assertFalse(
                get_user_model().objects.filter(username=nombre).exists(), nombre
            )
        # Cada rol con la empresa que le corresponde se acepta.
        for nombre, rol, empresa_id in (
            ("ok-admin", "administrador", empresa.pk),
            ("ok-plataforma", "plataforma", ""),
        ):
            r = self.client.post(
                url, {**base, "username": nombre, "rol": rol, "empresa": empresa_id}
            )
            self.assertEqual(r.status_code, 302, nombre)
        self.assertEqual(
            get_user_model().objects.get(username="ok-admin").empresa, empresa
        )

    @override_settings(EMPRESA_GUARDIA="exigir")
    def test_change_de_visita_con_raw_id_no_consulta_fuera_del_contexto(self):
        visita = crear_visita()
        self.client.force_login(crear_plataforma())
        url = reverse("admin:visitas_visita_change", args=[visita.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
