import shutil
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import mock
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connection, models
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla
from apps.sitios.models import PuntoControl
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita
from apps.visitas.services import (
    MAX_FOTOS,
    MAX_PRODUCTOS,
    RevisionDuplicada,
    VisitaNoEncontrada,
    VisitaYaCerrada,
    _cargar_proyecto,
    abrir_visita,
    cerrar_visita,
    registrar_revision,
    registrar_visita_manual,
)
from apps.visitas.tests.test_models import crear_revision, crear_visita, punto_de

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-test-")
COORDENADAS = {"latitud": Decimal("-35.1"), "longitud": Decimal("-57.7")}


def abrir(*, empleado, proyecto, **extra):
    """`abrir_visita` con el QR del punto General del sitio (el empleado lo escaneó)."""
    qr = proyecto.sitio.puntos.get(orden=0).qr_codigo
    extra.setdefault("qr_codigo", qr)
    return abrir_visita(empleado=empleado, proyecto=proyecto, **extra)


def jpeg_chico():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("f.jpg", buffer.getvalue(), content_type="image/jpeg")


def abierta(**extra):
    """Visita abierta (manual por defecto, para no exigir QR) y su punto General."""
    datos = {
        "origen": Visita.Origen.MANUAL,
        "motivo_manual": "Carga",
        "estado": Visita.Estado.ABIERTA,
        "abierta_en": timezone.now() - timedelta(hours=1),
    }
    datos.update(extra)
    return crear_visita(**datos)


@contextmanager
def espiar_bloqueos():
    """Lista, en orden, los modelos sobre los que se pide `select_for_update`.

    SQLite no emite `FOR UPDATE`, así que el orden de bloqueo se comprueba así.
    """
    modelos = []
    original = models.QuerySet.select_for_update

    def espia(self, *args, **kwargs):
        modelos.append(self.model)
        return original(self, *args, **kwargs)

    with mock.patch.object(models.QuerySet, "select_for_update", espia):
        yield modelos


@contextmanager
def espiar_bloqueos_con_argumentos():
    """Lista `(modelo, kwargs)` de cada `select_for_update`, en orden."""
    pedidos = []
    original = models.QuerySet.select_for_update

    def espia(self, *args, **kwargs):
        pedidos.append((self.model, kwargs))
        return original(self, *args, **kwargs)

    with mock.patch.object(models.QuerySet, "select_for_update", espia):
        yield pedidos


class SinArchivosMixin:
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CicloVisitaTests(SinArchivosMixin, TestCase):
    """Abrir, revisar y cerrar: el flujo de la jornada."""

    def setUp(self):
        self.visita = crear_visita(programada_para=date(2026, 9, 1))
        self.empleado = self.visita.empleado
        self.proyecto = self.visita.proyecto
        self.punto = punto_de(self.visita)
        self.producto = Producto.objects.create(nombre_comercial="Cebo")

    def revisar(self, visita, **extra):
        argumentos = {
            "visita": visita,
            "empleado": self.empleado,
            "qr_codigo": self.punto.qr_codigo,
            "cliente_uuid": uuid4(),
            "realizada_en": timezone.now() - timedelta(minutes=5),
            "latitud": Decimal("-35.1"),
            "longitud": Decimal("-57.7"),
            "precision_m": Decimal("8.5"),
            "datos": {},
            "productos_aplicados": [],
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_revision(**argumentos)

    def test_revision_sin_coordenadas_se_rechaza(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        for campo in ("latitud", "longitud"):
            with self.subTest(campo=campo):
                with self.assertRaises(ValidationError) as contexto:
                    self.revisar(visita, **{campo: None})
                self.assertEqual(
                    contexto.exception.message_dict[campo],
                    ["Este campo es obligatorio."],
                )
        self.assertEqual(visita.revisiones.count(), 0)

    def test_abrir_revisar_cerrar_actualiza_proyecto(self):
        self.proyecto.frecuencia_dias = 30
        self.proyecto.save()
        visita, creada = abrir(empleado=self.empleado, proyecto=self.proyecto)
        # Abre la pendiente asignada: no crea otra visita.
        self.assertTrue(creada)
        self.assertEqual(visita.pk, self.visita.pk)
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        self.assertIsNotNone(visita.abierta_en)
        item = {
            "producto": self.producto.pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad_dosis": "ml/l",
            "cantidad": "1",
            "unidad": "unidad",
        }
        revision = self.revisar(visita, productos_aplicados=[item])
        self.assertEqual(revision.orden, 1)
        self.assertEqual(revision.punto, self.punto)
        self.assertEqual(revision.fotos.count(), 1)
        self.assertEqual(revision.productos.get().lote, "L1")
        # Hasta cerrar, el proyecto no cambia.
        self.proyecto.refresh_from_db()
        self.assertIsNone(self.proyecto.proxima_visita)

        cerrada = cerrar_visita(
            visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        self.assertEqual(cerrada.estado, Visita.Estado.REALIZADA)
        self.assertEqual(cerrada.cierre, Visita.Cierre.EMPLEADO)
        self.assertEqual(cerrada.realizada_en, cerrada.cerrada_en)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.encargado_actual, self.empleado)
        self.assertEqual(
            self.proyecto.proxima_visita,
            timezone.localdate(cerrada.cerrada_en) + timedelta(days=30),
        )

    def test_abrir_es_idempotente_y_crea_con_incidencia_si_la_pendiente_es_ajena(self):
        otro = User.objects.create_user(
            username="emp-b", password="x", rol=User.Rol.EMPLEADO
        )
        self.visita.empleado = otro
        self.visita.save()
        visita, creada = abrir(empleado=self.empleado, proyecto=self.proyecto)
        self.assertTrue(creada)
        self.assertNotEqual(visita.pk, self.visita.pk)
        self.assertTrue(visita.incidencia_asignacion)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, Visita.Estado.PENDIENTE)
        otra, creada = abrir(empleado=self.empleado, proyecto=self.proyecto)
        self.assertFalse(creada)
        self.assertEqual(otra.pk, visita.pk)
        self.assertEqual(Visita.objects.count(), 2)

    def test_abrir_rechaza_proyecto_o_sitio_inactivo(self):
        self.proyecto.estado = Proyecto.Estado.PAUSADO
        self.proyecto.save()
        with self.assertRaises(ValidationError) as contexto:
            abrir(empleado=self.empleado, proyecto=self.proyecto)
        self.assertIn("proyecto", contexto.exception.message_dict)
        self.proyecto.estado = Proyecto.Estado.ACTIVO
        self.proyecto.save()
        sitio = self.proyecto.sitio
        sitio.activo = False
        sitio.save()
        with self.assertRaises(ValidationError):
            abrir(empleado=self.empleado, proyecto=self.proyecto)

    def test_revision_exige_punto_activo_coordenadas_y_foto(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        casos = {
            "latitud": {"latitud": Decimal("90.1")},
            "longitud": {"longitud": Decimal("-181")},
            "fotos": {"fotos": []},
            "fotos_de_mas": {"fotos": [jpeg_chico() for _ in range(MAX_FOTOS + 1)]},
        }
        for nombre, extra in casos.items():
            with self.subTest(nombre):
                with self.assertRaises(ValidationError) as contexto:
                    self.revisar(visita, **extra)
                self.assertIn(nombre.split("_")[0], contexto.exception.message_dict)
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Foto.objects.count(), 0)

        self.punto.activo = False
        self.punto.save()
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita)
        self.assertIn("qr_codigo", contexto.exception.message_dict)
        self.assertEqual(Revision.objects.count(), 0)

    def test_revision_exige_visita_abierta_y_propia(self):
        pendiente = crear_visita()
        otro = User.objects.create_user(
            username="emp-c", password="x", rol=User.Rol.EMPLEADO
        )
        propia = abierta()
        for nombre, visita, empleado in (
            ("pendiente", pendiente, pendiente.empleado),
            ("ajena", propia, otro),
        ):
            with self.subTest(nombre):
                with self.assertRaises(ValidationError) as contexto:
                    registrar_revision(
                        visita=visita,
                        empleado=empleado,
                        qr_codigo=punto_de(visita).qr_codigo,
                        cliente_uuid=uuid4(),
                        realizada_en=timezone.now(),
                        datos={},
                        productos_aplicados=[],
                        fotos=[jpeg_chico()],
                        precision_m=None,
                        **COORDENADAS,
                    )
                self.assertIn("visita", contexto.exception.message_dict)
        self.assertEqual(Revision.objects.count(), 0)

    def test_mismo_punto_dos_veces_la_ultima_manda(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        primera = self.revisar(visita, realizada_en=timezone.now() - timedelta(hours=2))
        segunda = self.revisar(visita, realizada_en=timezone.now() - timedelta(hours=1))
        self.assertEqual((primera.orden, segunda.orden), (1, 2))
        self.assertEqual(visita.revisiones.filter(punto=self.punto).count(), 2)
        cerrada = cerrar_visita(
            visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        ultima = cerrada.revisiones.order_by("-realizada_en", "-id").first()
        self.assertEqual(ultima.pk, segunda.pk)
        # Con cierre por sistema, la hora de cierre es la de la última revisión.
        otra = abierta(abierta_en=timezone.now() - timedelta(days=1))
        crear_revision(otra, realizada_en=timezone.now() - timedelta(hours=20))
        ultima_otra = crear_revision(
            otra, realizada_en=timezone.now() - timedelta(hours=18)
        )
        cerrada_otra = cerrar_visita(otra, quien=None, cierre=Visita.Cierre.SISTEMA)
        self.assertEqual(cerrada_otra.cerrada_en, ultima_otra.realizada_en)

    def test_revision_fija_ubicacion_solo_sin_coordenadas_y_precisa(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        # Precisión mala: no fija.
        self.revisar(visita, precision_m=Decimal("80"))
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.latitud)
        # Sin precisión informada: no fija.
        self.revisar(visita, precision_m=None)
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.latitud)
        # Precisa: fija las coordenadas de la revisión.
        self.revisar(visita, precision_m=Decimal("12.5"))
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.latitud, Decimal("-35.100000"))
        self.assertEqual(self.punto.longitud, Decimal("-57.700000"))
        # Ya fijadas: otro escaneo preciso no las mueve.
        self.revisar(
            visita,
            precision_m=Decimal("5"),
            latitud=Decimal("-36"),
            longitud=Decimal("-58"),
        )
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.latitud, Decimal("-35.100000"))
        self.assertEqual(self.punto.longitud, Decimal("-57.700000"))

    def test_qr_de_otro_sitio_se_rechaza(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        otro_sitio = crear_visita().proyecto.sitio
        ajeno = PuntoControl.objects.filter(sitio=otro_sitio).first()
        for nombre, codigo in (
            ("de otro sitio", ajeno.qr_codigo),
            ("inexistente", uuid4()),
            ("no es un uuid", "basura"),
        ):
            with self.subTest(nombre):
                with self.assertRaises(ValidationError) as contexto:
                    self.revisar(visita, qr_codigo=codigo)
                self.assertEqual(
                    contexto.exception.message_dict["qr_codigo"],
                    ["El código QR no corresponde a este proyecto."],
                )
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Foto.objects.count(), 0)

    def test_cliente_uuid_repetido_levanta_revision_duplicada(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        codigo = uuid4()
        primera = self.revisar(visita, cliente_uuid=codigo)
        with self.assertRaises(RevisionDuplicada) as contexto:
            self.revisar(visita, cliente_uuid=codigo)
        self.assertEqual(contexto.exception.revision.pk, primera.pk)
        self.assertEqual(Revision.objects.count(), 1)
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, cliente_uuid=None)
        self.assertIn("cliente_uuid", contexto.exception.message_dict)

    def test_atraso_y_futuro_se_rechazan(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        horas = 169
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, realizada_en=timezone.now() - timedelta(hours=horas))
        self.assertIn("168", str(contexto.exception.message_dict["realizada_en"]))
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, realizada_en=timezone.now() + timedelta(hours=1))
        self.assertIn("realizada_en", contexto.exception.message_dict)

    def test_foto_invalida_revierte_la_revision_y_borra_archivos(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        previos = set(Path(MEDIA_TEMPORAL).glob("visitas/fotos/*"))
        basura = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, fotos=[jpeg_chico(), basura])
        self.assertIn("fotos", contexto.exception.message_dict)
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(set(Path(MEDIA_TEMPORAL).glob("visitas/fotos/*")), previos)

    def test_planilla_de_punto_se_valida_y_se_copia_el_esquema(self):
        campo = CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=2,
            etiqueta="Resumen",
            clave="resumen",
            tipo=CampoPlanilla.Tipo.TEXTO,
            ambito=CampoPlanilla.Ambito.VISITA,
        )
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, datos={"resumen": "x"})
        self.assertIn("datos", contexto.exception.message_dict)
        revision = self.revisar(visita, datos={"cebos": 3})
        self.assertEqual([c["clave"] for c in revision.esquema_planilla], ["cebos"])
        campo.etiqueta = "Otra"
        campo.save()
        revision.refresh_from_db()
        self.assertEqual(revision.esquema_planilla[0]["etiqueta"], "Cebos")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CerrarVisitaTests(SinArchivosMixin, TestCase):
    def setUp(self):
        self.ahora = timezone.now()

    def con_revision(self, **extra):
        visita = abierta(**extra)
        crear_revision(visita, realizada_en=self.ahora - timedelta(minutes=30))
        return visita

    def otro_empleado(self):
        return User.objects.create_user(
            username="emp-otro", password="x", rol=User.Rol.EMPLEADO
        )

    def test_sin_frecuencia_no_toca_proxima_visita(self):
        visita = self.con_revision()
        proyecto = visita.proyecto
        proyecto.proxima_visita = date(2027, 1, 1)
        proyecto.save()
        cerrar_visita(visita, quien=visita.empleado, cierre=Visita.Cierre.EMPLEADO)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.proxima_visita, date(2027, 1, 1))

    def test_revisiones_anteriores_a_la_apertura_no_cuentan(self):
        visita = abierta(abierta_en=self.ahora - timedelta(minutes=10))
        crear_revision(
            visita,
            realizada_en=self.ahora - timedelta(days=3),
            recibida_en=self.ahora - timedelta(days=3),
        )
        with self.assertRaises(ValidationError):
            cerrar_visita(visita, quien=visita.empleado, cierre=Visita.Cierre.EMPLEADO)
        sistema = cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
        self.assertEqual(sistema.estado, Visita.Estado.CANCELADA)

    def test_revision_diferida_recibida_en_la_jornada_cuenta(self):
        punto = punto_de(crear_visita())
        proyecto = punto.sitio.proyectos.get()
        empleado = proyecto.encargado_actual
        visita, _ = abrir(empleado=empleado, proyecto=proyecto)
        registrar_revision(
            visita=visita,
            empleado=empleado,
            qr_codigo=punto.qr_codigo,
            cliente_uuid=uuid4(),
            realizada_en=timezone.now() - timedelta(hours=2),
            latitud=Decimal("-35.1"),
            longitud=Decimal("-57.7"),
            precision_m=None,
            datos={},
            productos_aplicados=[],
            fotos=[jpeg_chico()],
        )
        cerrada = cerrar_visita(visita, quien=empleado, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(cerrada.estado, Visita.Estado.REALIZADA)

    def test_exige_al_menos_una_revision(self):
        visita = abierta()
        with self.assertRaises(ValidationError):
            cerrar_visita(visita, quien=visita.empleado, cierre=Visita.Cierre.EMPLEADO)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)

    def test_exige_quien_corresponde_al_tipo_de_cierre(self):
        visita = self.con_revision()
        admin = User.objects.create_user(
            username="admin-svc", password="x", rol=User.Rol.ADMINISTRADOR
        )
        for quien, cierre in (
            (self.otro_empleado(), Visita.Cierre.EMPLEADO),
            (None, Visita.Cierre.EMPLEADO),
            (visita.empleado, Visita.Cierre.ADMINISTRADOR),
            (admin, "otro"),
        ):
            with self.subTest(cierre=cierre):
                with self.assertRaises(ValidationError):
                    cerrar_visita(visita, quien=quien, cierre=cierre)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        cerrada = cerrar_visita(visita, quien=admin, cierre=Visita.Cierre.ADMINISTRADOR)
        self.assertEqual(cerrada.cierre, Visita.Cierre.ADMINISTRADOR)

    def test_origen_manual_exige_motivo(self):
        visita = self.con_revision(motivo_manual="   ")
        with self.assertRaises(ValidationError):
            cerrar_visita(visita, quien=visita.empleado, cierre=Visita.Cierre.EMPLEADO)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        visita.motivo_manual = "Sin señal en el sitio"
        visita.save()
        cerrar_visita(visita, quien=visita.empleado, cierre=Visita.Cierre.EMPLEADO)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_planilla_de_visita_se_valida_y_se_guarda_con_copia_del_esquema(self):
        visita = self.con_revision()
        campo = CampoPlanilla.objects.create(
            tipo_servicio=visita.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Resumen",
            clave="resumen",
            tipo=CampoPlanilla.Tipo.TEXTO,
            obligatorio=True,
            ambito=CampoPlanilla.Ambito.VISITA,
        )
        quien = visita.empleado
        with self.assertRaises(ValidationError) as contexto:
            cerrar_visita(visita, quien=quien, cierre=Visita.Cierre.EMPLEADO)
        self.assertIn("datos", contexto.exception.message_dict)
        cerrar_visita(
            visita,
            quien=quien,
            cierre=Visita.Cierre.EMPLEADO,
            datos={"resumen": "Todo bien"},
            observaciones="Sin novedades",
        )
        visita.refresh_from_db()
        self.assertEqual(visita.datos, {"resumen": "Todo bien"})
        self.assertEqual(visita.observaciones, "Sin novedades")
        self.assertEqual(visita.esquema_planilla[0]["clave"], "resumen")
        campo.etiqueta = "Otra"
        campo.save()
        visita.refresh_from_db()
        self.assertEqual(visita.esquema_planilla[0]["etiqueta"], "Resumen")

    def test_rechaza_visita_no_abierta(self):
        visita = crear_visita(
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
            estado=Visita.Estado.CANCELADA,
        )
        with self.assertRaises(ValidationError):
            cerrar_visita(visita, quien=visita.empleado, cierre=Visita.Cierre.EMPLEADO)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.CANCELADA)

    def test_doble_cierre_con_lecturas_distintas(self):
        creada = self.con_revision()
        primera = Visita.objects.get(pk=creada.pk)
        segunda = Visita.objects.get(pk=creada.pk)
        cerrada = cerrar_visita(
            primera, quien=primera.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        # El mismo empleado cierra de nuevo: idempotente, no cambia nada.
        repetida = cerrar_visita(
            segunda, quien=segunda.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        self.assertEqual(repetida.cerrada_en, cerrada.cerrada_en)
        # Si la había cerrado un administrador, el empleado no la cierra.
        Visita.objects.filter(pk=creada.pk).update(cierre=Visita.Cierre.ADMINISTRADOR)
        with self.assertRaises(VisitaYaCerrada):
            cerrar_visita(
                segunda, quien=segunda.empleado, cierre=Visita.Cierre.EMPLEADO
            )
        creada.refresh_from_db()
        self.assertEqual(creada.estado, Visita.Estado.REALIZADA)

    def test_visita_atrasada_no_retrocede_el_proyecto(self):
        reciente = self.con_revision()
        proyecto = reciente.proyecto
        proyecto.frecuencia_dias = 30
        proyecto.save()
        atrasada = Visita.objects.create(
            proyecto=proyecto,
            empleado=self.otro_empleado(),
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga tardía",
            estado=Visita.Estado.ABIERTA,
            abierta_en=self.ahora - timedelta(days=11),
        )
        crear_revision(atrasada, realizada_en=self.ahora - timedelta(days=10))
        cerrar_visita(
            reciente,
            quien=reciente.empleado,
            cierre=Visita.Cierre.EMPLEADO,
            cerrada_en=self.ahora,
        )
        cerrar_visita(
            atrasada,
            quien=atrasada.empleado,
            cierre=Visita.Cierre.EMPLEADO,
            cerrada_en=self.ahora - timedelta(days=10),
        )
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual, reciente.empleado)
        self.assertEqual(
            proyecto.proxima_visita,
            timezone.localdate(self.ahora) + timedelta(days=30),
        )
        atrasada.refresh_from_db()
        self.assertEqual(atrasada.estado, Visita.Estado.REALIZADA)

    def test_rechaza_cierre_futuro(self):
        visita = self.con_revision()
        with self.assertRaises(ValidationError):
            cerrar_visita(
                visita,
                quien=visita.empleado,
                cierre=Visita.Cierre.EMPLEADO,
                cerrada_en=timezone.now() + timedelta(hours=1),
            )
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        self.assertIsNone(visita.cerrada_en)

    def test_falla_de_validacion_no_muta_la_instancia(self):
        visita = self.con_revision()
        admin = User.objects.create_user(
            username="admin-svc2", password="x", rol=User.Rol.ADMINISTRADOR
        )
        empleado_original = visita.empleado
        with self.assertRaises(ValidationError):
            cerrar_visita(visita, quien=admin, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        self.assertEqual(visita.empleado, empleado_original)
        self.assertIsNone(visita.cerrada_en)

    def test_cierre_por_sistema_sin_revisiones_no_toca_el_proyecto(self):
        asignada = abierta(asignada_por=self.otro_empleado())
        propia = abierta(origen=Visita.Origen.APP, motivo_manual="")
        for visita in (asignada, propia):
            proyecto = visita.proyecto
            antes = (proyecto.encargado_actual_id, proyecto.proxima_visita)
            cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
            proyecto.refresh_from_db()
            self.assertEqual(
                (proyecto.encargado_actual_id, proyecto.proxima_visita), antes
            )
        asignada.refresh_from_db()
        propia.refresh_from_db()
        self.assertEqual(asignada.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(asignada.abierta_en)
        self.assertEqual(propia.estado, Visita.Estado.CANCELADA)
        self.assertEqual(propia.cierre, Visita.Cierre.SISTEMA)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class AdministradorEnCampoTests(SinArchivosMixin, TestCase):
    """La visita de un administrador no cuenta como servicio."""

    def setUp(self):
        self.pendiente = crear_visita(programada_para=date(2026, 9, 1))
        self.proyecto = self.pendiente.proyecto
        self.proyecto.frecuencia_dias = 30
        self.proyecto.save()
        self.empleado = self.pendiente.empleado
        self.admin = User.objects.create_user(
            username="adm-campo", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def test_no_toma_pendiente_ni_toca_el_proyecto(self):
        propia = crear_visita(proyecto=self.proyecto, empleado=self.admin)
        visita, creada = abrir(empleado=self.admin, proyecto=self.proyecto)
        self.assertTrue(creada)
        self.assertNotIn(visita.pk, (self.pendiente.pk, propia.pk))
        self.assertFalse(visita.incidencia_asignacion)
        for pendiente in (self.pendiente, propia):
            pendiente.refresh_from_db()
            self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)
        crear_revision(visita, realizada_en=timezone.now() - timedelta(minutes=5))
        cerrada = cerrar_visita(visita, quien=self.admin, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(cerrada.estado, Visita.Estado.REALIZADA)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.encargado_actual, self.empleado)
        self.assertIsNone(self.proyecto.proxima_visita)

    def test_visita_posterior_de_administrador_no_anula_el_servicio(self):
        """El empleado no cierra; el administrador visita después; el cron cierra."""
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        crear_revision(visita, realizada_en=timezone.now() - timedelta(hours=3))
        de_admin, _ = abrir(empleado=self.admin, proyecto=self.proyecto)
        crear_revision(de_admin)
        cerrar_visita(de_admin, quien=self.admin, cierre=Visita.Cierre.EMPLEADO)
        otro = User.objects.create_user(
            username="otro-emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.proyecto.encargado_actual = otro
        self.proyecto.save()
        cerrada = cerrar_visita(visita, quien=self.admin, cierre=Visita.Cierre.SISTEMA)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.encargado_actual, self.empleado)
        self.assertEqual(
            self.proyecto.proxima_visita,
            timezone.localdate(cerrada.cerrada_en) + timedelta(days=30),
        )


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ManualPorPuntosTests(SinArchivosMixin, TestCase):
    def setUp(self):
        self.pendiente = crear_visita(programada_para=date(2026, 9, 1))
        self.empleado = self.pendiente.empleado
        self.proyecto = self.pendiente.proyecto
        self.admin = User.objects.create_user(
            username="admin-man", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.general = punto_de(self.pendiente)
        self.sala = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Sala", orden=1
        )
        self.techo = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Techo", orden=2
        )
        self.producto = Producto.objects.create(nombre_comercial="Cebo")
        self.fecha = timezone.now() - timedelta(hours=3)
        # Las cargas son anteriores a hoy: el proyecto ya existía.
        Proyecto.objects.filter(pk=self.proyecto.pk).update(
            creado=timezone.now() - timedelta(days=60)
        )
        self.proyecto.refresh_from_db()

    def cargar(self, **extra):
        argumentos = {
            "proyecto": self.proyecto,
            "empleado": self.empleado,
            "administrador": self.admin,
            "motivo": "Sin señal",
            "realizada_en": self.fecha,
            "puntos": [self.techo, self.general, self.sala],
            "datos": {},
            "productos_aplicados": [],
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_visita_manual(**argumentos)

    def test_hora_futura_se_rechaza_en_el_campo(self):
        with self.assertRaises(ValidationError) as ctx:
            self.cargar(realizada_en=timezone.now() + timedelta(minutes=20))
        self.assertEqual(
            ctx.exception.message_dict["realizada_en"],
            ["La fecha y hora de la visita no puede ser posterior a la hora actual."],
        )
        self.assertEqual(Visita.objects.count(), 1)
        # Dentro de la tolerancia de 10 minutos se acepta.
        self.cargar(realizada_en=timezone.now() + timedelta(minutes=5))

    def test_crea_una_revision_por_punto(self):
        item = {
            "producto": self.producto.pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad_dosis": "ml/l",
            "cantidad": "1",
            "unidad": "unidad",
        }
        CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )
        visita = self.cargar(
            datos={"cebos": 2}, productos_aplicados=[item], pendiente=self.pendiente
        )
        self.assertEqual(visita.pk, self.pendiente.pk)
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.cierre, Visita.Cierre.ADMINISTRADOR)
        self.assertEqual(visita.origen, Visita.Origen.MANUAL)
        self.assertEqual(visita.cerrada_en, self.fecha)
        self.assertEqual(visita.abierta_en, self.fecha)
        revisiones = list(visita.revisiones.all())
        # Una por punto, ordenadas por `orden` del punto.
        self.assertEqual(
            [r.punto for r in revisiones], [self.general, self.sala, self.techo]
        )
        self.assertTrue(all(r.datos == {"cebos": 2} for r in revisiones))
        self.assertTrue(all(r.realizada_en == self.fecha for r in revisiones))
        # Fotos y productos quedan en la revisión del primer punto.
        self.assertEqual(revisiones[0].fotos.count(), 1)
        self.assertEqual(revisiones[0].productos.count(), 1)
        self.assertEqual(Foto.objects.count(), 1)
        self.assertEqual(ProductoAplicado.objects.count(), 1)
        self.proyecto.refresh_from_db()
        self.assertEqual(self.proyecto.encargado_actual, self.empleado)

    def test_exige_puntos_activos_del_sitio_y_motivo(self):
        ajeno = punto_de(crear_visita())
        inactivo = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Viejo", orden=3, activo=False
        )
        for nombre, extra, campo in (
            ("sin puntos", {"puntos": []}, "puntos"),
            ("de otro sitio", {"puntos": [ajeno]}, "puntos"),
            ("inactivo", {"puntos": [inactivo]}, "puntos"),
            ("sin motivo", {"motivo": "  "}, "motivo"),
        ):
            with self.subTest(nombre):
                with self.assertRaises(ValidationError) as contexto:
                    self.cargar(**extra)
                self.assertIn(campo, contexto.exception.message_dict)
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Foto.objects.count(), 0)

    def test_atraso_exige_confirmacion_y_queda_en_el_historial(self):
        vieja = timezone.now() - timedelta(hours=200)
        with self.assertRaises(ValidationError) as contexto:
            self.cargar(realizada_en=vieja)
        self.assertIn("confirmar_atraso", contexto.exception.message_dict)
        visita = self.cargar(realizada_en=vieja, confirmar_atraso=True)
        ultimo = visita.history.first()
        self.assertIn("atrasada", ultimo.history_change_reason)

    def test_error_revierte_todo_y_borra_archivos(self):
        previos = set(Path(MEDIA_TEMPORAL).glob("visitas/fotos/*"))
        basura = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        with self.assertRaises(ValidationError) as contexto:
            self.cargar(fotos=[jpeg_chico(), basura])
        self.assertIn("fotos", contexto.exception.message_dict)
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Visita.objects.count(), 1)
        self.assertEqual(set(Path(MEDIA_TEMPORAL).glob("visitas/fotos/*")), previos)
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.estado, Visita.Estado.PENDIENTE)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class RegistrarRevisionTests(SinArchivosMixin, TestCase):
    """`registrar_revision` sobre una visita abierta: reemplaza a la envoltura vieja."""

    def setUp(self):
        pendiente = crear_visita(programada_para=date(2026, 9, 1))
        self.empleado = pendiente.empleado
        self.proyecto = pendiente.proyecto
        self.punto = punto_de(pendiente)
        self.visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        self.producto = Producto.objects.create(nombre_comercial="Cebo")
        self.archivos_previos = self.archivos_en_disco()

    def archivos_en_disco(self):
        return set(Path(MEDIA_TEMPORAL).glob("visitas/fotos/*"))

    def registrar(self, **extra):
        argumentos = {
            "visita": self.visita,
            "empleado": self.empleado,
            "qr_codigo": self.punto.qr_codigo,
            "cliente_uuid": uuid4(),
            "realizada_en": timezone.now() - timedelta(minutes=5),
            "latitud": Decimal("-35.1"),
            "longitud": Decimal("-57.7"),
            "precision_m": Decimal("8.5"),
            "datos": {},
            "productos_aplicados": [],
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_revision(**argumentos)

    def assertNadaCreado(self):
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(Foto.objects.count(), 0)
        self.assertEqual(ProductoAplicado.objects.count(), 0)
        self.assertEqual(self.archivos_en_disco(), self.archivos_previos)

    def item_valido(self, producto=None):
        return {
            "producto": (producto or self.producto).pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad_dosis": "ml/l",
            "cantidad": "1",
            "unidad": "unidad",
        }

    def test_abrir_limpia_motivo_manual_de_la_pendiente(self):
        pendiente = crear_visita(
            origen=Visita.Origen.MANUAL, motivo_manual="Carga a mano"
        )
        visita, _ = abrir(empleado=pendiente.empleado, proyecto=pendiente.proyecto)
        self.assertEqual(visita.pk, pendiente.pk)
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertEqual(visita.motivo_manual, "")

    def test_abrir_sin_pendiente_crea_nueva_con_origen_app(self):
        otra = crear_visita()
        otra.delete()
        visita, creada = abrir(empleado=otra.empleado, proyecto=otra.proyecto)
        self.assertTrue(creada)
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertFalse(visita.incidencia_asignacion)

    def test_registra_recibida_en_del_servidor(self):
        antes = timezone.now()
        revision = self.registrar(realizada_en=antes - timedelta(days=2))
        self.assertGreaterEqual(revision.recibida_en, antes)
        self.assertLessEqual(revision.recibida_en, timezone.now())
        self.assertLess(revision.realizada_en, revision.recibida_en)

    def test_qr_de_otro_punto_activo_del_sitio_sirve(self):
        sala = PuntoControl.objects.create(sitio=self.proyecto.sitio, nombre="Sala")
        self.assertEqual(self.registrar(qr_codigo=sala.qr_codigo).punto, sala)

    def test_cliente_dado_de_baja_se_rechaza(self):
        cliente = self.proyecto.sitio.cliente
        cliente.activo = False
        cliente.save()
        with self.assertRaises(ValidationError) as contexto:
            self.registrar()
        self.assertEqual(
            contexto.exception.message_dict["qr_codigo"],
            ["El código QR no corresponde a este proyecto."],
        )
        self.assertNadaCreado()

    def test_proyecto_no_activo_se_rechaza(self):
        self.proyecto.estado = Proyecto.Estado.PAUSADO
        self.proyecto.save()
        with self.assertRaises(ValidationError) as contexto:
            self.registrar()
        self.assertIn("proyecto", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_datos_invalidos_no_crean_nada(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(datos={"otro": 1})
        self.assertIn("datos", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_producto_inactivo_se_rechaza(self):
        self.producto.activo = False
        self.producto.save()
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(productos_aplicados=[self.item_valido()])
        self.assertIn("productos_aplicados.0.producto", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_mas_productos_que_el_tope_se_rechaza(self):
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(
                productos_aplicados=[self.item_valido()] * (MAX_PRODUCTOS + 1)
            )
        self.assertIn("productos_aplicados", contexto.exception.message_dict)
        self.assertNadaCreado()

    def test_productos_se_buscan_en_una_consulta(self):
        otro = Producto.objects.create(nombre_comercial="Gel")
        items = [self.item_valido(p) for p in (self.producto, otro, self.producto)]
        with CaptureQueriesContext(connection) as consultas:
            self.registrar(productos_aplicados=items)
        sobre_productos = [
            c["sql"] for c in consultas if 'FROM "productos_producto"' in c["sql"]
        ]
        self.assertEqual(len(sobre_productos), 1, sobre_productos)

    def test_fallo_del_insert_de_foto_no_deja_archivo_huerfano(self):
        guardar = models.Model.save_base

        def falla_en_foto(instancia, *args, **kwargs):
            if isinstance(instancia, Foto):
                raise OperationalError("fallo simulado del INSERT")
            return guardar(instancia, *args, **kwargs)

        with mock.patch.object(models.Model, "save_base", falla_en_foto):
            with self.assertRaises(OperationalError):
                self.registrar()
        self.assertNadaCreado()

    def test_error_al_borrar_no_tapa_la_excepcion_original(self):
        basura = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        with mock.patch(
            "django.core.files.storage.FileSystemStorage.delete",
            side_effect=OSError("no se pudo borrar"),
        ):
            with self.assertRaises(ValidationError) as contexto:
                self.registrar(fotos=[jpeg_chico(), basura])
        self.assertIn("fotos", contexto.exception.message_dict)

    def test_foto_y_coordenadas_invalidas_se_informan_juntas(self):
        with self.assertRaises(ValidationError) as contexto:
            self.registrar(fotos=[], latitud=Decimal("99"))
        self.assertEqual({"fotos", "latitud"}, set(contexto.exception.message_dict))
        self.assertNadaCreado()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BloqueosTests(SinArchivosMixin, TestCase):
    """Orden de bloqueo Proyecto -> Visita y rol fijado al abrir."""

    def setUp(self):
        self.visita = abierta()
        self.proyecto = self.visita.proyecto
        self.empleado = self.visita.empleado

    def test_orden_de_bloqueo_proyecto_visita(self):
        crear_revision(self.visita, realizada_en=timezone.now() - timedelta(minutes=5))
        with espiar_bloqueos() as al_cerrar:
            cerrar_visita(
                self.visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO
            )
        self.assertEqual(al_cerrar, [Proyecto, Visita])
        otro = User.objects.create_user(
            username="emp-bloqueo", password="x", rol=User.Rol.EMPLEADO
        )
        with espiar_bloqueos() as al_abrir:
            abrir(empleado=otro, proyecto=self.proyecto)
        self.assertLess(al_abrir.index(Proyecto), al_abrir.index(Visita))

    def test_manual_bloquea_proyecto_antes_que_pendiente(self):
        pendiente = crear_visita(programada_para=date(2026, 9, 1))
        admin = User.objects.create_user(
            username="adm-orden", password="x", rol=User.Rol.ADMINISTRADOR
        )
        with espiar_bloqueos() as modelos:
            registrar_visita_manual(
                proyecto=pendiente.proyecto,
                empleado=pendiente.empleado,
                administrador=admin,
                motivo="Sin señal",
                realizada_en=timezone.now(),
                puntos=[punto_de(pendiente)],
                datos={},
                productos_aplicados=[],
                fotos=[jpeg_chico()],
                pendiente=pendiente,
            )
        self.assertLess(modelos.index(Proyecto), modelos.index(Visita))

    def test_escaneo_bloquea_punto_sin_clave(self):
        punto = punto_de(self.visita)
        with espiar_bloqueos_con_argumentos() as pedidos:
            registrar_revision(
                visita=self.visita,
                empleado=self.empleado,
                qr_codigo=punto.qr_codigo,
                cliente_uuid=uuid4(),
                realizada_en=timezone.now() - timedelta(minutes=5),
                latitud=Decimal("-35.1"),
                longitud=Decimal("-57.7"),
                precision_m=Decimal("8.5"),
                datos={},
                productos_aplicados=[],
                fotos=[jpeg_chico()],
            )
        self.assertIn((PuntoControl, {"no_key": True}), pedidos)

    def test_pendiente_usada_cuenta_como_servicio(self):
        pendiente = crear_visita(programada_para=date(2026, 9, 1))
        Visita.objects.filter(pk=pendiente.pk).update(cuenta_como_servicio=False)
        visita, _ = abrir(empleado=pendiente.empleado, proyecto=pendiente.proyecto)
        self.assertEqual(visita.pk, pendiente.pk)
        visita.refresh_from_db()
        self.assertTrue(visita.cuenta_como_servicio)

        otra = crear_visita(programada_para=date(2026, 9, 2))
        Visita.objects.filter(pk=otra.pk).update(cuenta_como_servicio=False)
        admin = User.objects.create_user(
            username="adm-cs", password="x", rol=User.Rol.ADMINISTRADOR
        )
        manual = registrar_visita_manual(
            proyecto=otra.proyecto,
            empleado=otra.empleado,
            administrador=admin,
            motivo="Sin señal",
            realizada_en=timezone.now(),
            puntos=[punto_de(otra)],
            datos={},
            productos_aplicados=[],
            fotos=[jpeg_chico()],
            pendiente=otra,
        )
        self.assertEqual(manual.pk, otra.pk)
        manual.refresh_from_db()
        self.assertTrue(manual.cuenta_como_servicio)

    def test_revision_filtra_por_empleado_al_bloquear(self):
        ajeno = User.objects.create_user(
            username="emp-ajeno", password="x", rol=User.Rol.EMPLEADO
        )
        with CaptureQueriesContext(connection) as consultas:
            with self.assertRaises(VisitaNoEncontrada):
                registrar_revision(
                    visita=self.visita,
                    empleado=ajeno,
                    qr_codigo=punto_de(self.visita).qr_codigo,
                    cliente_uuid=uuid4(),
                    realizada_en=timezone.now(),
                    latitud=Decimal("-35.1"),
                    longitud=Decimal("-57.7"),
                    precision_m=None,
                    datos={},
                    productos_aplicados=[],
                    fotos=[jpeg_chico()],
                )
        sobre_visita = [
            c["sql"]
            for c in consultas.captured_queries
            if 'FROM "visitas_visita" WHERE' in c["sql"]
        ]
        self.assertTrue(sobre_visita)
        self.assertIn(
            '"visitas_visita"."empleado_id" =', sobre_visita[0].split("WHERE")[1]
        )

    def test_rol_se_evalua_al_abrir(self):
        proyecto = self.proyecto
        proyecto.frecuencia_dias = 30
        proyecto.save()
        admin = User.objects.create_user(
            username="adm-rol", password="x", rol=User.Rol.ADMINISTRADOR
        )
        de_admin, _ = abrir(empleado=admin, proyecto=proyecto)
        de_empleado, _ = abrir(empleado=self.empleado, proyecto=proyecto)
        self.assertFalse(de_admin.cuenta_como_servicio)
        self.assertTrue(de_empleado.cuenta_como_servicio)
        # El rol cambia después de abrir: el cierre usa el rol de cuando se abrió.
        User.objects.filter(pk=admin.pk).update(rol=User.Rol.EMPLEADO)
        User.objects.filter(pk=self.empleado.pk).update(rol=User.Rol.ADMINISTRADOR)
        for visita in (de_admin, de_empleado):
            crear_revision(visita, realizada_en=timezone.now() - timedelta(minutes=5))
        admin.refresh_from_db()
        self.empleado.refresh_from_db()
        cerrar_visita(de_admin, quien=admin, cierre=Visita.Cierre.EMPLEADO)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual_id, proyecto.encargado_inicial_id)
        self.assertIsNone(proyecto.proxima_visita)
        cerrar_visita(de_empleado, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.encargado_actual, self.empleado)
        self.assertIsNotNone(proyecto.proxima_visita)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class PrecisionTests(SinArchivosMixin, TestCase):
    def test_abrir_guarda_precision_m(self):
        pendiente = crear_visita(programada_para=date(2026, 9, 1))
        proyecto, empleado = pendiente.proyecto, pendiente.empleado
        visita, _ = abrir(
            empleado=empleado, proyecto=proyecto, precision_m=Decimal("8.5")
        )
        self.assertEqual(visita.pk, pendiente.pk)
        visita.refresh_from_db()
        self.assertEqual(visita.precision_m, Decimal("8.50"))
        otro = User.objects.create_user(
            username="emp-prec", password="x", rol=User.Rol.EMPLEADO
        )
        nueva, _ = abrir(empleado=otro, proyecto=proyecto)
        nueva.refresh_from_db()
        self.assertIsNone(nueva.precision_m)
        # Como en Revision, la precisión no entra en el historial.
        campos = {f.name for f in Visita.history.model._meta.get_fields()}
        self.assertNotIn("precision_m", campos)


class EsquemaTests(TestCase):
    def test_cargar_proyecto_prefetchea_campos(self):
        visita = crear_visita()
        CampoPlanilla.objects.create(
            tipo_servicio=visita.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )
        proyecto = _cargar_proyecto(visita.proyecto_id)
        with self.assertNumQueries(0):
            esquema = proyecto.tipo_servicio.esquema_planilla("punto")
            proyecto.tipo_servicio.esquema_planilla("visita")
        self.assertEqual([c["clave"] for c in esquema], ["cebos"])
