"""Pruebas de ``cargar_demo``: datos realistas, recreables y solo con SQLite."""

import os
import shutil
import tempfile
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.apps import apps as django_apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.demo import _es_sqlite
from apps.panel.demo_datos import CLIENTES, MARCA_DEMO
from apps.productos.models import MovimientoStock, Producto
from apps.productos.services import stock
from apps.productos.unidades import magnitud_de, unidades_permitidas
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita
from apps.visitas.planillas import validar_datos

MEDIA_DEMO = tempfile.mkdtemp(prefix="detach-demo-test-")


def _archivos(carpeta):
    return sorted(f for _, _, fs in os.walk(carpeta) for f in fs)


@override_settings(MEDIA_ROOT=MEDIA_DEMO)
class CargarDemoTests(TestCase):
    """Guardas de entorno, cuentas demo y limpieza ante una falla."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_DEMO, ignore_errors=True)

    def _cargar(self):
        call_command("cargar_demo", stdout=StringIO())

    @override_settings(DEBUG=True)
    def test_falla_tardia_no_deja_planos_huerfanos(self):
        with (
            tempfile.TemporaryDirectory() as media,
            override_settings(MEDIA_ROOT=media),
        ):
            ruta = "apps.panel.management.commands.cargar_demo.Command._crear_historia"
            with mock.patch(ruta, side_effect=RuntimeError("falla tardía")):
                with self.assertRaisesMessage(RuntimeError, "falla tardía"):
                    self._cargar()
            self.assertEqual(Plano.objects.count(), 0)
            self.assertEqual(_archivos(media), [])

    @override_settings(DEBUG=False)
    def test_rechaza_sin_debug_y_no_toca_la_base(self):
        with self.assertRaisesMessage(CommandError, "DEBUG activo"):
            self._cargar()
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=True)
    def test_rechaza_entorno_que_no_es_development(self):
        with mock.patch.dict(os.environ, {"DJANGO_ENV": "production"}):
            with self.assertRaisesMessage(CommandError, "DJANGO_ENV=development"):
                self._cargar()
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertFalse(User.objects.exists())

    def test_base_local_rechaza_host_remoto(self):
        postgres = "django.db.backends.postgresql"
        self.assertTrue(_es_sqlite({"ENGINE": "django.db.backends.sqlite3"}))
        self.assertFalse(_es_sqlite({"ENGINE": postgres, "HOST": "db.remoto.com"}))
        self.assertFalse(_es_sqlite({"ENGINE": postgres, "HOST": "localhost"}))
        self.assertFalse(
            _es_sqlite({"ENGINE": postgres, "HOST": "", "OPTIONS": {"host": "remoto"}})
        )
        self._rechaza_con({"ENGINE": postgres, "HOST": "db.remoto.com"})

    def test_rechaza_postgres_local(self):
        postgres = "django.db.backends.postgresql"
        self._rechaza_con({"ENGINE": postgres, "HOST": "localhost"})

    def _rechaza_con(self, configuracion):
        """El comando rechaza esa base con el mensaje de SQLite y sin escribir."""
        falsa = mock.Mock(settings_dict=configuracion)
        ruta = "apps.panel.demo.connection"
        with override_settings(DEBUG=True), mock.patch(ruta, falsa):
            with self.assertRaisesMessage(CommandError, "solo corre contra SQLite"):
                self._cargar()
        self.assertEqual(Cliente.objects.count(), 0)
        self.assertFalse(User.objects.exists())

    @override_settings(DEBUG=True)
    def test_no_carga_contenido_del_sitio_publico(self):
        self.assertNotIn("web", {c.label for c in django_apps.get_app_configs()})
        self._cargar()
        self.assertFalse(
            [t for t in connection.introspection.table_names() if t == "web_pagina"]
        )

    @override_settings(DEBUG=True)
    def test_carga_tipos_de_servicio_si_no_hay(self):
        self.assertFalse(TipoServicio.objects.exists())
        self._cargar()
        self.assertTrue(TipoServicio.objects.filter(slug="servicio-mipu").exists())
        # Con tipos ya cargados, el fixture no vuelve a correr ni pisa nada.
        TipoServicio.objects.filter(slug="servicio-mipu").update(nombre="Del cliente")
        self._cargar()
        self.assertTrue(TipoServicio.objects.filter(nombre="Del cliente").exists())

    @override_settings(DEBUG=True)
    def test_avisa_usuario_demo_existente_sin_modificarlo(self):
        previo = User.objects.create_user(
            "demo-admin", password="otra-clave", rol=User.Rol.EMPLEADO
        )
        salida, errores = StringIO(), StringIO()
        call_command("cargar_demo", stdout=salida, stderr=errores)
        previo.refresh_from_db()
        self.assertEqual(previo.rol, User.Rol.EMPLEADO)
        self.assertTrue(previo.check_password("otra-clave"))
        self.assertIn("demo-admin", errores.getvalue())
        self.assertNotIn("demo-admin", salida.getvalue())
        self.assertIn("demo-empleado", salida.getvalue())


@override_settings(MEDIA_ROOT=MEDIA_DEMO, DEBUG=True)
class CargarDemoClienteTests(TestCase):
    """Contenido, historia, marca y recreación de los datos de la demo."""

    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=StringIO())

    def _cargar(self):
        call_command("cargar_demo", stdout=StringIO())

    def _conteos(self):
        modelos = (
            *(User, Cliente, Sitio, PuntoControl, Plano, Proyecto, Visita),
            *(Revision, Foto, ProductoAplicado, Producto, TipoServicio),
        )
        return {modelo.__name__: modelo.objects.count() for modelo in modelos}

    def test_crea_los_conteos_esperados(self):
        self.assertEqual(Cliente.objects.count(), 4)
        self.assertEqual(Sitio.objects.count(), 6)
        self.assertTrue(20 <= PuntoControl.objects.count() <= 30)
        plano = Plano.objects.get()
        ubicados = plano.puntos.exclude(x=None).exclude(y=None)
        self.assertGreaterEqual(ubicados.count(), 4)
        self.assertGreater(plano.ancho_px, 0)
        self.assertTrue(ProductoAplicado.objects.exists())
        incidencias = Revision.objects.filter(incidencia_ubicacion=True)
        self.assertTrue(2 <= incidencias.count() <= 3)
        self.assertTrue(Visita.objects.filter(incidencia_ubicacion=True).exists())
        for rol in User.Rol.values:
            self.assertEqual(User.objects.filter(rol=rol).count(), 1)
        for revision in Revision.objects.all():
            self.assertGreaterEqual(revision.fotos.count(), 1)
        for sitio in Sitio.objects.all():
            self.assertTrue(sitio.notas.startswith(MARCA_DEMO))
            self.assertEqual(sitio.telefono_en_sitio, "0000-000000")
            self.assertRegex(sitio.direccion, r"^(Ruta 2 km \d+|Calle \d+ s/n)$")
        for cliente in Cliente.objects.all():
            self.assertTrue(cliente.notas.startswith(MARCA_DEMO))
            self.assertEqual((cliente.cuit, cliente.contacto_email), ("", ""))
        nombres = Producto.objects.values_list("nombre_comercial", flat=True)
        self.assertTrue(nombres)
        self.assertTrue(all(nombre.endswith(" (demo)") for nombre in nombres))

    def test_planillas_validas_contra_su_esquema(self):
        for revision in Revision.objects.all():
            errores = validar_datos(revision.esquema_planilla, revision.datos)
            self.assertEqual(errores, {})

    def test_visita_pendiente_coherente_con_el_proyecto(self):
        pendiente = Visita.objects.get(estado=Visita.Estado.PENDIENTE)
        self.assertEqual(pendiente.programada_para, pendiente.proyecto.proxima_visita)
        self.assertGreater(pendiente.programada_para, timezone.localdate())
        for proyecto in Proyecto.objects.all():
            ultima = proyecto.visitas.filter(estado=Visita.Estado.REALIZADA).first()
            esperada = timezone.localdate(ultima.cerrada_en) + timedelta(days=14)
            self.assertEqual(proyecto.proxima_visita, esperada)
            self.assertEqual(ultima.cierre, Visita.Cierre.EMPLEADO)
            self.assertEqual(ultima.origen, Visita.Origen.APP)

    def test_clientes_salen_de_la_carta(self):
        razones = set(Cliente.objects.values_list("razon_social", flat=True))
        self.assertEqual(razones, set(CLIENTES))

    def test_historial_de_tres_meses(self):
        ahora = timezone.now()
        edades = [
            (ahora - visita.cerrada_en).days
            for visita in Visita.objects.filter(estado=Visita.Estado.REALIZADA)
        ]
        self.assertGreaterEqual(max(edades), 85)
        for mes in range(3):
            self.assertTrue(any(mes * 30 <= edad < (mes + 1) * 30 for edad in edades))

    def test_segunda_corrida_no_duplica(self):
        with (
            tempfile.TemporaryDirectory() as media,
            override_settings(MEDIA_ROOT=media),
        ):
            self._cargar()
            primera = self._conteos()
            archivos = _archivos(media)
            with self.captureOnCommitCallbacks(execute=True):
                self._cargar()
            self.assertEqual(self._conteos(), primera)
            # Los archivos de la corrida anterior se borraron al confirmar.
            restantes = _archivos(media)
            self.assertEqual(len(restantes), len(archivos))
            self.assertFalse(set(restantes) & set(archivos))
        self.assertEqual(Sitio.history.filter(nombre="Planta Castelli").count(), 1)

    def test_conserva_datos_que_no_son_demo(self):
        cliente = Cliente.objects.create(razon_social="Cliente Propio", notas="mío")
        sitio = Sitio.objects.create(cliente=cliente, nombre="Sitio propio")
        ajeno = Cliente.objects.create(razon_social="Danone")
        producto = Producto.objects.create(nombre_comercial="Producto propio")
        tipo = TipoServicio.objects.create(nombre="Propio", slug="servicio-propio")
        empleado = User.objects.create_user("propio", password="x", rol="empleado")
        proyecto = Proyecto.objects.create(
            sitio=sitio,
            tipo_servicio=tipo,
            titulo="Propio",
            encargado_inicial=empleado,
            encargado_actual=empleado,
        )
        # Un sitio sin marca colgado de un cliente demo tampoco se toca.
        demo = Cliente.objects.get(razon_social="Nutrisur")
        cuelga = Sitio.objects.create(cliente=demo, nombre="Sitio mío")
        self._cargar()
        self._cargar()
        for objeto in (cliente, sitio, ajeno, producto, tipo, empleado, proyecto):
            self.assertTrue(type(objeto).objects.filter(pk=objeto.pk).exists())
        self.assertTrue(Sitio.objects.filter(pk=cuelga.pk).exists())
        self.assertTrue(Cliente.objects.filter(pk=cuelga.cliente_id).exists())
        self.assertEqual(sitio.puntos.count(), 1)

    def test_limpia_el_formato_viejo(self):
        viejo = Cliente.objects.create(razon_social="Cliente Demo 1")
        sitio = Sitio.objects.create(cliente=viejo, nombre="Planta Demo Norte")
        tipo = TipoServicio.objects.create(
            nombre="Control de plagas (demo)", slug="demo-control-de-plagas"
        )
        empleado = User.objects.get(username="demo-empleado")
        Proyecto.objects.create(
            sitio=sitio,
            tipo_servicio=tipo,
            titulo="Control mensual",
            encargado_inicial=empleado,
            encargado_actual=empleado,
        )
        self._cargar()
        self.assertFalse(
            Cliente.objects.filter(razon_social__startswith="Cliente Demo")
        )
        self.assertFalse(Sitio.objects.filter(nombre="Planta Demo Norte").exists())
        self.assertFalse(TipoServicio.objects.filter(slug=tipo.slug).exists())
        self.assertFalse(Sitio.history.filter(nombre="Planta Demo Norte").exists())
        self.assertFalse(Proyecto.history.filter(titulo="Control mensual").exists())
        self.assertEqual(Cliente.objects.count(), 4)


@override_settings(MEDIA_ROOT=MEDIA_DEMO, DEBUG=True)
class CargarDemoStockTests(TestCase):
    """Productos con unidades, ingreso inicial y consumo de cada aplicado."""

    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=StringIO())

    def test_productos_en_las_tres_magnitudes_y_ambos_modos(self):
        productos = Producto.objects.all()
        magnitudes = {magnitud_de(p.unidad_base) for p in productos}
        self.assertEqual(magnitudes, {"volumen", "masa", "conteo"})
        self.assertEqual(
            set(productos.values_list("modo_unidad", flat=True)),
            {"unica", "equivalentes"},
        )

    def test_cada_producto_tiene_ingreso_inicial(self):
        for producto in Producto.objects.all():
            ingresos = producto.movimientos.filter(tipo=MovimientoStock.Tipo.INGRESO)
            self.assertEqual(ingresos.count(), 1, producto)
            self.assertEqual(
                ingresos.get().cantidad_base % producto.contenido_por_envase, 0
            )
            self.assertGreater(stock(producto), 0, producto)

    def test_cada_aplicado_tiene_su_consumo(self):
        aplicados = ProductoAplicado.objects.select_related("movimiento")
        self.assertTrue(aplicados.exists())
        for aplicado in aplicados:
            movimiento = aplicado.movimiento
            self.assertEqual(movimiento.tipo, MovimientoStock.Tipo.CONSUMO)
            self.assertEqual(movimiento.producto, aplicado.producto)
            self.assertEqual(movimiento.cantidad_base, -aplicado.cantidad_base)
            self.assertIn(aplicado.unidad, unidades_permitidas(aplicado.producto))
        usadas = set(aplicados.values_list("unidad", flat=True))
        self.assertGreater(len(usadas), 1)
        self.assertEqual(
            MovimientoStock.objects.filter(tipo="consumo").count(), aplicados.count()
        )

    def test_segunda_corrida_limpia_movimientos_sin_error(self):
        antes = set(MovimientoStock.objects.values_list("pk", flat=True))
        with (
            tempfile.TemporaryDirectory() as media,
            override_settings(MEDIA_ROOT=media),
        ):
            call_command("cargar_demo", stdout=StringIO())
        despues = set(MovimientoStock.objects.values_list("pk", flat=True))
        self.assertEqual(len(despues), len(antes))
        self.assertFalse(antes & despues)
        self.assertEqual(Producto.objects.count(), 3)
