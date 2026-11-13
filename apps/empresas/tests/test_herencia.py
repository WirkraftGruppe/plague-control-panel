from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.pruebas import crear_empresa
from apps.productos.models import MovimientoStock, Producto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Foto, ItemTurno, ProductoAplicado, Revision, Visita
from apps.visitas.services import crear_turno


class HerenciaEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = crear_empresa("Empresa A")
        cls.b = crear_empresa("Empresa B")
        cls.cliente = Cliente.objects.create(empresa=cls.a, razon_social="ACME")
        cls.servicio = TipoServicio.objects.create(empresa=cls.a, nombre="Roedores")
        cls.producto = Producto.objects.create(empresa=cls.a, nombre_comercial="Cebo")
        cls.empleado = User.objects.create_user(
            "emp-a", password="x", rol=User.Rol.EMPLEADO, empresa=cls.a
        )
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta")

    def _visita(self):
        return Visita.objects.create(
            sitio=self.sitio, empleado=self.empleado, origen=Visita.Origen.APP
        )

    def _revision(self, visita, **extra):
        punto = self.sitio.puntos.get(orden=0)
        ahora = timezone.now()
        datos = {
            "visita": visita,
            "punto": punto,
            "servicio": self.servicio,
            "realizada_en": ahora,
            "recibida_en": ahora,
        }
        datos.update(extra)
        return Revision.objects.create(**datos)

    def test_hijos_heredan_la_empresa_del_padre(self):
        punto = self.sitio.puntos.get(orden=0)
        visita = self._visita()
        revision = self._revision(visita)
        plano = Plano.objects.create(
            sitio=self.sitio, nombre="Planta baja", imagen="sitios/planos/x.png"
        )
        item = ItemTurno.objects.create(
            visita=visita, punto=punto, servicio=self.servicio
        )
        foto = Foto.objects.create(revision=revision, imagen="visitas/fotos/x.jpg")
        aplicado = ProductoAplicado.objects.create(
            revision=revision,
            producto=self.producto,
            lote="L1",
            dosis=Decimal("1"),
            unidad_dosis="ml/l",
            unidad="unidad",
            cantidad=Decimal("1"),
            cantidad_base=Decimal("1"),
        )
        movimiento = MovimientoStock.objects.create(
            producto=self.producto,
            tipo=MovimientoStock.Tipo.INGRESO,
            cantidad_base=Decimal("5"),
            usuario=self.empleado,
        )
        campo = CampoPlanilla.objects.create(
            tipo_servicio=self.servicio,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )
        for objeto in (
            self.sitio,
            punto,
            plano,
            visita,
            item,
            revision,
            foto,
            aplicado,
            movimiento,
            campo,
        ):
            with self.subTest(modelo=type(objeto).__name__):
                self.assertEqual(objeto.empresa_id, self.a.pk)
                objeto.refresh_from_db()
                self.assertEqual(objeto.empresa_id, self.a.pk)

    def test_hijo_con_empresa_distinta_del_padre_lanza(self):
        with self.assertRaises(ValueError):
            Sitio.objects.create(cliente=self.cliente, nombre="X", empresa=self.b)
        with self.assertRaises(ValueError):
            PuntoControl.objects.create(sitio=self.sitio, nombre="X", empresa=self.b)
        with self.assertRaises(ValueError):
            Visita.objects.create(
                sitio=self.sitio,
                empleado=self.empleado,
                origen=Visita.Origen.APP,
                empresa=self.b,
            )

    def test_referencias_de_otra_empresa_no_validan(self):
        empleado_b = User.objects.create_user(
            "emp-b", password="x", rol=User.Rol.EMPLEADO, empresa=self.b
        )
        servicio_b = TipoServicio.objects.create(empresa=self.b, nombre="Roedores")
        producto_b = Producto.objects.create(empresa=self.b, nombre_comercial="Cebo")
        visita = self._visita()
        revision = self._revision(visita)
        punto = self.sitio.puntos.get(orden=0)
        casos = [
            (
                Visita(sitio=self.sitio, empleado=empleado_b, empresa=self.a),
                "empleado",
            ),
            (
                ItemTurno(
                    visita=visita, punto=punto, servicio=servicio_b, empresa=self.a
                ),
                "servicio",
            ),
            (
                ProductoAplicado(
                    revision=revision, producto=producto_b, empresa=self.a
                ),
                "producto",
            ),
            (
                Sitio(cliente=self.cliente, responsable=empleado_b, empresa=self.a),
                "responsable",
            ),
        ]
        for objeto, campo in casos:
            with self.subTest(campo=campo):
                with self.assertRaises(ValidationError) as ctx:
                    objeto.clean()
                self.assertIn(campo, ctx.exception.message_dict)
        # Sin empresa propia ni padre no hay empresa efectiva con qué comparar.
        Visita(empleado=empleado_b).clean()

    def test_items_de_turno_creados_por_bulk_create_tienen_empresa(self):
        punto = self.sitio.puntos.get(orden=0)
        turno = crear_turno(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=date.today(),
            items=[(punto, self.servicio)],
            asignada_por=self.empleado,
        )
        items = list(ItemTurno.todos.filter(visita=turno))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].empresa_id, self.a.pk)

    def test_mismo_cliente_uuid_en_dos_empresas(self):
        compartido = uuid4()
        self._revision(self._visita(), cliente_uuid=compartido)
        # Otra empresa con el mismo uuid: permitido.
        cliente_b = Cliente.objects.create(empresa=self.b, razon_social="B SA")
        servicio_b = TipoServicio.objects.create(empresa=self.b, nombre="Roedores")
        empleado_b = User.objects.create_user(
            "emp-b", password="x", rol=User.Rol.EMPLEADO, empresa=self.b
        )
        sitio_b = Sitio.objects.create(cliente=cliente_b, nombre="Planta B")
        visita_b = Visita.objects.create(
            sitio=sitio_b, empleado=empleado_b, origen=Visita.Origen.APP
        )
        ahora = timezone.now()
        Revision.objects.create(
            visita=visita_b,
            punto=sitio_b.puntos.get(orden=0),
            servicio=servicio_b,
            realizada_en=ahora,
            recibida_en=ahora,
            cliente_uuid=compartido,
        )
        # La misma empresa con el mismo uuid: IntegrityError.
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._revision(self._visita(), cliente_uuid=compartido)


class ValidacionConEmpresaEfectivaTests(TestCase):
    """`clean()` usa la empresa efectiva y la empresa es inmutable tras el alta."""

    @classmethod
    def setUpTestData(cls):
        cls.a = crear_empresa("Empresa A")
        cls.b = crear_empresa("Empresa B")
        cls.cliente = Cliente.objects.create(empresa=cls.a, razon_social="ACME")
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta")
        cls.empleado = User.objects.create_user(
            "emp-a", password="x", rol=User.Rol.EMPLEADO, empresa=cls.a
        )
        cls.servicio_b = TipoServicio.objects.create(empresa=cls.b, nombre="Roedores")
        cls.empleado_b = User.objects.create_user(
            "emp-b", password="x", rol=User.Rol.EMPLEADO, empresa=cls.b
        )

    def test_punto_nuevo_sin_empresa_con_servicio_de_otra_empresa_no_valida(self):
        punto = PuntoControl(sitio=self.sitio, nombre="P", servicio=self.servicio_b)
        with self.assertRaises(ValidationError) as ctx:
            punto.full_clean(exclude=["qr_codigo"])
        self.assertIn("servicio", ctx.exception.message_dict)

    def test_visita_nueva_sin_empresa_con_empleado_de_otra_empresa_no_valida(self):
        visita = Visita(
            sitio=self.sitio, empleado=self.empleado_b, origen=Visita.Origen.APP
        )
        with self.assertRaises(ValidationError) as ctx:
            visita.full_clean()
        self.assertIn("empleado", ctx.exception.message_dict)

    def test_hijo_con_empresa_fijada_y_padre_de_otra_empresa_no_valida(self):
        punto = PuntoControl(sitio=self.sitio, nombre="P", empresa=self.b)
        with self.assertRaises(ValidationError) as ctx:
            punto.full_clean(exclude=["qr_codigo"])
        self.assertIn("sitio", ctx.exception.message_dict)

    def test_producto_aplicado_con_movimiento_de_otra_empresa_no_valida(self):
        producto_b = Producto.objects.create(empresa=self.b, nombre_comercial="Cebo")
        movimiento_b = MovimientoStock.objects.create(
            producto=producto_b,
            tipo=MovimientoStock.Tipo.INGRESO,
            cantidad_base=Decimal("5"),
            usuario=self.empleado_b,
        )
        producto_a = Producto.objects.create(empresa=self.a, nombre_comercial="Cebo")
        visita = Visita.objects.create(
            sitio=self.sitio, empleado=self.empleado, origen=Visita.Origen.APP
        )
        ahora = timezone.now()
        servicio_a = TipoServicio.objects.create(empresa=self.a, nombre="Aves")
        revision = Revision.objects.create(
            visita=visita,
            punto=self.sitio.puntos.get(orden=0),
            servicio=servicio_a,
            realizada_en=ahora,
            recibida_en=ahora,
        )
        aplicado = ProductoAplicado(
            revision=revision,
            producto=producto_a,
            movimiento=movimiento_b,
            empresa=self.a,
        )
        with self.assertRaises(ValidationError) as ctx:
            aplicado.clean()
        self.assertIn("movimiento", ctx.exception.message_dict)

    def test_cambiar_la_empresa_de_un_registro_guardado_lanza(self):
        cliente = Cliente.todos.get(pk=self.cliente.pk)
        cliente.empresa = self.b
        with self.assertRaises(ValidationError):
            cliente.clean()
        with self.assertRaises(ValueError):
            cliente.save()
        cliente.empresa = None
        with self.assertRaises(ValidationError):
            cliente.clean()
        with self.assertRaises(ValueError):
            cliente.save()
        self.assertEqual(Cliente.todos.get(pk=self.cliente.pk).empresa_id, self.a.pk)

    def test_cambiar_la_empresa_de_un_registro_guardado_falla(self):
        cliente = Cliente.todos.create(razon_social="Con empresa", empresa=self.a)
        cliente = Cliente.todos.get(pk=cliente.pk)
        cliente.empresa = self.a
        cliente.full_clean()
        cliente.save()
        self.assertEqual(Cliente.todos.get(pk=cliente.pk).empresa_id, self.a.pk)
        cliente.empresa = self.b
        with self.assertRaises(ValueError):
            cliente.save()
