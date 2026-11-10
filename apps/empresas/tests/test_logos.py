import re
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.empresas.logos import procesar_logo
from apps.empresas.models import Empresa
from apps.empresas.pruebas import crear_empresa


def _png(tamano=(800, 600), exif=False):
    imagen = Image.new("RGBA", tamano, (10, 120, 30, 128))
    salida = BytesIO()
    if exif:
        datos = Image.Exif()
        datos[0x010F] = "Camara"
        imagen.save(salida, format="PNG", exif=datos.tobytes())
    else:
        imagen.save(salida, format="PNG")
    return salida.getvalue()


class LogoTests(TestCase):
    def test_rechaza_archivo_que_no_es_imagen(self):
        archivo = SimpleUploadedFile("logo.png", b"no soy una imagen")
        with self.assertRaises(ValidationError):
            procesar_logo(archivo)

    def test_rechaza_mas_de_2_mb(self):
        archivo = SimpleUploadedFile("logo.png", _png() + b"\0" * (2 * 1024 * 1024))
        with self.assertRaises(ValidationError):
            procesar_logo(archivo)

    def test_guarda_png_sin_exif_con_nombre_aleatorio(self):
        archivo = SimpleUploadedFile("logo.png", _png((1600, 900), exif=True))
        with override_settings(MEDIA_ROOT=self._media()):
            empresa = crear_empresa()
            empresa.logo = procesar_logo(archivo)
            empresa.save()
            empresa = Empresa.objects.get(pk=empresa.pk)
            self.assertRegex(empresa.logo.name, r"^empresas/logos/[0-9a-f]{32}\.png$")
            with Image.open(empresa.logo.path) as guardado:
                self.assertEqual(guardado.format, "PNG")
                self.assertEqual(max(guardado.size), 1000)
                self.assertEqual(guardado.mode, "RGBA")
                self.assertEqual(len(guardado.getexif()), 0)
                self.assertNotIn("exif", guardado.info)

    def test_no_amplia_un_logo_chico(self):
        resultado = procesar_logo(SimpleUploadedFile("l.png", _png((40, 30))))
        with Image.open(BytesIO(resultado.read())) as imagen:
            self.assertEqual(imagen.size, (40, 30))
        self.assertIsNotNone(re.match(r"^logo\.png$", resultado.name))

    def test_guarda_hasta_1000_px_de_lado_mayor(self):
        grande = procesar_logo(SimpleUploadedFile("l.png", _png((2000, 1000))))
        with Image.open(BytesIO(grande.read())) as imagen:
            self.assertEqual(imagen.size, (1000, 500))
        justo = procesar_logo(SimpleUploadedFile("l.png", _png((1000, 400))))
        with Image.open(BytesIO(justo.read())) as imagen:
            self.assertEqual(imagen.size, (1000, 400))

    def test_rechaza_mas_de_16_mp(self):
        # 4001 x 4001 = 16,008,001 px, comprimido pesa muy poco.
        archivo = SimpleUploadedFile("l.png", _png((4001, 4001)))
        with self.assertRaises(ValidationError):
            procesar_logo(archivo)

    def _media(self):
        import tempfile

        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        return directorio.name
