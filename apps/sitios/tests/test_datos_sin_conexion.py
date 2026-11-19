"""`GET me/datos-sin-conexion/`: puntos y servicios para trabajar sin conexión."""

import datetime
import hashlib

from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.sitios.tests.ayudas_empresa import DatosDeDosEmpresas
from apps.visitas.models import Revision, Visita

URL = "/api/v1/me/datos-sin-conexion/"


def _agregar_puntos(sitio, cantidad, desde=0):
    """Crea `cantidad` puntos activos en el sitio sin pasar por `save()`."""
    PuntoControl.objects.bulk_create(
        PuntoControl(
            empresa=sitio.empresa, sitio=sitio, nombre=f"Punto extra {desde + i}"
        )
        for i in range(cantidad)
    )


class DatosSinConexionTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        cache.clear()
        self.crear_empresas()
        self.api = APIClient()
        self.api.force_authenticate(self.empleado_a)

    def _pedir(self, **extra):
        return self.api.get(URL, **extra)

    def test_solo_puntos_de_la_empresa(self):
        respuesta = self._pedir()
        self.assertEqual(respuesta.status_code, 200)
        ids = {p["id"] for p in respuesta.data["puntos"]}
        self.assertEqual(ids, {self.punto_a.id})
        self.assertEqual(
            {s["id"] for s in respuesta.data["servicios"]}, {self.servicio_a.id}
        )

    def test_excluye_puntos_sitios_y_clientes_inactivos(self):
        inactivo = PuntoControl.objects.create(
            sitio=self.sitio_a, nombre="Inactivo", activo=False
        )
        sitio_baja = Sitio.objects.create(
            cliente=self.cliente_a, nombre="Sitio baja", activo=False
        )
        cliente_baja = Cliente.objects.create(
            razon_social="Baja", empresa=self.empresa_a, activo=False
        )
        sitio_cliente_baja = Sitio.objects.create(
            cliente=cliente_baja, nombre="Sitio de cliente baja"
        )
        TipoServicio.objects.create(nombre="Baja", empresa=self.empresa_a, activo=False)
        respuesta = self._pedir()
        ids = {p["id"] for p in respuesta.data["puntos"]}
        self.assertEqual(ids, {self.punto_a.id})
        self.assertNotIn(inactivo.id, ids)
        self.assertEqual(len(respuesta.data["servicios"]), 1)
        self.assertTrue(sitio_baja.puntos.exists())
        self.assertTrue(sitio_cliente_baja.puntos.exists())

    def test_consultas_iguales_con_50_y_500_puntos(self):
        _agregar_puntos(self.sitio_a, 49)
        with CaptureQueriesContext(connection) as con_50:
            self.assertEqual(len(self._pedir().data["puntos"]), 50)
        _agregar_puntos(self.sitio_a, 450, desde=49)
        with CaptureQueriesContext(connection) as con_500:
            self.assertEqual(len(self._pedir().data["puntos"]), 500)
        self.assertEqual(len(con_50), len(con_500))

    def test_mismo_etag_responde_304(self):
        primera = self._pedir()
        etag = primera["ETag"]
        self.assertTrue(etag)
        repetida = self._pedir(HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(repetida.status_code, 304)
        self.assertEqual(repetida["ETag"], etag)
        self.punto_a.nombre = "Otro nombre"
        self.punto_a.save()
        cambiada = self._pedir(HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(cambiada.status_code, 200)
        self.assertNotEqual(cambiada["ETag"], etag)

    def test_cache_control_no_store(self):
        primera = self._pedir()
        self.assertEqual(primera["Cache-Control"], "private, no-store")
        repetida = self._pedir(HTTP_IF_NONE_MATCH=primera["ETag"])
        self.assertEqual(repetida.status_code, 304)
        self.assertEqual(repetida["Cache-Control"], "private, no-store")

    def test_campos_de_punto_y_servicios_activos(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.servicio_a,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )
        self.punto_a.servicio = self.servicio_a
        self.punto_a.frecuencia_dias = 30
        self.punto_a.sector = "Cocina"
        self.punto_a.proximo_vencimiento = timezone.localdate() + datetime.timedelta(
            days=20
        )
        self.punto_a.save()
        visita = Visita.objects.create(
            sitio=self.sitio_a,
            empleado=self.empleado_a,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
            cuenta_como_servicio=True,
        )
        hace_dos_dias = timezone.now() - datetime.timedelta(days=2)
        for hora in (hace_dos_dias, hace_dos_dias - datetime.timedelta(days=1)):
            Revision.objects.create(
                visita=visita,
                punto=self.punto_a,
                servicio=self.servicio_a,
                realizada_en=hora,
                recibida_en=timezone.now(),
            )
        datos = self._pedir().data
        punto = datos["puntos"][0]
        self.assertEqual(
            set(punto),
            {
                "id",
                "qr_hash",
                "nombre",
                "sector",
                "sitio",
                "servicio",
                "estado",
                "proximo_vencimiento",
                "ultima_revision_fecha",
            },
        )
        self.assertEqual(punto["servicio"], self.servicio_a.id)
        self.assertEqual(punto["sector"], "Cocina")
        self.assertEqual(punto["estado"], "al_dia")
        self.assertEqual(
            set(punto["sitio"]), {"id", "nombre", "direccion", "localidad"}
        )
        self.assertEqual(punto["sitio"]["id"], self.sitio_a.id)
        self.assertTrue(punto["ultima_revision_fecha"])
        servicio = datos["servicios"][0]
        self.assertEqual(
            set(servicio),
            {"id", "nombre", "slug", "esquema_punto", "esquema_visita"},
        )
        self.assertEqual(servicio["esquema_punto"][0]["clave"], "cebos")
        self.assertEqual(servicio["esquema_visita"], [])

    def test_ultima_revision_ignora_visitas_que_no_cuentan(self):
        visita = Visita.objects.create(
            sitio=self.sitio_a,
            empleado=self.empleado_a,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
            cuenta_como_servicio=False,
        )
        Revision.objects.create(
            visita=visita,
            punto=self.punto_a,
            servicio=self.servicio_a,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
        )
        self.assertIsNone(self._pedir().data["puntos"][0]["ultima_revision_fecha"])

    def _visita_contada(self):
        return Visita.objects.create(
            sitio=self.sitio_a,
            empleado=self.empleado_a,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
            cuenta_como_servicio=True,
        )

    def _revision_en(self, visita, hora):
        Revision.objects.create(
            visita=visita,
            punto=self.punto_a,
            servicio=self.servicio_a,
            realizada_en=hora,
            recibida_en=timezone.now(),
        )

    def test_ultima_revision_fecha_es_solo_la_fecha_de_la_mas_reciente(self):
        visita = self._visita_contada()
        antigua = timezone.now() - datetime.timedelta(days=5)
        reciente = timezone.now() - datetime.timedelta(days=1)
        self._revision_en(visita, antigua)
        self._revision_en(visita, reciente)
        valor = self._pedir().data["puntos"][0]["ultima_revision_fecha"]
        self.assertEqual(valor, timezone.localdate(reciente).isoformat())
        self.assertNotIn("T", valor)

    def test_ultima_revision_fecha_usa_el_dia_local_cerca_de_medianoche(self):
        visita = self._visita_contada()
        # 01:30 UTC del 10 es 22:30 del 9 en Buenos Aires (UTC-3).
        hora = datetime.datetime(2026, 5, 10, 1, 30, tzinfo=datetime.timezone.utc)
        self._revision_en(visita, hora)
        valor = self._pedir().data["puntos"][0]["ultima_revision_fecha"]
        self.assertEqual(valor, "2026-05-09")

    def test_entrega_qr_hash_y_nunca_qr_codigo(self):
        respuesta = self._pedir()
        punto = respuesta.data["puntos"][0]
        esperado = hashlib.sha256(str(self.punto_a.qr_codigo).encode()).hexdigest()
        self.assertEqual(punto["qr_hash"], esperado)
        self.assertNotIn("qr_codigo", punto)
        self.assertNotIn(str(self.punto_a.qr_codigo), respuesta.content.decode())

    def test_anonimo_401(self):
        self.assertEqual(APIClient().get(URL).status_code, 401)

    def test_administrador_puede_y_plataforma_no(self):
        admin = APIClient()
        admin.force_authenticate(self.admin_a)
        self.assertEqual(admin.get(URL).status_code, 200)
        plataforma = User.objects.create_user(
            "plat", password="clave-segura-123", rol=User.Rol.PLATAFORMA
        )
        cliente = APIClient()
        cliente.force_authenticate(plataforma)
        self.assertEqual(cliente.get(URL).status_code, 403)
