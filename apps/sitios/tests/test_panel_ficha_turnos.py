"""Ficha del sitio: estado de los puntos, turnos pendientes y realizados, acciones."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import ItemTurno, Visita


class FichaSitioTurnosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = Cliente.objects.create(razon_social="ACME")
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta 1")
        cls.servicio = TipoServicio.objects.create(nombre="Roedores", slug="roedores-f")
        cls.punto = cls.sitio.puntos.get(orden=0)
        cls.empleado = User.objects.create_user(
            "emp-ficha", password="x", rol=User.Rol.EMPLEADO, first_name="Ana"
        )
        cls.admin = User.objects.create_user(
            "adm-ficha", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("panel:sitios:ficha", args=[self.sitio.pk])

    def test_punto_vencido_ayer_figura_vencida_en_la_ficha(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.punto.proximo_vencimiento = ayer
        self.punto.servicio = self.servicio
        self.punto.save()
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "etiqueta-danger")
        self.assertContains(respuesta, "Vencida")
        self.assertEqual(respuesta.context["puntos"][0].estado, "vencida")

    def test_lista_turnos_pendientes_y_realizados(self):
        pendiente = Visita.objects.create(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=timezone.localdate() + timedelta(days=1),
        )
        ItemTurno.objects.create(
            visita=pendiente, punto=self.punto, servicio=self.servicio
        )
        realizada = Visita.objects.create(
            sitio=self.sitio,
            empleado=self.empleado,
            estado=Visita.Estado.REALIZADA,
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
            abierta_en=timezone.now(),
            cerrada_en=timezone.now(),
        )
        respuesta = self.client.get(self.url)
        self.assertEqual(list(respuesta.context["turnos_pendientes"]), [pendiente])
        self.assertEqual(list(respuesta.context["turnos_realizados"]), [realizada])
        self.assertContains(respuesta, "Turnos pendientes")
        self.assertContains(respuesta, "Turnos realizados")
        self.assertContains(
            respuesta, reverse("panel:visitas:ficha", args=[pendiente.pk])
        )
        self.assertContains(
            respuesta, reverse("panel:visitas:ficha", args=[realizada.pk])
        )

    def test_acciones_nuevo_turno_y_cargar_visita(self):
        respuesta = self.client.get(self.url)
        self.assertContains(
            respuesta,
            f'href="{reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])}"',
        )
        self.assertContains(
            respuesta, f'href="{reverse("panel:visitas:cargar", args=[self.sitio.pk])}"'
        )
        self.assertContains(respuesta, "Nuevo turno")
        self.assertContains(respuesta, "Cargar visita")
