"""Integración de ajustes-api-app-base: las rutas por su URL real y con JWT real."""

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.visitas.models import Visita
from apps.visitas.tests.ayudas_empresa import dos_empresas


def _api_con_jwt(usuario):
    """Cliente con un token de acceso real, para pasar por la autenticación JWT."""
    api = APIClient()
    acceso = RefreshToken.for_user(usuario).access_token
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso}")
    return api


class IntegracionAppBaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()
        for lado in (cls.a, cls.b):
            Visita.objects.de_empresa(lado.empresa).filter(pk=lado.visita.pk).update(
                origen=Visita.Origen.APP,
                motivo_manual="",
                incidencia=False,
                estado=Visita.Estado.ABIERTA,
                abierta_en=timezone.now(),
            )

    def test_detalle_de_turno_por_url(self):
        api = _api_con_jwt(self.a.empleado)
        r = api.get(f"/api/v1/me/visitas/{self.a.visita.pk}/")
        self.assertEqual(r.status_code, 200, r.content)
        (de_la_lista,) = api.get("/api/v1/me/visitas/").json()["results"]
        self.assertEqual(r.json(), de_la_lista)
        self.assertIn("contacto", r.json()["sitio"])

    def test_detalle_de_otra_empresa_por_url_da_404(self):
        r = _api_con_jwt(self.a.empleado).get(f"/api/v1/me/visitas/{self.b.visita.pk}/")
        self.assertEqual(r.status_code, 404)
        self.assertNotIn(self.b.sitio.nombre, r.content.decode())

    def test_me_visitas_con_empresa_inactiva_trae_code(self):
        api = _api_con_jwt(self.a.empleado)
        self.assertEqual(api.get("/api/v1/me/visitas/").status_code, 200)
        self.a.empresa.activo = False
        self.a.empresa.save()
        r = api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["code"], "empresa_inactiva")
        self.assertEqual(set(r.json()), {"detalle", "campos", "code"})
