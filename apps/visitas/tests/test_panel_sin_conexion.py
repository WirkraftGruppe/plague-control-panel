"""Panel de Visitas: servicio distinto y hora de llegada de las revisiones."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.models import Visita

from .test_models import crear_revision, crear_visita


class FichaSinConexionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-sc", password="x", rol=User.Rol.ADMINISTRADOR, empresa=una_empresa()
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _visita(self):
        ahora = timezone.now()
        return crear_visita(
            estado=Visita.Estado.REALIZADA,
            origen=Visita.Origen.APP,
            abierta_en=ahora,
            cerrada_en=ahora,
            cierre=Visita.Cierre.ADMINISTRADOR,
        )

    def _ficha(self, visita):
        return self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))

    def _con_diferencia(self, minutos):
        visita = self._visita()
        recibida = timezone.now()
        crear_revision(
            visita,
            realizada_en=recibida - timedelta(minutes=minutos),
            recibida_en=recibida,
        )
        return visita

    def test_ficha_muestra_servicio_distinto(self):
        visita = self._visita()
        crear_revision(visita, incidencia_servicio=True)
        self.assertContains(self._ficha(visita), "Servicio distinto del asignado")
        otra = self._visita()
        crear_revision(otra)
        self.assertNotContains(self._ficha(otra), "Servicio distinto del asignado")

    def test_ficha_muestra_llegada_si_difiere_mas_de_10_minutos(self):
        visita = self._con_diferencia(11)
        self.assertContains(self._ficha(visita), "Llegó ")

    def test_ficha_no_muestra_llegada_si_difiere_10_minutos_o_menos(self):
        visita = self._con_diferencia(10)
        self.assertNotContains(self._ficha(visita), "Llegó ")

    def test_boton_marcar_revisada_con_incidencia_de_servicio(self):
        visita = self._visita()
        crear_revision(visita, incidencia_servicio=True)
        self.assertContains(self._ficha(visita), "Marcar como revisada")
        sin = self._visita()
        crear_revision(sin)
        self.assertNotContains(self._ficha(sin), "Marcar como revisada")

    def test_menu_cuenta_incidencia_de_servicio(self):
        visita = self._visita()
        crear_revision(visita, incidencia_servicio=True)
        menu = self.client.get(reverse("panel:sitios:listado"))
        self.assertContains(menu, 'class="contador-menu">1<')
