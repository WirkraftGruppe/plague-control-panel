"""`visita_destino` y `servicio_para_punto`: visita y servicio de un escaneo."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.utils import timezone

from apps.visitas.models import Revision, Visita
from apps.visitas.services import (
    abrir_visita,
    servicio_para_punto,
    visita_destino,
)
from apps.visitas.tests.test_turnos import BaseTurnoTests


class VisitaDestinoTests(BaseTurnoTests):
    def abierta_propia(self):
        return Visita.objects.create(
            sitio=self.sitio,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
        )

    def test_abierta_propia_gana_sobre_pendiente_con_el_punto(self):
        self.turno([(self.sala, self.roedores)])
        abierta = self.abierta_propia()
        destino = visita_destino(empleado=self.empleado, sitio=self.sitio)
        self.assertEqual(destino, abierta)

    def test_sin_abierta_devuelve_la_pendiente_mas_antigua_sin_revisiones(self):
        hoy = timezone.localdate()
        con_revision = self.turno(
            [(self.sala, self.roedores)], programada_para=hoy - timedelta(days=5)
        )
        Revision.objects.create(
            visita=con_revision,
            punto=self.sala,
            servicio=self.roedores,
            orden=1,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
            cliente_uuid=uuid4(),
            latitud=Decimal("-35.1"),
            longitud=Decimal("-57.7"),
        )
        self.turno(
            [(self.techo, self.insectos)], programada_para=hoy + timedelta(days=3)
        )
        antigua = self.turno(
            [(self.general, self.roedores)], programada_para=hoy + timedelta(days=1)
        )
        destino = visita_destino(empleado=self.empleado, sitio=self.sitio)
        self.assertEqual(destino, antigua)

    def test_administrador_no_toma_pendientes(self):
        Visita.objects.create(
            sitio=self.sitio,
            empleado=self.admin,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.PENDIENTE,
        )
        self.assertIsNone(visita_destino(empleado=self.admin, sitio=self.sitio))

    def test_sin_visitas_devuelve_none(self):
        self.assertIsNone(visita_destino(empleado=self.empleado, sitio=self.sitio))

    def test_abrir_visita_abre_la_visita_destino(self):
        pendiente = self.turno([(self.sala, self.roedores)])
        esperada = visita_destino(empleado=self.empleado, sitio=self.sitio)
        visita, creada = abrir_visita(
            empleado=self.empleado, qr_codigo=self.sala.qr_codigo
        )
        self.assertEqual(esperada, pendiente)
        self.assertEqual(visita, esperada)
        self.assertTrue(creada)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        # Con la abierta ya existente, la devuelve sin crear otra.
        otra, creada = abrir_visita(
            empleado=self.empleado, qr_codigo=self.techo.qr_codigo
        )
        self.assertEqual(otra, visita)
        self.assertFalse(creada)


class ServicioParaPuntoTests(BaseTurnoTests):
    def test_item_de_la_visita_da_su_servicio_en_turno(self):
        visita = self.turno([(self.sala, self.insectos)])
        resultado = servicio_para_punto(visita=visita, punto=self.sala)
        self.assertEqual(resultado, (self.insectos, True))

    def test_item_de_otra_visita_no_cuenta(self):
        self.turno([(self.sala, self.insectos)])
        visita = self.turno([(self.techo, self.insectos)])
        resultado = servicio_para_punto(visita=visita, punto=self.sala)
        self.assertEqual(resultado, (self.roedores, False))

    def test_sin_visita_da_el_servicio_del_punto_fuera_de_turno(self):
        resultado = servicio_para_punto(visita=None, punto=self.techo)
        self.assertEqual(resultado, (self.insectos, False))
