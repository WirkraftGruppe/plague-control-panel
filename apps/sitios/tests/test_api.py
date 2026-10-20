import datetime
import io
import tempfile
import uuid
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.api_views import (
    MAX_BYTES_PEDIDO_PUNTO,
    AltaPuntoView,
    AltaSitioView,
    UbicacionPuntoView,
)
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sitios-api-test-")


def crear_plano(sitio, nombre="Planta baja", **extra):
    """Plano con un PNG real de 40x20 px (el modelo lo procesa al guardar)."""
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buffer, "PNG")
    archivo = SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")
    return Plano.objects.create(sitio=sitio, nombre=nombre, imagen=archivo, **extra)


class ResolverQRTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(
            cliente=self.cliente,
            nombre="Planta 1",
            direccion="Calle 1",
            localidad="Castelli",
            latitud="-36.100000",
            longitud="-57.800000",
            contacto_en_sitio="Juan Contacto",
            telefono_en_sitio="2245-000000",
            horario_acceso="8 a 12",
            notas="Nota interna",
        )
        self.punto = self.sitio.puntos.get()
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.otro = User.objects.create_user(
            username="otro", password="x", rol=User.Rol.EMPLEADO
        )
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.cliente_api = APIClient()
        self.cliente_api.force_authenticate(self.empleado)

    def _visita(self, empleado, dias):
        return Visita.objects.create(
            sitio=self.sitio,
            empleado=empleado,
            origen=Visita.Origen.MANUAL,
            programada_para=datetime.date(2026, 1, 1) + datetime.timedelta(days=dias),
        )

    def _resolver(self, codigo=None, cliente=None):
        codigo = codigo or self.punto.qr_codigo
        return (cliente or self.cliente_api).post(f"/api/v1/qr/{codigo}/resolver/")

    def test_qr_valido_devuelve_punto_sitio_cliente_y_visitas_propias(self):
        r = self._resolver()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["sitio"],
            {"nombre": "Planta 1", "direccion": "Calle 1", "localidad": "Castelli"},
        )
        self.assertEqual(r.json()["cliente"], {"razon_social": "ACME"})
        self.assertIsNone(r.json()["visita_pendiente_propia"])
        self.assertIsNone(r.json()["visita_abierta_propia"])
        self.assertEqual(
            r.json()["punto"],
            {"id": self.punto.id, "nombre": "General", "sector": "", "plano": None},
        )

    def test_devuelve_punto_plano_y_visita_abierta(self):
        with override_settings(MEDIA_ROOT=MEDIA_TEMPORAL):
            plano = crear_plano(self.sitio)
        self.punto.plano = plano
        self.punto.x, self.punto.y = "0.2500", "0.5000"
        self.punto.save()
        vecino = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Depósito", plano=plano, x="0.7500", y="0.1000"
        )
        PuntoControl.objects.create(  # sin coordenadas: no aparece en el plano
            sitio=self.sitio, nombre="Sin ubicar", plano=plano
        )
        PuntoControl.objects.create(  # inactivo: no aparece
            sitio=self.sitio, nombre="Baja", plano=plano, x="0.1", y="0.1", activo=False
        )
        abierta = self._visita(self.empleado, 1)
        abierta.estado = Visita.Estado.ABIERTA
        abierta.abierta_en = "2026-01-02T10:00:00Z"
        abierta.save()
        pendiente = self._visita(self.empleado, 5)
        r = self._resolver()
        self.assertEqual(r.status_code, 200)
        cuerpo = r.json()
        self.assertEqual(
            cuerpo["punto"]["plano"],
            {
                "id": plano.id,
                "nombre": "Planta baja",
                "url": f"/api/v1/planos/{plano.id}/imagen/",
                "ancho_px": 40,
                "alto_px": 20,
                "puntos": [
                    {
                        "id": self.punto.id,
                        "nombre": "General",
                        "x": 0.25,
                        "y": 0.5,
                        "estado": "sin_programar",
                    },
                    {
                        "id": vecino.id,
                        "nombre": "Depósito",
                        "x": 0.75,
                        "y": 0.1,
                        "estado": "sin_programar",
                    },
                ],
            },
        )
        self.assertEqual(cuerpo["visita_abierta_propia"], abierta.id)
        self.assertEqual(cuerpo["visita_pendiente_propia"], pendiente.id)
        self.assertNotIn("latitud", r.content.decode())

    def test_plano_inactivo_no_se_devuelve(self):
        with override_settings(MEDIA_ROOT=MEDIA_TEMPORAL):
            plano = crear_plano(self.sitio, activo=False)
        self.punto.plano = plano
        self.punto.save()
        self.assertIsNone(self._resolver().json()["punto"]["plano"])

    def test_qr_inactivo_da_404_igual_que_inexistente(self):
        self.sitio.activo = False
        self.sitio.save()
        inactivo = self._resolver()
        inexistente = self._resolver(uuid.uuid4())
        self.assertEqual(inactivo.status_code, 404)
        self.assertEqual(inexistente.status_code, 404)
        self.assertEqual(inactivo.json(), inexistente.json())

    def test_qr_de_punto_inactivo_da_404(self):
        self.punto.activo = False
        self.punto.save()
        inactivo = self._resolver()
        inexistente = self._resolver(uuid.uuid4())
        self.assertEqual(inactivo.status_code, 404)
        self.assertEqual(inactivo.json(), inexistente.json())
        self.assertEqual(self.sitio.puntos.filter(activo=True).count(), 0)

    def test_cliente_inactivo_da_404(self):
        self.cliente.activo = False
        self.cliente.save()
        inactivo = self._resolver()
        inexistente = self._resolver(uuid.uuid4())
        self.assertEqual(inactivo.status_code, 404)
        self.assertEqual(inactivo.json(), inexistente.json())

    def test_administrador_resuelve_qr(self):
        cliente = APIClient()
        cliente.force_authenticate(self.admin)
        self.assertEqual(self._resolver(cliente=cliente).status_code, 200)
        self.assertEqual(self._resolver(cliente=APIClient()).status_code, 401)

    def test_respuesta_sin_coordenadas_ni_contactos(self):
        texto = self._resolver().content.decode()
        for prohibido in (
            "-36.1",
            "-57.8",
            "Juan Contacto",
            "2245-000000",
            "8 a 12",
            "Nota interna",
            "latitud",
            "notas",
        ):
            self.assertNotIn(prohibido, texto)

    def test_pendiente_propia_es_la_mas_antigua_del_sitio(self):
        self._visita(self.empleado, 10)
        antigua = self._visita(self.empleado, 1)
        self._visita(self.otro, 1)  # de otro empleado: no aparece
        realizada = self._visita(self.empleado, 1)
        realizada.estado = Visita.Estado.REALIZADA
        realizada.abierta_en = realizada.cerrada_en = "2026-01-02T10:00:00Z"
        realizada.save()
        cuerpo = self._resolver().json()
        self.assertEqual(cuerpo["visita_pendiente_propia"], antigua.id)
        self.assertIsNone(cuerpo["visita_abierta_propia"])

    def test_throttle_por_usuario(self):
        for _ in range(30):
            self.assertEqual(self._resolver().status_code, 200)
        self.assertEqual(self._resolver().status_code, 429)
        otro = APIClient()
        otro.force_authenticate(self.otro)
        self.assertEqual(self._resolver(cliente=otro).status_code, 200)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class PlanoApiTests(TestCase):
    def setUp(self):
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        self.otro_sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 2")
        self.plano = crear_plano(self.sitio)
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        self.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.ajeno = User.objects.create_user(
            username="ajeno", password="x", rol=User.Rol.EMPLEADO
        )
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.url = f"/api/v1/planos/{self.plano.id}/imagen/"

    def _visita(self, sitio, empleado, estado=Visita.Estado.PENDIENTE):
        return Visita.objects.create(
            sitio=sitio,
            empleado=empleado,
            origen=Visita.Origen.MANUAL,
            estado=estado,
            programada_para=datetime.date(2026, 1, 1),
        )

    def _get(self, usuario):
        api = APIClient()
        if usuario:
            api.force_authenticate(usuario)
        return api.get(self.url)

    def test_imagen_solo_con_visita_en_el_sitio(self):
        self.assertEqual(self._get(None).status_code, 401)
        self.assertEqual(self._get(self.empleado).status_code, 404)  # sin visita
        # visita propia en otro sitio, o ajena en este: sigue sin acceso
        self._visita(self.otro_sitio, self.empleado)
        self._visita(self.sitio, self.ajeno)
        self.assertEqual(self._get(self.empleado).status_code, 404)
        self._visita(self.sitio, self.empleado, Visita.Estado.CANCELADA)
        self.assertEqual(self._get(self.empleado).status_code, 404)

        visita = self._visita(self.sitio, self.empleado)
        respuesta = self._get(self.empleado)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "image/png")
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        contenido = b"".join(respuesta.streaming_content)
        self.assertTrue(contenido.startswith(b"\x89PNG"))

        Visita.objects.filter(pk=visita.pk).update(estado=Visita.Estado.ABIERTA)
        self.assertEqual(self._get(self.empleado).status_code, 200)
        self.assertEqual(self._get(self.admin).status_code, 200)

    def test_plano_inactivo_o_inexistente_da_404(self):
        self._visita(self.sitio, self.empleado)
        Plano.objects.filter(pk=self.plano.pk).update(activo=False)
        self.assertEqual(self._get(self.empleado).status_code, 404)
        self.assertEqual(self._get(self.admin).status_code, 404)
        api = APIClient()
        api.force_authenticate(self.admin)
        self.assertEqual(api.get("/api/v1/planos/99999/imagen/").status_code, 404)

    def test_archivo_faltante_da_404(self):
        self._visita(self.sitio, self.empleado)
        self.plano.imagen.storage.delete(self.plano.imagen.name)
        self.assertEqual(self._get(self.empleado).status_code, 404)

    def test_cliente_inactivo_da_404(self):
        self._visita(self.sitio, self.empleado)
        self.assertEqual(self._get(self.empleado).status_code, 200)
        Cliente.objects.filter(pk=self.sitio.cliente_id).update(activo=False)
        self.assertEqual(self._get(self.empleado).status_code, 404)
        Cliente.objects.filter(pk=self.sitio.cliente_id).update(activo=True)
        Sitio.objects.filter(pk=self.sitio.pk).update(activo=False)
        self.assertEqual(self._get(self.empleado).status_code, 404)

    def test_abrir_sin_qr_no_da_acceso_al_plano(self):
        api = APIClient()
        api.force_authenticate(self.empleado)
        r = api.post("/api/v1/visitas/abrir/", {}, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertFalse(Visita.objects.exists())
        self.assertEqual(api.get("/api/v1/me/puntos/").json(), [])
        self.assertEqual(self._get(self.empleado).status_code, 404)


class MisPuntosTests(TestCase):
    URL = "/api/v1/me/puntos/"

    def setUp(self):
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")
        self.sitio2 = Sitio.objects.create(cliente=self.cliente, nombre="Planta 2")
        self.sitio3 = Sitio.objects.create(cliente=self.cliente, nombre="Planta 3")
        self.tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        self.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.otro = User.objects.create_user(
            username="otro", password="x", rol=User.Rol.EMPLEADO
        )
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.api = APIClient()
        self.api.force_authenticate(self.empleado)

    def _visita(self, sitio, empleado, estado=Visita.Estado.PENDIENTE):
        return Visita.objects.create(
            sitio=sitio,
            empleado=empleado,
            origen=Visita.Origen.MANUAL,
            estado=estado,
            programada_para=datetime.date(2026, 1, 1),
        )

    def test_solo_sitios_con_visita_asignada_o_abierta(self):
        self._visita(self.sitio, self.empleado)
        self._visita(self.sitio2, self.empleado, Visita.Estado.ABIERTA)
        self._visita(self.sitio3, self.otro)  # de otro empleado
        extra = PuntoControl.objects.create(
            sitio=self.sitio,
            nombre="Techo",
            sector="Norte",
            latitud="-36.100000",
            longitud="-57.800000",
        )
        PuntoControl.objects.create(sitio=self.sitio, nombre="Baja", activo=False)
        r = self.api.get(self.URL)
        self.assertEqual(r.status_code, 200)
        nombres = {(p["sitio"]["nombre"], p["nombre"]) for p in r.json()}
        self.assertEqual(
            nombres,
            {("Planta 1", "General"), ("Planta 1", "Techo"), ("Planta 2", "General")},
        )
        techo = next(p for p in r.json() if p["id"] == extra.id)
        self.assertEqual(techo["latitud"], -36.1)
        self.assertEqual(techo["longitud"], -57.8)
        self.assertEqual(techo["estado"], "sin_programar")
        self.assertEqual(techo["sector"], "Norte")

        filtrado = self.api.get(self.URL, {"sitio": self.sitio2.id}).json()
        self.assertEqual([p["sitio"]["id"] for p in filtrado], [self.sitio2.id])
        ajeno = self.api.get(self.URL, {"sitio": self.sitio3.id}).json()
        self.assertEqual(ajeno, [])
        self.assertEqual(self.api.get(self.URL, {"sitio": "x"}).status_code, 400)

    def test_sitio_invalido_da_400(self):
        self._visita(self.sitio, self.empleado)
        for valor in ("²", "abc", "0", "9" * 5000):
            with self.subTest(valor=valor[:10]):
                r = self.api.get(self.URL, {"sitio": valor})
                self.assertEqual(r.status_code, 400, r.content)

    def test_sitio_fuera_de_rango_da_400(self):
        self._visita(self.sitio, self.empleado)
        for valor in (2**31, 2**63):
            with self.subTest(valor=valor):
                r = self.api.get(self.URL, {"sitio": valor})
                self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self.api.get(self.URL, {"sitio": 2**31 - 1}).status_code, 200)

    def test_realizada_o_sitio_inactivo_no_cuentan_y_solo_empleados(self):
        self._visita(self.sitio, self.empleado, Visita.Estado.REALIZADA)
        self._visita(self.sitio2, self.empleado)
        Sitio.objects.filter(pk=self.sitio2.pk).update(activo=False)
        self.assertEqual(self.api.get(self.URL).json(), [])
        admin = APIClient()
        admin.force_authenticate(self.admin)
        self.assertEqual(admin.get(self.URL).status_code, 200)
        self.assertEqual(APIClient().get(self.URL).status_code, 401)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ModoCampoTests(TestCase):
    """Alta de sitios y puntos y fijado de ubicación por un administrador en campo."""

    def setUp(self):
        cache.clear()
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.empleado = User.objects.create_user(
            username="emp", password="x", rol=User.Rol.EMPLEADO
        )
        self.api = APIClient()
        self.api.force_authenticate(self.admin)
        self.url_sitio = reverse("api:sitios:alta-sitio")

    def _sitio(self, **extra):
        datos = {
            "cliente": self.cliente.id,
            "nombre": "Galpón",
            "latitud": "-36.100000",
            "longitud": "-57.800000",
            "precision_m": 12,
            **extra,
        }
        return self.api.post(self.url_sitio, datos, format="json")

    def _url_punto(self, sitio):
        return reverse("api:sitios:alta-punto", kwargs={"pk": sitio.pk})

    def _url_ubicacion(self, punto):
        return reverse("api:sitios:ubicacion-punto", kwargs={"pk": punto.pk})

    def _png(self):
        buffer = io.BytesIO()
        Image.new("RGB", (30, 30), "red").save(buffer, "PNG")
        return SimpleUploadedFile("mi foto.png", buffer.getvalue(), "image/png")

    def test_administrador_crea_sitio_y_punto_con_coordenadas(self):
        r = self._sitio()
        self.assertEqual(r.status_code, 201, r.content)
        sitio = Sitio.objects.get(pk=r.json()["id"])
        self.assertEqual(float(sitio.latitud), -36.1)
        self.assertEqual(sitio.puntos.get().nombre, "General")
        self.assertEqual(sitio.history.first().history_user, self.admin)
        r = self.api.post(
            self._url_punto(sitio),
            {
                "nombre": "Depósito",
                "sector": "Norte",
                "latitud": "-36.100500",
                "longitud": "-57.800500",
                "precision_m": 50,
                "foto": self._png(),
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, 201, r.content)
        punto = PuntoControl.objects.get(pk=r.json()["id"])
        self.assertEqual(float(punto.latitud), -36.1005)
        self.assertEqual(punto.orden, 1)
        self.assertRegex(punto.foto.name, r"^sitios/puntos/[0-9a-f]{32}\.jpg$")
        self.assertEqual(punto.history.first().history_user, self.admin)

    def test_empleado_no_puede_crear_sitio_ni_punto(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        self.api.force_authenticate(self.empleado)
        self.assertEqual(self._sitio().status_code, 403)
        r = self.api.post(self._url_punto(sitio), {"nombre": "X"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(PuntoControl.objects.count(), 1)
        self.assertEqual(APIClient().post(self.url_sitio, {}).status_code, 401)

    def test_precision_insuficiente_da_400(self):
        self.assertEqual(self._sitio(precision_m=50.5).status_code, 400)
        self.assertEqual(Sitio.objects.count(), 0)
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        r = self.api.post(
            self._url_punto(sitio),
            {"nombre": "X", "latitud": "-36.1", "longitud": "-57.8", "precision_m": 80},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(sitio.puntos.count(), 1)

    def test_punto_sin_coordenadas_se_crea(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        r = self.api.post(self._url_punto(sitio), {"nombre": "Techo"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        punto = PuntoControl.objects.get(pk=r.json()["id"])
        self.assertIsNone(punto.latitud)
        self.assertFalse(punto.foto)
        solo_latitud = {"nombre": "Y", "latitud": "-36.1", "precision_m": 5}
        r = self.api.post(self._url_punto(sitio), solo_latitud, format="json")
        self.assertEqual(r.status_code, 400)

    def test_fijar_ubicacion_registra_quien(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        punto = sitio.puntos.get()
        r = self.api.post(
            self._url_ubicacion(punto),
            {"latitud": "-36.100000", "longitud": "-57.800000", "precision_m": 8},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        punto.refresh_from_db()
        self.assertEqual(float(punto.latitud), -36.1)
        ultimo = punto.history.first()
        self.assertEqual(ultimo.history_user, self.admin)
        self.assertEqual(
            ultimo.history_change_reason, "Ubicación fijada en campo desde la app"
        )

    def test_ubicacion_exige_administrador_precision_y_activos(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        punto = sitio.puntos.get()
        url = self._url_ubicacion(punto)
        datos = {"latitud": "-36.1", "longitud": "-57.8", "precision_m": 5}
        self.api.force_authenticate(self.empleado)
        self.assertEqual(self.api.post(url, datos, format="json").status_code, 403)
        self.assertEqual(APIClient().post(url, datos, format="json").status_code, 401)
        self.api.force_authenticate(self.admin)
        r = self.api.post(url, {**datos, "precision_m": 51}, format="json")
        self.assertEqual(r.status_code, 400)
        punto.refresh_from_db()
        self.assertIsNone(punto.latitud)
        r = self.api.post(self._url_ubicacion(PuntoControl(pk=0)), datos, format="json")
        self.assertEqual(r.status_code, 404)
        self.cliente.activo = False
        self.cliente.save()
        self.assertEqual(self.api.post(url, datos, format="json").status_code, 400)

    def test_cliente_inactivo_da_400(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        self.cliente.activo = False
        self.cliente.save()
        self.assertEqual(self._sitio().status_code, 400)
        r = self.api.post(self._url_punto(sitio), {"nombre": "X"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(PuntoControl.objects.count(), 1)

    def test_altas_usan_cupo_alta_campo(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        punto = sitio.puntos.get()
        # El cupo se lee al instanciar el throttle: se baja a 2 por hora.
        cupo = {"alta_campo": "2/hour"}
        with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, cupo):
            self.assertEqual(self._sitio().status_code, 201)
            r = self.api.post(self._url_punto(sitio), {"nombre": "X"}, format="json")
            self.assertEqual(r.status_code, 201)
            datos = {"latitud": "-36.1", "longitud": "-57.8", "precision_m": 5}
            r = self.api.post(self._url_ubicacion(punto), datos, format="json")
            self.assertEqual(r.status_code, 429, r.content)
        vistas = (AltaSitioView, AltaPuntoView, UbicacionPuntoView)
        self.assertEqual([v.throttle_scope for v in vistas], ["alta_campo"] * 3)

    def test_administrador_resuelve_qr_y_ve_mis_puntos(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        punto = sitio.puntos.get()
        Visita.objects.create(
            sitio=sitio,
            empleado=self.admin,
            origen=Visita.Origen.MANUAL,
            programada_para=datetime.date(2026, 1, 1),
        )
        r = self.api.post(f"/api/v1/qr/{punto.qr_codigo}/resolver/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["punto"]["id"], punto.id)
        r = self.api.get("/api/v1/me/puntos/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([p["id"] for p in r.json()], [punto.id])

    def test_administrador_resuelve_qr_y_abre_visita(self):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        punto = sitio.puntos.get()
        r = self.api.post(f"/api/v1/qr/{punto.qr_codigo}/resolver/")
        self.assertEqual(r.status_code, 200, r.content)
        r = self.api.post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(punto.qr_codigo)},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        visita = Visita.objects.get(pk=r.json()["id"])
        self.assertEqual(visita.empleado, self.admin)
        self.assertEqual(visita.estado, Visita.Estado.ABIERTA)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class AltaPuntoTests(TestCase):
    """Alta de puntos y sitios en campo: tamaño del pedido y precisión guardada."""

    def setUp(self):
        cache.clear()
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.admin = User.objects.create_user(
            username="adm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta")
        self.api = APIClient()
        self.api.force_authenticate(self.admin)
        self.url = reverse("api:sitios:alta-punto", kwargs={"pk": self.sitio.pk})

    def test_foto_enorme_da_400_sin_500(self):
        enorme = SimpleUploadedFile(
            "f.jpg", b"0" * (MAX_BYTES_PEDIDO_PUNTO + 1), "image/jpeg"
        )
        r = self.api.post(self.url, {"nombre": "X", "foto": enorme}, format="multipart")
        self.assertEqual(r.status_code, 400, r.content[:200])
        self.assertIn("detalle", r.json())
        self.assertEqual(self.sitio.puntos.count(), 1)

    def test_demasiados_campos_da_400(self):
        datos = {f"campo{i}": "x" for i in range(1100)}
        r = self.api.post(self.url, {"nombre": "X", **datos}, format="multipart")
        self.assertEqual(r.status_code, 400, r.content[:200])
        self.assertIn("detalle", r.json())
        self.assertEqual(self.sitio.puntos.count(), 1)

    def test_alta_guarda_precision_m(self):
        r = self.api.post(
            self.url,
            {
                "nombre": "Techo",
                "latitud": "-36.1",
                "longitud": "-57.8",
                "precision_m": 12.5,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        punto = PuntoControl.objects.get(pk=r.json()["id"])
        self.assertEqual(punto.precision_m, Decimal("12.50"))
        r = self.api.post(self.url, {"nombre": "Sin GPS"}, format="json")
        self.assertIsNone(PuntoControl.objects.get(pk=r.json()["id"]).precision_m)
        r = self.api.post(
            reverse("api:sitios:ubicacion-punto", kwargs={"pk": punto.pk}),
            {"latitud": "-36.2", "longitud": "-57.9", "precision_m": 7},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        punto.refresh_from_db()
        self.assertEqual(punto.precision_m, Decimal("7.00"))
        r = self.api.post(
            reverse("api:sitios:alta-sitio"),
            {
                "cliente": self.cliente.id,
                "nombre": "Galpón",
                "latitud": "-36.1",
                "longitud": "-57.8",
                "precision_m": 33.25,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(
            Sitio.objects.get(pk=r.json()["id"]).precision_m, Decimal("33.25")
        )
