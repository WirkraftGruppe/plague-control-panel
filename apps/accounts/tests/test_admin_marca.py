from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.accounts.admin import CuentaAdmin
from apps.accounts.models import User


class CuentaAdminMarcaTests(SimpleTestCase):
    def setUp(self):
        self.admin = CuentaAdmin(User, AdminSite())
        self.request = RequestFactory().get("/admin/")

    def titulos(self, obj):
        return [t for t, _ in self.admin.get_fieldsets(self.request, obj)]

    @override_settings(NOMBRE_EMPRESA="Empresa de Prueba")
    def test_seccion_propia_no_lleva_nombre_de_empresa(self):
        for obj in (User(username="x"), None):
            self.assertNotIn("Empresa de Prueba", self.titulos(obj))

    def test_seccion_propia_ofrece_empresa_y_rol(self):
        for obj in (User(username="x"), None):
            campos = self.admin.get_fieldsets(self.request, obj)[-1][1]["fields"]
            self.assertIn("empresa", campos)
            self.assertIn("rol", campos)
