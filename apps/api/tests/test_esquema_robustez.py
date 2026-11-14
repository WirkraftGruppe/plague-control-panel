"""Sesión con empresa activa y postproceso del esquema OpenAPI."""

from unittest import mock

from django.test import RequestFactory, TestCase
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.settings import spectacular_settings
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import User
from apps.accounts.pruebas import crear_plataforma
from apps.api.autenticacion import SesionAutenticacionEmpresa
from apps.api.esquema import agregar_respuestas_comunes
from apps.empresas.tests.ayudas import una_empresa


class EsquemaRobustezTests(TestCase):
    def _autenticar(self, usuario):
        self.client.force_login(usuario)
        pedido = RequestFactory().get("/api/v1/")
        pedido.user = usuario
        pedido._request = pedido
        pedido.csrf_processing_done = True
        return SesionAutenticacionEmpresa().authenticate(pedido)

    def test_sesion_sin_empresa_activa_se_rechaza(self):
        with self.assertRaises(AuthenticationFailed):
            self._autenticar(crear_plataforma())
        empresa = una_empresa()
        usuario = User.objects.create_user("emp", password="x" * 12, empresa=empresa)
        self.assertIsNotNone(self._autenticar(usuario))
        empresa.activo = False
        empresa.save()
        usuario.refresh_from_db()
        with self.assertRaises(AuthenticationFailed):
            self._autenticar(usuario)

    def test_postproceso_agrega_401_y_429(self):
        generador = SchemaGenerator()
        # Sin hooks: el de settings ya aplica este postproceso (cableado en T6).
        with mock.patch.object(
            spectacular_settings, "POSTPROCESSING_HOOKS", [], create=True
        ):
            esquema = generador.get_schema(request=None, public=True)
        alta = esquema["paths"]["/api/v1/sitios/"]["post"]["responses"]
        self.assertNotIn("429", alta)
        resultado = agregar_respuestas_comunes(esquema, generador, None, True)
        alta = resultado["paths"]["/api/v1/sitios/"]["post"]["responses"]
        self.assertIn("429", alta)
        self.assertIn("401", alta)
        self.assertIn("Retry-After", alta["429"]["headers"])
        self.assertEqual(
            alta["401"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/Error",
        )
        self.assertEqual(
            set(resultado["components"]["schemas"]["Error"]["properties"]),
            {"detalle", "campos"},
        )
        token = resultado["paths"]["/api/v1/auth/token/"]["post"]["responses"]
        self.assertIn("400", token)
        self.assertNotIn("headers", token["429"])
