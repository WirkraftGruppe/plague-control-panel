from django.test import TestCase

from apps.servicios.models import TipoServicio


class SinDescripcionTests(TestCase):
    def test_tipo_servicio_no_tiene_descripcion(self):
        nombres = {campo.name for campo in TipoServicio._meta.get_fields()}
        self.assertNotIn("descripcion", nombres)

    def test_una_base_nueva_arranca_sin_servicios(self):
        self.assertEqual(TipoServicio.todos.count(), 0)
