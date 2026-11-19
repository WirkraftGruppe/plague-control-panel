"""Cierre de una visita con solo reportes de puntos no revisados."""

from datetime import timedelta
from io import StringIO
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.empresas.tests.ayudas import una_empresa
from apps.sitios.models import PuntoControl
from apps.visitas.models import PuntoNoRevisado, Visita
from apps.visitas.services import cerrar_visita, condicion_incidencia_sin_revisar
from apps.visitas.tests.test_api import ApiVisitasBase


class CierreSoloReportesTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.sala = PuntoControl.objects.create(sitio=self.sitio, nombre="Sala")

    def _reporte(self, visita):
        return PuntoNoRevisado.objects.create(
            visita=visita,
            punto=self.sala,
            motivo=PuntoNoRevisado.Motivo.SIN_ACCESO,
            cliente_uuid=uuid4(),
        )

    def _con_reporte(self, **extra):
        visita = self._abierta(**extra)
        self._reporte(visita)
        return visita

    def test_empleado_cierra_visita_con_solo_reportes(self):
        visita = self._con_reporte()
        r = self._cerrar(visita)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["sin_revisiones"])
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.cierre, Visita.Cierre.EMPLEADO)
        self.assertIsNotNone(visita.cerrada_en)
        # Idempotente para el mismo empleado.
        self.assertEqual(self._cerrar(visita).status_code, 200)
        # El administrador también puede cerrarla con solo reportes.
        otra = self._con_reporte()
        cerrada = cerrar_visita(
            otra, quien=self.admin, cierre=Visita.Cierre.ADMINISTRADOR
        )
        self.assertEqual(cerrada.cierre, Visita.Cierre.ADMINISTRADOR)

    def test_visita_sin_revisiones_ni_reportes_no_se_cierra(self):
        visita = self._abierta()
        with self.assertRaises(ValidationError):
            cerrar_visita(visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(self._cerrar(visita).status_code, 400)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        # El sistema cancela la no asignada y devuelve a pendiente la asignada.
        cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.CANCELADA)
        asignada = self._abierta(asignada_por=self.admin)
        cerrar_visita(asignada, quien=None, cierre=Visita.Cierre.SISTEMA)
        asignada.refresh_from_db()
        self.assertEqual(asignada.estado, Visita.Estado.PENDIENTE)

    def test_cierre_nocturno_con_solo_reportes_queda_realizada(self):
        vieja = timezone.now() - timedelta(days=3)
        visita = self._con_reporte(abierta_en=vieja)
        asignada = self._abierta(abierta_en=vieja, asignada_por=self.admin)
        self._reporte(asignada)
        sin_nada = self._abierta(self.otro, abierta_en=vieja)
        # Sin actividad reciente: la visita, su reporte y el reporte de la asignada.
        Visita.objects.de_empresa(una_empresa()).update(actualizado=vieja)
        PuntoNoRevisado.objects.de_empresa(una_empresa()).update(creado=vieja)
        call_command("cerrar_visitas_abiertas", stdout=StringIO())
        for v in (visita, asignada, sin_nada):
            v.refresh_from_db()
        for v in (visita, asignada):
            self.assertEqual(v.estado, Visita.Estado.REALIZADA)
            self.assertEqual(v.cierre, Visita.Cierre.SISTEMA)
        ultimo = visita.no_revisados.get().reportado_en
        self.assertEqual(visita.cerrada_en, ultimo)
        self.assertEqual(sin_nada.estado, Visita.Estado.CANCELADA)

    def test_cierre_con_solo_reportes_no_cambia_vencimiento(self):
        self.sala.frecuencia_dias = 30
        self.sala.save()
        self.punto.frecuencia_dias = 30
        self.punto.save()
        antes = {
            p.pk: p.proximo_vencimiento
            for p in PuntoControl.objects.de_empresa(una_empresa())
        }
        visita = self._con_reporte()
        self.assertEqual(self._cerrar(visita).status_code, 200)
        despues = {
            p.pk: p.proximo_vencimiento
            for p in PuntoControl.objects.de_empresa(una_empresa())
        }
        self.assertEqual(antes, despues)

    def test_historial_marca_sin_revisiones(self):
        solo_reportes = self._con_reporte()
        self.assertEqual(self._cerrar(solo_reportes).status_code, 200)
        con_revision = self._realizada(self.empleado, 5)
        r = self.api.get("/api/v1/me/historial/")
        self.assertEqual(r.status_code, 200, r.content)
        marcas = {v["id"]: v["sin_revisiones"] for v in r.json()["results"]}
        self.assertEqual(marcas, {solo_reportes.id: True, con_revision.id: False})
        # Sin consultas por visita: más visitas, las mismas consultas.
        with CaptureQueriesContext(connection) as pocas:
            self.api.get("/api/v1/me/historial/")
        for _ in range(2):
            otra = self._con_reporte()
            self.assertEqual(self._cerrar(otra).status_code, 200)
        with CaptureQueriesContext(connection) as muchas:
            self.api.get("/api/v1/me/historial/")
        self.assertEqual(len(pocas), len(muchas))

    def test_panel_muestra_cerrado_sin_revisiones(self):
        visita = self._con_reporte()
        self.assertEqual(self._cerrar(visita).status_code, 200)
        normal = self._realizada(self.empleado, 5)
        self.client.force_login(self.admin)
        ficha = self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))
        self.assertContains(ficha, "Cerrado sin revisiones")
        ficha = self.client.get(reverse("panel:visitas:ficha", args=[normal.pk]))
        self.assertNotContains(ficha, "Cerrado sin revisiones")
        listado = self.client.get(reverse("panel:visitas:listado"))
        self.assertEqual(listado.content.decode().count("Cerrado sin revisiones"), 1)
        self.assertTrue(
            any(
                v.sin_revisiones
                for v in listado.context["visitas"]
                if v.pk == visita.pk
            )
        )

    def test_cuenta_en_incidencias_sin_revisar(self):
        visita = self._con_reporte()
        self.assertEqual(self._cerrar(visita).status_code, 200)
        encontradas = Visita.objects.de_empresa(una_empresa()).filter(
            condicion_incidencia_sin_revisar()
        )
        self.assertEqual(list(encontradas.values_list("pk", flat=True)), [visita.pk])
        self.client.force_login(self.admin)
        r = self.client.get(reverse("panel:visitas:listado"))
        self.assertIn(visita, r.context["incidencias_sin_revisar"])
