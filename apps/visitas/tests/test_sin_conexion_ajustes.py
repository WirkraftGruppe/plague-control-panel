"""Ajustes del trabajo sin conexión: reenvío de `abrir`, hora de recepción, tope
nocturno y horas anteriores a la apertura."""

from datetime import timedelta
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.empresas.tests.ayudas import una_empresa
from apps.sitios.models import Sitio
from apps.visitas.models import Visita
from apps.visitas.services import abrir_visita, cerrar_visita, registrar_visita_manual
from apps.visitas.tests.test_comandos import abierta_hace
from apps.visitas.tests.test_models import crear_revision
from apps.visitas.tests.test_sin_conexion import BaseSinConexionApi, hace
from apps.visitas.tests.test_sin_conexion_servicios import BaseSinConexion

SIN_CONEXION = "registrado sin conexión"


class ReenvioAbrirTests(BaseSinConexion):
    def _con_abierta_y_hora(self, **hora):
        visita = self.abrir()
        antes = Visita.objects.de_empresa(una_empresa()).get(pk=visita.pk)
        devuelta, creada = abrir_visita(
            empleado=self.empleado, qr_codigo=self.general.qr_codigo, **hora
        )
        despues = Visita.objects.de_empresa(una_empresa()).get(pk=visita.pk)
        self.assertFalse(creada)
        self.assertEqual(devuelta.pk, visita.pk)
        self.assertEqual(despues.abierta_en, antes.abierta_en)
        self.assertEqual(despues.abierta_recibida_en, antes.abierta_recibida_en)

    def test_abrir_con_abierta_y_abierta_en_de_73_horas_200_sin_tocarla(self):
        self._con_abierta_y_hora(abierta_en=hace(hours=73))

    def test_abrir_con_abierta_y_abierta_en_futura_200_sin_tocarla(self):
        self._con_abierta_y_hora(abierta_en=timezone.now() + timedelta(hours=3))

    def test_qr_invalido_con_abierta_en_invalida_da_error_en_qr_codigo(self):
        with self.assertRaises(ValidationError) as contexto:
            abrir_visita(
                empleado=self.empleado,
                qr_codigo="no-es-un-qr",
                abierta_en=hace(hours=73),
            )
        self.assertEqual(list(contexto.exception.error_dict), ["qr_codigo"])


class HoraRecepcionTests(BaseSinConexion):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def _ficha(self, visita):
        return self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))

    def _cerrar(self, visita, **extra):
        return cerrar_visita(
            visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO, **extra
        )

    def _sin_conexion(self, **cierre):
        visita = self.abrir(abierta_en=hace(hours=2))
        self.revisar(visita, self.general)
        return self._cerrar(visita, **cierre)

    def test_abrir_y_cerrar_guardan_la_hora_de_recepcion(self):
        antes = timezone.now()
        visita = self.abrir(abierta_en=hace(hours=2))
        self.assertGreaterEqual(visita.abierta_recibida_en, antes)
        self.assertLess(visita.abierta_en, visita.abierta_recibida_en)
        self.assertIsNone(visita.cerrada_recibida_en)
        self.revisar(visita, self.general)
        cerrada = self._cerrar(visita, cerrada_en=hace(minutes=30))
        self.assertGreaterEqual(cerrada.cerrada_recibida_en, visita.abierta_recibida_en)
        self.assertLess(cerrada.cerrada_en, cerrada.cerrada_recibida_en)

    def test_ficha_muestra_llegada_de_apertura_y_cierre_sin_conexion(self):
        visita = self._sin_conexion(cerrada_en=hace(minutes=30))
        self.assertContains(self._ficha(visita), SIN_CONEXION, count=2)

    def test_ficha_no_muestra_llegada_de_apertura_si_difiere_10_minutos_o_menos(self):
        visita = self.abrir(abierta_en=hace(minutes=8))
        self.revisar(visita, self.general)
        self._cerrar(visita)
        self.assertNotContains(self._ficha(visita), SIN_CONEXION)

    def test_cierre_por_sistema_y_manual_no_guardan_hora_de_recepcion(self):
        visita = self.abrir()
        self.revisar(visita, self.general)
        cerrada = cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
        self.assertIsNone(cerrada.cerrada_recibida_en)
        Sitio.objects.de_empresa(una_empresa()).filter(pk=self.sitio.pk).update(
            creado=hace(days=30)
        )
        self.sitio.refresh_from_db()
        manual = registrar_visita_manual(
            sitio=self.sitio,
            empleado=self.empleado,
            administrador=self.admin,
            motivo="Carga",
            items=[(self.general, self.roedores)],
            datos={},
            productos_aplicados=[],
            fotos=[],
            realizada_en=hace(hours=3),
        )
        self.assertIsNone(manual.cerrada_recibida_en)
        self.assertEqual(manual.cierre, Visita.Cierre.ADMINISTRADOR)

    def test_cierre_repetido_no_pisa_la_hora_de_recepcion(self):
        cerrada = self._sin_conexion()
        otra = self._cerrar(cerrada)
        self.assertEqual(otra.cerrada_recibida_en, cerrada.cerrada_recibida_en)
        self.assertEqual(
            Visita.objects.de_empresa(una_empresa())
            .get(pk=cerrada.pk)
            .cerrada_recibida_en,
            cerrada.cerrada_recibida_en,
        )

    def test_ficha_no_muestra_llegada_en_apertura_en_linea(self):
        visita = self.abrir()
        self.assertNotContains(self._ficha(visita), SIN_CONEXION)

    def test_ficha_revision_dice_registrado_sin_conexion(self):
        # Apertura en línea: el único "registrado sin conexión" es el de la revisión.
        visita = self.abrir()
        self.revisar(visita, self.general, realizada_en=hace(hours=2))
        respuesta = self._ficha(visita)
        self.assertContains(respuesta, "Llegó ", count=1)
        self.assertContains(respuesta, SIN_CONEXION, count=1)

    def test_ficha_no_muestra_llegada_en_revisiones_manuales(self):
        Sitio.objects.de_empresa(una_empresa()).filter(pk=self.sitio.pk).update(
            creado=hace(days=30)
        )
        self.sitio.refresh_from_db()
        manual = registrar_visita_manual(
            sitio=self.sitio,
            empleado=self.empleado,
            administrador=self.admin,
            motivo="Carga",
            items=[(self.general, self.roedores)],
            datos={},
            productos_aplicados=[],
            fotos=[],
            realizada_en=hace(hours=3),
        )
        self.assertNotContains(self._ficha(manual), "Llegó ")

    def test_ficha_de_pendiente_tras_cierre_sin_revisiones_200(self):
        turno = self.turno([(self.general, self.roedores)])
        visita = self.abrir()
        self.assertEqual(visita.pk, turno.pk)
        cerrada = cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
        self.assertEqual(cerrada.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(cerrada.abierta_en)
        self.assertIsNone(cerrada.abierta_recibida_en)
        self.assertEqual(self._ficha(cerrada).status_code, 200)


class TopeCierreNocturnoTests(TestCase):
    def _ejecutar(self):
        call_command("cerrar_visitas_abiertas", stdout=StringIO())

    def _con_actividad(self, horas):
        visita = abierta_hace(horas)
        crear_revision(visita)
        return visita

    @override_settings(VISITA_ABIERTA_TOPE_HORAS=2)
    def test_tope_se_lee_de_settings(self):
        visita = self._con_actividad(3)
        self._ejecutar()
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.cierre, Visita.Cierre.SISTEMA)

    def test_cierra_visita_de_mas_de_36_horas_con_actividad_reciente(self):
        vieja = self._con_actividad(37)
        reciente = self._con_actividad(30)
        self._ejecutar()
        vieja.refresh_from_db()
        reciente.refresh_from_db()
        self.assertEqual(vieja.estado, Visita.Estado.REALIZADA)
        self.assertEqual(vieja.cierre, Visita.Cierre.SISTEMA)
        self.assertEqual(reciente.estado, Visita.Estado.ABIERTA)


class HoraAnteriorApiTests(BaseSinConexionApi):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta(abierta_en=hace(hours=5))

    def test_cerrada_en_anterior_a_abierta_en_400_en_el_campo(self):
        self._post(self.visita, realizada_en=hace(hours=3).isoformat())
        r = self._cerrar(self.visita, cuerpo={"cerrada_en": hace(hours=6).isoformat()})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("cerrada_en", r.data["campos"])
        self.assertEqual(
            Visita.objects.de_empresa(una_empresa()).get(pk=self.visita.pk).estado,
            Visita.Estado.ABIERTA,
        )

    def test_reportado_en_anterior_a_abierta_en_400_en_el_campo(self):
        r = self._reportar(self.visita, reportado_en=hace(hours=6).isoformat())
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("reportado_en", r.data["campos"])
