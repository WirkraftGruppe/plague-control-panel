import uuid

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path

from apps.sitios import publico_urls, qr

urlpatterns = [path("", lambda r: None, name="raiz"), *publico_urls.urlpatterns]


@override_settings(ROOT_URLCONF=__name__, NOMBRE_EMPRESA="Empresa <Prueba>")
class PaginaQRTests(TestCase):
    def test_q_uuid_muestra_nombre_empresa_sin_consultar_la_base(self):
        with self.assertNumQueries(0):
            respuesta = self.client.get(f"/q/{uuid.uuid4()}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta, "Punto de control de Empresa &lt;Prueba&gt; — use la app"
        )
        self.assertContains(respuesta, 'alt="Empresa &lt;Prueba&gt;"')

    def test_q_no_uuid_da_404(self):
        self.assertEqual(self.client.get("/q/no-es-uuid/").status_code, 404)

    def test_pagina_qr_es_noindex_y_no_expone_el_codigo(self):
        codigo = uuid.uuid4()
        respuesta = self.client.get(f"/q/{codigo}/")
        self.assertContains(respuesta, '<meta name="robots" content="noindex">')
        self.assertContains(respuesta, "css/panel.css")
        self.assertNotContains(respuesta, str(codigo))


class ContenidoQRTests(SimpleTestCase):
    @override_settings(
        ROOT_URLCONF="apps.sitios.publico_urls", SITE_URL="https://e.test"
    )
    def test_contenido_no_depende_de_la_urlconf_raiz(self):
        codigo = uuid.uuid4()
        punto = type("Punto", (), {"qr_codigo": codigo})()
        self.assertEqual(qr.contenido_qr(punto), f"https://e.test/q/{codigo}/")
        with override_settings(ROOT_URLCONF="apps.sitios.tests.urlconf_inexistente"):
            self.assertEqual(qr.contenido_qr(punto), f"https://e.test/q/{codigo}/")
