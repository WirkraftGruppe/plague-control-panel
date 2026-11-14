"""API de la empresa: datos propios y logo."""

import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import include, path
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.empresas.logos import procesar_logo
from apps.empresas.pruebas import crear_empresa

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="empresas-api-")

# Namespaces `api` y `empresas`, como los montará `apps/api/urls.py`.
urlpatterns = [
    path(
        "api/v1/",
        include(
            (
                [path("", include("apps.empresas.api_urls"))],
                "api",
            ),
            namespace="api",
        ),
    ),
]


def _png():
    from io import BytesIO

    from PIL import Image

    salida = BytesIO()
    Image.new("RGB", (20, 10), "green").save(salida, format="PNG")
    return procesar_logo(ContentFile(salida.getvalue(), name="x.png"))


def _api(usuario):
    api = APIClient()
    api.force_authenticate(usuario)
    return api


@override_settings(ROOT_URLCONF=__name__, MEDIA_ROOT=MEDIA_TEMPORAL)
class EmpresaApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa = crear_empresa("Alfa")
        cls.otra = crear_empresa("Beta")
        cls.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO, empresa=cls.empresa
        )
        cls.plataforma = User.objects.create_user(
            username="plat", password="x", rol=User.Rol.PLATAFORMA
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def _con_logo(self, empresa):
        empresa.logo.save("logo.png", _png(), save=True)

    def test_me_empresa_devuelve_nombre_y_logo(self):
        self._con_logo(self.empresa)
        r = _api(self.empleado).get("/api/v1/me/empresa/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["nombre"], "Alfa")
        self.assertEqual(
            r.data["logo"], f"http://testserver/api/v1/empresas/{self.empresa.pk}/logo/"
        )

    def test_me_empresa_sin_logo_devuelve_null(self):
        r = _api(self.empleado).get("/api/v1/me/empresa/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, {"nombre": "Alfa", "logo": None})

    def test_logo_propio_lo_ve_un_empleado(self):
        self._con_logo(self.empresa)
        r = _api(self.empleado).get(f"/api/v1/empresas/{self.empresa.pk}/logo/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertTrue(b"".join(r.streaming_content).startswith(b"\x89PNG"))

    def test_logo_de_otra_empresa_da_404(self):
        self._con_logo(self.otra)
        r = _api(self.empleado).get(f"/api/v1/empresas/{self.otra.pk}/logo/")
        self.assertEqual(r.status_code, 404)

    def test_logo_lleva_cabeceras_privadas(self):
        self._con_logo(self.empresa)
        r = _api(self.empleado).get(f"/api/v1/empresas/{self.empresa.pk}/logo/")
        self.assertEqual(r["Cache-Control"], "private, no-store")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_plataforma_da_403(self):
        self._con_logo(self.empresa)
        api = _api(self.plataforma)
        self.assertEqual(api.get("/api/v1/me/empresa/").status_code, 403)
        url = f"/api/v1/empresas/{self.empresa.pk}/logo/"
        self.assertEqual(api.get(url).status_code, 403)
