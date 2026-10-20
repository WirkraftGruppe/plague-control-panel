import datetime
from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError, QuerySet
from django.test import TestCase

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios import services
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Visita


class _BaseSitio(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")


class SuprimirSitioTests(_BaseSitio):
    def test_suprimir_borra_sitio_e_historial(self):
        self.sitio.nombre = "Planta Norte"
        self.sitio.save()
        pk = self.sitio.pk
        self.assertEqual(Sitio.history.filter(id=pk).count(), 2)
        services.suprimir_sitio(self.sitio)
        self.assertFalse(Sitio.objects.filter(pk=pk).exists())
        self.assertEqual(Sitio.history.filter(id=pk).count(), 0)

    def _visita(self, sitio):
        empleado = User.objects.create_user(
            username=f"emp-{sitio.pk}", password="x", rol=User.Rol.EMPLEADO
        )
        return Visita.objects.create(
            sitio=sitio, empleado=empleado, origen=Visita.Origen.APP
        )

    def test_suprimir_con_visitas_no_borra_nada(self):
        self._visita(self.sitio)
        pk = self.sitio.pk
        with self.assertRaises(ProtectedError):
            services.suprimir_sitio(self.sitio)
        self.assertTrue(Sitio.objects.filter(pk=pk).exists())
        self.assertEqual(Sitio.history.filter(id=pk).count(), 1)

    def test_suprimir_sitios_informa_los_que_tienen_visitas(self):
        con_visita = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        self._visita(con_visita)
        pk_libre = self.sitio.pk
        resultado = services.suprimir_sitios([self.sitio, con_visita])
        self.assertEqual(resultado, (1, [con_visita]))
        self.assertFalse(Sitio.objects.filter(pk=pk_libre).exists())
        self.assertEqual(Sitio.history.filter(id=pk_libre).count(), 0)
        self.assertTrue(Sitio.objects.filter(pk=con_visita.pk).exists())

    def test_suprimir_borra_puntos_y_su_historial(self):
        pk = self.sitio.pk
        self.assertEqual(PuntoControl.history.filter(sitio_id=pk).count(), 1)
        services.suprimir_sitio(self.sitio)
        self.assertFalse(PuntoControl.objects.filter(sitio_id=pk).exists())
        self.assertEqual(PuntoControl.history.filter(sitio_id=pk).count(), 0)


class RegenerarQrPuntoTests(_BaseSitio):
    def setUp(self):
        super().setUp()
        self.general = self.sitio.puntos.get()

    def test_regenerar_qr_cambia_codigo_y_borra_fecha_de_impresion(self):
        self.general.qr_impreso_el = datetime.date(2026, 1, 1)
        self.general.save()
        anterior = self.general.qr_codigo
        historial = PuntoControl.history.filter(id=self.general.pk).count()
        nuevo = services.regenerar_qr(self.general)
        self.general.refresh_from_db()
        self.assertNotEqual(nuevo, anterior)
        self.assertEqual(self.general.qr_codigo, nuevo)
        self.assertIsNone(self.general.qr_impreso_el)
        self.assertEqual(
            PuntoControl.history.filter(id=self.general.pk).count(), historial + 1
        )

    def test_regenerar_qr_guarda_motivo_en_historial(self):
        services.regenerar_qr(self.general)
        self.assertEqual(
            self.general.history.first().history_change_reason, "Regeneración de QR"
        )

    def test_regenerar_el_general_no_toca_el_sitio(self):
        actualizado = self.sitio.actualizado
        historial = self.sitio.history.count()
        services.regenerar_qr(self.general)
        self.sitio.refresh_from_db()
        self.assertEqual(self.sitio.actualizado, actualizado)
        self.assertEqual(self.sitio.history.count(), historial)

    def test_regenera_solo_el_punto_y_respeta_tope(self):
        otro = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        codigo_general = self.general.qr_codigo
        nuevo = services.regenerar_qr(otro)
        self.general.refresh_from_db()
        otro.refresh_from_db()
        self.assertEqual(otro.qr_codigo, nuevo)
        self.assertNotEqual(nuevo, codigo_general)
        self.assertEqual(self.general.qr_codigo, codigo_general)
        puntos = [
            PuntoControl.objects.create(sitio=self.sitio, nombre=f"P{i}", orden=i + 2)
            for i in range(services.TOPE_REGENERAR_QR + 1)
        ]
        codigos = [p.qr_codigo for p in puntos]
        with self.assertRaises(ValidationError):
            services.regenerar_qr_lote(puntos)
        for punto, codigo in zip(puntos, codigos):
            punto.refresh_from_db()
            self.assertEqual(punto.qr_codigo, codigo)
        self.assertEqual(services.regenerar_qr_lote(puntos[:3]), 3)


class UbicarEnPlanoTests(_BaseSitio):
    def test_ubica_valida_sitio_y_rango(self):
        punto = self.sitio.puntos.get()
        plano = Plano.objects.create(sitio=self.sitio, nombre="PB", imagen="p.png")
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Otra")
        ajeno = Plano.objects.create(sitio=otro, nombre="Aj", imagen="a.png")
        services.ubicar_en_plano(punto, plano, Decimal("0.2"), Decimal("0.8"))
        punto.refresh_from_db()
        self.assertEqual(
            (punto.plano, punto.x, punto.y), (plano, Decimal("0.2"), Decimal("0.8"))
        )
        for destino, x, y in ((ajeno, 0.5, 0.5), (plano, 1.5, 0.5), (plano, 0.5, -1)):
            with self.assertRaises(ValidationError):
                services.ubicar_en_plano(punto, destino, x, y)


class FijarUbicacionTests(_BaseSitio):
    def test_fijar_ubicacion_bloquea_la_fila(self):
        punto = self.sitio.puntos.get()
        administrador = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        original = QuerySet.select_for_update
        with mock.patch.object(
            QuerySet, "select_for_update", autospec=True, side_effect=original
        ) as bloqueo:
            # Regla nueva: FOR NO KEY UPDATE, para no chocar con los inserts
            # que referencian el punto.
            services.fijar_ubicacion(punto, Decimal("-36.1"), Decimal("-57.8"))
            self.assertEqual(bloqueo.call_count, 1)
            services.fijar_ubicacion_en_campo(
                administrador=administrador,
                punto=punto,
                latitud=Decimal("-36.2"),
                longitud=Decimal("-57.9"),
                precision_m=9.5,
            )
            self.assertEqual(bloqueo.call_count, 2)
            for llamada in bloqueo.call_args_list:
                self.assertTrue(llamada.kwargs["no_key"])
        punto.refresh_from_db()
        self.assertEqual(punto.latitud, Decimal("-36.2"))
        self.assertEqual(punto.precision_m, Decimal("9.50"))

    def test_corregir_ubicacion_limpia_fijada_por_escaneo(self):
        administrador = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        for corregir in (
            lambda p: services.fijar_ubicacion(p, Decimal("-36.1"), Decimal("-57.8")),
            lambda p: services.fijar_ubicacion_en_campo(
                administrador=administrador,
                punto=p,
                latitud=Decimal("-36.2"),
                longitud=Decimal("-57.9"),
                precision_m=9.5,
            ),
        ):
            punto = self.sitio.puntos.get()
            PuntoControl.objects.filter(pk=punto.pk).update(
                ubicacion_fijada_por=administrador,
                ubicacion_fijada_en=datetime.datetime(2026, 3, 1, tzinfo=datetime.UTC),
            )
            corregir(punto)
            punto.refresh_from_db()
            self.assertIsNone(punto.ubicacion_fijada_por)
            self.assertIsNone(punto.ubicacion_fijada_en)

    def test_fijar_ubicacion_usa_la_fila_releida(self):
        """El punto en memoria quedó viejo: manda lo que hay en la base."""
        punto = self.sitio.puntos.get()
        PuntoControl.objects.filter(pk=punto.pk).update(activo=False)
        administrador = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        with self.assertRaises(ValidationError):
            services.fijar_ubicacion_en_campo(
                administrador=administrador,
                punto=punto,
                latitud=Decimal("-36.2"),
                longitud=Decimal("-57.9"),
                precision_m=9,
            )
