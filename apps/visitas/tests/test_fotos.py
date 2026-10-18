import shutil
import struct
import tempfile
import zlib
from io import BytesIO
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.visitas.models import Foto

from .test_models import crear_revision, crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="detach-test-")


def _bytes(imagen, formato, **opciones):
    salida = BytesIO()
    imagen.save(salida, format=formato, **opciones)
    return salida.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.revision = crear_revision(crear_visita())

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def test_redimensiona_y_quita_exif(self):
        exif = Image.Exif()
        exif[0x010F] = "Camara"
        exif[0x8825] = {1: "S", 2: (34.0, 36.0, 0.0), 3: "W", 4: (58.0, 22.0, 0.0)}
        datos = _bytes(Image.new("RGB", (3000, 2000), "red"), "JPEG", exif=exif)
        self.assertTrue(Image.open(BytesIO(datos)).getexif())
        foto = Foto.objects.create(
            revision=self.revision,
            imagen=SimpleUploadedFile("foto.jpg", datos, content_type="image/jpeg"),
        )
        with Image.open(foto.imagen.path) as guardada:
            self.assertEqual(max(guardada.size), 1600)
            self.assertEqual(len(guardada.getexif()), 0)

    def test_exif_corrupto_no_impide_guardar(self):
        datos = _bytes(Image.new("RGB", (2000, 1000), "red"), "JPEG")
        for error in (struct.error("exif roto"), SyntaxError("exif roto")):
            with self.subTest(error=type(error).__name__):
                with mock.patch(
                    "apps.visitas.imagenes.ImageOps.exif_transpose",
                    side_effect=error,
                ):
                    foto = Foto.objects.create(
                        revision=self.revision,
                        imagen=SimpleUploadedFile(
                            "foto.jpg", datos, content_type="image/jpeg"
                        ),
                    )
                with Image.open(foto.imagen.path) as guardada:
                    self.assertEqual(max(guardada.size), 1600)
                    self.assertEqual(len(guardada.getexif()), 0)

    def test_png_se_guarda_como_jpeg(self):
        datos = _bytes(Image.new("RGBA", (100, 80), "blue"), "PNG")
        foto = Foto.objects.create(
            revision=self.revision,
            imagen=SimpleUploadedFile(
                "casa de Perez.png", datos, content_type="image/png"
            ),
        )
        with Image.open(foto.imagen.path) as guardada:
            self.assertEqual(guardada.format, "JPEG")
        self.assertNotIn("Perez", foto.imagen.name)

    def test_rechaza_imagen_con_demasiados_pixeles(self):
        datos = _bytes(Image.new("L", (8000, 6000)), "PNG")
        with self.assertRaises(ValidationError):
            Foto.objects.create(
                revision=self.revision,
                imagen=SimpleUploadedFile(
                    "grande.png", datos, content_type="image/png"
                ),
            )
        self.assertEqual(Foto.objects.count(), 0)

    def test_mensaje_de_resolucion_excesiva(self):
        datos = _bytes(Image.new("L", (8000, 6000)), "PNG")
        with self.assertRaises(ValidationError) as contexto:
            Foto.objects.create(
                revision=self.revision,
                imagen=SimpleUploadedFile(
                    "grande.png", datos, content_type="image/png"
                ),
            )
        self.assertIn("resolución", contexto.exception.messages[0])
        self.assertNotIn("no es una imagen", contexto.exception.messages[0])

    def test_quita_comentario_del_jpeg(self):
        datos = _bytes(Image.new("RGB", (100, 80), "green"), "JPEG", comment=b"SECRETO")
        self.assertIn(b"SECRETO", datos)
        foto = Foto.objects.create(
            revision=self.revision,
            imagen=SimpleUploadedFile("foto.jpg", datos, content_type="image/jpeg"),
        )
        with open(foto.imagen.path, "rb") as guardada:
            self.assertNotIn(b"SECRETO", guardada.read())

    def test_archivo_que_no_es_imagen_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            Foto.objects.create(
                revision=self.revision,
                imagen=SimpleUploadedFile(
                    "falso.jpg", b"esto no es una imagen", content_type="image/jpeg"
                ),
            )
        self.assertEqual(Foto.objects.count(), 0)

    def _png_con_idat_corrupto(self, recalcular_crc):
        """PNG real con los bytes de datos del IDAT sobrescritos."""
        imagen = Image.effect_noise((200, 200), 80).convert("RGB")
        datos = bytearray(_bytes(imagen, "PNG"))
        inicio = datos.index(b"IDAT")
        largo = struct.unpack(">I", datos[inicio - 4 : inicio])[0]
        desde, hasta = inicio + 4, inicio + 4 + largo
        datos[desde:hasta] = bytes([0xFF]) * largo
        if recalcular_crc:
            crc = zlib.crc32(bytes(datos[inicio:hasta]))
            datos[hasta : hasta + 4] = struct.pack(">I", crc)
        return bytes(datos)

    def test_png_corrupto_se_rechaza(self):
        for recalcular_crc in (True, False):
            with self.subTest(crc_recalculado=recalcular_crc):
                datos = self._png_con_idat_corrupto(recalcular_crc)
                with self.assertRaises(ValidationError):
                    Foto.objects.create(
                        revision=self.revision,
                        imagen=SimpleUploadedFile(
                            "roto.png", datos, content_type="image/png"
                        ),
                    )
                self.assertEqual(Foto.objects.count(), 0)

    def test_webp_con_dimensiones_enormes_se_rechaza(self):
        # 39,2 MP: bajo el tope de JPEG pero sobre el de WebP (16 MP).
        datos = _bytes(Image.new("L", (8000, 4900)), "WEBP", lossless=True)
        with self.assertRaises(ValidationError):
            Foto.objects.create(
                revision=self.revision,
                imagen=SimpleUploadedFile(
                    "enorme.webp", datos, content_type="image/webp"
                ),
            )
        self.assertEqual(Foto.objects.count(), 0)

    def test_formato_no_permitido_se_rechaza(self):
        for formato in ("ICNS", "GIF", "BMP"):
            with self.subTest(formato=formato):
                datos = _bytes(Image.new("RGB", (128, 128), "red"), formato)
                with self.assertRaises(ValidationError):
                    Foto.objects.create(
                        revision=self.revision,
                        imagen=SimpleUploadedFile("foto." + formato.lower(), datos),
                    )
                self.assertEqual(Foto.objects.count(), 0)

    def _crear(self, nombre, datos, tipo):
        return Foto.objects.create(
            revision=self.revision,
            imagen=SimpleUploadedFile(nombre, datos, content_type=tipo),
        )

    def test_mpo_se_acepta(self):
        # Pillow abre un JPEG con varios cuadros como MPO (format == "MPO").
        base = Image.new("RGB", (200, 100), "red")
        datos = _bytes(
            base, "MPO", save_all=True, append_images=[Image.new("RGB", (200, 100))]
        )
        with Image.open(BytesIO(datos)) as abierta:
            self.assertEqual(abierta.format, "MPO")
        foto = self._crear("foto.jpg", datos, "image/jpeg")
        with Image.open(foto.imagen.path) as guardada:
            self.assertEqual(guardada.format, "JPEG")
            self.assertEqual(getattr(guardada, "n_frames", 1), 1)

    def test_png_con_ztxt_enorme_se_rechaza(self):
        # El zTXt va después del IDAT: Pillow lo descomprime en load() y lanza
        # ValueError("Decompressed data too large") si pasa de MAX_TEXT_CHUNK.
        datos = _bytes(Image.new("RGB", (20, 20), "red"), "PNG")
        cuerpo = b"clave\x00\x00" + zlib.compress(b"\x00" * (2 * 1024 * 1024))
        chunk = b"zTXt" + cuerpo
        chunk = (
            struct.pack(">I", len(cuerpo))
            + chunk
            + struct.pack(">I", zlib.crc32(chunk))
        )
        fin = datos.rindex(b"IEND") - 4
        datos = datos[:fin] + chunk + datos[fin:]
        with self.assertRaises(ValidationError):
            self._crear("ztxt.png", datos, "image/png")
        self.assertEqual(Foto.objects.count(), 0)

    def test_webp_de_10_mp_se_rechaza(self):
        datos = _bytes(Image.new("L", (4000, 2500)), "WEBP", lossless=True)
        with self.assertRaises(ValidationError):
            self._crear("grande.webp", datos, "image/webp")
        self.assertEqual(Foto.objects.count(), 0)

    def test_jpeg_progresivo_grande_se_rechaza(self):
        # 20 MP: libjpeg guarda los coeficientes completos y draft no los reduce.
        imagen = Image.new("L", (5000, 4000))
        with self.assertRaises(ValidationError):
            self._crear(
                "prog.jpg", _bytes(imagen, "JPEG", progressive=True), "image/jpeg"
            )
        self.assertEqual(Foto.objects.count(), 0)
        self._crear("base.jpg", _bytes(imagen, "JPEG"), "image/jpeg")
        self.assertEqual(Foto.objects.count(), 1)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class MemoriaImagenTests(TestCase):
    """Topes de memoria para JPEG: el muestreo y draft() condicionan el costo."""

    @classmethod
    def setUpTestData(cls):
        cls.revision = crear_revision(crear_visita())

    def _crear(self, datos):
        return Foto.objects.create(
            revision=self.revision,
            imagen=SimpleUploadedFile("foto.jpg", datos, content_type="image/jpeg"),
        )

    def test_jpeg_secuencial_con_muestreo_costoso_se_rechaza(self):
        # 20 MP secuencial 4:4:4 (muestreo 0): bajo el tope de JPEG (40 MP) pero
        # sobre el de JPEG costoso (16 MP).
        datos = _bytes(Image.new("RGB", (5000, 4000)), "JPEG", subsampling=0)
        with self.assertRaises(ValidationError):
            self._crear(datos)
        self.assertEqual(Foto.objects.count(), 0)

    def test_proporcion_extrema_se_rechaza(self):
        # 30 MP muy apaisados: draft() no reduce porque el alto ya es menor que
        # el lado máximo y quedarían 30 MP en memoria.
        datos = _bytes(Image.new("RGB", (20000, 1500)), "JPEG")
        with self.assertRaises(ValidationError):
            self._crear(datos)
        self.assertEqual(Foto.objects.count(), 0)
