from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa


class VistaDePrueba(AdministradorRequeridoMixin, View):
    def get(self, request):
        return HttpResponse("ok")


class AdministradorRequeridoMixinTests(TestCase):
    def _responder(self, usuario):
        peticion = RequestFactory().get("/panel/algo/")
        peticion.user = usuario
        peticion.empresa = getattr(usuario, "empresa", None)
        return VistaDePrueba.as_view()(peticion)

    def test_anonimo_redirige_al_login(self):
        respuesta = self._responder(AnonymousUser())
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, "/panel/ingresar/?next=/panel/algo/")

    def test_empleado_recibe_403(self):
        empleado = User.objects.create_user(
            "emp", password="clave-segura-123", empresa=una_empresa()
        )
        with self.assertRaises(PermissionDenied):
            self._responder(empleado)

    def test_administrador_activo_accede(self):
        admin = User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        self.assertEqual(self._responder(admin).status_code, 200)

    def test_administrador_inactivo_recibe_403(self):
        admin = User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        admin.is_active = False
        with self.assertRaises(PermissionDenied):
            self._responder(admin)

    def test_administrador_con_empresa_inactiva_pierde_la_sesion(self):
        empresa = una_empresa()
        empresa.activo = False
        admin = User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=empresa,
        )
        peticion = RequestFactory().get("/panel/algo/")
        peticion.user = admin
        peticion.empresa = empresa
        peticion.session = self.client.session
        respuesta = VistaDePrueba.as_view()(peticion)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.url, "/panel/ingresar/")
