from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import User
from apps.empresas.pruebas import crear_empresa


class EmpresaMiddlewareTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = crear_empresa("Una")
        cls.admin = User.objects.create_user(
            "admin-una",
            password="clave-larga-de-prueba",
            rol=User.Rol.ADMINISTRADOR,
            empresa=cls.empresa,
        )
        cls.plataforma = User.objects.create_user(
            "plataforma", password="clave-larga-de-prueba", rol=User.Rol.PLATAFORMA
        )

    def test_fija_la_empresa_del_usuario(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/panel/")
        self.assertEqual(respuesta.wsgi_request.empresa, self.empresa)

    def test_anonimo_y_plataforma_sin_empresa(self):
        respuesta = self.client.get("/panel/ingresar/")
        self.assertIsNone(respuesta.wsgi_request.empresa)
        self.client.force_login(self.plataforma)
        respuesta = self.client.get("/panel/ingresar/")
        self.assertIsNone(respuesta.wsgi_request.empresa)

    def test_la_empresa_llega_con_el_usuario_sin_consulta_extra(self):
        self.client.force_login(self.admin)
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get("/panel/ingresar/")
        self.assertEqual(respuesta.wsgi_request.empresa, self.empresa)
        sql = [c["sql"] for c in consultas]
        sueltas = [s for s in sql if 'FROM "empresas_empresa"' in s]
        self.assertEqual(sueltas, [])
        self.assertTrue(any('JOIN "empresas_empresa"' in s for s in sql))
