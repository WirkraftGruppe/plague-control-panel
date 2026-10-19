"""Los routers de api incluyen un conjunto de rutas por cada app."""

from django.test import SimpleTestCase
from django.urls import URLResolver

from apps.api import urls

APPS = [
    "sitios",
    "clientes",
    "servicios",
    "proyectos",
    "productos",
    "visitas",
    "informes",
]


class RoutersApiTests(SimpleTestCase):
    def test_api_incluye_un_router_por_app(self):
        incluidos = {
            getattr(patron.urlconf_name, "__name__", patron.urlconf_name)
            for patron in urls.urlpatterns
            if isinstance(patron, URLResolver)
        }
        esperados = {f"apps.{app}.api_urls" for app in APPS}
        self.assertEqual(incluidos, esperados)
