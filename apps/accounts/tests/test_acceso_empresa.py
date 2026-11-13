from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.pruebas import crear_plataforma
from apps.empresas.pruebas import crear_empresa

CLAVE = "Clave-Segura-2026"


class AccesoEmpresaTests(TestCase):
    def test_plataforma_en_panel_redirige_a_admin(self):
        self.client.force_login(crear_plataforma())
        respuesta = self.client.get(reverse("panel:usuarios:listado"))
        self.assertRedirects(
            respuesta, reverse("admin:index"), fetch_redirect_response=False
        )

    def test_sesion_con_empresa_inactiva_pierde_el_panel(self):
        empresa = crear_empresa("Baja")
        admin = User.objects.create_user(
            "admin-baja", password=CLAVE, rol=User.Rol.ADMINISTRADOR, empresa=empresa
        )
        self.client.force_login(admin)
        self.assertEqual(
            self.client.get(reverse("panel:usuarios:listado")).status_code, 200
        )
        empresa.activo = False
        empresa.save()
        respuesta = self.client.get(reverse("panel:usuarios:listado"))
        self.assertRedirects(
            respuesta, "/panel/ingresar/", fetch_redirect_response=False
        )
        self.assertNotIn("_auth_user_id", self.client.session)
