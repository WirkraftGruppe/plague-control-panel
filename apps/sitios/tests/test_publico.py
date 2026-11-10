import uuid

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path

from apps.empresas.models import Empresa
from apps.sitios import publico_urls, qr

urlpatterns = [path("", lambda r: None, name="raiz"), *publico_urls.urlpatterns]


@override_settings(ROOT_URLCONF=__name__)
class PaginaQRTests(TestCase):
    def test_q_uuid_es_neutra_y_no_consulta_la_base(self):
        with self.assertNumQueries(0):
            respuesta = self.client.get(f"/q/{uuid.uuid4()}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Punto de control de Detach — use la app")
        self.assertContains(respuesta, 'alt="Detach"')

    def test_q_no_uuid_da_404(self):
        self.assertEqual(self.client.get("/q/no-es-uuid/").status_code, 404)

    def test_pagina_qr_es_noindex_y_no_expone_el_codigo(self):
        codigo = uuid.uuid4()
        respuesta = self.client.get(f"/q/{codigo}/")
        self.assertContains(respuesta, '<meta name="robots" content="noindex">')
        self.assertContains(respuesta, "css/panel.css")
        self.assertNotContains(respuesta, str(codigo))

    def test_q_lleva_cabecera_x_robots_tag_noindex(self):
        respuesta = self.client.get(f"/q/{uuid.uuid4()}/")
        self.assertEqual(respuesta["X-Robots-Tag"], "noindex, nofollow")


@override_settings(ROOT_URLCONF=__name__)
class PublicoSinEmpresaTests(TestCase):
    def test_pagina_del_qr_no_muestra_datos_de_ninguna_empresa(self):
        empresas = [Empresa.objects.create(nombre=n) for n in ("Alfa SA", "Beta SRL")]
        respuesta = self.client.get(f"/q/{uuid.uuid4()}/")
        self.assertEqual(respuesta.status_code, 200)
        for empresa in empresas:
            self.assertNotContains(respuesta, empresa.nombre)
        self.assertContains(respuesta, "Detach")


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
