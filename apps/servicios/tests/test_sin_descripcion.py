from django.core.management import call_command
from django.test import TestCase

from apps.servicios.models import TipoServicio


class SinDescripcionTests(TestCase):
    def test_tipo_servicio_no_tiene_descripcion(self):
        nombres = {campo.name for campo in TipoServicio._meta.get_fields()}
        self.assertNotIn("descripcion", nombres)

    def test_fixture_tipos_servicio_carga_los_nueve(self):
        call_command("loaddata", "tipos_servicio", verbosity=0)
        self.assertEqual(TipoServicio.objects.count(), 9)
