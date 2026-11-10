import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import User
from apps.empresas.pruebas import crear_empresa

CLAVE = "clave-larga-de-prueba"


def _png(tamano=(1600, 900), color=(10, 120, 30, 128)):
    salida = BytesIO()
    Image.new("RGBA", tamano, color).save(salida, format="PNG")
    return salida.getvalue()


class _ConMedia(TestCase):
    """Cada test escribe los logos en un MEDIA_ROOT temporal."""

    def setUp(self):
        directorio = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(directorio.cleanup)
        sustituto = override_settings(MEDIA_ROOT=directorio.name)
        sustituto.enable()
        self.addCleanup(sustituto.disable)

    @classmethod
    def setUpTestData(cls):
        cls.empresa = crear_empresa("Fumigaciones Sur")
        cls.otra = crear_empresa("Control Norte")
        cls.admin = User.objects.create_user(
            "admin-sur",
            password=CLAVE,
            rol=User.Rol.ADMINISTRADOR,
            empresa=cls.empresa,
        )
        cls.empleado = User.objects.create_user(
            "emp-sur", password=CLAVE, empresa=cls.empresa
        )

    def _con_logo(self, empresa, tamano=(60, 30)):
        empresa.logo.save("x.png", SimpleUploadedFile("x.png", _png(tamano)))
        return empresa


class PanelEmpresaTests(_ConMedia):
    url = "/panel/empresa/"

    def test_administrador_edita_nombre_logo_y_correo(self):
        self.client.force_login(self.admin)
        self.assertEqual(reverse("panel:empresas:editar"), self.url)
        respuesta = self.client.post(
            self.url,
            {
                "nombre": "Fumigaciones del Sur",
                "correo_contacto": "info@sur.example",
                "logo": SimpleUploadedFile("mi logo.jpg", _png(), "image/png"),
            },
        )
        self.assertRedirects(respuesta, self.url)
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.nombre, "Fumigaciones del Sur")
        self.assertEqual(self.empresa.correo_contacto, "info@sur.example")
        self.assertRegex(self.empresa.logo.name, r"^empresas/logos/[0-9a-f]{32}\.png$")
        with Image.open(self.empresa.logo.path) as guardado:
            self.assertEqual(max(guardado.size), 1000)
        # La otra empresa no cambia.
        self.otra.refresh_from_db()
        self.assertEqual(self.otra.nombre, "Control Norte")
        # Reemplazar el logo borra el archivo anterior.
        anterior = self.empresa.logo.path
        self.client.post(
            self.url,
            {
                "nombre": "Fumigaciones del Sur",
                "correo_contacto": "",
                "logo": SimpleUploadedFile("n.png", _png((50, 50)), "image/png"),
            },
        )
        self.empresa.refresh_from_db()
        self.assertNotEqual(self.empresa.logo.path, anterior)
        self.assertEqual(self.empresa.correo_contacto, "")
        with self.assertRaises(FileNotFoundError):
            open(anterior, "rb")

    def test_sin_subir_logo_se_conserva_el_actual(self):
        self._con_logo(self.empresa)
        nombre = self.empresa.logo.name
        self.client.force_login(self.admin)
        self.client.post(self.url, {"nombre": "Otro nombre", "correo_contacto": ""})
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.nombre, "Otro nombre")
        self.assertEqual(self.empresa.logo.name, nombre)

    def test_logo_que_no_es_imagen_o_de_mas_de_2_mb_da_error_de_formulario(self):
        self.client.force_login(self.admin)
        casos = {
            "texto": SimpleUploadedFile("l.png", b"no soy una imagen"),
            "pesado": SimpleUploadedFile("l.png", _png() + b"\0" * (2 * 1024 * 1024)),
        }
        for caso, archivo in casos.items():
            with self.subTest(caso=caso):
                respuesta = self.client.post(
                    self.url,
                    {"nombre": "Nuevo", "correo_contacto": "", "logo": archivo},
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["form"].errors["logo"])
                self.empresa.refresh_from_db()
                self.assertEqual(self.empresa.nombre, "Fumigaciones Sur")
                self.assertFalse(self.empresa.logo)

    def test_logo_se_sirve_solo_al_administrador_de_la_empresa(self):
        url = reverse("panel:empresas:logo")
        self.assertEqual(url, "/panel/empresa/logo/")
        # Sin logo: 404.
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 404)
        self._con_logo(self.empresa, (60, 30))
        self._con_logo(self.otra, (20, 20))
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        # Recibe el de su empresa, no el de la otra.
        with Image.open(BytesIO(b"".join(respuesta.streaming_content))) as imagen:
            self.assertEqual(imagen.size, (60, 30))
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_empleado_no_entra(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        respuesta = self.client.post(self.url, {"nombre": "Hackeada"})
        self.assertEqual(respuesta.status_code, 403)
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.nombre, "Fumigaciones Sur")


class BarraLateralTests(_ConMedia):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_muestra_el_logo_de_la_empresa(self):
        self._con_logo(self.empresa)
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        self.assertIn(
            f'<img src="{reverse("panel:empresas:logo")}" alt="Fumigaciones Sur">',
            html,
        )
        self.assertNotIn("img/logo.png", html)

    def test_sin_logo_muestra_el_nombre(self):
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        self.assertIn('class="panel-logo-nombre">Fumigaciones Sur<', html)
        self.assertNotIn("<img", html.split('<nav aria-label="Principal">')[0])

    def test_menu_administracion_tiene_empresa(self):
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        href = f'href="{reverse("panel:empresas:editar")}"'
        self.assertGreater(html.index(href), html.index(">Administración<"))
        self.assertIn(">Empresa</a>", html)
        html = self.client.get(reverse("panel:empresas:editar")).content.decode()
        self.assertIn(f'{href} aria-current="page">Empresa</a>', html)


class IngresoTests(TestCase):
    def test_login_no_muestra_el_nombre_de_ninguna_empresa(self):
        crear_empresa("Fumigaciones Sur")
        crear_empresa("Control Norte")
        with override_settings(NOMBRE_EMPRESA="Fumigaciones Sur"):
            html = self.client.get("/panel/ingresar/").content.decode()
        self.assertIn('alt="Detach"', html)
        self.assertNotIn("Fumigaciones Sur", html)
        self.assertNotIn("Control Norte", html)
