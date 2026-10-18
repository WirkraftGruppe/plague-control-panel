from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.views.defaults import server_error


class ErroresTests(TestCase):
    def test_404_propia_y_500_sin_base(self):
        respuesta = self.client.get("/no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertContains(respuesta, "Página no encontrada", status_code=404)
        self.assertContains(respuesta, "css/panel.css", status_code=404)
        peticion = RequestFactory().get("/boom/")
        with self.assertNumQueries(0):
            error = server_error(peticion)
        self.assertEqual(error.status_code, 500)
        self.assertIn("Error del servidor", error.content.decode())
        self.assertIn("css/panel.css", error.content.decode())

    def test_404_y_500_sin_marca(self):
        """Ni logo ni nombre de empresa: son autónomas y neutras."""
        html_404 = self.client.get("/no-existe/").content.decode()
        html_500 = server_error(RequestFactory().get("/boom/")).content.decode()
        for html in (html_404, html_500):
            self.assertIn("pagina-error", html)
            self.assertIn("noindex", html)
            self.assertIn("Detach", html)
            self.assertNotIn(settings.NOMBRE_EMPRESA.lower(), html.lower())
            self.assertNotIn("logo", html)
            self.assertNotIn("<img", html)

    def test_404_bajo_panel_enlaza_al_panel(self):
        casos = {
            "/panel/no-existe/": ('href="/panel/"', "Volver al panel"),
            "/admin/no-existe/": ('href="/admin/"', "Volver al admin"),
            "/no-existe/": ('href="/panel/"', "Volver al panel"),
        }
        for ruta, (enlace, texto) in casos.items():
            html = render_to_string("404.html", {"request_path": ruta})
            self.assertIn(enlace, html, ruta)
            self.assertIn(texto, html, ruta)
            self.assertIn("noindex", html, ruta)
