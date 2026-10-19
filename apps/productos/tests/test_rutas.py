"""Rutas de Productos: la API expone el catálogo y el panel sigue vacío."""

from django.test import SimpleTestCase

from apps.productos import api_urls, panel_urls


class RutasProductosTests(SimpleTestCase):
    """Pruebas de los routers de Productos."""

    def test_routers_de_productos_estan_vacios(self):
        """Comprueba app_name, la ruta del catálogo y que el panel no tiene rutas."""
        self.assertEqual(api_urls.app_name, "productos")
        self.assertEqual([p.name for p in api_urls.urlpatterns], ["catalogo"])

        self.assertEqual(panel_urls.app_name, "productos")
        self.assertEqual(
            [p.name for p in panel_urls.urlpatterns],
            ["listado", "alta", "ficha", "movimiento_alta", "editar"],
        )
