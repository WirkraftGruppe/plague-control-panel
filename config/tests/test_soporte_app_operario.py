"""Integración de soporte-app-operario: las rutas nuevas de la API por su URL real."""

import shutil
import tempfile
from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.empresas.logos import procesar_logo
from apps.visitas.models import PuntoNoRevisado, Revision, Visita
from apps.visitas.tests.ayudas_empresa import dos_empresas


def _api(usuario):
    api = APIClient()
    api.force_authenticate(usuario)
    return api


def _logo_png():
    """Un logo procesado como lo guarda el panel."""
    salida = BytesIO()
    Image.new("RGB", (20, 10), "green").save(salida, format="PNG")
    return procesar_logo(ContentFile(salida.getvalue(), name="logo.png"))


class IntegracionSoporteAppTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """El logo de `setUpTestData` va a un MEDIA_ROOT temporal."""
        media = tempfile.mkdtemp(prefix="soporte-app-")
        cls.addClassCleanup(shutil.rmtree, media, ignore_errors=True)
        cls.enterClassContext(override_settings(MEDIA_ROOT=media))
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()
        Visita.objects.de_empresa(cls.a.empresa).filter(pk=cls.a.visita.pk).update(
            origen=Visita.Origen.APP,
            motivo_manual="",
            incidencia=False,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
        )
        cls.a.empresa.logo.save("logo.png", _logo_png(), save=True)

    def test_reporte_no_revisado_por_url_da_201(self):
        r = _api(self.a.empleado).post(
            f"/api/v1/visitas/{self.a.visita.pk}/no-revisados/",
            {
                "punto": self.a.punto.pk,
                "motivo": "sin_acceso",
                "cliente_uuid": str(uuid4()),
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["visita"], self.a.visita.pk)
        self.assertEqual(r.data["punto"]["id"], self.a.punto.pk)
        self.assertNotIn("latitud", r.data)
        reporte = PuntoNoRevisado.objects.de_empresa(self.a.empresa).get()
        self.assertEqual(reporte.motivo, "sin_acceso")
        self.assertFalse(Revision.objects.de_empresa(self.a.empresa).exists())

    def test_me_empresa_por_url(self):
        r = _api(self.a.empleado).get("/api/v1/me/empresa/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["nombre"], "Empresa A")
        self.assertEqual(
            r.data["logo"],
            f"http://testserver/api/v1/empresas/{self.a.empresa.pk}/logo/",
        )
        logo = _api(self.a.admin).get(f"/api/v1/empresas/{self.a.empresa.pk}/logo/")
        self.assertEqual(logo.status_code, 200)
        self.assertEqual(logo["Content-Type"], "image/png")
        self.assertEqual(logo["Cache-Control"], "private, no-store")
        sin_logo = _api(self.b.empleado).get("/api/v1/me/empresa/")
        self.assertEqual(sin_logo.data, {"nombre": "Empresa B", "logo": None})

    def test_logo_de_otra_empresa_por_url_da_404(self):
        for usuario in (self.b.empleado, self.b.admin):
            with self.subTest(usuario=usuario.username):
                r = _api(usuario).get(f"/api/v1/empresas/{self.a.empresa.pk}/logo/")
                self.assertEqual(r.status_code, 404)
                self.assertEqual(r["Content-Type"], "application/json")
