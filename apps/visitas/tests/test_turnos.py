"""Turnos por punto: `crear_turno`, servicio de cada revisión, cierre y carga manual."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import MovimientoStock, Producto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import ItemTurno, Revision, Visita
from apps.visitas.services import (
    abrir_visita,
    cerrar_visita,
    crear_turno,
    registrar_revision,
    registrar_visita_manual,
)
from apps.visitas.tests.test_services import (
    MEDIA_TEMPORAL,
    SinArchivosMixin,
    jpeg_chico,
)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class BaseTurnoTests(SinArchivosMixin, TestCase):
    """Un sitio con tres puntos y dos servicios; el General es de `roedores`."""

    def setUp(self):
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        self.roedores = TipoServicio.objects.create(nombre="Roedores", slug="roedores")
        self.insectos = TipoServicio.objects.create(nombre="Insectos", slug="insectos")
        self.general = self.sitio.puntos.get(orden=0)
        self.general.servicio = self.roedores
        self.general.save()
        self.sala = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Sala", orden=1, servicio=self.roedores
        )
        self.techo = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Techo", orden=2, servicio=self.insectos
        )
        self.empleado = User.objects.create_user(
            "emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.admin = User.objects.create_user(
            "adm", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def turno(self, items, **extra):
        datos = {
            "sitio": self.sitio,
            "empleado": self.empleado,
            "programada_para": timezone.localdate() + timedelta(days=1),
            "items": items,
            "asignada_por": self.admin,
        }
        datos.update(extra)
        return crear_turno(**datos)

    def revisar(self, visita, punto, **extra):
        argumentos = {
            "visita": visita,
            "empleado": self.empleado,
            "qr_codigo": punto.qr_codigo,
            "cliente_uuid": uuid4(),
            "realizada_en": timezone.now() - timedelta(minutes=5),
            "latitud": Decimal("-35.1"),
            "longitud": Decimal("-57.7"),
            "precision_m": Decimal("8.5"),
            "datos": {},
            "productos_aplicados": [],
            "fotos": [],
        }
        argumentos.update(extra)
        return registrar_revision(**argumentos)


class CrearTurnoTests(BaseTurnoTests):
    def test_tres_puntos_uno_con_servicio_cambiado_guarda_tres_items(self):
        visita = self.turno(
            [
                (self.general, self.roedores),
                (self.sala, self.insectos),
                (self.techo, self.insectos),
            ]
        )
        self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)
        self.assertEqual(visita.sitio, self.sitio)
        self.assertEqual(visita.empleado, self.empleado)
        self.assertEqual(visita.asignada_por, self.admin)
        self.assertEqual(
            {(i.punto, i.servicio) for i in visita.items.all()},
            {
                (self.general, self.roedores),
                (self.sala, self.insectos),
                (self.techo, self.insectos),
            },
        )
        # El servicio del ítem no cambia el del punto.
        self.sala.refresh_from_db()
        self.assertEqual(self.sala.servicio, self.roedores)

    def test_sin_puntos_da_error(self):
        with self.assertRaises(ValidationError) as contexto:
            self.turno([])
        self.assertIn("puntos", contexto.exception.message_dict)
        self.assertFalse(Visita.objects.exists())

    def test_punto_de_otro_sitio_da_error(self):
        otro = Sitio.objects.create(cliente=self.sitio.cliente, nombre="Otra")
        ajeno = otro.puntos.get(orden=0)
        with self.assertRaises(ValidationError) as contexto:
            self.turno([(self.general, self.roedores), (ajeno, self.roedores)])
        self.assertIn("puntos", contexto.exception.message_dict)
        self.assertFalse(Visita.objects.exists())
        self.assertFalse(ItemTurno.objects.exists())

    def test_rechaza_punto_inactivo_repetido_servicio_inactivo_y_administrador(self):
        self.sala.activo = False
        self.sala.save()
        self.insectos.activo = False
        self.insectos.save()
        casos = {
            "puntos": [(self.sala, self.roedores)],
            "servicios": [(self.general, self.insectos)],
        }
        for campo, items in casos.items():
            with self.subTest(campo):
                with self.assertRaises(ValidationError) as contexto:
                    self.turno(items)
                self.assertIn(campo, contexto.exception.message_dict)
        with self.assertRaises(ValidationError) as contexto:
            self.turno([(self.general, self.roedores)] * 2)
        self.assertIn("puntos", contexto.exception.message_dict)
        with self.assertRaises(ValidationError) as contexto:
            self.turno([(self.general, self.roedores)], empleado=self.admin)
        self.assertIn("empleado", contexto.exception.message_dict)
        self.assertFalse(Visita.objects.exists())


class RevisionTurnoTests(BaseTurnoTests):
    def abrir(self):
        return abrir_visita(empleado=self.empleado, qr_codigo=self.general.qr_codigo)[0]

    def test_punto_del_turno_usa_el_servicio_del_item(self):
        pendiente = self.turno([(self.general, self.insectos)])
        visita = self.abrir()
        self.assertEqual(visita.pk, pendiente.pk)
        revision = self.revisar(visita, self.general)
        # El punto es de roedores, pero el turno pide insectos.
        self.assertEqual(self.general.servicio, self.roedores)
        self.assertEqual(revision.servicio, self.insectos)
        self.assertFalse(revision.fuera_de_turno)

    def test_punto_fuera_del_turno_queda_fuera_de_turno(self):
        self.turno([(self.sala, self.roedores)])
        visita = self.abrir()
        revision = self.revisar(visita, self.techo)
        self.assertEqual(revision.servicio, self.insectos)
        self.assertTrue(revision.fuera_de_turno)
        dentro = self.revisar(visita, self.sala)
        self.assertFalse(dentro.fuera_de_turno)

    def test_punto_sin_servicio_fuera_del_turno_da_error(self):
        self.turno([(self.sala, self.roedores)])
        visita = self.abrir()
        PuntoControl.objects.filter(pk=self.techo.pk).update(servicio=None)
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, self.techo)
        self.assertEqual(
            contexto.exception.message_dict["qr_codigo"],
            ["El punto no tiene servicio asignado."],
        )
        self.assertFalse(Revision.objects.exists())
        # Dentro del turno el punto sin servicio sí se revisa: manda el ítem.
        PuntoControl.objects.filter(pk=self.sala.pk).update(servicio=None)
        self.assertEqual(self.revisar(visita, self.sala).servicio, self.roedores)

    def test_planilla_de_punto_sale_del_servicio_resuelto(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.insectos,
            orden=1,
            etiqueta="Trampas",
            clave="trampas",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.turno([(self.general, self.insectos)])
        visita = self.abrir()
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, self.general)
        self.assertIn("datos", contexto.exception.message_dict)
        revision = self.revisar(visita, self.general, datos={"trampas": 2})
        self.assertEqual([c["clave"] for c in revision.esquema_planilla], ["trampas"])


class CerrarTurnoTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        for servicio, clave, obligatorio in (
            (self.roedores, "resumen", True),
            (self.insectos, "notas", False),
        ):
            CampoPlanilla.objects.create(
                tipo_servicio=servicio,
                orden=1,
                etiqueta=clave.title(),
                clave=clave,
                tipo=CampoPlanilla.Tipo.TEXTO,
                ambito=CampoPlanilla.Ambito.VISITA,
                obligatorio=obligatorio,
            )
        self.turno([(self.general, self.roedores), (self.techo, self.insectos)])
        self.visita = abrir_visita(
            empleado=self.empleado, qr_codigo=self.general.qr_codigo
        )[0]
        self.revisar(self.visita, self.general)
        self.revisar(self.visita, self.techo)

    def cerrar(self, **extra):
        return cerrar_visita(
            self.visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO, **extra
        )

    def test_datos_de_visita_por_servicio_presente(self):
        datos = {"roedores": {"resumen": "Sin novedades"}, "insectos": {}}
        cerrada = self.cerrar(datos=datos)
        cerrada.refresh_from_db()
        self.assertEqual(cerrada.datos, datos)
        self.assertEqual(set(cerrada.esquema_planilla), {"roedores", "insectos"})
        self.assertEqual(
            [c["clave"] for c in cerrada.esquema_planilla["roedores"]], ["resumen"]
        )

    def test_servicio_con_campo_obligatorio_sin_datos_da_error(self):
        with self.assertRaises(ValidationError) as contexto:
            self.cerrar(datos={"insectos": {"notas": "x"}})
        mensajes = contexto.exception.message_dict["datos"]
        self.assertEqual(mensajes, ["roedores: resumen: Este campo es obligatorio."])
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, Visita.Estado.ABIERTA)

    def test_servicio_ajeno_a_la_visita_da_error(self):
        otro = TipoServicio.objects.create(nombre="Aves", slug="aves")
        with self.assertRaises(ValidationError) as contexto:
            self.cerrar(datos={"roedores": {"resumen": "x"}, otro.slug: {}})
        self.assertIn("aves: El servicio", contexto.exception.message_dict["datos"][0])


class CargaManualTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        Sitio.objects.filter(pk=self.sitio.pk).update(
            creado=timezone.now() - timedelta(days=30)
        )
        self.sitio.refresh_from_db()
        self.producto = Producto.objects.create(
            nombre_comercial="Concentrado", unidad_base="ml", modo_unidad="equivalentes"
        )

    def cargar(self, **extra):
        argumentos = {
            "sitio": self.sitio,
            "empleado": self.empleado,
            "administrador": self.admin,
            "motivo": "Sin señal",
            "realizada_en": timezone.now() - timedelta(hours=2),
            "items": [(self.general, self.roedores), (self.techo, self.insectos)],
            "datos": {},
            "productos_aplicados": [],
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_visita_manual(**argumentos)

    def test_cantidad_desbordada_da_error_sin_movimiento(self):
        item = {
            "producto": self.producto.pk,
            "lote": "L1",
            "dosis": "1",
            "unidad_dosis": "ml/l",
            "cantidad": "9999999",
            "unidad": "gal",
        }
        with self.assertRaises(ValidationError) as contexto:
            self.cargar(productos_aplicados=[item])
        self.assertIn("productos_aplicados.0.cantidad", contexto.exception.message_dict)
        self.assertFalse(MovimientoStock.objects.exists())
        self.assertFalse(Visita.objects.exists())

    def test_fecha_anterior_al_alta_del_sitio_da_error(self):
        with self.assertRaises(ValidationError) as contexto:
            self.cargar(
                realizada_en=self.sitio.creado - timedelta(days=2),
                confirmar_atraso=True,
            )
        self.assertEqual(
            contexto.exception.message_dict["realizada_en"],
            ["La fecha no puede ser anterior al alta del sitio."],
        )
        self.assertFalse(Visita.objects.exists())

    def test_servicio_por_punto_y_items_de_la_visita_nueva(self):
        visita = self.cargar()
        revisiones = {r.punto: r for r in visita.revisiones.all()}
        self.assertEqual(revisiones[self.general].servicio, self.roedores)
        self.assertEqual(revisiones[self.techo].servicio, self.insectos)
        self.assertFalse(any(r.fuera_de_turno for r in revisiones.values()))
        self.assertEqual(visita.items.count(), 2)

    def test_en_una_pendiente_el_punto_sin_item_queda_fuera_de_turno(self):
        pendiente = self.turno([(self.general, self.roedores)])
        visita = self.cargar(pendiente=pendiente)
        fuera = {r.punto: r.fuera_de_turno for r in visita.revisiones.all()}
        self.assertEqual(fuera, {self.general: False, self.techo: True})
