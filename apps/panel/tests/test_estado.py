"""Parcial de estado por sitio: contrato con el editor del plano."""

import re
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios.models import Plano, PuntoControl, Sitio


class EstadoSitioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user("emp", password="clave-segura-123")
        cliente = Cliente.objects.create(razon_social="Cliente SA")
        cls.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        cls.plano = Plano.objects.create(
            sitio=cls.sitio, nombre="Planta baja", imagen="planos/p.png"
        )
        cls.url = reverse("panel:estado_sitio", args=[cls.sitio.pk])

    def punto(self, nombre, **campos):
        return PuntoControl.objects.create(sitio=self.sitio, nombre=nombre, **campos)

    def programar(self, punto, dias):
        """Deja el próximo vencimiento del punto dentro de `dias` días."""
        punto.proximo_vencimiento = timezone.localdate() + timedelta(days=dias)
        punto.save()

    def items(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        html = respuesta.content.decode()
        self.assertIn('<ul id="estado-puntos"', html)
        return {
            int(m["punto"]): m
            for m in re.finditer(
                r'<li data-punto="(?P<punto>\d+)" data-estado="(?P<estado>[a-z_]*)"'
                r' data-x="(?P<x>[^"]*)" data-y="(?P<y>[^"]*)"'
                r' data-plano="(?P<plano>[^"]*)"',
                html,
            )
        }

    def test_parcial_refleja_el_vencimiento(self):
        general = self.sitio.puntos.get(nombre="General")
        ubicado = self.punto(
            "Ubicado", plano=self.plano, x=Decimal("0.2500"), y=Decimal("0.5000")
        )
        libre = self.punto("Libre")
        self.punto("Inactivo", activo=False)

        items = self.items()
        self.assertEqual(set(items), {general.pk, ubicado.pk, libre.pk})
        self.assertEqual(items[ubicado.pk]["estado"], "sin_programar")
        self.assertEqual(items[ubicado.pk]["x"], "0.2500")
        self.assertEqual(items[ubicado.pk]["y"], "0.5000")
        self.assertEqual(items[ubicado.pk]["plano"], str(self.plano.pk))
        self.assertEqual(items[libre.pk]["x"], "")
        self.assertEqual(items[libre.pk]["plano"], "")

        self.programar(ubicado, 20)
        self.assertEqual(self.items()[ubicado.pk]["estado"], "al_dia")
        self.programar(libre, -1)
        self.assertEqual(self.items()[libre.pk]["estado"], "vencida")

    def test_consultas_constantes(self):
        self.client.force_login(self.admin)

        def medir():
            with self.assertNumQueries(4):
                # sesión, usuario, sitio y puntos
                self.client.get(self.url)

        for n in range(2):
            self.programar(self.punto(f"P{n}"), n)
        medir()
        for n in range(2, 8):
            self.programar(self.punto(f"P{n}"), n)
        medir()

    def test_empleado_recibe_403(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_sitio_inexistente_da_404(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("panel:estado_sitio", args=[999999]))
        self.assertEqual(respuesta.status_code, 404)
