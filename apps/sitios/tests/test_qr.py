from unittest import mock

from django.test import TestCase
from PIL import ImageFont

from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.sitios import qr
from apps.sitios.models import Sitio


class QrTests(TestCase):
    def test_dibuja_letras_acentuadas(self):
        """La fuente del QR tiene glifo propio para "ó", no el de un faltante."""
        fuente = ImageFont.truetype(qr.RUTA_FUENTE, 22)

        def mapa(letra):
            mascara = fuente.getmask(letra)
            return mascara.size, bytes(mascara)

        self.assertNotEqual(mapa("ó"), mapa("o"))
        self.assertNotEqual(mapa("ó"), mapa("中"))

    def test_sin_fuente_usa_la_de_pillow_y_avisa(self):
        """Si la fuente no carga, el QR se genera con la de Pillow y queda un aviso."""
        sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME", empresa=una_empresa()),
            nombre="Planta",
        )
        with (
            mock.patch.object(qr, "RUTA_FUENTE", "no-existe.woff2"),
            self.assertLogs("apps.sitios.qr", level="WARNING") as registro,
        ):
            contenido = qr.png_qr(sitio.puntos.get())
        self.assertEqual(contenido[1:4], b"PNG")
        self.assertIn("fuente", registro.output[0])
