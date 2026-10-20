import json
import shutil
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas import api_views
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-api-test-")


def jpeg_chico():
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("f.jpg", buffer.getvalue(), content_type="image/jpeg")


class BaseApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cache.clear()
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(
            cliente=cliente,
            nombre="Planta 1",
            direccion="Calle 1",
            localidad="Castelli",
            latitud="-36.100000",
            longitud="-57.800000",
        )
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.empleado = self._usuario("emp", User.Rol.EMPLEADO)
        self.otro = self._usuario("otro", User.Rol.EMPLEADO)
        self.admin = self._usuario("adm", User.Rol.ADMINISTRADOR)
        self.punto = self.sitio.puntos.get(orden=0)
        self.punto.servicio = self.tipo
        self.punto.save()
        self.api = self._api(self.empleado)

    def _usuario(self, nombre, rol):
        return User.objects.create_user(username=nombre, password="x", rol=rol)

    def _api(self, usuario):
        api = APIClient()
        api.force_authenticate(usuario)
        return api

    def _visita(self, empleado, **extra):
        extra.setdefault("origen", Visita.Origen.MANUAL)
        extra.setdefault("motivo_manual", "Carga")
        return Visita.objects.create(sitio=self.sitio, empleado=empleado, **extra)

    def _revision(self, visita, **extra):
        extra.setdefault("realizada_en", timezone.now())
        extra.setdefault("recibida_en", extra["realizada_en"])
        extra.setdefault("orden", visita.revisiones.count() + 1)
        extra.setdefault("servicio", self.tipo)
        return Revision.objects.create(visita=visita, punto=self.punto, **extra)

    def _realizada(self, empleado, dia):
        """Visita realizada ese día de septiembre, con su revisión General."""
        cerrada = timezone.make_aware(datetime(2026, 9, dia, 12, 0))
        visita = self._visita(
            empleado,
            estado=Visita.Estado.REALIZADA,
            abierta_en=cerrada,
            cerrada_en=cerrada,
            cierre=Visita.Cierre.EMPLEADO,
        )
        self._revision(visita, realizada_en=cerrada)
        return visita


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ApiVisitasBase(BaseApiTests):
    """Cuerpos y llamadas comunes a abrir, revisiones y cerrar."""

    def setUp(self):
        super().setUp()
        self.producto = Producto.objects.create(nombre_comercial="Cebo X")

    def _abierta(self, empleado=None, **extra):
        extra.setdefault("origen", Visita.Origen.APP)
        extra.setdefault("motivo_manual", "")
        extra.setdefault("estado", Visita.Estado.ABIERTA)
        extra.setdefault("abierta_en", timezone.now() - timedelta(hours=1))
        return self._visita(empleado or self.empleado, **extra)

    def _cuerpo(self, visita, **cambios):
        cuerpo = {
            "visita": visita.id,
            "qr_codigo": str(self.punto.qr_codigo),
            "cliente_uuid": str(uuid4()),
            "realizada_en": (timezone.now() - timedelta(minutes=1)).isoformat(),
            "latitud": "-36.100000",
            "longitud": "-57.800000",
            "precision_m": "8.5",
            "datos": json.dumps({"cebos": 3}),
            "fotos": [jpeg_chico()],
        }
        cuerpo.update(cambios)
        return {k: v for k, v in cuerpo.items() if v is not None}

    def _post(self, visita, api=None, **cambios):
        return (api or self.api).post(
            "/api/v1/revisiones/", self._cuerpo(visita, **cambios), format="multipart"
        )

    def _cerrar(self, visita, api=None, cuerpo=None):
        return (api or self.api).post(
            f"/api/v1/visitas/{visita.id}/cerrar/", cuerpo or {}, format="json"
        )


class FlujoRevisionesTests(ApiVisitasBase):
    def test_abrir_tres_revisiones_cerrar(self):
        self.punto.frecuencia_dias = 30
        self.punto.save()
        pendiente = self._visita(self.empleado, programada_para=date(2026, 9, 1))
        sala = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Sala", servicio=self.tipo
        )
        galpon = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Galpón", servicio=self.tipo
        )

        r = self.api.post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(self.punto.qr_codigo)},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["id"], pendiente.id)
        self.assertEqual(r.data["estado"], "abierta")
        r = self.api.post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(self.punto.qr_codigo)},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.data["id"], pendiente.id)
        self.assertEqual(Visita.objects.count(), 1)

        for punto in (self.punto, sala, galpon):
            r = self._post(pendiente, qr_codigo=str(punto.qr_codigo))
            self.assertEqual(r.status_code, 201, r.content)
            self.assertEqual(r.data["punto"], {"id": punto.id, "nombre": punto.nombre})
            self.assertNotIn("latitud", r.data)
        self.assertEqual(pendiente.revisiones.count(), 3)
        self.punto.refresh_from_db()
        self.assertIsNotNone(self.punto.proximo_vencimiento)

        r = self._cerrar(pendiente, cuerpo={"observaciones": "Todo en orden"})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.data["revisiones"]), 3)
        self.assertNotIn("latitud", r.data)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.REALIZADA)
        self.assertEqual(pendiente.cierre, Visita.Cierre.EMPLEADO)

        historial = self.api.get("/api/v1/me/historial/")
        self.assertEqual([v["id"] for v in historial.data["results"]], [pendiente.id])
        revisiones = historial.data["results"][0]["revisiones"]
        self.assertEqual(
            {r["punto"]["nombre"] for r in revisiones},
            {"General", "Sala", "Galpón"},
        )
        self.assertEqual(self.api.get("/api/v1/me/visitas/").data["results"], [])

    def test_post_visitas_ya_no_existe(self):
        r = self.api.post("/api/v1/visitas/", {}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_revision_en_visita_cerrada_o_pendiente_se_rechaza(self):
        casos = {
            "cerrada": self._realizada(self.empleado, 2),
            "pendiente": self._visita(self.empleado),
        }
        for nombre, visita in casos.items():
            with self.subTest(nombre):
                r = self._post(visita)
                self.assertEqual(r.status_code, 400, r.content)
                self.assertIn("visita", r.data["campos"])
        self.assertEqual(Revision.objects.filter(cliente_uuid__isnull=False).count(), 0)

    def test_las_tres_rutas_comparten_el_throttle_crear_visita(self):
        for vista in (
            api_views.AbrirVisitaView,
            api_views.CrearRevisionView,
            api_views.CerrarVisitaView,
        ):
            self.assertEqual(vista.throttle_scope, "crear_visita")

    def test_administrador_usa_las_rutas_de_escritura_sin_tocar_el_vencimiento(self):
        self.punto.frecuencia_dias = 30
        self.punto.save()
        admin = self._api(self.admin)
        r = admin.post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(self.punto.qr_codigo)},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        visita = Visita.objects.get(pk=r.data["id"])
        self.assertEqual(visita.empleado, self.admin)
        self.assertEqual(self._post(visita, api=admin).status_code, 201)
        self.assertEqual(self._cerrar(visita, api=admin).status_code, 200)
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.proximo_vencimiento)
        self.assertEqual(APIClient().post("/api/v1/revisiones/").status_code, 401)


class AbrirVisitaTests(ApiVisitasBase):
    def _abrir(self, **cuerpo):
        cuerpo.setdefault("qr_codigo", str(self.punto.qr_codigo))
        return self.api.post("/api/v1/visitas/abrir/", cuerpo, format="json")

    def test_sin_pendiente_crea_con_origen_app(self):
        r = self._abrir()
        self.assertEqual(r.status_code, 201, r.content)
        visita = Visita.objects.get(pk=r.data["id"])
        self.assertEqual(visita.origen, Visita.Origen.APP)
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
        self.assertFalse(visita.incidencia_asignacion)
        self.assertEqual(self._abrir().status_code, 200)
        self.assertEqual(Visita.objects.count(), 1)

    def test_pendiente_de_otro_marca_incidencia_asignacion(self):
        ajena = self._visita(self.otro, programada_para=date(2026, 9, 1))
        r = self._abrir()
        self.assertEqual(r.status_code, 201, r.content)
        nueva = Visita.objects.get(pk=r.data["id"])
        self.assertNotEqual(nueva.id, ajena.id)
        self.assertTrue(nueva.incidencia_asignacion)
        ajena.refresh_from_db()
        self.assertEqual(ajena.estado, Visita.Estado.PENDIENTE)

    def test_precision_fuera_de_rango_da_400(self):
        for precision in ("100000", "99999.9"):
            r = self._abrir(precision_m=precision)
            with self.subTest(precision=precision):
                self.assertEqual(r.status_code, 400 if precision == "100000" else 201)
                if r.status_code == 400:
                    self.assertIn("precision_m", r.data["campos"])
                else:
                    visita = Visita.objects.get(pk=r.data["id"])
                    self.assertEqual(visita.precision_m, Decimal("99999.90"))

    def test_sitio_inactivo_da_400(self):
        self.sitio.activo = False
        self.sitio.save()
        r = self._abrir()
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("qr_codigo", r.data["campos"])
        self.assertFalse(Visita.objects.exists())

    def test_qr_invalido_da_400_con_el_mismo_mensaje(self):
        inactivo = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Baja", activo=False
        )
        sin_qr = self.api.post("/api/v1/visitas/abrir/", {}, format="json")
        self.assertEqual(sin_qr.status_code, 400, sin_qr.content)
        self.assertIn("qr_codigo", sin_qr.data["campos"])
        inexistente = self._abrir(qr_codigo=str(uuid4()))
        self.assertEqual(inexistente.status_code, 400, inexistente.content)
        # Mismo mensaje que un QR inexistente: no se distingue el motivo.
        inactivo_r = self._abrir(qr_codigo=str(inactivo.qr_codigo))
        self.assertEqual(inactivo_r.status_code, 400, inactivo_r.content)
        self.assertEqual(
            inactivo_r.data["campos"]["qr_codigo"],
            inexistente.data["campos"]["qr_codigo"],
        )
        self.assertFalse(Visita.objects.exists())


class CrearRevisionTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta()

    def _enviar(self, api=None, **cambios):
        return self._post(self.visita, api=api, **cambios)

    def test_crea_revision_con_fotos_y_productos(self):
        productos = [
            {
                "producto": self.producto.id,
                "lote": "L1",
                "dosis": "2.5",
                "unidad_dosis": "ml/l",
                "cantidad": "10",
                "unidad": "unidad",
            }
        ]
        r = self._enviar(
            fotos=[jpeg_chico(), jpeg_chico()],
            productos_aplicados=json.dumps(productos),
            observaciones="Todo en orden",
        )
        self.assertEqual(r.status_code, 201, r.content)
        revision = Revision.objects.get(pk=r.data["id"])
        self.assertEqual(revision.visita, self.visita)
        self.assertEqual(Foto.objects.filter(revision=revision).count(), 2)
        self.assertEqual(ProductoAplicado.objects.filter(revision=revision).count(), 1)
        self.assertEqual(len(r.data["fotos"]), 2)
        self.assertEqual(r.data["productos"][0]["lote"], "L1")
        self.assertNotIn("latitud", r.data)
        self.assertNotIn("longitud", r.data)

    def test_qr_invalido_da_400(self):
        for codigo in (str(uuid4()), "basura"):
            with self.subTest(codigo=codigo):
                r = self._enviar(qr_codigo=codigo)
                self.assertEqual(r.status_code, 400)
                self.assertIn("qr_codigo", r.data["campos"])
        self.assertFalse(Revision.objects.exists())

    def test_qr_de_un_punto_de_otro_sitio_da_400(self):
        otro_sitio = Sitio.objects.create(
            cliente=self.sitio.cliente,
            nombre="Planta 2",
            direccion="Calle 2",
            localidad="Castelli",
        )
        ajeno = otro_sitio.puntos.get(orden=0)
        r = self._enviar(qr_codigo=str(ajeno.qr_codigo))
        self.assertEqual(r.status_code, 400)
        self.assertIn("qr_codigo", r.data["campos"])

    def test_sin_foto_se_acepta(self):
        r = self._enviar(fotos=None)
        self.assertEqual(r.status_code, 201, r.content)

    def test_coordenadas_obligatorias(self):
        for campo in ("latitud", "longitud"):
            with self.subTest(campo=campo):
                r = self._enviar(**{campo: None})
                self.assertEqual(r.status_code, 400, r.content)
                self.assertIn(campo, r.data["campos"])
        self.assertFalse(Revision.objects.exists())

    def test_mas_de_dos_fotos_da_400(self):
        r = self._enviar(fotos=[jpeg_chico() for _ in range(3)])
        self.assertEqual(r.status_code, 400)
        self.assertIn("fotos", r.data["campos"])
        self.assertFalse(Revision.objects.exists())

    def test_datos_invalidos_contra_esquema_da_400(self):
        r = self._enviar(datos=json.dumps({"cebos": "mucho", "otra": 1}))
        self.assertEqual(r.status_code, 400)
        self.assertIn("datos", r.data["campos"])
        r = self._enviar(datos="no es json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("datos", r.data["campos"])

    def test_reintento_con_mismo_cliente_uuid_da_409(self):
        clave = str(uuid4())
        primera = self._enviar(cliente_uuid=clave)
        self.assertEqual(primera.status_code, 201, primera.content)
        r = self._enviar(cliente_uuid=clave)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["revision"], primera.data["id"])
        self.assertEqual(r.data["visita"], self.visita.id)
        self.assertEqual(r.data["detalle"], "La revisión ya fue registrada.")
        ajena = self._abierta(self.otro)
        r = self._post(ajena, api=self._api(self.otro), cliente_uuid=clave)
        self.assertEqual(r.status_code, 409)
        self.assertNotIn("visita", r.data)
        self.assertNotIn("revision", r.data)
        self.assertEqual(Revision.objects.count(), 1)

    def test_producto_fuera_del_catalogo_da_400(self):
        productos = [
            {
                "producto": 99999,
                "lote": "L",
                "dosis": "1",
                "unidad_dosis": "ml",
                "cantidad": "1",
                "unidad": "unidad",
            }
        ]
        r = self._enviar(productos_aplicados=json.dumps(productos))
        self.assertEqual(r.status_code, 400)
        self.assertIn("productos_aplicados.0.producto", r.data["campos"])
        self.assertFalse(Revision.objects.exists())

    def test_cliente_uuid_es_obligatorio(self):
        r = self._enviar(cliente_uuid=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn("cliente_uuid", r.data["campos"])

    def test_topes_de_coordenadas_precision_y_productos(self):
        for cambio in (
            {"latitud": "90.5"},
            {"longitud": "-180.1"},
            {"latitud": "-36.1234567"},
            {"precision_m": "-1"},
            {"precision_m": "8.55"},
            {"productos_aplicados": json.dumps([{}] * 31)},
            {"productos_aplicados": json.dumps(["x"])},
        ):
            with self.subTest(cambio=cambio):
                r = self._enviar(**cambio)
                self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(Revision.objects.exists())

    def test_foto_de_mas_de_8_mb_da_400(self):
        grande = SimpleUploadedFile(
            "g.jpg", b"0" * (8 * 1024 * 1024 + 1), content_type="image/jpeg"
        )
        r = self._enviar(fotos=[grande])
        self.assertEqual(r.status_code, 400)
        self.assertIn("fotos.0", r.data["campos"])

    def test_textos_libres_tienen_tope(self):
        for campo in ("observaciones", "incidencia_detalle"):
            with self.subTest(campo=campo):
                r = self._enviar(**{campo: "x" * 2001})
                self.assertEqual(r.status_code, 400, r.content)
                self.assertIn(campo, r.data["campos"])
        self.assertEqual(self._enviar(observaciones="x" * 2000).status_code, 201)

    def test_pedido_demasiado_grande_da_413_sin_escribir_a_disco(self):
        with mock.patch(
            "django.core.files.uploadhandler.TemporaryFileUploadHandler.new_file"
        ) as nuevo_archivo:
            r = self.api.post(
                "/api/v1/revisiones/",
                self._cuerpo(self.visita),
                format="multipart",
                CONTENT_LENGTH=str(11 * 1024 * 1024 * 10),
            )
        self.assertEqual(r.status_code, 413)
        self.assertEqual(r.data["detalle"], "El pedido supera el tamaño permitido.")
        nuevo_archivo.assert_not_called()
        self.assertFalse(Revision.objects.exists())

    def test_demasiados_archivos_da_413(self):
        r = self._enviar(fotos=[jpeg_chico() for _ in range(101)])
        self.assertEqual(r.status_code, 413)
        self.assertFalse(Revision.objects.exists())


class RevisionesTests(ApiVisitasBase):
    def test_409_no_expone_visita_ajena(self):
        clave = str(uuid4())
        de_otro = self._abierta(self.otro)
        primera = self._post(de_otro, api=self._api(self.otro), cliente_uuid=clave)
        self.assertEqual(primera.status_code, 201, primera.content)
        propia = self._abierta()
        for visita in (propia, de_otro):
            with self.subTest(visita=visita.pk):
                r = self._post(visita, cliente_uuid=clave)
                self.assertEqual(r.status_code, 409)
                self.assertEqual(
                    r.json(),
                    {"detalle": "La revisión ya fue registrada.", "campos": {}},
                )
        self.assertEqual(Revision.objects.count(), 1)
        # El dueño sí recibe los ids para reconciliar.
        r = self._post(de_otro, api=self._api(self.otro), cliente_uuid=clave)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data["revision"], primera.data["id"])
        self.assertEqual(r.data["visita"], de_otro.id)


class CerrarVisitaApiTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta()

    def test_sin_revisiones_da_400(self):
        r = self._cerrar(self.visita)
        self.assertEqual(r.status_code, 400, r.content)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, Visita.Estado.ABIERTA)

    def test_planilla_de_visita_invalida_da_400_y_valida_cierra(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo,
            orden=2,
            etiqueta="Resumen",
            clave="resumen",
            tipo=CampoPlanilla.Tipo.TEXTO,
            ambito=CampoPlanilla.Ambito.VISITA,
            obligatorio=True,
        )
        self._post(self.visita)
        r = self._cerrar(self.visita)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("datos", r.data["campos"])
        r = self._cerrar(
            self.visita,
            cuerpo={"datos": {self.tipo.slug: {"resumen": "ok"}}, "incidencia": True},
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.data["incidencia"])
        self.assertEqual(r.data["datos"], {self.tipo.slug: {"resumen": "ok"}})


class CerrarVisitaTests(ApiVisitasBase):
    def test_cerrar_dos_veces_mismo_empleado_da_200(self):
        visita = self._abierta()
        self._post(visita)
        primera = self._cerrar(visita)
        self.assertEqual(primera.status_code, 200, primera.content)
        segunda = self._cerrar(visita)
        self.assertEqual(segunda.status_code, 200, segunda.content)
        self.assertEqual(segunda.data["id"], visita.id)
        self.assertEqual(len(segunda.data["revisiones"]), 1)

    def test_cerrada_por_otro_da_409(self):
        for cierre in (Visita.Cierre.SISTEMA, Visita.Cierre.ADMINISTRADOR):
            with self.subTest(cierre=cierre):
                visita = self._abierta(
                    estado=Visita.Estado.REALIZADA,
                    cerrada_en=timezone.now(),
                    cierre=cierre,
                )
                self._revision(visita)
                r = self._cerrar(visita)
                self.assertEqual(r.status_code, 409, r.content)
                self.assertEqual(r.data["detalle"], "La visita ya fue cerrada.")
                visita.refresh_from_db()
                self.assertEqual(visita.cierre, cierre)


class VisitaAjenaTests(ApiVisitasBase):
    def test_ajena_e_inexistente_dan_el_mismo_404(self):
        ajena = self._abierta(self.otro)
        self._revision(ajena)
        inexistente = SimpleNamespace(id=999999)
        cuerpos = []
        for nombre, visita in (("ajena", ajena), ("inexistente", inexistente)):
            with self.subTest(nombre):
                for r in (self._post(visita), self._cerrar(visita)):
                    self.assertEqual(r.status_code, 404, r.content)
                    cuerpos.append(r.json())
        self.assertEqual(len(cuerpos), 4)
        self.assertTrue(all(c == cuerpos[0] for c in cuerpos))
        self.assertEqual(cuerpos[0]["detalle"], "La visita no existe.")
        ajena.refresh_from_db()
        self.assertEqual(ajena.estado, Visita.Estado.ABIERTA)
        self.assertEqual(ajena.revisiones.count(), 1)


class MisVisitasTests(BaseApiTests):
    def test_solo_pendientes_y_abiertas_propias(self):
        propia = self._visita(self.empleado, programada_para=date(2026, 9, 1))
        abierta = self._visita(
            self.empleado,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
        )
        self._visita(self.otro, programada_para=date(2026, 9, 1))
        self._realizada(self.empleado, 2)
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([v["id"] for v in r.data["results"]], [abierta.id, propia.id])
        self.assertEqual(
            [v["estado"] for v in r.data["results"]], ["abierta", "pendiente"]
        )
        item = r.data["results"][1]
        self.assertEqual(
            item["sitio"],
            {
                "id": self.sitio.id,
                "nombre": "Planta 1",
                "direccion": "Calle 1",
                "localidad": "Castelli",
            },
        )
        self.assertEqual(item["programada_para"], "2026-09-01")
        self.assertNotIn("latitud", item)
        r = self._api(self.admin).get("/api/v1/me/visitas/")
        self.assertEqual((r.status_code, r.data["results"]), (200, []))
        self.assertEqual(APIClient().get("/api/v1/me/visitas/").status_code, 401)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class HistorialTests(BaseApiTests):
    def test_solo_visitas_propias_con_sus_revisiones(self):
        propia = self._realizada(self.empleado, 2)
        revision = propia.revisiones.get()
        revision.datos = {"cebos": 4}
        revision.latitud, revision.longitud = "-36.1", "-57.8"
        revision.save()
        Foto.objects.create(revision=revision, imagen=jpeg_chico())
        self._realizada(self.otro, 2)
        self._visita(self.empleado)
        r = self.api.get("/api/v1/me/historial/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([v["id"] for v in r.data["results"]], [propia.id])
        item = r.data["results"][0]
        self.assertNotIn("latitud", item)
        self.assertNotIn("longitud", item)
        (rev,) = item["revisiones"]
        self.assertNotIn("latitud", rev)
        self.assertNotIn("longitud", rev)
        self.assertEqual(rev["punto"], {"id": self.punto.id, "nombre": "General"})
        self.assertEqual(rev["datos"], {"cebos": 4})
        self.assertIn("realizada_en", rev)
        self.assertEqual(rev["productos"], [])
        codigo = Foto.objects.get(revision__visita=propia).codigo
        self.assertEqual(rev["fotos"], [f"/api/v1/fotos/{codigo}/"])

    def test_rango_de_fechas_filtra(self):
        ids = {dia: self._realizada(self.empleado, dia).id for dia in (1, 5, 10)}

        def pedir(**parametros):
            r = self.api.get("/api/v1/me/historial/", parametros)
            self.assertEqual(r.status_code, 200, r.content)
            return {v["id"] for v in r.data["results"]}

        self.assertEqual(
            pedir(desde="2026-09-05", hasta="2026-09-10"), {ids[5], ids[10]}
        )
        self.assertEqual(pedir(hasta="2026-09-01"), {ids[1]})
        self.assertEqual(pedir(desde="2026-09-11"), set())
        r = self.api.get("/api/v1/me/historial/", {"desde": "ayer"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("desde", r.data["campos"])


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoTests(BaseApiTests):
    def setUp(self):
        super().setUp()
        self.visita = self._realizada(self.empleado, 2)
        self.foto = Foto.objects.create(
            revision=self.visita.revisiones.get(), imagen=jpeg_chico()
        )
        self.url = f"/api/v1/fotos/{self.foto.codigo}/"

    def test_foto_se_sirve_al_dueno_y_403_a_otro(self):
        r = self.api.get(self.url, HTTP_ACCEPT="image/jpeg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertEqual(r["Cache-Control"], "private, no-store")
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertTrue(b"".join(r.streaming_content).startswith(b"\xff\xd8"))
        r = self._api(self.otro).get(self.url)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["campos"], {})
        self.assertEqual(self.api.get(f"/api/v1/fotos/{uuid4()}/").status_code, 404)
        self.assertEqual(APIClient().get(self.url).status_code, 401)

    def test_foto_de_revision_ajena_da_403(self):
        ajena = self._realizada(self.otro, 3)
        foto = Foto.objects.create(revision=ajena.revisiones.get(), imagen=jpeg_chico())
        r = self.api.get(f"/api/v1/fotos/{foto.codigo}/")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self._api(self.otro).get(self.url).status_code, 403)

    def test_administrador_ve_la_foto(self):
        r = self._api(self.admin).get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        r.close()
