"""El resolver de QR devuelve el servicio del punto, su estado y si está en turno."""

import datetime
import json
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Revision, Visita
from apps.visitas.services import crear_turno
from apps.visitas.tests.test_api import MEDIA_TEMPORAL, jpeg_chico


class BaseResolverTests(TestCase):
    """Datos y ayudas comunes de los tests del resolver."""

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


class ResolverServicioTests(BaseResolverTests):
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
        self.assertEqual(
            set(cuerpo),
            {
                "punto",
                "sitio",
                "cliente",
                "visita_pendiente_propia",
                "visita_abierta_propia",
                "visita_destino",
            },
        )


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ResolverCoherenteConRevisionTests(BaseResolverTests):
    """Lo que el resolver muestra es lo que la revisión guarda."""

    def _abierta(self):
        return Visita.objects.create(
            sitio=self.sitio,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            motivo_manual="",
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now() - datetime.timedelta(hours=1),
        )

    def _abrir(self):
        r = self.api.post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(self.punto.qr_codigo)},
            format="json",
        )
        self.assertIn(r.status_code, (200, 201), r.content)
        return r.json()["id"]

    def _revisar(self, visita_id, servicio):
        datos = {"cebos": 3} if servicio == self.desrat else {}
        r = self.api.post(
            "/api/v1/revisiones/",
            {
                "visita": visita_id,
                "qr_codigo": str(self.punto.qr_codigo),
                "cliente_uuid": str(uuid4()),
                "realizada_en": (
                    timezone.now() - datetime.timedelta(minutes=1)
                ).isoformat(),
                "latitud": "-36.100000",
                "longitud": "-57.800000",
                "precision_m": "8.5",
                "datos": json.dumps(datos),
                "fotos": [jpeg_chico()],
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def _flujo(self):
        """Resuelve, abre si hace falta y registra: `(resolver, abrir_id, revision)`."""
        cuerpo = self._resolver()
        abierta = cuerpo["visita_abierta_propia"]
        abrir_id = abierta or self._abrir()
        servicio = (
            TipoServicio.objects.get(pk=cuerpo["punto"]["servicio"]["id"])
            if cuerpo["punto"]["servicio"]
            else None
        )
        revision = self._revisar(abrir_id, servicio)
        self.assertEqual(revision["servicio"]["id"], cuerpo["punto"]["servicio"]["id"])
        self.assertEqual(revision["fuera_de_turno"], not cuerpo["punto"]["en_turno"])
        return cuerpo, abrir_id, revision

    def test_abierta_sin_items_y_pendiente_con_el_punto_guarda_el_servicio_devuelto(
        self,
    ):
        self.punto.servicio = self.desrat
        self.punto.save()
        abierta = self._abierta()
        self._turno(self.fumiga)
        cuerpo, _, revision = self._flujo()
        self.assertEqual(cuerpo["visita_destino"], abierta.id)
        self.assertEqual(cuerpo["punto"]["servicio"]["id"], self.desrat.id)
        self.assertFalse(cuerpo["punto"]["en_turno"])
        self.assertEqual(revision["servicio"]["id"], self.desrat.id)
        self.assertTrue(revision["fuera_de_turno"])
        self.assertEqual(Revision.objects.get().visita_id, abierta.id)

    def test_abierto_y_pendiente_con_el_punto_devuelve_y_guarda_el_del_abierto(self):
        self.punto.servicio = self.desrat
        self.punto.save()
        abierto = self._turno(self.fumiga)
        Visita.objects.filter(pk=abierto.pk).update(
            estado=Visita.Estado.ABIERTA, abierta_en=timezone.now()
        )
        self._turno(self.desrat, dias=2)
        cuerpo, abrir_id, revision = self._flujo()
        self.assertEqual(cuerpo["visita_destino"], abierto.id)
        self.assertEqual(abrir_id, abierto.id)
        self.assertEqual(cuerpo["punto"]["servicio"]["id"], self.fumiga.id)
        self.assertTrue(cuerpo["punto"]["en_turno"])
        self.assertEqual(revision["servicio"]["id"], self.fumiga.id)
        self.assertFalse(revision["fuera_de_turno"])

    def test_pendiente_mas_antigua_sin_el_punto_devuelve_y_guarda_fuera_de_turno(self):
        self.punto.servicio = self.desrat
        self.punto.save()
        otro = self.sitio.puntos.create(nombre="Depósito", orden=1)
        antigua = crear_turno(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=timezone.localdate() + datetime.timedelta(days=1),
            items=[(otro, self.fumiga)],
            asignada_por=self.admin,
        )
        self._turno(self.fumiga, dias=2)
        cuerpo, abrir_id, revision = self._flujo()
        self.assertEqual(cuerpo["visita_destino"], antigua.id)
        self.assertEqual(abrir_id, antigua.id)
        self.assertEqual(cuerpo["punto"]["servicio"]["id"], self.desrat.id)
        self.assertFalse(cuerpo["punto"]["en_turno"])
        self.assertEqual(revision["servicio"]["id"], self.desrat.id)
        self.assertTrue(revision["fuera_de_turno"])

    def test_visita_destino_es_la_que_abre_abrir_visita(self):
        pendiente = self._turno(self.fumiga)
        self._turno(self.desrat, dias=2)
        cuerpo = self._resolver()
        self.assertEqual(cuerpo["visita_destino"], pendiente.id)
        self.assertEqual(cuerpo["visita_destino"], self._abrir())

    def test_sin_visitas_visita_destino_nula(self):
        self.punto.servicio = self.desrat
        self.punto.save()
        cuerpo = self._resolver()
        self.assertIsNone(cuerpo["visita_destino"])
        self.assertEqual(cuerpo["punto"]["servicio"]["id"], self.desrat.id)
        self.assertFalse(cuerpo["punto"]["en_turno"])
