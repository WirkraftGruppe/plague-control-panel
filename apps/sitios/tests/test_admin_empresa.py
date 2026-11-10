"""Admin de Sitios: los tres modelos son hijos y no piden la empresa."""

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.accounts.pruebas import crear_plataforma
from apps.sitios.models import Plano, PuntoControl, Sitio


class AdminEmpresaSitiosTests(TestCase):
    def test_formularios_del_admin_no_piden_empresa(self):
        request = RequestFactory().get("/admin/")
        request.user = crear_plataforma(username="root")
        for modelo in (Sitio, Plano, PuntoControl):
            with self.subTest(modelo=modelo.__name__):
                formulario = admin.site._registry[modelo].get_form(request)
                self.assertNotIn("empresa", formulario.base_fields)
