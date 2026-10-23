"""La plantilla base del panel es de un solo tema y sin atributo de tema."""

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class PanelBaseTests(SimpleTestCase):
    def test_panel_base_es_de_un_solo_tema(self):
        html = render_to_string("panel/base.html")
        self.assertIn('<html lang="es">', html)
        self.assertNotIn("data-tema", html)
