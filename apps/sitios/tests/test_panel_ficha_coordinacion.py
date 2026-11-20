"""Ficha del sitio: marca de turnos con un punto revisado por dos operarios."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Revision, Visita

MARCA = "Punto revisado por dos operarios el mismo día"


class FichaSitioCoordinacionTests(TestCase):
    def setUp(self):
        empresa = una_empresa()
        self.sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME", empresa=empresa),
            nombre="Planta 1",
        )
        self.punto = self.sitio.puntos.get()
        self.servicio = TipoServicio.objects.create(
            nombre="Roedores", slug="roedores-fc", empresa=empresa
        )
        empleado = User.objects.create_user(
            "emp-fc", password="x", rol=User.Rol.EMPLEADO, empresa=empresa
        )
        admin = User.objects.create_user(
            "adm-fc", password="x", rol=User.Rol.ADMINISTRADOR, empresa=empresa
        )
        self.visita = Visita.objects.create(
            sitio=self.sitio,
            empleado=empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.REALIZADA,
            abierta_en=timezone.now(),
            cerrada_en=timezone.now(),
        )
        self.client.force_login(admin)
        self.url = reverse("panel:sitios:ficha", args=[self.sitio.pk])

    def _revision(self, duplicada):
        return Revision.objects.create(
            visita=self.visita,
            punto=self.punto,
            servicio=self.servicio,
            orden=1,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
            incidencia_duplicada=duplicada,
        )

    def test_turno_con_revision_duplicada_queda_senalado(self):
        self._revision(duplicada=True)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, MARCA)
        self.assertEqual(respuesta.context["turnos_duplicados"], [self.visita])

    def test_turno_sin_duplicada_no_lleva_la_marca(self):
        self._revision(duplicada=False)
        self.assertNotContains(self.client.get(self.url), MARCA)
