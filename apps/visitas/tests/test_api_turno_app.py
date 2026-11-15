"""Turno de la app: contacto del sitio, estado de los puntos y detalle del turno."""

from datetime import date, timedelta

from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.sitios.models import PuntoControl
from apps.visitas.models import Visita
from apps.visitas.services import crear_turno
from apps.visitas.tests.ayudas_empresa import dos_empresas
from apps.visitas.tests.test_api import MEDIA_TEMPORAL, ApiVisitasBase


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class TurnoAppTests(ApiVisitasBase):
    def _turno(self, puntos=None, dia=1, empleado=None):
        return crear_turno(
            sitio=self.sitio,
            empleado=empleado or self.empleado,
            programada_para=date(2026, 9, dia),
            items=[(p, self.tipo) for p in (puntos or [self.punto])],
            asignada_por=self.admin,
        )

    def test_item_vencido_ayer_trae_estado_vencida(self):
        ayer = timezone.localdate() - timedelta(days=1)
        self.punto.proximo_vencimiento = ayer
        self.punto.save()
        self._turno()
        (cuerpo,) = self.api.get("/api/v1/me/visitas/").json()["results"]
        punto = cuerpo["items"][0]["punto"]
        self.assertEqual(punto["estado"], "vencida")
        self.assertEqual(punto["proximo_vencimiento"], ayer.isoformat())

    def test_estado_coincide_con_el_resolver_de_qr(self):
        hoy = timezone.localdate()
        self.punto.proximo_vencimiento = hoy + timedelta(days=3)
        self.punto.save()
        self._turno()
        (cuerpo,) = self.api.get("/api/v1/me/visitas/").json()["results"]
        punto = cuerpo["items"][0]["punto"]
        r = self.api.post(f"/api/v1/qr/{self.punto.qr_codigo}/resolver/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(punto["estado"], r.json()["punto"]["estado"])
        self.assertEqual(punto["estado"], "proxima")
        self.assertEqual(
            punto["proximo_vencimiento"], r.json()["punto"]["proximo_vencimiento"]
        )

    def test_consultas_iguales_con_5_y_50_items(self):
        puntos = [
            PuntoControl.objects.create(
                sitio=self.sitio, nombre=f"P{i}", orden=i + 1, servicio=self.tipo
            )
            for i in range(50)
        ]
        chico = self._turno(puntos[:5], dia=1)
        grande = self._turno(puntos, dia=2)
        self.api.get(f"/api/v1/me/visitas/{chico.id}/")  # calienta cachés
        consultas = {}
        for turno, cantidad in ((chico, 5), (grande, 50)):
            with CaptureQueriesContext(connection) as captura:
                r = self.api.get(f"/api/v1/me/visitas/{turno.id}/")
            self.assertEqual(len(r.json()["items"]), cantidad)
            consultas[cantidad] = len(captura)
        self.assertEqual(consultas[5], consultas[50])

    def test_sitio_trae_contacto_o_null(self):
        self._turno()
        (cuerpo,) = self.api.get("/api/v1/me/visitas/").json()["results"]
        self.assertIsNone(cuerpo["sitio"]["contacto"])
        self.sitio.contacto_en_sitio = "Marta"
        self.sitio.telefono_en_sitio = "221-555"
        self.sitio.save()
        (cuerpo,) = self.api.get("/api/v1/me/visitas/").json()["results"]
        self.assertEqual(
            cuerpo["sitio"]["contacto"], {"nombre": "Marta", "telefono": "221-555"}
        )
        self.assertNotIn("latitud", cuerpo["sitio"])
        self.assertNotIn("notas", cuerpo["sitio"])
        self.sitio.contacto_en_sitio = ""
        self.sitio.save()
        (cuerpo,) = self.api.get("/api/v1/me/visitas/").json()["results"]
        self.assertEqual(
            cuerpo["sitio"]["contacto"], {"nombre": "", "telefono": "221-555"}
        )

    def test_historial_y_cierre_no_traen_contacto(self):
        self.sitio.contacto_en_sitio = "Marta"
        self.sitio.telefono_en_sitio = "221-555"
        self.sitio.save()
        self._realizada(self.empleado, 5)
        r = self.api.get("/api/v1/me/historial/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.json()["results"]), 1)
        self.assertNotIn("contacto", r.json()["results"][0]["sitio"])
        self.assertNotIn("221-555", r.content.decode())
        abierta = self._abierta()
        self._revision(abierta)
        r = self._cerrar(abierta)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertNotIn("contacto", r.json()["sitio"])
        self.assertNotIn("221-555", r.content.decode())

    def test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista(self):
        self.sitio.contacto_en_sitio = "Marta"
        self.sitio.save()
        turno = self._turno()
        (de_lista,) = self.api.get("/api/v1/me/visitas/").json()["results"]
        r = self.api.get(f"/api/v1/me/visitas/{turno.id}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json(), de_lista)

    def test_detalle_de_otro_empleado_da_404(self):
        ajeno = self._turno(dia=2, empleado=self.otro)
        r = self.api.get(f"/api/v1/me/visitas/{ajeno.id}/")
        self.assertEqual(r.status_code, 404)

    def test_detalle_de_otra_empresa_da_404(self):
        lado = dos_empresas()[1]
        Visita.objects.de_empresa(lado.empresa).filter(pk=lado.visita.pk).update(
            estado=Visita.Estado.ABIERTA, abierta_en=timezone.now()
        )
        r = self.api.get(f"/api/v1/me/visitas/{lado.visita.pk}/")
        self.assertEqual(r.status_code, 404)
        r = self._api(lado.empleado).get(f"/api/v1/me/visitas/{lado.visita.pk}/")
        self.assertEqual(r.status_code, 200, r.content)

    def test_detalle_de_turno_realizado_da_404(self):
        visita = self._realizada(self.empleado, 5)
        r = self.api.get(f"/api/v1/me/visitas/{visita.id}/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.api.get("/api/v1/me/visitas/99999/").status_code, 404)

    def _contacto_en_lista_y_detalle(self, turno):
        """`sitio.contacto` del turno en `me/visitas/` y en `me/visitas/<pk>/`."""
        lista = self.api.get("/api/v1/me/visitas/").json()["results"]
        (de_la_lista,) = [v for v in lista if v["id"] == turno.id]
        detalle = self.api.get(f"/api/v1/me/visitas/{turno.id}/")
        self.assertEqual(detalle.status_code, 200)
        return de_la_lista["sitio"]["contacto"], detalle.json()["sitio"]["contacto"]

    def _con_contacto(self):
        self.sitio.contacto_en_sitio = "Marta"
        self.sitio.telefono_en_sitio = "221-555"
        self.sitio.save()
        turno = self._turno()
        esperado = {"nombre": "Marta", "telefono": "221-555"}
        self.assertEqual(self._contacto_en_lista_y_detalle(turno), (esperado, esperado))
        return turno

    def test_contacto_null_con_cliente_dado_de_baja(self):
        turno = self._con_contacto()
        cliente = self.sitio.cliente
        cliente.activo = False
        cliente.save()
        self.sitio.refresh_from_db()
        self.assertTrue(self.sitio.activo)
        self.assertEqual(self._contacto_en_lista_y_detalle(turno), (None, None))

    def test_contacto_null_con_sitio_dado_de_baja(self):
        turno = self._con_contacto()
        self.sitio.activo = False
        self.sitio.save()
        self.assertTrue(self.sitio.cliente.activo)
        self.assertEqual(self._contacto_en_lista_y_detalle(turno), (None, None))
