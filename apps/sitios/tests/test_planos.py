import tempfile
import time
import zlib
from io import BytesIO
from unittest import mock

import pypdfium2
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.sitios import planos
from apps.sitios.models import Plano, Sitio

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sitios-planos-test-")


def _imagen(formato, tamano=(300, 200), modo="RGB"):
    buffer = BytesIO()
    Image.new(modo, tamano, "white").save(buffer, format=formato)
    return buffer.getvalue()


def _pdf(paginas=1):
    documento = pypdfium2.PdfDocument.new()
    for _ in range(paginas):
        documento.new_page(400, 200)
    buffer = BytesIO()
    documento.save(buffer)
    return buffer.getvalue()


def _subida(contenido, nombre="plano.bin"):
    return SimpleUploadedFile(nombre, contenido)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class PlanoTests(TestCase):
    def setUp(self):
        cliente = Cliente.objects.create(razon_social="ACME", empresa=una_empresa())
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")

    def test_pdf_se_convierte_a_imagen_y_otros_formatos_se_rechazan(self):
        contenido, ancho, alto = planos.procesar_plano(_subida(_pdf(2)))
        self.assertIsInstance(contenido, ContentFile)
        imagen = Image.open(BytesIO(contenido.read()))
        self.assertEqual(imagen.format, "PNG")
        self.assertEqual((ancho, alto), imagen.size)
        self.assertEqual((ancho, alto), (4000, 2000))
        for invalido in (
            _imagen("GIF"),
            _imagen("WEBP"),
            b"texto que no es una imagen",
            _pdf(0),
            b"%PDF-1.4 corrupto",
        ):
            with self.assertRaises(ValidationError):
                planos.procesar_plano(_subida(invalido))

    def test_imagen_grande_se_reduce_a_4000_px(self):
        contenido, ancho, alto = planos.procesar_plano(
            _subida(_imagen("PNG", (5000, 2500)))
        )
        self.assertEqual((ancho, alto), (4000, 2000))
        self.assertEqual(Image.open(BytesIO(contenido.read())).size, (4000, 2000))
        contenido, ancho, alto = planos.procesar_plano(_subida(_imagen("JPEG")))
        self.assertEqual((ancho, alto), (300, 200))

    def test_rechaza_bombas_de_pixeles_y_archivos_enormes(self):
        with self.assertRaises(ValidationError):
            planos.procesar_plano(_subida(_imagen("PNG", (9000, 9000), "1")))
        enorme = _subida(b"x")
        enorme.size = planos.TAMANO_MAXIMO + 1
        with self.assertRaises(ValidationError):
            planos.procesar_plano(enorme)

    def test_guardar_fija_dimensiones_y_usa_ruta_aleatoria(self):
        plano = Plano(sitio=self.sitio, nombre="Planta baja")
        plano.imagen = _subida(_imagen("JPEG", (800, 600)), "mi plano.jpg")
        plano.save()
        self.assertEqual((plano.ancho_px, plano.alto_px), (800, 600))
        self.assertRegex(plano.imagen.name, r"^sitios/planos/[0-9a-f]{32}\.png$")
        self.assertNotIn("mi plano", plano.imagen.name)

    def test_borrar_el_plano_borra_el_archivo(self):
        plano = Plano(sitio=self.sitio, nombre="Techo")
        plano.imagen = _subida(_imagen("PNG"))
        plano.save()
        almacenamiento, nombre = plano.imagen.storage, plano.imagen.name
        self.assertTrue(almacenamiento.exists(nombre))
        with self.captureOnCommitCallbacks(execute=True):
            plano.delete()
        self.assertFalse(almacenamiento.exists(nombre))

    def test_reemplazar_imagen_borra_la_anterior(self):
        plano = Plano(sitio=self.sitio, nombre="Techo")
        plano.imagen = _subida(_imagen("PNG"))
        plano.save()
        almacenamiento, anterior = plano.imagen.storage, plano.imagen.name
        plano.imagen = _subida(_imagen("JPEG", (500, 400)))
        with self.captureOnCommitCallbacks(execute=True):
            plano.save()
        self.assertNotEqual(plano.imagen.name, anterior)
        self.assertFalse(almacenamiento.exists(anterior))
        self.assertTrue(almacenamiento.exists(plano.imagen.name))
        nombre = plano.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            plano.nombre = "Techo norte"
            plano.save()
        self.assertTrue(almacenamiento.exists(nombre))

    def test_save_respeta_update_fields(self):
        plano = Plano(sitio=self.sitio, nombre="Techo")
        plano.imagen = _subida(_imagen("PNG"))
        plano.save()
        almacenamiento, anterior = plano.imagen.storage, plano.imagen.name
        plano.nombre = "Techo norte"
        with self.assertNumQueries(2):  # UPDATE + historial; sin leer el anterior
            plano.save(update_fields=["nombre"])
        plano.imagen = _subida(_imagen("JPEG", (500, 400)))
        with self.captureOnCommitCallbacks(execute=True):
            plano.save(update_fields=["imagen", "ancho_px", "alto_px"])
        self.assertFalse(almacenamiento.exists(anterior))

    def test_clean_rechaza_un_archivo_invalido(self):
        plano = Plano(sitio=self.sitio, nombre="Techo")
        plano.imagen = _subida(b"no es imagen")
        with self.assertRaises(ValidationError):
            plano.clean()


def _pdf_complejo(operaciones=10_000):
    """PDF mínimo cuya primera página rellena el mismo rectángulo muchas veces."""
    contenido = zlib.compress(b"0 0 600 800 re f\n" * operaciones)
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Contents 4 0 R >>",
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(contenido)
        + contenido
        + b"\nendstream",
    ]
    salida = b"%PDF-1.4\n"
    for numero, cuerpo in enumerate(objetos, start=1):
        salida += b"%d 0 obj\n" % numero + cuerpo + b"\nendobj\n"
    return salida + b"trailer\n<< /Root 1 0 R /Size 5 >>\n%%EOF\n"


class PdfComplejoTests(TestCase):
    def test_pdf_complejo_se_rechaza_con_tiempo_maximo(self):
        inicio = time.monotonic()
        with mock.patch.object(planos, "TIEMPO_MAXIMO_PDF", 2):
            with self.assertRaises(ValidationError) as contexto:
                planos.procesar_plano(_subida(_pdf_complejo()))
        transcurrido = time.monotonic() - inicio
        self.assertIn("demasiado complejo", contexto.exception.messages[0])
        self.assertLess(transcurrido, 2 + 3)
