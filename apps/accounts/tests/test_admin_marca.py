from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase, override_settings

from apps.accounts.admin import CuentaAdmin
from apps.accounts.models import User


class CuentaAdminMarcaTests(TestCase):
    def setUp(self):
        self.admin = CuentaAdmin(User, AdminSite())
        self.request = RequestFactory().get("/admin/")

    def titulos(self, obj):
        return [t for t, _ in self.admin.get_fieldsets(self.request, obj)]

    @override_settings(NOMBRE_EMPRESA="Empresa de Prueba")
    def test_seccion_propia_lleva_nombre_de_la_empresa(self):
        usuario = User(username="x")
        self.assertIn("Empresa de Prueba", self.titulos(usuario))
        self.assertIn("Empresa de Prueba", self.titulos(None))

    @override_settings(NOMBRE_EMPRESA="<b>Otra</b>")
    def test_titulo_no_se_marca_como_seguro(self):
        titulo = self.titulos(None)[-1]
        self.assertEqual(titulo, "<b>Otra</b>")
        self.assertFalse(hasattr(titulo, "__html__"))
