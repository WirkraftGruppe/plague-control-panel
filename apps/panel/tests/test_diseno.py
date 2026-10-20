"""Diseño del panel: layout, filtro de tonos y listado base con HTMX."""

import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from apps.panel.listados import ListadoPanelMixin
from apps.panel.templatetags.panel_ui import tono_estado

User = get_user_model()

RAIZ = Path(__file__).resolve().parents[3]
PLANTILLAS = RAIZ / "apps" / "panel" / "templates" / "panel"
CSS = (RAIZ / "static" / "css" / "panel.css").read_text(encoding="utf-8")


class ListadoPrueba(ListadoPanelMixin):
    model = User
    template_name = "prueba/listado.html"
    template_parcial = "prueba/parcial.html"
    orden_permitido = ("username",)
    campos_busqueda = ("username",)


class DisenoTests(TestCase):
    def setUp(self):
        self.fabrica = RequestFactory()

    def _vista(self, ruta="/", **cabeceras):
        peticion = self.fabrica.get(ruta, **cabeceras)
        vista = ListadoPrueba()
        vista.setup(peticion)
        vista.object_list = User.objects.none()
        return vista

    def test_base_carga_htmx_y_css_desde_static(self):
        html = render_to_string("panel/base.html")
        self.assertIn("css/panel.css", html)
        self.assertIn("vendor/htmx/htmx.min.js", html)
        self.assertIn('"includeIndicatorStyles":false', html)
        self.assertIn("hx-headers", html)

    def test_ingresar_no_muestra_barra_lateral(self):
        respuesta = self.client.get("/panel/ingresar/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "barra-lateral")
        self.assertContains(respuesta, 'name="username"')
        self.assertContains(respuesta, 'name="password"')

    def test_tono_estado_mapea_los_cuatro_tonos(self):
        esperado = {
            "vencida": "danger",
            "proxima": "warn",
            "al_dia": "ok",
            "sin_programar": "neutral",
            "abierta": "warn",
            "realizada": "ok",
            "pendiente": "warn",
            "cancelada": "neutral",
        }
        for estado, tono in esperado.items():
            self.assertEqual(tono_estado(estado), tono)

    def test_listado_devuelve_parcial_con_hx_request(self):
        self.assertEqual(self._vista().get_template_names()[0], "prueba/listado.html")
        vista = self._vista(HTTP_HX_REQUEST="true")
        self.assertEqual(vista.get_template_names(), ["prueba/parcial.html"])
        self.assertEqual(vista.paginate_by, 25)

    def test_orden_fuera_de_la_lista_blanca_se_ignora(self):
        User.objects.create_user(username="b", password="x")
        User.objects.create_user(username="a", password="x")
        vista = self._vista("/?orden=password")
        self.assertEqual(vista.get_orden(), "")
        self.assertFalse(vista.get_queryset().query.order_by)
        vista = self._vista("/?orden=-username&q=a")
        self.assertEqual(vista.get_orden(), "-username")
        self.assertEqual(
            list(vista.get_queryset().values_list("username", flat=True)), ["a"]
        )

    def test_panel_css_define_enlace(self):
        bloque = re.search(r"(?m)^\.enlace\s*\{([^}]*)\}", CSS)
        self.assertIsNotNone(bloque, "panel.css no define .enlace")
        self.assertIn("text-decoration: underline", bloque.group(1))
        self.assertIn("cursor: pointer", bloque.group(1))
        self.assertIn("background: none", bloque.group(1))

    def test_mapa_sin_style_propio(self):
        texto = (PLANTILLAS / "mapa.html").read_text(encoding="utf-8")
        self.assertNotIn("<style", texto)
        for clase in (".mapa-filtros", "#mapa"):
            self.assertIn(clase, CSS)

    def test_clases_de_fichas_tienen_estilo(self):
        for clase in ("linea-tiempo", "miniaturas", "planilla", "fotos"):
            with self.subTest(clase=clase):
                self.assertRegex(CSS, rf"(?m)^\.{clase}\b")
