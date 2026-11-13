from django.test import TestCase
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.empresas.autenticacion import JWTAutenticacionEmpresa
from apps.empresas.pruebas import crear_empresa


def _cabecera(usuario):
    return {"HTTP_AUTHORIZATION": f"Bearer {AccessToken.for_user(usuario)}"}


class JWTEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = crear_empresa("Una")
        cls.usuario = User.objects.create_user(
            "emp-una",
            password="clave-larga-de-prueba",
            rol=User.Rol.EMPLEADO,
            empresa=cls.empresa,
        )

    def test_jwt_carga_la_empresa_con_el_usuario_sin_consulta_extra(self):
        token = AccessToken.for_user(self.usuario)
        with self.assertNumQueries(1):
            usuario = JWTAutenticacionEmpresa().get_user(token)
        with self.assertNumQueries(0):
            self.assertEqual(usuario.empresa, self.empresa)

    def test_token_vigente_con_empresa_inactiva_da_401(self):
        cabecera = _cabecera(self.usuario)
        self.empresa.activo = False
        self.empresa.save()
        respuesta = APIClient().get(reverse("api:raiz"), **cabecera)
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["detalle"], "La empresa está inactiva.")

    def test_token_con_empresa_activa_fija_request_empresa(self):
        pedido = APIRequestFactory().get("/", **_cabecera(self.usuario))
        request = Request(pedido)
        usuario, _ = JWTAutenticacionEmpresa().authenticate(request)
        self.assertEqual(usuario, self.usuario)
        self.assertEqual(request.empresa, self.empresa)
        self.assertEqual(pedido.empresa, self.empresa)

    def test_esquema_openapi_conserva_jwt_auth(self):
        esquema = SchemaGenerator().get_schema(request=None, public=True)
        self.assertEqual(
            esquema["components"]["securitySchemes"],
            {"jwtAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
        )

    def test_schema_con_token_de_empresa_inactiva_da_401(self):
        cabecera = _cabecera(self.usuario)
        self.empresa.activo = False
        self.empresa.save()
        respuesta = APIClient().get(reverse("api:schema"), **cabecera)
        self.assertEqual(respuesta.status_code, 401)
