import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, models, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita, ruta_foto


def crear_visita(**extra):
    """Visita guardada con proyecto, empleado y administrador propios."""
    cliente = Cliente.objects.create(razon_social="ACME")
    sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
    sufijo = uuid4().hex[:8]
    tipo = TipoServicio.objects.create(nombre="Roedores", slug=f"roedores-{sufijo}")
    empleado = User.objects.create_user(
        username=f"emp-{sufijo}", password="x", rol=User.Rol.EMPLEADO
    )
    proyecto = Proyecto.objects.create(
        sitio=sitio,
        tipo_servicio=tipo,
        titulo="Roedores mensual",
        encargado_inicial=empleado,
        encargado_actual=empleado,
    )
    datos = {"proyecto": proyecto, "empleado": empleado, "origen": Visita.Origen.APP}
    datos.update(extra)
    return Visita.objects.create(**datos)


def punto_de(visita):
    """Punto "General" del sitio de la visita (su QR es `punto.qr_codigo`)."""
    return visita.proyecto.sitio.puntos.get(orden=0)


def crear_revision(visita, **extra):
    """Revisión guardada en el punto General del sitio de la visita."""
    ahora = timezone.now()
    datos = {
        "visita": visita,
        "punto": punto_de(visita),
        "orden": visita.revisiones.count() + 1,
        "realizada_en": ahora,
        "recibida_en": ahora,
    }
    datos.update(extra)
    return Revision.objects.create(**datos)


class VisitaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita()
        cls.admin = User.objects.create_user(
            username="admin-vis", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def test_empleado_acepta_empleado_o_administrador_y_rechaza_otro_rol(self):
        self.visita.empleado = self.admin
        self.visita.estado = Visita.Estado.ABIERTA
        self.visita.abierta_en = timezone.now()
        self.visita.full_clean()
        self.visita.estado = Visita.Estado.PENDIENTE
        self.visita.empleado = User.objects.create_user(
            username="otro-rol", password="x", rol="visitante"
        )
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("empleado", ctx.exception.message_dict)

    def test_realizada_exige_cerrada_en(self):
        self.visita.estado = Visita.Estado.REALIZADA
        self.visita.cerrada_en = None
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("cerrada_en", ctx.exception.message_dict)

    def test_cancelada_no_admite_cerrada_en(self):
        self.visita.estado = Visita.Estado.CANCELADA
        self.visita.cerrada_en = timezone.now()
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("cerrada_en", ctx.exception.message_dict)

    def test_abierta_exige_abierta_en(self):
        self.visita.estado = Visita.Estado.ABIERTA
        with self.assertRaises(ValidationError) as ctx:
            self.visita.full_clean()
        self.assertIn("abierta_en", ctx.exception.message_dict)
        self.visita.abierta_en = timezone.now()
        self.visita.full_clean()

    def test_realizada_en_es_la_fecha_de_cierre(self):
        ahora = timezone.now()
        self.visita.cerrada_en = ahora
        self.assertEqual(self.visita.realizada_en, ahora)

    def test_pendiente_no_admite_revisiones(self):
        visita = crear_visita()
        visita.full_clean()
        crear_revision(visita)
        with self.assertRaises(ValidationError):
            visita.full_clean()
        visita.estado = Visita.Estado.REALIZADA
        visita.cerrada_en = timezone.now()
        visita.full_clean()

    def test_historial_excluye_datos_y_ya_no_tiene_la_evidencia(self):
        campos = {f.name for f in Visita.history.model._meta.get_fields()}
        for excluido in ("datos", "latitud", "longitud", "precision_m", "cliente_uuid"):
            self.assertNotIn(excluido, campos)
        self.assertIn("estado", campos)
        self.assertIn("cierre", campos)


class RevisionTests(TestCase):
    def test_historial_excluye_coordenadas_y_datos(self):
        campos = {f.name for f in Revision.history.model._meta.get_fields()}
        for excluido in ("latitud", "longitud", "precision_m", "datos"):
            self.assertNotIn(excluido, campos)
        self.assertIn("realizada_en", campos)

    def test_cliente_uuid_es_unico_y_admite_varias_sin_valor(self):
        visita = crear_visita()
        identificador = uuid4()
        crear_revision(visita, cliente_uuid=identificador)
        with self.assertRaises(IntegrityError), transaction.atomic():
            crear_revision(visita, cliente_uuid=identificador)
        crear_revision(visita)
        crear_revision(visita)

    def test_un_punto_puede_revisarse_mas_de_una_vez_en_la_visita(self):
        visita = crear_visita()
        crear_revision(visita)
        crear_revision(visita)
        self.assertEqual(
            list(visita.revisiones.values_list("orden", flat=True)), [1, 2]
        )

    def test_el_punto_con_revisiones_no_se_borra(self):
        visita = crear_visita()
        crear_revision(visita)
        with self.assertRaises(models.ProtectedError):
            punto_de(visita).delete()


class FotoModeloTests(TestCase):
    def test_ruta_foto_usa_uuid_y_no_el_nombre_original(self):
        ruta = ruta_foto(None, "casa de Perez.png")
        self.assertRegex(ruta, r"^visitas/fotos/[0-9a-f]{32}\.jpg$")
        self.assertNotIn("Perez", ruta)
        self.assertNotEqual(ruta, ruta_foto(None, "casa de Perez.png"))


def imagen_real(color="red"):
    """Archivo subido con un PNG real generado con Pillow."""
    buffer = BytesIO()
    Image.new("RGB", (40, 30), color).save(buffer, format="PNG")
    return SimpleUploadedFile("foto.png", buffer.getvalue(), content_type="image/png")


class FotoArchivoTests(TestCase):
    """El archivo de la foto no queda en disco al borrar o reemplazar la foto."""

    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        configuracion = override_settings(MEDIA_ROOT=self.media)
        configuracion.enable()
        self.addCleanup(configuracion.disable)
        self.visita = crear_visita()
        self.revision = crear_revision(self.visita)

    def _crear_foto(self):
        return Foto.objects.create(revision=self.revision, imagen=imagen_real())

    def test_borrar_foto_borra_el_archivo(self):
        foto = self._crear_foto()
        ruta = Path(foto.imagen.path)
        self.assertTrue(ruta.exists())
        with self.captureOnCommitCallbacks(execute=True):
            foto.delete()
        self.assertFalse(ruta.exists())

    def test_borrar_visita_borra_los_archivos_de_sus_fotos(self):
        rutas = [Path(self._crear_foto().imagen.path) for _ in range(2)]
        self.assertTrue(all(ruta.exists() for ruta in rutas))
        with self.captureOnCommitCallbacks(execute=True):
            self.visita.delete()
        self.assertFalse(any(ruta.exists() for ruta in rutas))

    def test_reemplazar_imagen_borra_el_archivo_anterior(self):
        foto = self._crear_foto()
        anterior = Path(foto.imagen.path)
        foto.imagen = imagen_real("blue")
        with self.captureOnCommitCallbacks(execute=True):
            foto.save()
        nueva = Path(foto.imagen.path)
        self.assertNotEqual(anterior, nueva)
        self.assertFalse(anterior.exists())
        self.assertTrue(nueva.exists())


class ProductoAplicadoTests(TestCase):
    def test_historial_registra_cambio_de_lote(self):
        revision = crear_revision(crear_visita())
        producto = Producto.objects.create(nombre_comercial="Cebo X")
        aplicado = ProductoAplicado.objects.create(
            revision=revision,
            producto=producto,
            lote="L-1",
            dosis=Decimal("1.500"),
            unidad_dosis="g",
            unidad="g",
            cantidad=Decimal("1"),
            cantidad_base=Decimal("1"),
        )
        aplicado.lote = "L-2"
        aplicado.save()
        historial = aplicado.history.order_by("history_id")
        lotes = list(historial.values_list("lote", flat=True))
        self.assertEqual(lotes, ["L-1", "L-2"])


class CamposAppTests(TestCase):
    def test_visita_nueva_no_es_incidencia_de_asignacion_ni_esta_cerrada(self):
        visita = crear_visita()
        self.assertFalse(visita.incidencia_asignacion)
        self.assertEqual(visita.cierre, "")
        self.assertIsNone(visita.abierta_en)

    def test_codigo_de_foto_se_genera_y_es_unico(self):
        revision = crear_revision(crear_visita())
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            primera = Foto.objects.create(revision=revision, imagen=imagen_real())
            segunda = Foto.objects.create(revision=revision, imagen=imagen_real("blue"))
        self.assertIsInstance(primera.codigo, UUID)
        self.assertNotEqual(primera.codigo, segunda.codigo)
        segunda.codigo = primera.codigo
        with self.assertRaises(IntegrityError), transaction.atomic():
            segunda.save()
