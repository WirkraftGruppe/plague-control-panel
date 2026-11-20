"""API de visitas con coordinación: duplicada, coordenadas y dosis opcionales,
apertura sin escaneo y `revisado_por_otro`."""

import json
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.empresas.tests.ayudas import una_empresa
from apps.productos.models import Producto
from apps.sitios.models import PuntoControl
from apps.visitas.models import ItemTurno, ProductoAplicado, Revision, Visita
from apps.visitas.tests.ayudas_empresa import dos_empresas
from apps.visitas.tests.test_api import ApiVisitasBase


class RevisionApiTests(ApiVisitasBase):
    def test_segunda_del_dia_por_otro_201_duplicada_hoy_true(self):
        self._revision(self._abierta(self.otro))
        r = self._post(self._abierta())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIs(r.data["duplicada_hoy"], True)

    def test_primera_del_dia_201_duplicada_hoy_false(self):
        r = self._post(self._abierta())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIs(r.data["duplicada_hoy"], False)

    def test_visita_de_administrador_duplicada_hoy_false(self):
        self._revision(self._abierta(self.otro))
        visita = self._abierta(self.admin, cuenta_como_servicio=False)
        r = self._post(visita, api=self._api(self.admin))
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIs(r.data["duplicada_hoy"], False)

    def test_sin_coordenadas_201_con_incidencia(self):
        visita = self._abierta()
        r = self._post(visita, latitud=None, longitud=None, precision_m=None)
        self.assertEqual(r.status_code, 201, r.content)
        revision = Revision.objects.de_empresa(una_empresa()).get(pk=r.data["id"])
        self.assertTrue(revision.incidencia_sin_ubicacion)
        self.assertIsNone(revision.latitud)
        self.assertNotIn("latitud", r.data)

    def _aplicar(self, producto, **item):
        item = {
            "producto": producto.pk,
            "lote": "L1",
            "cantidad": "10",
            "unidad": "ml",
            **item,
        }
        return self._post(self._abierta(), productos_aplicados=json.dumps([item]))

    def _producto(self, **campos):
        return Producto.objects.create(
            nombre_comercial="Concentrado",
            unidad_base="ml",
            modo_unidad="equivalentes",
            empresa=una_empresa(),
            **campos,
        )

    def test_sin_dosis_variable_sin_dosis_201_guarda_habitual(self):
        producto = self._producto(
            dosis_habitual=Decimal("5"), unidad_dosis_habitual="ml/l"
        )
        r = self._aplicar(producto)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["productos"][0]["dosis"], "5.000")
        self.assertEqual(r.data["productos"][0]["unidad_dosis"], "ml/l")

    def test_producto_sin_dosis_devuelve_null(self):
        r = self._aplicar(self._producto())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIsNone(r.data["productos"][0]["dosis"])
        self.assertIsNone(r.data["productos"][0]["unidad_dosis"])
        self.assertEqual(ProductoAplicado.objects.de_empresa(una_empresa()).count(), 1)
        historial = self.api.get("/api/v1/me/historial/")
        self.assertEqual(historial.status_code, 200)

    def test_sin_lote_400_en_productos_aplicados_i_lote(self):
        r = self._aplicar(self._producto(dosis_variable=True), lote="")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("productos_aplicados.0.lote", r.data["campos"])
        self.assertFalse(Revision.objects.de_empresa(una_empresa()).exists())


class AbrirSinEscaneoApiTests(ApiVisitasBase):
    def _abrir(self, visita, api=None, **cuerpo):
        return (api or self.api).post(
            f"/api/v1/visitas/{visita.pk}/abrir/", cuerpo, format="json"
        )

    def test_turno_pendiente_propio_se_abre_con_incidencia(self):
        visita = self._visita(self.empleado)
        ItemTurno.objects.create(visita=visita, punto=self.punto, servicio=self.tipo)
        r = self._abrir(visita, latitud="-36.1", longitud="-57.8", precision_m="9")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["id"], visita.pk)
        self.assertEqual(r.data["estado"], "abierta")
        visita.refresh_from_db()
        self.assertTrue(visita.incidencia_apertura_sin_escaneo)
        self.assertEqual(self._abrir(visita).status_code, 200)

    def test_turno_ajeno_404(self):
        visita = self._visita(self.otro)
        self.assertEqual(self._abrir(visita).status_code, 404)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.PENDIENTE)

    def test_turno_de_otra_empresa_404(self):
        a, b = dos_empresas()
        Visita.objects.de_empresa(b.empresa).update(estado=Visita.Estado.PENDIENTE)
        r = self._abrir(b.visita, api=self._api(a.empleado))
        self.assertEqual(r.status_code, 404, r.content)

    def test_turno_no_pendiente_409(self):
        realizada = self._realizada(self.empleado, 2)
        r = self._abrir(realizada)
        self.assertEqual(r.status_code, 409, r.content)
        futura = self._visita(
            self.empleado, programada_para=timezone.localdate() + timedelta(days=3)
        )
        self.assertEqual(self._abrir(futura).status_code, 409)

    def test_abierta_en_futura_400(self):
        visita = self._visita(self.empleado)
        futura = (timezone.now() + timedelta(days=2)).isoformat()
        r = self._abrir(visita, abierta_en=futura)
        self.assertEqual(r.status_code, 400, r.content)

    def test_revision_sin_qr_codigo_sigue_400(self):
        visita = self._visita(self.empleado)
        self._abrir(visita)
        r = self.api.post(
            "/api/v1/revisiones/",
            self._cuerpo(visita, qr_codigo=None),
            format="multipart",
        )
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("qr_codigo", r.data["campos"])


class RevisadoPorOtroTests(ApiVisitasBase):
    def _turno(self, puntos):
        visita = self._visita(self.empleado)
        for punto in puntos:
            ItemTurno.objects.create(visita=visita, punto=punto, servicio=self.tipo)
        return visita

    def _revisar_otro(self, punto, **extra):
        visita = self._visita(self.otro, estado=Visita.Estado.ABIERTA)
        visita.abierta_en = timezone.now() - timedelta(hours=1)
        visita.save()
        return Revision.objects.create(
            visita=visita,
            punto=punto,
            servicio=self.tipo,
            orden=1,
            realizada_en=extra.pop("realizada_en", timezone.now()),
            recibida_en=timezone.now(),
            **extra,
        )

    def _items(self, respuesta):
        return respuesta.data["results"][0]["items"]

    def test_item_revisado_hoy_por_otro_trae_revisado_por_otro(self):
        self._turno([self.punto])
        revision = self._revisar_otro(self.punto)
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 200, r.content)
        dato = self._items(r)[0]["revisado_por_otro"]
        self.assertEqual(dato["operario"], {"nombre": "otro"})
        self.assertIn(
            timezone.localtime(revision.realizada_en).strftime("%H:%M"),
            dato["realizada_en"],
        )

    def test_revision_propia_o_de_ayer_es_null(self):
        visita = self._turno([self.punto])
        self.assertIsNone(
            self._items(self.api.get("/api/v1/me/visitas/"))[0]["revisado_por_otro"]
        )
        self._revisar_otro(
            self.punto, realizada_en=timezone.now() - timedelta(days=1, hours=1)
        )
        self.assertIsNone(
            self._items(self.api.get("/api/v1/me/visitas/"))[0]["revisado_por_otro"]
        )
        propia = self._visita(self.empleado, estado=Visita.Estado.ABIERTA)
        Revision.objects.create(
            visita=propia,
            punto=self.punto,
            servicio=self.tipo,
            orden=1,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
        )
        self.assertEqual(visita.items.count(), 1)
        for turno in self.api.get("/api/v1/me/visitas/").data["results"]:
            for item in turno["items"]:
                self.assertIsNone(item["revisado_por_otro"])

    def _consultas(self, cantidad):
        puntos = [
            PuntoControl.objects.create(
                sitio=self.sitio, nombre=f"P{i}", servicio=self.tipo
            )
            for i in range(cantidad)
        ]
        self._turno(puntos)
        for punto in puntos:
            self._revisar_otro(punto)
        with CaptureQueriesContext(connection) as consultas:
            r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(len(self._items(r)), cantidad)
        return len(consultas)

    def test_consultas_iguales_con_5_y_50_items(self):
        con_5 = self._consultas(5)
        Visita.objects.de_empresa(una_empresa()).filter(empleado=self.empleado).delete()
        self.assertEqual(self._consultas(50), con_5)

    def test_detalle_trae_revisado_por_otro(self):
        visita = self._turno([self.punto])
        self._revisar_otro(self.punto)
        r = self.api.get(f"/api/v1/me/visitas/{visita.pk}/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(
            r.data["items"][0]["revisado_por_otro"]["operario"], {"nombre": "otro"}
        )
