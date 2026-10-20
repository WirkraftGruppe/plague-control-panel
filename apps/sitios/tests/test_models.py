import io
import shutil
import tempfile

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from PIL import Image

from apps.clientes.models import Cliente
from apps.sitios import services
from apps.sitios.models import Plano, PuntoControl, Sitio


class SitioTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")

    def _sitio(self, nombre, **extra):
        return Sitio.objects.create(cliente=self.cliente, nombre=nombre, **extra)

    def test_sitio_ya_no_tiene_qr_propio(self):
        for campo in ("qr_codigo", "qr_impreso_el"):
            for modelo in (Sitio, Sitio.history.model):
                with self.assertRaises(FieldDoesNotExist):
                    modelo._meta.get_field(campo)

    def test_historial_registra_cambios(self):
        sitio = self._sitio("Planta 1")
        sitio.nombre = "Planta Norte"
        sitio.save()
        self.assertEqual(sitio.history.count(), 2)

    def test_historial_no_guarda_contacto_ni_telefono(self):
        modelo = Sitio.history.model
        for campo in ("contacto_en_sitio", "telefono_en_sitio"):
            with self.assertRaises(FieldDoesNotExist):
                modelo._meta.get_field(campo)


class PuntoControlTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")

    def test_qr_unico_y_sitio_inactivo_desactiva_puntos(self):
        uno = PuntoControl.objects.create(sitio=self.sitio, nombre="Depósito", orden=1)
        dos = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=2)
        self.assertNotEqual(uno.qr_codigo, dos.qr_codigo)
        self.assertIs(PuntoControl._meta.get_field("qr_codigo").editable, False)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PuntoControl.objects.create(
                    sitio=self.sitio, nombre="Copia", qr_codigo=uno.qr_codigo
                )
        self.sitio.activo = False
        self.sitio.save()
        self.assertFalse(self.sitio.puntos.filter(activo=True).exists())
        self.assertEqual(self.sitio.puntos.count(), 3)

    def test_sitio_nuevo_recibe_punto_general_con_qr_propio(self):
        general = self.sitio.puntos.get()
        self.assertEqual(general.nombre, "General")
        self.assertEqual(general.orden, 0)
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        self.assertNotEqual(general.qr_codigo, otro.puntos.get().qr_codigo)
        self.sitio.nombre = "Planta Norte"
        self.sitio.save()
        self.assertEqual(self.sitio.puntos.count(), 1)

    def test_reemplazar_foto_borra_la_anterior(self):
        media = tempfile.mkdtemp(prefix="sitios-modelo-test-")
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        buffer = io.BytesIO()
        Image.new("RGB", (30, 30), "red").save(buffer, "PNG")
        with override_settings(MEDIA_ROOT=media):
            punto = self.sitio.puntos.get()
            punto.foto = SimpleUploadedFile("a.png", buffer.getvalue())
            punto.save()
            almacenamiento, anterior = punto.foto.storage, punto.foto.name
            punto.foto = SimpleUploadedFile("b.png", buffer.getvalue())
            with self.captureOnCommitCallbacks(execute=True):
                punto.save()
            self.assertNotEqual(punto.foto.name, anterior)
            self.assertFalse(almacenamiento.exists(anterior))
            self.assertTrue(almacenamiento.exists(punto.foto.name))
            nombre = punto.foto.name
            with self.captureOnCommitCallbacks(execute=True):
                punto.nombre = "Entrada"
                punto.save()
            self.assertTrue(almacenamiento.exists(nombre))

    def test_no_desactiva_el_ultimo_punto_y_reactivar_sitio_reactiva(self):
        general = self.sitio.puntos.get()
        with self.assertRaises(ValidationError):
            services.desactivar_punto(general)
        general.refresh_from_db()
        self.assertTrue(general.activo)
        cocina = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        deposito = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Depósito", orden=2
        )
        services.desactivar_punto(deposito)
        self.sitio.activo = False
        self.sitio.save()
        self.assertFalse(self.sitio.puntos.filter(activo=True).exists())
        self.sitio.activo = True
        self.sitio.save()
        general.refresh_from_db()
        cocina.refresh_from_db()
        deposito.refresh_from_db()
        self.assertTrue(general.activo)
        self.assertTrue(cocina.activo)
        self.assertFalse(deposito.activo, "Lo apagó una persona, no el sitio")
        self.assertEqual(
            cocina.history.first().history_change_reason, "Sitio reactivado"
        )
        self.assertEqual(
            deposito.history.first().history_change_reason, "Punto desactivado"
        )

    def test_clean_rechaza_activo_en_sitio_inactivo_y_plano_ajeno(self):
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        plano = Plano(sitio=otro, nombre="Planta baja")
        plano.ancho_px = plano.alto_px = 10
        Plano.objects.bulk_create([plano])
        punto = PuntoControl(sitio=self.sitio, nombre="Techo", plano=plano)
        with self.assertRaises(ValidationError) as error:
            punto.clean()
        self.assertIn("plano", error.exception.message_dict)
        Sitio.objects.filter(pk=self.sitio.pk).update(activo=False)
        self.sitio.refresh_from_db()
        punto = PuntoControl(sitio=self.sitio, nombre="Techo", activo=True)
        with self.assertRaises(ValidationError) as error:
            punto.clean()
        self.assertIn("activo", error.exception.message_dict)
