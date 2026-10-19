import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase


class BaseTemplateTests(SimpleTestCase):
    def test_titulo_es_detach_y_logo_lleva_nombre_empresa(self):
        peticion = RequestFactory().get("/")
        html = render_to_string("base.html", request=peticion)
        self.assertIn("<title>Detach</title>", html)
        self.assertIn("img/logo.png", html)
        self.assertIn(f'alt="{settings.NOMBRE_EMPRESA}"', html)
        for plantilla in ("panel/base.html", "panel/ingresar.html"):
            html = render_to_string(plantilla, request=peticion)
            self.assertIn("· Detach</title>", html, plantilla)
            self.assertIn(f'alt="{settings.NOMBRE_EMPRESA}"', html, plantilla)

    def test_base_es_noindex_y_de_un_solo_tema(self):
        html = render_to_string("base.html")
        self.assertIn('<meta name="robots" content="noindex, nofollow">', html)
        self.assertIn('<html lang="es" data-tema="claro">', html)
        self.assertNotIn("oscuro", html)
        self.assertNotIn("sitio público", html)
        self.assertEqual(html.count("[data-tema="), 1)
        self.assertIn("--brand: #ffc600", html)

    def test_base_no_carga_fuentes_de_terceros(self):
        html = render_to_string("base.html")
        self.assertNotIn("fonts.googleapis.com", html)
        self.assertNotIn("fonts.gstatic.com", html)

    def test_fuentes_referenciadas_existen(self):
        html = render_to_string("base.html")
        bloques = re.findall(r"@font-face\s*\{[^}]*\}", html)
        urls = [u for b in bloques for u in re.findall(r'url\("([^"]+)"\)', b)]
        self.assertGreaterEqual(len(urls), 7)
        for url in urls:
            ruta = url.removeprefix(settings.STATIC_URL)
            self.assertIsNotNone(finders.find(ruta), url)
