"""Nombre de la empresa, correo de contacto, SITE_URL y marca Detach del producto."""

from django.apps import apps
from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase, override_settings

from config.contexto import empresa
from config.tests.test_settings import _correr

_PROD = {
    "DJANGO_ENV": "production",
    "SECRET_KEY": "x" * 60,
    "DATABASE_URL": "sqlite:///prod-test.sqlite3",
    "ALLOWED_HOSTS": "demo.up.railway.app",
}


def _leer(expresion, **entorno):
    """Imprime una expresión sobre los settings en un proceso aparte."""
    return _correr(
        ["shell", "-c", f"from django.conf import settings as s; print({expresion})"],
        **entorno,
    )


class EmpresaTests(SimpleTestCase):
    @override_settings(NOMBRE_EMPRESA="Ejemplo S.R.L.")
    def test_contexto_expone_nombre_empresa(self):
        """El context processor está registrado y toma el valor de settings."""
        request = RequestFactory().get("/")
        self.assertEqual(empresa(request), {"NOMBRE_EMPRESA": "Ejemplo S.R.L."})
        plantilla = engines["django"].from_string("[{{ NOMBRE_EMPRESA }}]")
        self.assertEqual(plantilla.render({}, request), "[Ejemplo S.R.L.]")

    def test_nombre_empresa_y_correo_salen_del_entorno(self):
        """Se leen del entorno; vacíos o con espacios caen al valor por defecto."""
        r = _leer(
            "s.NOMBRE_EMPRESA, s.CORREO_CONTACTO",
            DJANGO_ENV="development",
            NOMBRE_EMPRESA=" Otra S.A. ",
            CORREO_CONTACTO="contacto@ejemplo.test",
        )
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(
            r.stdout.strip().splitlines()[-1], "Otra S.A. contacto@ejemplo.test"
        )
        for vacio in ("", "   "):
            with self.subTest(vacio=vacio):
                r = _leer(
                    "s.NOMBRE_EMPRESA, s.CORREO_CONTACTO",
                    DJANGO_ENV="development",
                    NOMBRE_EMPRESA=vacio,
                    CORREO_CONTACTO=vacio,
                )
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(
                    r.stdout.strip().splitlines()[-1],
                    "MAControl S.A. administracion@macontrol.com.ar",
                )

    def test_site_url_por_defecto_es_local(self):
        """Sin SITE_URL (o vacía), desarrollo usa el origen local."""
        for vacio in ("", "  "):
            with self.subTest(vacio=vacio):
                r = _leer("s.SITE_URL", DJANGO_ENV="development", SITE_URL=vacio)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(
                    r.stdout.strip().splitlines()[-1], "http://localhost:8000"
                )

    def test_prod_sin_site_url_no_arranca(self):
        """Producción sin SITE_URL (o vacía) no arranca; con ella, sí."""
        for vacio in ("", "   "):
            with self.subTest(vacio=vacio):
                r = _leer("s.SITE_URL", **_PROD, SITE_URL=vacio)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("SITE_URL", r.stdout + r.stderr)
                self.assertIn("ImproperlyConfigured", r.stdout + r.stderr)
        r = _leer("s.SITE_URL", **_PROD, SITE_URL="https://ejemplo.test/")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip().splitlines()[-1], "https://ejemplo.test")

    def test_admin_y_api_se_llaman_detach(self):
        """El admin usa AdminDetachConfig y la API se titula Detach con la empresa."""
        self.assertEqual(
            type(apps.get_app_config("admin")).__name__, "AdminDetachConfig"
        )
        self.assertEqual(settings.SPECTACULAR_SETTINGS["TITLE"], "API de Detach")
        self.assertIn(
            settings.NOMBRE_EMPRESA, settings.SPECTACULAR_SETTINGS["DESCRIPTION"]
        )
        self.assertNotIn("MAControl", settings.SPECTACULAR_SETTINGS["TITLE"])
