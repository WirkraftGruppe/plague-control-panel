"""Admin de visitas: ningún formulario ni inline pide la empresa."""

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita


class AdminEmpresaVisitasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plataforma = User.objects.create_user(
            "plat", password="clave-segura-123", rol=User.Rol.PLATAFORMA
        )

    def test_formularios_del_admin_no_piden_empresa(self):
        request = RequestFactory().get("/admin/")
        request.user = self.plataforma
        for modelo in (Visita, Revision, Foto, ProductoAplicado):
            ma = admin.site._registry[modelo]
            self.assertNotIn("empresa", ma.get_form(request).base_fields, modelo)
            for inline in ma.get_inline_instances(request):
                formulario = inline.get_formset(request).form
                self.assertNotIn("empresa", formulario.base_fields, inline)
