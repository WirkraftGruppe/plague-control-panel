import datetime

from django.test import TestCase

from apps.clientes.models import Cliente
from apps.sitios.estado import (
    EstadoVencimiento,
    estado_por_vencimiento,
    estados_por_vencimiento,
    resumen_de_sitios,
)
from apps.sitios.models import PuntoControl, Sitio

HOY = datetime.date(2026, 10, 20)


def _en(dias):
    return HOY + datetime.timedelta(days=dias)


class EstadoVencimientoTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")

    def _sitio(self, nombre, *vencimientos):
        """Sitio cuyo punto General queda sin programar y suma un punto por fecha."""
        sitio = Sitio.objects.create(cliente=self.cliente, nombre=nombre)
        for i, fecha in enumerate(vencimientos, start=1):
            PuntoControl.objects.create(
                sitio=sitio, nombre=f"P{i}", orden=i, proximo_vencimiento=fecha
            )
        return sitio

    def test_vencido_ayer_es_vencida(self):
        self.assertEqual(
            estado_por_vencimiento(_en(-1), HOY), EstadoVencimiento.VENCIDA
        )

    def test_en_7_dias_es_proxima(self):
        self.assertEqual(estado_por_vencimiento(_en(7), HOY), EstadoVencimiento.PROXIMA)
        self.assertEqual(estado_por_vencimiento(HOY, HOY), EstadoVencimiento.PROXIMA)

    def test_en_8_dias_es_al_dia(self):
        self.assertEqual(estado_por_vencimiento(_en(8), HOY), EstadoVencimiento.AL_DIA)

    def test_sin_fecha_es_sin_programar(self):
        self.assertEqual(
            estado_por_vencimiento(None, HOY), EstadoVencimiento.SIN_PROGRAMAR
        )
        punto = PuntoControl(pk=1)
        self.assertEqual(
            estados_por_vencimiento([punto], HOY),
            {1: EstadoVencimiento.SIN_PROGRAMAR},
        )

    def test_sitio_toma_el_peor_estado_y_el_vencimiento_mas_cercano(self):
        sitio = self._sitio("Planta", _en(30), _en(3), _en(-2))
        inactivo = PuntoControl.objects.create(
            sitio=sitio, nombre="Baja", orden=9, proximo_vencimiento=_en(-100)
        )
        PuntoControl.objects.filter(pk=inactivo.pk).update(activo=False)
        resumen = resumen_de_sitios([sitio], HOY)[sitio.pk]
        self.assertEqual(resumen.estado, EstadoVencimiento.VENCIDA)
        self.assertEqual(resumen.vencimiento, _en(-2))
        # Sin programar (General) pesa más que al día, pero menos que próxima.
        otro = self._sitio("Otro", _en(30))
        self.assertEqual(
            resumen_de_sitios([otro], HOY)[otro.pk].estado,
            EstadoVencimiento.SIN_PROGRAMAR,
        )

    def test_consultas_fijas_con_uno_o_cinco_sitios(self):
        sitios = [self._sitio(f"S{i}", _en(i), None) for i in range(5)]
        with self.assertNumQueries(1):
            resumen_de_sitios(sitios[:1], HOY)
        with self.assertNumQueries(1):
            resumen_de_sitios(sitios, HOY)
