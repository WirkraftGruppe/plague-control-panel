"""Días de aviso por frecuencia en el estado del punto, del sitio y de la API."""

import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.sitios.estado import (
    EstadoSitio,
    EstadoVencimiento,
    condicion_de_estado,
    dias_aviso,
    estado_de_sitio_por_puntos,
    estado_por_vencimiento,
    resumen_de_sitios,
)
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import Visita

HOY = datetime.date(2026, 10, 20)


def _en(dias, base=HOY):
    return base + datetime.timedelta(days=dias)


def _estado(dias, frecuencia):
    return estado_por_vencimiento(_en(dias), HOY, frecuencia)


class DiasAvisoTests(TestCase):
    def test_dias_aviso_por_frecuencia(self):
        esperado = {
            None: 7,
            0: 7,
            1: 0,
            2: 1,
            4: 1,
            5: 2,
            7: 2,
            8: 2,
            9: 3,
            14: 4,
            24: 6,
            25: 7,
            30: 7,
            90: 7,
            365: 7,
        }
        for frecuencia, dias in esperado.items():
            with self.subTest(frecuencia=frecuencia):
                self.assertEqual(dias_aviso(frecuencia), dias)


class EstadoPuntoTests(TestCase):
    def test_frecuencia_7_revisado_hoy_queda_al_dia(self):
        # Revisado hoy: vence en 7 días y el aviso es de 2.
        self.assertEqual(_estado(7, 7), EstadoVencimiento.AL_DIA)

    def test_frecuencia_7_a_dos_dias_queda_proxima(self):
        self.assertEqual(_estado(2, 7), EstadoVencimiento.PROXIMA)
        self.assertEqual(_estado(3, 7), EstadoVencimiento.AL_DIA)
        self.assertEqual(_estado(-1, 7), EstadoVencimiento.VENCIDA)

    def test_frecuencia_14_proxima_a_4_dias_o_menos(self):
        self.assertEqual(_estado(4, 14), EstadoVencimiento.PROXIMA)
        self.assertEqual(_estado(5, 14), EstadoVencimiento.AL_DIA)

    def test_frecuencia_30_y_90_proxima_a_7_dias_o_menos(self):
        for frecuencia in (30, 90):
            with self.subTest(frecuencia=frecuencia):
                self.assertEqual(_estado(7, frecuencia), EstadoVencimiento.PROXIMA)
                self.assertEqual(_estado(8, frecuencia), EstadoVencimiento.AL_DIA)

    def test_sin_frecuencia_proxima_a_7_dias_o_menos(self):
        for frecuencia in (None, 0):
            with self.subTest(frecuencia=frecuencia):
                self.assertEqual(_estado(7, frecuencia), EstadoVencimiento.PROXIMA)
                self.assertEqual(_estado(8, frecuencia), EstadoVencimiento.AL_DIA)

    def test_frecuencia_1_proxima_solo_el_dia_que_vence(self):
        self.assertEqual(_estado(0, 1), EstadoVencimiento.PROXIMA)
        self.assertEqual(_estado(1, 1), EstadoVencimiento.AL_DIA)
        self.assertEqual(_estado(-1, 1), EstadoVencimiento.VENCIDA)


class _ConSitios:
    def setUp(self):
        self.empresa = una_empresa()
        self.cliente = Cliente.objects.create(razon_social="ACME", empresa=self.empresa)

    def sitio(self, nombre, *puntos):
        """Sitio con un punto por ``(dias, frecuencia)``; el General se descarta."""
        sitio = Sitio.objects.create(cliente=self.cliente, nombre=nombre)
        sitio.puntos.update(activo=False)
        for i, (dias, frecuencia, *resto) in enumerate(puntos, start=1):
            PuntoControl.objects.create(
                sitio=sitio,
                nombre=f"P{i}",
                orden=i,
                proximo_vencimiento=None if dias is None else _en(dias),
                frecuencia_dias=frecuencia,
                activo=not resto,
            )
        return sitio


class EstadoSitioTests(_ConSitios, TestCase):
    def test_condicion_sql_coincide_con_estado_en_python(self):
        casos = [
            [],
            [(None, None)],
            [(-1, 7)],
            [(2, 7)],
            [(3, 7), (40, 90)],
            [(30, 30)],
            [(3, 7), (-1, None)],
            [(None, 7), (30, 90)],
            [(1, 1), (0, 1)],
            [(5, 14), (5, 14, "inactivo"), (-9, 7, "inactivo")],
            [(7, 30), (8, 30)],
        ]
        sitios = [self.sitio(f"S{i}", *c) for i, c in enumerate(casos)]
        for sitio in sitios:
            esperado = estado_de_sitio_por_puntos(sitio.puntos.filter(activo=True), HOY)
            for estado in EstadoSitio:
                with self.subTest(sitio=sitio.nombre, estado=estado):
                    en_sql = Sitio.objects.de_empresa(self.empresa).filter(
                        condicion_de_estado(estado, HOY), pk=sitio.pk
                    )
                    self.assertEqual(en_sql.exists(), estado == esperado)

    def test_sitio_proximo_por_un_punto_que_no_es_el_mas_cercano(self):
        # El punto de frecuencia 90 vence antes pero no está en aviso (aviso 7);
        # el de frecuencia 7 vence después y sí lo está.
        sitio = self.sitio("Mixto", (9, 90), (2, 7))
        puntos = sitio.puntos.filter(activo=True)
        self.assertEqual(estado_de_sitio_por_puntos(puntos, HOY), EstadoSitio.SEMANA)
        otro = self.sitio("Lejano", (4, 7), (40, 90))
        self.assertEqual(
            estado_de_sitio_por_puntos(otro.puntos.filter(activo=True), HOY),
            EstadoSitio.AL_DIA,
        )

    def test_mapa_usa_los_dias_de_aviso(self):
        revisado = self.sitio("Revisado", (7, 7))
        aviso = self.sitio("Aviso", (2, 7))
        resumen = resumen_de_sitios([revisado, aviso], HOY, self.empresa)
        self.assertEqual(resumen[revisado.pk].estado, EstadoVencimiento.AL_DIA)
        self.assertEqual(resumen[aviso.pk].estado, EstadoVencimiento.PROXIMA)
        with self.assertNumQueries(1):
            resumen_de_sitios([revisado, aviso], HOY, self.empresa)


class ApiSitiosTests(_ConSitios, TestCase):
    def test_resolver_y_me_puntos_usan_los_dias_de_aviso(self):
        hoy = timezone.localdate()
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="API")
        punto = sitio.puntos.get()
        punto.frecuencia_dias = 14
        punto.proximo_vencimiento = hoy + datetime.timedelta(days=5)
        punto.save()
        empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO, empresa=self.empresa
        )
        Visita.objects.create(
            sitio=sitio,
            empleado=empleado,
            origen=Visita.Origen.MANUAL,
            programada_para=hoy,
        )
        api = APIClient()
        api.force_authenticate(empleado)

        def estados():
            resuelto = api.post(f"/api/v1/qr/{punto.qr_codigo}/resolver/")
            mios = api.get("/api/v1/me/puntos/")
            return resuelto.json()["punto"]["estado"], mios.json()[0]["estado"]

        # Frecuencia 14: aviso de 4 días, así que a 5 sigue al día.
        self.assertEqual(estados(), ("al_dia", "al_dia"))
        punto.proximo_vencimiento = hoy + datetime.timedelta(days=4)
        punto.save()
        self.assertEqual(estados(), ("proxima", "proxima"))
