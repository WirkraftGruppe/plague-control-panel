"""Incidencias de coordinación: horas, sin ubicación, duplicada y apertura sin QR."""

from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.productos.models import MovimientoStock
from apps.sitios.models import Sitio
from apps.visitas.models import Revision, Visita
from apps.visitas.services import (
    AperturaNoPermitida,
    abrir_turno_sin_escaneo,
    abrir_visita,
    cerrar_visita,
    condicion_incidencia_sin_revisar,
    marcar_incidencia_revisada,
)
from apps.visitas.tests.ayudas_empresa import dos_empresas
from apps.visitas.tests.test_sin_conexion import BaseSinConexionApi, hace
from apps.visitas.tests.test_turnos import BaseTurnoTests


class HorasInconsistentesTests(BaseSinConexionApi):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta(abierta_en=hace(hours=5))

    def _recargada(self):
        return Visita.objects.de_empresa(una_empresa()).get(pk=self.visita.pk)

    def test_reporte_un_minuto_antes_de_abierta_201_con_incidencia(self):
        hora = self.visita.abierta_en - timedelta(minutes=1)
        r = self._reportar(self.visita, reportado_en=hora.isoformat())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(self._recargada().incidencia_horas)

    def test_cierre_un_minuto_antes_de_abierta_200_con_incidencia(self):
        self._post(self.visita, realizada_en=hace(hours=3).isoformat())
        hora = self.visita.abierta_en - timedelta(minutes=1)
        r = self._cerrar(self.visita, cuerpo={"cerrada_en": hora.isoformat()})
        self.assertEqual(r.status_code, 200, r.content)
        visita = self._recargada()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.cerrada_en, hora)
        self.assertTrue(visita.incidencia_horas)

    def test_no_cambia_proximo_vencimiento_ni_stock(self):
        self.punto.frecuencia_dias = 30
        self.punto.save()
        self._post(self.visita, realizada_en=hace(hours=3).isoformat())
        self.punto.refresh_from_db()
        vencimiento = self.punto.proximo_vencimiento
        self.assertIsNotNone(vencimiento)
        hora = self.visita.abierta_en - timedelta(minutes=1)
        self._reportar(self.visita, reportado_en=hora.isoformat())
        self._cerrar(self.visita, cuerpo={"cerrada_en": hora.isoformat()})
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.proximo_vencimiento, vencimiento)
        movimientos = MovimientoStock.objects.de_empresa(una_empresa())
        self.assertFalse(movimientos.exists())


class SinUbicacionTests(BaseTurnoTests):
    def test_servicio_guarda_revision_sin_coordenadas_con_incidencia(self):
        visita, _ = abrir_visita(
            empleado=self.empleado, qr_codigo=self.general.qr_codigo
        )
        revision = self.revisar(visita, self.general, latitud=None, longitud=None)
        revision.refresh_from_db()
        self.assertTrue(revision.incidencia_sin_ubicacion)
        self.assertIsNone(revision.latitud)
        self.assertIsNone(revision.distancia_m)
        self.assertFalse(revision.incidencia_ubicacion)

    def test_sin_coordenadas_no_fija_ubicacion_del_sitio(self):
        visita, _ = abrir_visita(
            empleado=self.empleado, qr_codigo=self.general.qr_codigo
        )
        self.revisar(visita, self.general, latitud=None, longitud=None)
        self.general.refresh_from_db()
        self.assertIsNone(self.general.latitud)
        # Con coordenadas, el mismo escaneo sí fija la ubicación.
        self.revisar(visita, self.general)
        self.general.refresh_from_db()
        self.assertIsNotNone(self.general.latitud)


class BaseConOtroEmpleado(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.otro = User.objects.create_user(
            "otro", password="x", rol=User.Rol.EMPLEADO, empresa=una_empresa()
        )

    def abrir(self, empleado, punto=None):
        return abrir_visita(
            empleado=empleado, qr_codigo=(punto or self.general).qr_codigo
        )[0]

    def directa(self, empleado, estado=Visita.Estado.REALIZADA, **extra):
        datos = {
            "sitio": self.sitio,
            "empleado": empleado,
            "origen": Visita.Origen.APP,
            "estado": estado,
        }
        if estado == Visita.Estado.REALIZADA:
            datos["abierta_en"] = hace(hours=3)
            datos["cerrada_en"] = hace(hours=1)
        datos.update(extra)
        return Visita.objects.create(**datos)


class DuplicadaTests(BaseConOtroEmpleado):
    def test_segunda_del_dia_por_otro_marca_incidencia(self):
        primera = self.revisar(self.abrir(self.otro), self.general, empleado=self.otro)
        segunda = self.revisar(self.abrir(self.empleado), self.general)
        self.assertFalse(
            Revision.objects.de_empresa(una_empresa())
            .get(pk=primera.pk)
            .incidencia_duplicada
        )
        self.assertTrue(
            Revision.objects.de_empresa(una_empresa())
            .get(pk=segunda.pk)
            .incidencia_duplicada
        )

    def test_misma_persona_dos_veces_no_marca(self):
        visita = self.abrir(self.empleado)
        self.revisar(visita, self.general)
        segunda = self.revisar(visita, self.general)
        self.assertFalse(segunda.incidencia_duplicada)

    def test_visita_de_administrador_no_marca(self):
        self.revisar(self.abrir(self.otro), self.general, empleado=self.otro)
        revision = self.revisar(
            self.abrir(self.admin), self.general, empleado=self.admin
        )
        self.assertFalse(revision.incidencia_duplicada)

    def test_revision_de_ayer_no_marca(self):
        self.revisar(
            self.abrir(self.otro),
            self.general,
            empleado=self.otro,
            realizada_en=hace(hours=25),
        )
        revision = self.revisar(self.abrir(self.empleado), self.general)
        self.assertFalse(revision.incidencia_duplicada)

    def test_sin_conexion_compara_con_el_dia_de_realizada_en(self):
        ayer = timezone.localdate() - timedelta(days=1)
        mediodia = timezone.make_aware(datetime.combine(ayer, time(12)))
        self.revisar(
            self.abrir(self.otro),
            self.general,
            empleado=self.otro,
            realizada_en=mediodia,
        )
        # Hoy no hay otras revisiones, pero la hora declarada cae en el día de ayer.
        revision = self.revisar(
            self.abrir(self.empleado),
            self.general,
            realizada_en=mediodia + timedelta(hours=1),
        )
        self.assertTrue(revision.incidencia_duplicada)


class AperturaSinEscaneoTests(BaseConOtroEmpleado):
    def hoy(self, **extra):
        return self.turno(
            [(self.general, self.roedores)],
            programada_para=timezone.localdate(),
            **extra,
        )

    def test_abre_pendiente_propio_con_incidencia(self):
        pendiente = self.hoy()
        abierta_en = hace(minutes=30)
        visita = abrir_turno_sin_escaneo(
            pendiente.pk, self.empleado, abierta_en=abierta_en
        )
        visita.refresh_from_db()
        self.assertEqual(visita.pk, pendiente.pk)
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        self.assertEqual(visita.abierta_en, abierta_en)
        self.assertIsNotNone(visita.abierta_recibida_en)
        self.assertTrue(visita.incidencia_apertura_sin_escaneo)
        self.assertIsNone(visita.distancia_m)

    def test_con_otra_abierta_en_el_sitio_devuelve_esa(self):
        pendiente = self.hoy()
        abierta = self.directa(
            self.empleado, Visita.Estado.ABIERTA, abierta_en=hace(hours=1)
        )
        devuelta = abrir_turno_sin_escaneo(pendiente.pk, self.empleado)
        self.assertEqual(devuelta.pk, abierta.pk)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)
        self.assertFalse(pendiente.incidencia_apertura_sin_escaneo)

    def test_rechaza_programada_futura_y_sitio_inactivo(self):
        futura = self.turno([(self.general, self.roedores)])
        with self.assertRaises(AperturaNoPermitida):
            abrir_turno_sin_escaneo(futura.pk, self.empleado)
        hoy = self.hoy()
        Sitio.objects.de_empresa(una_empresa()).filter(pk=self.sitio.pk).update(
            activo=False
        )
        with self.assertRaises(AperturaNoPermitida):
            abrir_turno_sin_escaneo(hoy.pk, self.empleado)
        hoy.refresh_from_db()
        self.assertEqual(hoy.estado, Visita.Estado.PENDIENTE)
        self.assertFalse(hoy.incidencia_apertura_sin_escaneo)

    def test_ajena_o_de_otra_empresa_no_existe(self):
        pendiente = self.hoy()
        with self.assertRaises(Visita.DoesNotExist):
            abrir_turno_sin_escaneo(pendiente.pk, self.otro)
        _, b = dos_empresas()
        with self.assertRaises(Visita.DoesNotExist):
            abrir_turno_sin_escaneo(pendiente.pk, b.empleado)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)

    def test_vuelta_a_pendiente_baja_la_incidencia(self):
        pendiente = self.hoy()
        abrir_turno_sin_escaneo(pendiente.pk, self.empleado)
        cerrada = cerrar_visita(pendiente, quien=None, cierre=Visita.Cierre.SISTEMA)
        self.assertEqual(cerrada.estado, Visita.Estado.PENDIENTE)
        pendiente.refresh_from_db()
        self.assertFalse(pendiente.incidencia_apertura_sin_escaneo)


class ConteoIncidenciasTests(BaseConOtroEmpleado):
    def sin_revisar(self):
        return (
            Visita.objects.de_empresa(una_empresa())
            .filter(condicion_incidencia_sin_revisar())
            .count()
        )

    def revision_marcada(self, visita, **marca):
        ahora = timezone.now()
        return Revision.objects.create(
            visita=visita,
            punto=self.general,
            servicio=self.roedores,
            orden=1,
            realizada_en=ahora,
            recibida_en=ahora,
            **marca,
        )

    def test_cuatro_incidencias_cuentan_y_marcar_revisada_las_saca(self):
        visitas = [
            self.directa(self.empleado, incidencia_horas=True),
            self.directa(self.empleado, incidencia_apertura_sin_escaneo=True),
            self.directa(self.empleado),
            self.directa(self.empleado),
        ]
        self.revision_marcada(visitas[2], incidencia_duplicada=True)
        self.revision_marcada(visitas[3], incidencia_sin_ubicacion=True)
        # Con la visita abierta no cuentan, aunque tenga la marca.
        self.directa(
            self.otro,
            Visita.Estado.ABIERTA,
            abierta_en=hace(hours=1),
            incidencia_horas=True,
        )
        self.directa(self.otro)
        self.assertEqual(self.sin_revisar(), 4)
        for numero, visita in enumerate(visitas, start=1):
            marcar_incidencia_revisada(visita, self.admin)
            self.assertEqual(self.sin_revisar(), 4 - numero)
        limpia = (
            Visita.objects.de_empresa(una_empresa())
            .filter(
                incidencia_horas=False,
                incidencia_apertura_sin_escaneo=False,
                incidencia_revisada_en__isnull=True,
                estado=Visita.Estado.REALIZADA,
            )
            .first()
        )
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(limpia, self.admin)
