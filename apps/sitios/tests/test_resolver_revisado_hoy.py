"""Resolver de QR: `punto.revisado_hoy_por` (coordinación entre operarios)."""

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Revision, Visita


class RevisadoHoyTests(TestCase):
    def setUp(self):
        cache.clear()
        empresa = una_empresa()
        self.sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME", empresa=empresa),
            nombre="Planta 1",
        )
        self.punto = self.sitio.puntos.get()
        self.servicio = TipoServicio.objects.create(
            nombre="Roedores", slug="roedores-rh", empresa=empresa
        )
        self.yo = User.objects.create_user(
            "yo", password="x", rol=User.Rol.EMPLEADO, empresa=empresa
        )
        self.otro = User.objects.create_user(
            "otro",
            password="x",
            rol=User.Rol.EMPLEADO,
            empresa=empresa,
            first_name="Ana",
            last_name="Pérez",
        )
        self.admin = User.objects.create_user(
            "adm", password="x", rol=User.Rol.ADMINISTRADOR, empresa=empresa
        )
        self.api = APIClient()
        self.api.force_authenticate(self.yo)

    def _revision(self, empleado, hace=timedelta(0), cuenta=True):
        visita = Visita.objects.create(
            sitio=self.sitio,
            empleado=empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now() - timedelta(hours=2),
            cuenta_como_servicio=cuenta,
        )
        ahora = timezone.now()
        return Revision.objects.create(
            visita=visita,
            punto=self.punto,
            servicio=self.servicio,
            orden=1,
            realizada_en=ahora - hace,
            recibida_en=ahora,
        )

    def _punto(self):
        respuesta = self.api.post(f"/api/v1/qr/{self.punto.qr_codigo}/resolver/")
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        return respuesta.json()["punto"]

    def test_revisado_hoy_por_otro_trae_nombre_y_propia_false(self):
        self._revision(self.otro)
        revisado = self._punto()["revisado_hoy_por"]
        self.assertEqual(
            revisado["operario"], {"id": self.otro.pk, "nombre": "Ana Pérez"}
        )
        self.assertFalse(revisado["propia"])
        self.assertTrue(revisado["realizada_en"])

    def test_revisado_ayer_es_null(self):
        self._revision(self.otro, hace=timedelta(days=1, hours=1))
        self.assertIsNone(self._punto()["revisado_hoy_por"])

    def test_revisado_hoy_por_el_mismo_usuario_propia_true(self):
        self._revision(self.yo)
        revisado = self._punto()["revisado_hoy_por"]
        self.assertEqual(revisado["operario"]["id"], self.yo.pk)
        self.assertTrue(revisado["propia"])

    def test_visita_de_administrador_no_cuenta(self):
        self._revision(self.admin, cuenta=False)
        self.assertIsNone(self._punto()["revisado_hoy_por"])

    def test_datos_sin_conexion_sin_nombres_ni_horas(self):
        self._revision(self.otro)
        respuesta = self.api.get("/api/v1/me/datos-sin-conexion/")
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        self.assertNotIn("Ana", contenido)
        self.assertNotIn("revisado_hoy_por", contenido)
