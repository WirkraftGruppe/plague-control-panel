"""Consumo de stock al guardar los productos aplicados de una revisión."""

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.productos.models import MovimientoStock, Producto
from apps.productos.services import registrar_ingreso, stock
from apps.proyectos.models import Proyecto
from apps.visitas.models import ProductoAplicado, Visita
from apps.visitas.services import registrar_revision, registrar_visita_manual
from apps.visitas.tests.test_models import crear_visita, punto_de
from apps.visitas.tests.test_services import (
    MEDIA_TEMPORAL,
    SinArchivosMixin,
    abrir,
    jpeg_chico,
)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ConsumoTests(SinArchivosMixin, TestCase):
    def setUp(self):
        self.pendiente = crear_visita(programada_para=date(2026, 9, 1))
        self.empleado = self.pendiente.empleado
        self.proyecto = self.pendiente.proyecto
        self.punto = punto_de(self.pendiente)
        self.admin = User.objects.create_user(
            username="admin-stock", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.gel = Producto.objects.create(
            nombre_comercial="Gel", unidad_base="g", modo_unidad="equivalentes"
        )
        self.cebo = Producto.objects.create(nombre_comercial="Cebo")
        for producto in (self.gel, self.cebo):
            registrar_ingreso(producto, Decimal("1000"), False, self.admin)
        self.items = [
            self._item(self.gel, cantidad="2", unidad="kg"),
            self._item(self.cebo, cantidad="3", unidad="unidad"),
        ]
        # Las cargas manuales son anteriores a hoy: el proyecto ya existía.
        Proyecto.objects.filter(pk=self.proyecto.pk).update(
            creado=timezone.now() - timedelta(days=60)
        )
        self.proyecto.refresh_from_db()

    def _item(self, producto, **cambios):
        item = {
            "producto": producto.pk,
            "lote": "L1",
            "dosis": "1",
            "unidad_dosis": "g/l",
        }
        item.update(cambios)
        return item

    def _consumos(self):
        return MovimientoStock.objects.filter(tipo=MovimientoStock.Tipo.CONSUMO)

    def _cargar(self, **extra):
        argumentos = {
            "proyecto": self.proyecto,
            "empleado": self.empleado,
            "administrador": self.admin,
            "motivo": "Sin señal",
            "realizada_en": timezone.now() - timedelta(hours=3),
            "puntos": [self.punto],
            "datos": {},
            "productos_aplicados": self.items,
            "fotos": [jpeg_chico()],
        }
        argumentos.update(extra)
        return registrar_visita_manual(**argumentos)

    def test_un_consumo_por_producto_aplicado_con_el_empleado(self):
        visita, _ = abrir(empleado=self.empleado, proyecto=self.proyecto)
        registrar_revision(
            visita=visita,
            empleado=self.empleado,
            qr_codigo=self.punto.qr_codigo,
            cliente_uuid=uuid4(),
            realizada_en=timezone.now() - timedelta(minutes=5),
            latitud=Decimal("-35.1"),
            longitud=Decimal("-57.7"),
            precision_m=Decimal("8.5"),
            datos={},
            productos_aplicados=self.items,
            fotos=[jpeg_chico()],
        )
        self.assertEqual(self._consumos().count(), 2)
        for aplicado in ProductoAplicado.objects.all():
            movimiento = aplicado.movimiento
            self.assertEqual(movimiento.tipo, MovimientoStock.Tipo.CONSUMO)
            self.assertEqual(movimiento.usuario, self.empleado)
            self.assertEqual(movimiento.cantidad_base, -aplicado.cantidad_base)
            self.assertEqual(movimiento.producto, aplicado.producto)
        self.assertEqual(stock(self.gel), Decimal("-1000"))
        self.assertEqual(stock(self.cebo), Decimal("997"))

    def test_carga_manual_crea_consumo_del_administrador(self):
        self._cargar()
        consumos = self._consumos()
        self.assertEqual(consumos.count(), 2)
        self.assertEqual({m.usuario for m in consumos}, {self.admin})
        self.assertFalse(ProductoAplicado.objects.filter(movimiento=None).exists())
        self.assertEqual(Visita.objects.filter(origen="manual").count(), 1)

    def test_carga_manual_fallida_no_deja_movimiento(self):
        falsa = SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")
        with self.assertRaises(ValidationError):
            self._cargar(fotos=[falsa])
        self.assertFalse(self._consumos().exists())
        self.assertFalse(ProductoAplicado.objects.exists())
        # Una falla posterior a guardar los aplicados también revierte los consumos.
        with mock.patch(
            "apps.visitas.services.cerrar_visita", side_effect=ValidationError("x")
        ):
            with self.assertRaises(ValidationError):
                self._cargar()
        self.assertFalse(self._consumos().exists())
        self.assertEqual(stock(self.cebo), Decimal("1000"))

    def test_errores_anidados_por_posicion_y_campo(self):
        items = [self.items[0], self._item(self.cebo, cantidad="1", unidad="kg")]
        with self.assertRaises(ValidationError) as contexto:
            self._cargar(productos_aplicados=items)
        self.assertEqual(
            list(contexto.exception.message_dict), ["productos_aplicados.1.unidad"]
        )
