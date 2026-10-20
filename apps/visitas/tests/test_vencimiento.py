"""El vencimiento de un punto se recalcula con su revisión más reciente."""

from datetime import timedelta

from django.utils import timezone

from apps.sitios.models import Sitio
from apps.visitas.services import abrir_visita, registrar_visita_manual
from apps.visitas.tests.test_services import jpeg_chico
from apps.visitas.tests.test_turnos import BaseTurnoTests


class VencimientoTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.general.frecuencia_dias = 30
        self.general.save()

    def abrir(self, usuario=None):
        usuario = usuario or self.empleado
        return abrir_visita(empleado=usuario, qr_codigo=self.general.qr_codigo)[0]

    def vencimiento(self):
        self.general.refresh_from_db()
        return self.general.proximo_vencimiento

    def test_revision_con_frecuencia_30_fija_fecha_mas_30(self):
        self.assertIsNone(self.vencimiento())
        revision = self.revisar(self.abrir(), self.general)
        esperado = timezone.localdate(revision.realizada_en) + timedelta(days=30)
        self.assertEqual(self.vencimiento(), esperado)

    def test_revision_anterior_no_pisa(self):
        visita = self.abrir()
        reciente = self.revisar(visita, self.general)
        self.revisar(
            visita, self.general, realizada_en=timezone.now() - timedelta(days=3)
        )
        esperado = timezone.localdate(reciente.realizada_en) + timedelta(days=30)
        self.assertEqual(self.vencimiento(), esperado)

    def test_visita_de_administrador_no_cambia(self):
        visita = self.abrir(self.admin)
        self.assertFalse(visita.cuenta_como_servicio)
        self.revisar(visita, self.general, empleado=self.admin)
        self.assertIsNone(self.vencimiento())

    def test_punto_sin_frecuencia_no_cambia(self):
        self.sala.frecuencia_dias = None
        self.sala.save()
        visita = self.abrir()
        self.revisar(visita, self.sala)
        self.sala.refresh_from_db()
        self.assertIsNone(self.sala.proximo_vencimiento)

    def test_carga_manual_actualiza_el_vencimiento(self):
        Sitio.objects.filter(pk=self.sitio.pk).update(
            creado=timezone.now() - timedelta(days=30)
        )
        self.sitio.refresh_from_db()
        realizada = timezone.now() - timedelta(days=3)
        registrar_visita_manual(
            sitio=self.sitio,
            empleado=self.empleado,
            administrador=self.admin,
            motivo="Sin señal",
            realizada_en=realizada,
            items=[(self.general, self.roedores)],
            datos={},
            productos_aplicados=[],
            fotos=[jpeg_chico()],
        )
        esperado = timezone.localdate(realizada) + timedelta(days=30)
        self.assertEqual(self.vencimiento(), esperado)
