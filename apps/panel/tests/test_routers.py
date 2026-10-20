"""Los routers de panel incluyen un conjunto de rutas por cada app."""

from django.test import SimpleTestCase
from django.urls import URLResolver

from apps.panel import urls

APPS = [
    "sitios",
    "clientes",
    "servicios",
    "productos",
    "visitas",
    "informes",
    "accounts",
]


class RoutersPanelTests(SimpleTestCase):
    def test_panel_incluye_un_router_por_app(self):
        incluidos = {
            getattr(patron.urlconf_name, "__name__", patron.urlconf_name)
            for patron in urls.urlpatterns
            if isinstance(patron, URLResolver)
        }
        esperados = {f"apps.{app}.panel_urls" for app in APPS}
        self.assertEqual(incluidos, esperados)
