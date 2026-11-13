"""Admin: las raíces piden la empresa (inmutable al editar) y los hijos no."""

from django.contrib import admin
from django.test import RequestFactory, TestCase

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.productos.models import MovimientoStock, Producto
from apps.servicios.models import CampoPlanilla, TipoServicio


class AdminEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(nombre="Empresa A")
        cls.plataforma = User.objects.create_user(
            "plat", password="clave-segura-123", rol=User.Rol.PLATAFORMA
        )

    def _request(self):
        request = RequestFactory().get("/admin/")
        request.user = self.plataforma
        return request

    def _form(self, modelo, obj=None):
        return admin.site._registry[modelo].get_form(self._request(), obj)

    def test_raices_piden_empresa_e_hijos_no(self):
        for modelo in (Cliente, TipoServicio, Producto):
            campo = self._form(modelo).base_fields["empresa"]
            self.assertTrue(campo.required, modelo.__name__)
        for modelo in (CampoPlanilla, MovimientoStock):
            self.assertNotIn("empresa", self._form(modelo).base_fields, modelo.__name__)

    def test_empresa_es_de_solo_lectura_al_editar_una_raiz(self):
        cliente = Cliente.objects.create(razon_social="C", empresa=self.empresa)
        servicio = TipoServicio.objects.create(nombre="S", empresa=self.empresa)
        producto = Producto.objects.create(nombre_comercial="P", empresa=self.empresa)
        for modelo, obj in (
            (Cliente, cliente),
            (TipoServicio, servicio),
            (Producto, producto),
        ):
            self.assertNotIn("empresa", self._form(modelo, obj).base_fields)
            ma = admin.site._registry[modelo]
            self.assertIn("empresa", ma.get_readonly_fields(self._request(), obj))
            self.assertNotIn("empresa", ma.get_readonly_fields(self._request()))
