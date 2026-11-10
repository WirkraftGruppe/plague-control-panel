"""La API de Sitios resuelve todo por la empresa del usuario."""

import datetime
import tempfile
import uuid

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.sitios.models import Sitio
from apps.visitas.models import Visita

from .ayudas_empresa import DatosDeDosEmpresas

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sitios-api-empresa-test-")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ApiSitiosPorEmpresaTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        cache.clear()
        self.crear_empresas()
        # Caso cruzado: un turno del sitio de B asignado al empleado de A.
        Visita.objects.create(
            sitio=self.sitio_b,
            empleado=self.empleado_a,
            origen=Visita.Origen.MANUAL,
            programada_para=datetime.date.today(),
        )
        self.api_empleado = APIClient()
        self.api_empleado.force_authenticate(self.empleado_a)
        self.api_admin = APIClient()
        self.api_admin.force_authenticate(self.admin_a)

    def test_qr_de_otra_empresa_da_el_mismo_404_que_uno_inexistente(self):
        inexistente = self.api_empleado.post(f"/api/v1/qr/{uuid.uuid4()}/resolver/")
        ajeno = self.api_empleado.post(f"/api/v1/qr/{self.punto_b.qr_codigo}/resolver/")
        self.assertEqual(inexistente.status_code, 404)
        self.assertEqual(ajeno.status_code, 404)
        self.assertEqual(ajeno.json(), inexistente.json())
        propio = self.api_empleado.post(
            f"/api/v1/qr/{self.punto_a.qr_codigo}/resolver/"
        )
        self.assertEqual(propio.status_code, 200)

    def test_plano_punto_y_ubicacion_de_otra_empresa_dan_404(self):
        # Con un turno propio en el sitio ajeno, el empleado igual no ve su plano.
        r = self.api_empleado.get(f"/api/v1/planos/{self.plano_b.pk}/imagen/")
        self.assertEqual(r.status_code, 404)
        r = self.api_admin.get(f"/api/v1/planos/{self.plano_b.pk}/imagen/")
        self.assertEqual(r.status_code, 404)
        r = self.api_admin.get(f"/api/v1/planos/{self.plano_a.pk}/imagen/")
        self.assertEqual(r.status_code, 200)
        r = self.api_admin.post(
            f"/api/v1/sitios/{self.sitio_b.pk}/puntos/", {"nombre": "Intruso"}
        )
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.sitio_b.puntos.count(), 1)
        ubicacion = {"latitud": "-36.1", "longitud": "-57.8", "precision_m": 5}
        r = self.api_admin.post(
            f"/api/v1/puntos/{self.punto_b.pk}/ubicacion/", ubicacion, format="json"
        )
        self.assertEqual(r.status_code, 404)
        self.punto_b.refresh_from_db()
        self.assertIsNone(self.punto_b.latitud)
        r = self.api_admin.post(
            f"/api/v1/puntos/{self.punto_a.pk}/ubicacion/", ubicacion, format="json"
        )
        self.assertEqual(r.status_code, 200)

    def test_alta_de_sitio_con_cliente_de_otra_empresa_da_400(self):
        datos = {
            "nombre": "Nuevo",
            "latitud": "-36.1",
            "longitud": "-57.8",
            "precision_m": 5,
        }
        r = self.api_admin.post(
            "/api/v1/sitios/", {**datos, "cliente": self.cliente_b.pk}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("cliente", r.json()["campos"])
        self.assertFalse(Sitio.todos.filter(nombre="Nuevo").exists())
        r = self.api_admin.post(
            "/api/v1/sitios/", {**datos, "cliente": self.cliente_a.pk}, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Sitio.todos.get(nombre="Nuevo").empresa_id, self.empresa_a.pk)

    def test_mis_puntos_solo_de_la_empresa(self):
        r = self.api_empleado.get("/api/v1/me/puntos/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([p["id"] for p in r.json()], [self.punto_a.pk])
        r = self.api_empleado.get("/api/v1/me/puntos/", {"sitio": self.sitio_b.pk})
        self.assertEqual(r.json(), [])
