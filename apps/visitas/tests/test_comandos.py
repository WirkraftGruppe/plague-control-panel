import os
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.sitios import services as servicios_sitio
from apps.visitas.models import Revision, Visita
from apps.visitas.services import cerrar_visita
from apps.visitas.tests.test_models import crear_revision, crear_visita, punto_de


def abierta_hace(horas, **extra):
    return crear_visita(
        origen=Visita.Origen.APP,
        estado=Visita.Estado.ABIERTA,
        abierta_en=timezone.now() - timedelta(hours=horas),
        **extra,
    )


class CerrarAbiertasTests(TestCase):
    def ejecutar(self):
        salida = StringIO()
        call_command("cerrar_visitas_abiertas", stdout=salida)
        return salida.getvalue()

    def test_cierra_por_sistema_pasado_el_maximo(self):
        vieja = abierta_hace(20)
        crear_revision(vieja, realizada_en=timezone.now() - timedelta(hours=19))
        ultima = crear_revision(
            vieja, realizada_en=timezone.now() - timedelta(hours=18)
        )
        reciente = abierta_hace(2)
        crear_revision(reciente)
        salida = self.ejecutar()
        vieja.refresh_from_db()
        reciente.refresh_from_db()
        self.assertEqual(vieja.estado, Visita.Estado.REALIZADA)
        self.assertEqual(vieja.cierre, Visita.Cierre.SISTEMA)
        # La hora de cierre es la de la última revisión, no la del comando.
        self.assertEqual(vieja.cerrada_en, ultima.realizada_en)
        self.assertEqual(reciente.estado, Visita.Estado.ABIERTA)
        self.assertIn("1", salida)

    @override_settings(VISITA_ABIERTA_MAXIMO_HORAS=1)
    def test_el_maximo_sale_del_setting(self):
        visita = abierta_hace(2)
        crear_revision(visita)
        self.ejecutar()
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_sin_revisiones_vuelve_a_pendiente_o_se_cancela(self):
        asignador = User.objects.create_user(
            username="adm-cmd", password="x", rol=User.Rol.ADMINISTRADOR
        )
        asignada = abierta_hace(20, asignada_por=asignador)
        propia = abierta_hace(20)
        self.ejecutar()
        asignada.refresh_from_db()
        propia.refresh_from_db()
        self.assertEqual(asignada.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(asignada.abierta_en)
        self.assertEqual(propia.estado, Visita.Estado.CANCELADA)
        self.assertIsNone(propia.cerrada_en)
        for visita in (asignada, propia):
            self.assertIsNone(punto_de(visita).proximo_vencimiento)

    def test_operational_error_no_corta_la_corrida(self):
        trabada = abierta_hace(30)
        crear_revision(trabada)
        libre = abierta_hace(20)
        crear_revision(libre)

        def cierra(visita, **opciones):
            if visita.pk == trabada.pk:
                raise OperationalError("bloqueo no disponible")
            return cerrar_visita(visita, **opciones)

        with mock.patch(
            "apps.visitas.management.commands.cerrar_visitas_abiertas.cerrar_visita",
            side_effect=cierra,
        ):
            with self.assertLogs(
                "apps.visitas.management.commands.cerrar_visitas_abiertas", "ERROR"
            ):
                salida = self.ejecutar()
        trabada.refresh_from_db()
        libre.refresh_from_db()
        self.assertEqual(trabada.estado, Visita.Estado.ABIERTA)
        self.assertEqual(libre.estado, Visita.Estado.REALIZADA)
        self.assertIn("1", salida)


@override_settings(DEBUG=True, MEDIA_ROOT=tempfile.mkdtemp(prefix="revision-demo-"))
class RevisionDemoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def preparar(self):
        visita = crear_visita(origen=Visita.Origen.APP, estado=Visita.Estado.CANCELADA)
        punto = visita.sitio.puntos.get(nombre="General")
        servicios_sitio.fijar_ubicacion(punto, Decimal("-36.1"), Decimal("-57.8"))
        return punto, visita.empleado

    def ejecutar(self, *args):
        salida = StringIO()
        call_command("registrar_revision_demo", *args, stdout=salida)
        return salida.getvalue()

    def test_crea_revision_con_foto_y_guardas(self):
        punto, empleado = self.preparar()
        self.ejecutar("General")
        revision = Revision.objects.get()
        self.assertEqual(revision.punto, punto)
        self.assertEqual(revision.visita.empleado, empleado)
        self.assertEqual(revision.visita.estado, Visita.Estado.ABIERTA)
        self.assertEqual(revision.fotos.count(), 1)
        self.assertFalse(revision.incidencia_ubicacion)

        # Segunda corrida: reutiliza la visita abierta.
        self.ejecutar("General")
        self.assertEqual(Visita.objects.filter(estado=Visita.Estado.ABIERTA).count(), 1)
        self.assertEqual(Revision.objects.count(), 2)

        # Guardas: sin DEBUG o fuera de development no toca nada.
        with override_settings(DEBUG=False):
            with self.assertRaisesMessage(CommandError, "DEBUG activo"):
                self.ejecutar("General")
        with mock.patch.dict(os.environ, {"DJANGO_ENV": "production"}):
            with self.assertRaisesMessage(CommandError, "DJANGO_ENV=development"):
                self.ejecutar("General")
        self.assertEqual(Revision.objects.count(), 2)

    def test_lejos_marca_incidencia_de_ubicacion(self):
        self.preparar()
        self.ejecutar("General", "--lejos")
        revision = Revision.objects.get()
        self.assertTrue(revision.incidencia_ubicacion)
        self.assertGreater(revision.distancia_m, 500)

    def test_punto_inexistente(self):
        with self.assertRaises(CommandError):
            self.ejecutar("No existe")
