from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.visitas.models import Visita
from apps.visitas.services import MOTIVO_UBICACION_FIJADA, registrar_revision
from apps.visitas.tests.test_models import crear_visita, punto_de
from apps.visitas.tests.test_services import (
    MEDIA_TEMPORAL,
    SinArchivosMixin,
    abrir,
    jpeg_chico,
)
from apps.visitas.ubicacion import distancia_m, verificar

# Sobre el mismo paralelo, 0,01 grados de longitud son unos 910 m y 0,001, unos 91 m.
PUNTO = {"latitud": Decimal("-35.000000"), "longitud": Decimal("-57.000000")}
LEJOS = {"latitud": Decimal("-35.000000"), "longitud": Decimal("-57.010000")}
CERCA = {"latitud": Decimal("-35.000000"), "longitud": Decimal("-57.001000")}


class DistanciaTests(SimpleTestCase):
    def test_haversine_con_radio_de_6371_km(self):
        self.assertEqual(distancia_m(0, 0, 1, 0), 111195)
        self.assertEqual(distancia_m(-35, -57, -35, -57), 0)
        self.assertEqual(distancia_m(10, 20, 11, 20), distancia_m(11, 20, 10, 20))


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class UbicacionTests(SinArchivosMixin, TestCase):
    def setUp(self):
        self.visita = crear_visita()
        self.empleado = self.visita.empleado
        self.sitio = self.visita.sitio
        self.punto = punto_de(self.visita)
        self.admin = User.objects.create_user(
            username="adm-ubic", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def _con_coordenadas(self, objeto, coordenadas=PUNTO):
        objeto.latitud, objeto.longitud = coordenadas.values()
        objeto.save()

    def _revisar(self, usuario=None, **extra):
        usuario = usuario or self.empleado
        visita, _ = abrir(empleado=usuario, sitio=self.sitio)
        argumentos = {
            "visita": visita,
            "empleado": usuario,
            "qr_codigo": self.punto.qr_codigo,
            "cliente_uuid": uuid4(),
            "realizada_en": timezone.now() - timedelta(minutes=5),
            "latitud": Decimal("-35.1"),
            "longitud": Decimal("-57.7"),
            "precision_m": Decimal("8.5"),
            "datos": {},
            "productos_aplicados": [],
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_revision(**argumentos)

    def test_lejos_del_punto_marca_incidencia_sin_rechazar(self):
        self._con_coordenadas(self.punto)
        lejos = self._revisar(**LEJOS)
        self.assertTrue(lejos.incidencia_ubicacion)
        self.assertGreater(lejos.distancia_m, 300)
        self.assertLess(lejos.distancia_m, 1000)
        cerca = self._revisar(**CERCA)
        self.assertFalse(cerca.incidencia_ubicacion)
        self.assertLess(cerca.distancia_m, 300)
        lejos.refresh_from_db()
        self.assertEqual(lejos.visita.revisiones.count(), 2)

    @override_settings(DISTANCIA_MAXIMA_M=50)
    def test_el_umbral_sale_de_la_configuracion(self):
        self._con_coordenadas(self.punto)
        self.assertTrue(self._revisar(**CERCA).incidencia_ubicacion)

    def test_sin_coordenadas_queda_sin_verificar(self):
        revision = self._revisar(**LEJOS)
        self.assertIsNone(revision.distancia_m)
        self.assertFalse(revision.incidencia_ubicacion)
        self.assertEqual(verificar(self.punto, None, None), (None, False))

    def test_usa_el_sitio_si_el_punto_no_tiene_coordenadas(self):
        self._con_coordenadas(self.sitio)
        revision = self._revisar(**LEJOS)
        self.assertGreater(revision.distancia_m, 300)
        self.assertTrue(revision.incidencia_ubicacion)

    def test_apertura_guarda_distancia(self):
        self._con_coordenadas(self.punto)
        visita, _ = abrir(empleado=self.empleado, sitio=self.sitio, **LEJOS)
        visita.refresh_from_db()
        self.assertEqual(visita.pk, self.visita.pk)
        self.assertTrue(visita.incidencia_ubicacion)
        self.assertGreater(visita.distancia_m, 300)
        otro, _ = abrir(empleado=self.admin, sitio=self.sitio, **CERCA)
        self.assertFalse(otro.incidencia_ubicacion)
        self.assertLess(otro.distancia_m, 300)
        nuevo = User.objects.create_user(
            username="e2", password="x", rol=User.Rol.EMPLEADO
        )
        sin, _ = abrir(empleado=nuevo, sitio=self.sitio)
        self.assertIsNone(sin.distancia_m)

    def test_administrador_fija_coordenadas_del_punto(self):
        imprecisa = self._revisar(self.admin, precision_m=Decimal("80"))
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.latitud)
        self.assertEqual(imprecisa.orden, 1)
        revision = self._revisar(self.admin, precision_m=Decimal("12.5"))
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.latitud, Decimal("-35.100000"))
        self.assertEqual(self.punto.longitud, Decimal("-57.700000"))
        ultimo = self.punto.history.first()
        self.assertEqual(ultimo.history_user, self.admin)
        self.assertEqual(ultimo.history_change_reason, MOTIVO_UBICACION_FIJADA)
        # Con coordenadas ya fijadas, otro escaneo no las mueve.
        self._revisar(self.admin, latitud=Decimal("-36"), longitud=Decimal("-58"))
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.latitud, Decimal("-35.100000"))
        self.assertEqual(revision.visita.empleado, self.admin)

    def test_revision_lejos_del_sitio_no_fija_coordenadas(self):
        self._con_coordenadas(self.sitio)
        revision = self._revisar(**LEJOS)
        self.assertTrue(revision.incidencia_ubicacion)
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.latitud)
        self.assertIsNone(self.punto.longitud)

    def test_sitio_sin_coordenadas_el_escaneo_fija(self):
        self.assertIsNone(self.sitio.latitud)
        revision = self._revisar(precision_m=Decimal("8.5"), **LEJOS)
        self.assertFalse(revision.incidencia_ubicacion)
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.latitud, LEJOS["latitud"])
        self.assertEqual(self.punto.longitud, LEJOS["longitud"])

    def test_escaneo_registra_quien_y_cuando_fijo(self):
        antes = timezone.now()
        self._revisar(precision_m=Decimal("8.5"))
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.ubicacion_fijada_por, self.empleado)
        self.assertGreaterEqual(self.punto.ubicacion_fijada_en, antes)
        self.assertLessEqual(self.punto.ubicacion_fijada_en, timezone.now())

    def test_empleado_fija_coordenadas_del_punto(self):
        revision = self._revisar(precision_m=Decimal("8.5"))
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.latitud, Decimal("-35.100000"))
        self.assertEqual(self.punto.longitud, Decimal("-57.700000"))
        self.assertEqual(self.punto.history.first().history_user, self.empleado)
        self.assertEqual(
            Visita.objects.get(pk=revision.visita_id).empleado, self.empleado
        )
