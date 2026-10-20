"""Acceso del empleado a planos y puntos: depende de su visita en el sitio."""

import shutil

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios.models import PuntoControl, Sitio
from apps.sitios.tests.test_api import MEDIA_TEMPORAL, crear_plano
from apps.visitas.models import Visita


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class AccesoPorSitioTests(TestCase):
    URL_PUNTOS = "/api/v1/me/puntos/"

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        self.otro_sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 2")
        self.plano = crear_plano(self.sitio)
        self.empleado = User.objects.create_user(
            "emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.ajeno = User.objects.create_user(
            "ajeno", password="x", rol=User.Rol.EMPLEADO
        )
        self.api = APIClient()
        self.api.force_authenticate(self.empleado)
        self.url_plano = f"/api/v1/planos/{self.plano.id}/imagen/"

    def visita(self, sitio, empleado=None, estado=Visita.Estado.PENDIENTE):
        return Visita.objects.create(
            sitio=sitio,
            empleado=empleado or self.empleado,
            origen=Visita.Origen.APP,
            estado=estado,
        )

    def test_plano_exige_visita_del_empleado_en_el_sitio(self):
        self.assertEqual(self.api.get(self.url_plano).status_code, 404)
        self.visita(self.sitio, estado=Visita.Estado.CANCELADA)
        self.visita(self.sitio, estado=Visita.Estado.REALIZADA)
        self.assertEqual(self.api.get(self.url_plano).status_code, 404)
        # Una visita pendiente o abierta propia en el sitio da acceso.
        pendiente = self.visita(self.sitio)
        self.assertEqual(self.api.get(self.url_plano).status_code, 200)
        Visita.objects.filter(pk=pendiente.pk).update(estado=Visita.Estado.ABIERTA)
        self.assertEqual(self.api.get(self.url_plano).status_code, 200)

    def test_plano_con_visita_en_otro_sitio_da_404(self):
        self.visita(self.otro_sitio)
        self.visita(self.sitio, empleado=self.ajeno)
        self.assertEqual(self.api.get(self.url_plano).status_code, 404)

    def test_mis_puntos_solo_de_sitios_con_visita_propia(self):
        extra = PuntoControl.objects.create(sitio=self.sitio, nombre="Sala")
        PuntoControl.objects.create(sitio=self.sitio, nombre="Baja", activo=False)
        self.visita(self.sitio)
        self.visita(self.otro_sitio, empleado=self.ajeno)
        r = self.api.get(self.URL_PUNTOS)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            {p["id"] for p in r.json()},
            {self.sitio.puntos.get(nombre="General").id, extra.id},
        )
        # Pedir un sitio sin visita propia devuelve la lista vacía.
        r = self.api.get(self.URL_PUNTOS, {"sitio": self.otro_sitio.id})
        self.assertEqual(r.json(), [])
        r = self.api.get(self.URL_PUNTOS, {"sitio": self.sitio.id})
        self.assertEqual(len(r.json()), 2)
