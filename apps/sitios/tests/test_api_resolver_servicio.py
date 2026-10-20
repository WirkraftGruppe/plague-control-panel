"""El resolver de QR devuelve el servicio del punto, su estado y si está en turno."""

import datetime

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Visita
from apps.visitas.services import crear_turno


class ResolverServicioTests(TestCase):
    def setUp(self):
        cache.clear()
        self.sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME"), nombre="Planta 1"
        )
        self.punto = self.sitio.puntos.get()
        self.desrat = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        self.fumiga = TipoServicio.objects.create(nombre="Fumigación", slug="fumiga")
        CampoPlanilla.objects.create(
            tipo_servicio=self.desrat,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        CampoPlanilla.objects.create(
            tipo_servicio=self.desrat,
            orden=1,
            etiqueta="Observación general",
            clave="general",
            tipo=CampoPlanilla.Tipo.TEXTO,
            ambito=CampoPlanilla.Ambito.VISITA,
        )
        self.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.api = APIClient()
        self.api.force_authenticate(self.empleado)

    def _turno(self, servicio, empleado=None, dias=1):
        return crear_turno(
            sitio=self.sitio,
            empleado=empleado or self.empleado,
            programada_para=timezone.localdate() + datetime.timedelta(days=dias),
            items=[(self.punto, servicio)],
            asignada_por=self.admin,
        )

    def _resolver(self):
        r = self.api.post(f"/api/v1/qr/{self.punto.qr_codigo}/resolver/")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_punto_del_turno_devuelve_el_servicio_del_item(self):
        self.punto.servicio = self.desrat
        self.punto.save()
        turno = self._turno(self.fumiga)
        cuerpo = self._resolver()
        self.assertTrue(cuerpo["punto"]["en_turno"])
        self.assertEqual(cuerpo["punto"]["servicio"]["id"], self.fumiga.id)
        self.assertEqual(cuerpo["punto"]["servicio"]["slug"], "fumiga")
        self.assertEqual(cuerpo["visita_pendiente_propia"], turno.id)
        # Un turno ajeno no cuenta.
        ajeno = User.objects.create_user(username="otro", password="x")
        Visita.objects.filter(pk=turno.pk).update(empleado=ajeno)
        punto = self._resolver()["punto"]
        self.assertFalse(punto["en_turno"])
        self.assertEqual(punto["servicio"]["id"], self.desrat.id)

    def test_punto_fuera_del_turno_devuelve_el_servicio_del_punto(self):
        self.punto.servicio = self.desrat
        self.punto.save()
        punto = self._resolver()["punto"]
        self.assertFalse(punto["en_turno"])
        self.assertEqual(punto["servicio"]["id"], self.desrat.id)
        self.assertEqual(punto["servicio"]["nombre"], "Desratización")

    def test_devuelve_el_esquema_del_servicio(self):
        self._turno(self.desrat)
        servicio = self._resolver()["punto"]["servicio"]
        self.assertEqual([c["clave"] for c in servicio["esquema_punto"]], ["cebos"])
        self.assertEqual(servicio["esquema_punto"][0]["etiqueta"], "Cebos")
        self.assertTrue(servicio["esquema_punto"][0]["obligatorio"])
        self.assertEqual([c["clave"] for c in servicio["esquema_visita"]], ["general"])
        self.assertEqual(
            sorted(servicio),
            ["esquema_punto", "esquema_visita", "id", "nombre", "slug"],
        )

    def test_punto_vencido_ayer_figura_vencida(self):
        ayer = timezone.localdate() - datetime.timedelta(days=1)
        self.punto.proximo_vencimiento = ayer
        self.punto.save()
        punto = self._resolver()["punto"]
        self.assertEqual(punto["estado"], "vencida")
        self.assertEqual(punto["proximo_vencimiento"], ayer.isoformat())

    def test_punto_sin_servicio_devuelve_servicio_nulo(self):
        cuerpo = self._resolver()
        punto = cuerpo["punto"]
        self.assertIsNone(punto["servicio"])
        self.assertFalse(punto["en_turno"])
        self.assertEqual(punto["estado"], "sin_programar")
        self.assertIsNone(punto["proximo_vencimiento"])
        self.assertNotIn("proyectos", cuerpo)
