import datetime

from django.test import TestCase
from django.urls import reverse

from .ayudas_empresa import DatosDeDosEmpresas


class AltaMultiplePuntosTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        self.crear_empresas()
        self.client.force_login(self.admin_a)
        self.url = reverse("panel:sitios:puntos_alta_multiple", args=[self.sitio_a.pk])

    def _datos(self, **extra):
        datos = {"cantidad": "12", "prefijo": "Cebadero", "numero_inicial": "5"}
        datos.update(extra)
        return datos

    def test_doce_puntos_desde_cinco_con_servicio_y_frecuencia(self):
        respuesta = self.client.post(
            self.url,
            self._datos(
                servicio=self.servicio_a.pk,
                frecuencia_dias="30",
                proximo_vencimiento="2026-12-01",
                sector="Cocina",
            ),
        )
        self.assertEqual(respuesta.status_code, 302)
        nuevos = self.sitio_a.puntos.filter(nombre__startswith="Cebadero")
        self.assertEqual(
            sorted(p.nombre for p in nuevos),
            sorted(f"Cebadero {n}" for n in range(5, 17)),
        )
        for punto in nuevos:
            self.assertEqual(punto.servicio, self.servicio_a)
            self.assertEqual(punto.frecuencia_dias, 30)
            self.assertEqual(punto.proximo_vencimiento, datetime.date(2026, 12, 1))
            self.assertEqual(punto.sector, "Cocina")
        self.assertEqual(len({p.qr_codigo for p in nuevos}), 12)

    def test_ciento_uno_da_error_de_formulario(self):
        respuesta = self.client.post(self.url, self._datos(cantidad="101"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("cantidad", respuesta.context["form"].errors)
        self.assertEqual(self.sitio_a.puntos.count(), 1)

    def test_nombre_de_mas_de_cien_da_error_de_formulario(self):
        respuesta = self.client.post(
            self.url,
            self._datos(prefijo="x" * 90, cantidad="1", numero_inicial="99999999999"),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("prefijo", respuesta.context["form"].errors)
        self.assertEqual(self.sitio_a.puntos.count(), 1)
        # Con el número 0 el último nombre mide 92 caracteres: se acepta.
        respuesta = self.client.post(
            self.url, self._datos(prefijo="x" * 90, cantidad="1", numero_inicial="0")
        )
        self.assertEqual(respuesta.status_code, 302)

    def test_servicio_de_otra_empresa_no_se_acepta(self):
        respuesta = self.client.post(self.url, self._datos(servicio=self.servicio_b.pk))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("servicio", respuesta.context["form"].errors)
        self.assertEqual(self.sitio_a.puntos.count(), 1)

    def test_sitio_de_otra_empresa_da_404(self):
        url = reverse("panel:sitios:puntos_alta_multiple", args=[self.sitio_b.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self._datos()).status_code, 404)
        self.assertEqual(self.sitio_b.puntos.count(), 1)

    def test_puntos_siguen_el_orden_de_los_existentes(self):
        ultimo = self.punto_a.orden
        self.client.post(self.url, self._datos(cantidad="3"))
        ordenes = list(
            self.sitio_a.puntos.filter(nombre__startswith="Cebadero")
            .order_by("orden")
            .values_list("orden", flat=True)
        )
        self.assertEqual(ordenes, [ultimo + 1, ultimo + 2, ultimo + 3])
