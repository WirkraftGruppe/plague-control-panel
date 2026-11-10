"""Pruebas de ``cargar_demo``: datos realistas, recreables y solo con SQLite."""

import os
import shutil
import tempfile
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
from apps.empresas.models import Empresa
from apps.empresas.tests.ayudas import una_empresa
from apps.panel.demo import _es_sqlite
from apps.panel.demo_datos import CLIENTES, EMPRESA_DEMO, EMPRESA_DEMO_B, MARCA_DEMO
from apps.productos.models import MovimientoStock, Producto
from apps.productos.services import stock
from apps.productos.unidades import magnitud_de, unidades_permitidas
from apps.servicios.models import TipoServicio
from apps.sitios.estado import EstadoVencimiento, estados_por_vencimiento
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import (
    Foto,
    ItemTurno,
    ProductoAplicado,
    Revision,
    Visita,
)
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
        # Con tipos ya creados, la demo no los pisa.
        TipoServicio.objects.filter(slug="servicio-mipu").update(nombre="Del cliente")
        self._cargar()
        self.assertTrue(TipoServicio.objects.filter(nombre="Del cliente").exists())

    @override_settings(DEBUG=True)
    def test_avisa_usuario_demo_existente_sin_modificarlo(self):
        previo = User.objects.create_user(
            "demo-admin",
            password="otra-clave",
            rol=User.Rol.EMPLEADO,
            empresa=Empresa.objects.get_or_create(nombre=EMPRESA_DEMO)[0],
        )
        salida, errores = StringIO(), StringIO()
        call_command("cargar_demo", stdout=salida, stderr=errores)
        previo.refresh_from_db()
        self.assertEqual(previo.rol, User.Rol.EMPLEADO)
        self.assertTrue(previo.check_password("otra-clave"))
        self.assertIn("demo-admin", errores.getvalue())
        self.assertNotIn("Usuario creado: demo-admin,", salida.getvalue())
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
            *(User, Cliente, Sitio, PuntoControl, Plano, Visita, ItemTurno),
            *(Revision, Foto, ProductoAplicado, Producto, TipoServicio),
        )
        return {modelo.__name__: modelo.objects.count() for modelo in modelos}

    @classmethod
    def _demo(cls):
        return Empresa.objects.get(nombre=EMPRESA_DEMO)

    def test_crea_los_conteos_esperados(self):
        demo = self._demo()
        self.assertEqual(Cliente.objects.de_empresa(demo).count(), 4)
        self.assertEqual(Sitio.objects.de_empresa(demo).count(), 6)
        self.assertTrue(20 <= PuntoControl.objects.de_empresa(demo).count() <= 30)
        plano = Plano.objects.de_empresa(demo).get()
        ubicados = plano.puntos.exclude(x=None).exclude(y=None)
        self.assertGreaterEqual(ubicados.count(), 4)
        self.assertGreater(plano.ancho_px, 0)
        self.assertTrue(ProductoAplicado.objects.exists())
        incidencias = Revision.objects.de_empresa(demo).filter(
            incidencia_ubicacion=True
        )
        self.assertTrue(2 <= incidencias.count() <= 3)
        self.assertTrue(Visita.objects.filter(incidencia_ubicacion=True).exists())
        for rol in (User.Rol.ADMINISTRADOR, User.Rol.EMPLEADO):
            self.assertEqual(User.objects.filter(empresa=demo, rol=rol).count(), 1)
        self.assertEqual(User.objects.filter(rol=User.Rol.PLATAFORMA).count(), 1)
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

    def test_usuario_plataforma_es_superusuario_sin_empresa(self):
        usuario = User.objects.get(username="demo-plataforma")
        self.assertTrue(usuario.es_plataforma)
        self.assertTrue(usuario.is_superuser)
        self.assertIsNone(usuario.empresa_id)

    def test_planillas_validas_contra_su_esquema(self):
        for revision in Revision.objects.all():
            errores = validar_datos(revision.esquema_planilla, revision.datos)
            self.assertEqual(errores, {})

    def test_cada_sitio_tiene_su_historia_de_turnos_realizados(self):
        for sitio in Sitio.objects.all():
            ultima = sitio.visitas.filter(estado=Visita.Estado.REALIZADA).first()
            self.assertEqual(ultima.cierre, Visita.Cierre.EMPLEADO)
            self.assertEqual(ultima.origen, Visita.Origen.APP)
            activos = sitio.puntos.filter(activo=True).count()
            self.assertEqual(ultima.items.count(), activos)

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
        # Una fila por empresa demo.
        self.assertEqual(Sitio.history.filter(nombre="Planta Castelli").count(), 2)

    def test_conserva_datos_que_no_son_demo(self):
        cliente = Cliente.objects.create(
            razon_social="Cliente Propio", notas="mío", empresa=una_empresa()
        )
        sitio = Sitio.objects.create(cliente=cliente, nombre="Sitio propio")
        ajeno = Cliente.objects.create(razon_social="Danone", empresa=una_empresa())
        producto = Producto.objects.create(
            nombre_comercial="Producto propio", empresa=una_empresa()
        )
        tipo = TipoServicio.objects.create(
            nombre="Propio", slug="servicio-propio", empresa=una_empresa()
        )
        empleado = User.objects.create_user(
            "propio", password="x", rol="empleado", empresa=una_empresa()
        )
        visita = Visita.objects.create(
            sitio=sitio, empleado=empleado, origen=Visita.Origen.APP
        )
        # Un sitio sin marca colgado de un cliente demo tampoco se toca.
        demo = Cliente.objects.de_empresa(self._demo()).get(razon_social="Nutrisur")
        cuelga = Sitio.objects.create(cliente=demo, nombre="Sitio mío")
        self._cargar()
        self._cargar()
        for objeto in (cliente, sitio, ajeno, producto, tipo, empleado, visita):
            self.assertTrue(type(objeto).objects.filter(pk=objeto.pk).exists())
        self.assertTrue(Sitio.objects.filter(pk=cuelga.pk).exists())
        self.assertTrue(Cliente.objects.filter(pk=cuelga.cliente_id).exists())
        self.assertEqual(sitio.puntos.count(), 1)

    def test_limpia_el_formato_viejo(self):
        viejo = Cliente.objects.create(
            razon_social="Cliente Demo 1", empresa=self._demo()
        )
        sitio = Sitio.objects.create(cliente=viejo, nombre="Planta Demo Norte")
        tipo = TipoServicio.objects.create(
            nombre="Control de plagas (demo)",
            slug="demo-control-de-plagas",
            empresa=self._demo(),
        )
        empleado = User.objects.get(username="demo-empleado")
        Visita.objects.create(sitio=sitio, empleado=empleado, origen=Visita.Origen.APP)
        self._cargar()
        self.assertFalse(
            Cliente.objects.filter(razon_social__startswith="Cliente Demo")
        )
        self.assertFalse(Sitio.objects.filter(nombre="Planta Demo Norte").exists())
        self.assertFalse(TipoServicio.objects.filter(slug=tipo.slug).exists())
        self.assertFalse(Sitio.history.filter(nombre="Planta Demo Norte").exists())
        self.assertEqual(Cliente.objects.de_empresa(self._demo()).count(), 4)


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
        self.assertEqual(Producto.objects.count(), 6)


@override_settings(MEDIA_ROOT=MEDIA_DEMO, DEBUG=True)
class CargarDemoTurnosTests(TestCase):
    """Turnos de la demo y servicios, frecuencias y vencimientos por punto."""

    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=StringIO())

    def test_turnos_en_los_tres_estados(self):
        estados = set(Visita.objects.values_list("estado", flat=True))
        self.assertTrue(
            {"pendiente", "abierta", "realizada"} <= estados, f"Hay {estados}"
        )
        for visita in Visita.objects.all():
            self.assertTrue(visita.items.exists(), visita)
        demo = Empresa.objects.get(nombre=EMPRESA_DEMO)
        pendiente = Visita.objects.de_empresa(demo).get(estado=Visita.Estado.PENDIENTE)
        self.assertGreater(pendiente.programada_para, timezone.localdate())
        self.assertEqual(pendiente.asignada_por.username, "demo-admin")
        self.assertEqual(pendiente.items.count(), pendiente.sitio.puntos.count())

    def test_puntos_con_servicios_y_vencimientos_distintos(self):
        puntos = list(PuntoControl.objects.filter(activo=True))
        self.assertGreaterEqual(len({p.servicio_id for p in puntos}), 2)
        self.assertTrue(all(p.servicio_id for p in puntos))
        estados = estados_por_vencimiento(puntos, timezone.localdate()).values()
        self.assertEqual(set(estados), set(EstadoVencimiento.values))
        self.assertGreaterEqual(len({p.frecuencia_dias for p in puntos}), 3)
        for item in ItemTurno.objects.select_related("punto"):
            self.assertEqual(item.servicio_id, item.punto.servicio_id)


@override_settings(MEDIA_ROOT=MEDIA_DEMO, DEBUG=True)
class DosEmpresasDemoTests(TestCase):
    """La demo crea dos empresas con datos y usuarios propios."""

    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", stdout=StringIO())
        cls.empresa_a = Empresa.objects.get(nombre=EMPRESA_DEMO)
        cls.empresa_b = Empresa.objects.get(nombre=EMPRESA_DEMO_B)

    def test_crea_dos_empresas_con_datos_separados(self):
        self.assertEqual(Empresa.objects.count(), 2)
        for empresa in (self.empresa_a, self.empresa_b):
            self.assertEqual(Cliente.objects.de_empresa(empresa).count(), 4)
            self.assertEqual(Sitio.objects.de_empresa(empresa).count(), 6)
            self.assertEqual(Producto.objects.de_empresa(empresa).count(), 3)
            self.assertEqual(TipoServicio.objects.de_empresa(empresa).count(), 2)
            self.assertEqual(Plano.objects.de_empresa(empresa).count(), 1)
            visitas = Visita.objects.de_empresa(empresa).select_related(
                "sitio", "empleado", "asignada_por"
            )
            self.assertTrue(visitas.exists())
            for visita in visitas:
                self.assertEqual(visita.sitio.empresa_id, empresa.pk)
                self.assertEqual(visita.empleado.empresa_id, empresa.pk)
        # Una nueva corrida limpia cada empresa sin tocar la otra.
        antes = Visita.objects.de_empresa(self.empresa_b).count()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("cargar_demo", stdout=StringIO())
        despues = Empresa.objects.get(nombre=EMPRESA_DEMO_B)
        self.assertEqual(Visita.objects.de_empresa(despues).count(), antes)
        self.assertEqual(Sitio.objects.de_empresa(despues).count(), 6)

    def test_crea_los_usuarios_de_cada_empresa_y_el_de_plataforma(self):
        esperados = {
            "demo-admin": (User.Rol.ADMINISTRADOR, self.empresa_a),
            "demo-empleado": (User.Rol.EMPLEADO, self.empresa_a),
            "demo-admin-b": (User.Rol.ADMINISTRADOR, self.empresa_b),
            "demo-empleado-b": (User.Rol.EMPLEADO, self.empresa_b),
        }
        for nombre, (rol, empresa) in esperados.items():
            usuario = User.objects.get(username=nombre)
            self.assertEqual((usuario.rol, usuario.empresa_id), (rol, empresa.pk))
            self.assertTrue(usuario.check_password("demo1234"))
        plataforma = User.objects.get(username="demo-plataforma")
        self.assertTrue(plataforma.es_plataforma and plataforma.is_superuser)
        self.assertIsNone(plataforma.empresa_id)

    def test_empresas_repetidas_y_admin_sin_empresa(self):
        Empresa.objects.create(nombre=EMPRESA_DEMO)
        User.objects.filter(username="demo-admin").update(empresa=None)
        call_command("cargar_demo", stdout=StringIO())
        admin = User.objects.get(username="demo-admin")
        # Se usa la empresa demo más antigua y el administrador vuelve a ella.
        self.assertEqual(admin.empresa_id, self.empresa_a.pk)
