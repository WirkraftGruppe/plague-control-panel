"""API de turnos por sitio: abrir por QR, fotos de 0 a 2 y tope de la cantidad."""

import json
from datetime import date, timedelta
from decimal import Decimal

from apps.productos.models import MovimientoStock, Producto
from apps.productos.services import registrar_ingreso, stock
from apps.sitios.models import Sitio
from apps.visitas.models import ItemTurno, ProductoAplicado, Revision, Visita
from apps.visitas.services import crear_turno
from apps.visitas.tests.test_api import ApiVisitasBase, jpeg_chico


class AbrirVisitaSitioApiTests(ApiVisitasBase):
    def _abrir(self, punto=None, api=None):
        punto = punto or self.punto
        return (api or self.api).post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(punto.qr_codigo)},
            format="json",
        )

    def _turno(self, empleado, dias=1):
        return crear_turno(
            sitio=self.sitio,
            empleado=empleado,
            programada_para=date(2026, 9, 1) + timedelta(days=dias),
            items=[(self.punto, self.tipo)],
            asignada_por=self.admin,
        )

    def test_abre_el_turno_pendiente_del_sitio(self):
        self._turno(self.empleado, dias=5)
        mas_antiguo = self._turno(self.empleado, dias=1)
        ajeno = self._turno(self.otro, dias=0)
        r = self._abrir()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["id"], mas_antiguo.id)
        self.assertEqual(r.data["estado"], "abierta")
        self.assertEqual(r.data["sitio"]["nombre"], "Planta 1")
        mas_antiguo.refresh_from_db()
        self.assertEqual(mas_antiguo.estado, Visita.Estado.ABIERTA)
        self.assertEqual(mas_antiguo.items.count(), 1)
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.estado, Visita.Estado.PENDIENTE)
        # Abrir de nuevo devuelve la misma visita abierta.
        otra = self._abrir()
        self.assertEqual((otra.status_code, otra.data["id"]), (200, mas_antiguo.id))

    def test_sin_turno_crea_visita_sin_items(self):
        r = self._abrir()
        self.assertEqual(r.status_code, 201, r.content)
        visita = Visita.objects.get(pk=r.data["id"])
        self.assertEqual(visita.sitio, self.sitio)
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        self.assertEqual(visita.items.count(), 0)
        self.assertFalse(ItemTurno.objects.exists())

    def test_el_qr_de_otro_sitio_abre_en_ese_sitio(self):
        otro = Sitio.objects.create(cliente=self.sitio.cliente, nombre="Otra")
        r = self._abrir(otro.puntos.get(orden=0))
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Visita.objects.get(pk=r.data["id"]).sitio, otro)

    def test_el_pedido_no_acepta_un_sitio_elegido_por_el_cliente(self):
        otro = Sitio.objects.create(cliente=self.sitio.cliente, nombre="Otra")
        r = self.api.post(
            "/api/v1/visitas/abrir/",
            {"sitio": otro.id, "qr_codigo": str(self.punto.qr_codigo)},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Visita.objects.get(pk=r.data["id"]).sitio, self.sitio)


class RevisionFotosApiTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta()

    def test_cero_fotos_da_201(self):
        r = self._post(self.visita, fotos=None)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["fotos"], [])
        self.assertEqual(Revision.objects.count(), 1)

    def test_dos_fotos_da_201(self):
        r = self._post(self.visita, fotos=[jpeg_chico(), jpeg_chico()])
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.data["fotos"]), 2)

    def test_tres_fotos_da_400(self):
        r = self._post(self.visita, fotos=[jpeg_chico() for _ in range(3)])
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("fotos", r.data["campos"])
        self.assertFalse(Revision.objects.exists())

    def test_punto_sin_servicio_fuera_del_turno_da_400(self):
        self.punto.servicio = None
        self.punto.save()
        r = self._post(self.visita)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("El punto no tiene servicio asignado.", str(r.data["campos"]))
        self.assertFalse(Revision.objects.exists())


class RevisionCantidadApiTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta()
        self.concentrado = Producto.objects.create(
            nombre_comercial="Concentrado",
            unidad_base="ml",
            modo_unidad="equivalentes",
        )
        registrar_ingreso(self.concentrado, Decimal("1000"), False, self.empleado)

    def _item(self, **cambios):
        item = {
            "producto": self.concentrado.pk,
            "lote": "L1",
            "dosis": "2.5",
            "unidad_dosis": "ml/l",
            "cantidad": "2",
            "unidad": "l",
        }
        item.update(cambios)
        return item

    def test_9999999_gal_en_base_ml_da_400_sin_movimiento(self):
        antes = stock(self.concentrado)
        r = self._post(
            self.visita,
            productos_aplicados=json.dumps(
                [self._item(cantidad="9999999", unidad="gal")]
            ),
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("productos_aplicados.0.cantidad", r.data["campos"])
        self.assertFalse(ProductoAplicado.objects.exists())
        self.assertFalse(Revision.objects.exists())
        self.assertFalse(
            MovimientoStock.objects.filter(tipo=MovimientoStock.Tipo.CONSUMO).exists()
        )
        self.assertEqual(stock(self.concentrado), antes)

    def test_cantidad_normal_sigue_aceptada(self):
        r = self._post(
            self.visita, productos_aplicados=json.dumps([self._item(cantidad="1")])
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(stock(self.concentrado), Decimal("0"))
