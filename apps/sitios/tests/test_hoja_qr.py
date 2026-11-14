import datetime

from django.test import TestCase
from django.urls import reverse

from apps.sitios.models import PuntoControl

from .ayudas_empresa import DatosDeDosEmpresas


class HojaQRTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        self.crear_empresas()
        self.client.force_login(self.admin_a)
        self.url = reverse("panel:sitios:hoja_qr", args=[self.sitio_a.pk])
        self.cocina = self._punto("Cocina 1", "Cocina")
        self.patio = self._punto("Patio 1", "Patio", impreso=datetime.date(2026, 1, 1))

    def _punto(self, nombre, sector, impreso=None):
        return PuntoControl.objects.create(
            sitio=self.sitio_a, nombre=nombre, sector=sector, qr_impreso_el=impreso
        )

    def _qr(self, punto):
        return reverse("panel:sitios:punto_qr_png", args=[punto.pk])

    def test_filtra_por_sector(self):
        respuesta = self.client.get(self.url, {"sector": "Cocina"})
        self.assertContains(respuesta, self._qr(self.cocina) + "?inline=1")
        self.assertNotContains(respuesta, self._qr(self.patio))
        self.assertNotContains(respuesta, self._qr(self.punto_a))

    def test_filtra_sin_imprimir(self):
        respuesta = self.client.get(self.url, {"sin_imprimir": "1"})
        self.assertContains(respuesta, self._qr(self.cocina))
        self.assertNotContains(respuesta, self._qr(self.patio))

    def test_marcar_impresos_fija_la_fecha_solo_en_los_filtrados(self):
        respuesta = self.client.post(f"{self.url}?sector=Cocina")
        self.assertRedirects(respuesta, f"{self.url}?sector=Cocina")
        for punto in (self.cocina, self.patio, self.punto_a):
            punto.refresh_from_db()
        self.assertIsNotNone(self.cocina.qr_impreso_el)
        self.assertEqual(self.patio.qr_impreso_el, datetime.date(2026, 1, 1))
        self.assertIsNone(self.punto_a.qr_impreso_el)

    def test_hoja_respeta_la_csp(self):
        respuesta = self.client.get(self.url)
        nonce = respuesta.wsgi_request.csp_nonce
        self.assertContains(respuesta, f'<style nonce="{nonce}">')
        self.assertNotContains(respuesta, "onclick=")
        self.assertNotContains(respuesta, 'loading="lazy"')

    def test_sitio_de_otra_empresa_da_404(self):
        url = reverse("panel:sitios:hoja_qr", args=[self.sitio_b.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_marcar_impresos_de_otra_empresa_da_404(self):
        url = reverse("panel:sitios:hoja_qr", args=[self.sitio_b.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.punto_b.refresh_from_db()
        self.assertIsNone(self.punto_b.qr_impreso_el)
