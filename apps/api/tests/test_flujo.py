"""Flujo de punta a punta del empleado con JWT real: QR, jornada, historial y foto."""

import json
import shutil
import tempfile
from io import BytesIO
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
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import ProductoAplicado, Visita

CLAVE = "clave-segura-123"
MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="flujo-api-test-")


def jpeg(nombre, color):
    """Imagen JPEG real, lista para subir en un multipart."""
    buffer = BytesIO()
    Image.new("RGB", (30, 30), color).save(buffer, "JPEG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FlujoEmpleadoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(
            cliente=cliente,
            nombre="Planta 1",
            direccion="Calle 1",
            localidad="Castelli",
            latitud="-36.100000",
            longitud="-57.800000",
        )
        tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")
        CampoPlanilla.objects.create(
            tipo_servicio=tipo,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.empleado = User.objects.create_user(
            "emp", password=CLAVE, rol=User.Rol.EMPLEADO
        )
        self.otro = User.objects.create_user(
            "otro", password=CLAVE, rol=User.Rol.EMPLEADO
        )
        Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=tipo,
            titulo="Control",
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
        )
        Producto.objects.create(nombre_comercial="Cebo X")
        self.punto = self.sitio.puntos.get(orden=0)

    def _cliente_con_token(self, usuario):
        """Cliente que se autentica solo con el JWT obtenido del endpoint real."""
        api = APIClient()
        respuesta = api.post(
            "/api/v1/auth/token/",
            {"username": usuario, "password": CLAVE},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
        return api

    def test_escanear_registrar_historial_foto(self):
        """Escanear, abrir, revisar, cerrar y ver historial y foto, con JWT real."""
        api = self._cliente_con_token("emp")

        qr = api.post(f"/api/v1/qr/{self.punto.qr_codigo}/resolver/")
        self.assertEqual(qr.status_code, 200, qr.content)
        proyecto = qr.data["proyectos"][0]
        self.assertEqual(proyecto["esquema_punto"][0]["clave"], "cebos")

        catalogo = api.get("/api/v1/productos/")
        self.assertEqual(catalogo.status_code, 200, catalogo.content)
        producto = catalogo.data[0]

        productos = [
            {
                "producto": producto["id"],
                "lote": "L1",
                "dosis": "2",
                "unidad_dosis": "g",
                "cantidad": "5",
                "unidad": "unidad",
            }
        ]
        abierta = api.post(
            "/api/v1/visitas/abrir/",
            {"proyecto": proyecto["id"], "qr_codigo": str(self.punto.qr_codigo)},
            format="json",
        )
        self.assertEqual(abierta.status_code, 201, abierta.content)
        cuerpo = {
            "visita": abierta.data["id"],
            "qr_codigo": str(self.punto.qr_codigo),
            "cliente_uuid": str(uuid4()),
            "realizada_en": timezone.now().isoformat(),
            "latitud": "-36.100000",
            "longitud": "-57.800000",
            "precision_m": "8.5",
            "datos": json.dumps({"cebos": 3}),
            "productos_aplicados": json.dumps(productos),
            "fotos": [jpeg("a.jpg", "red"), jpeg("b.jpg", "blue")],
        }
        creada = api.post("/api/v1/revisiones/", cuerpo, format="multipart")
        self.assertEqual(creada.status_code, 201, creada.content)
        cerrada = api.post(
            f"/api/v1/visitas/{abierta.data['id']}/cerrar/", {}, format="json"
        )
        self.assertEqual(cerrada.status_code, 200, cerrada.content)

        historial = api.get("/api/v1/me/historial/")
        self.assertEqual(historial.status_code, 200, historial.content)
        self.assertEqual(
            [v["id"] for v in historial.data["results"]], [abierta.data["id"]]
        )
        visita = Visita.objects.get(pk=abierta.data["id"])
        self.assertEqual(
            ProductoAplicado.objects.filter(revision__visita=visita).count(), 1
        )
        urls = historial.data["results"][0]["revisiones"][0]["fotos"]
        self.assertEqual(len(urls), 2)

        respuesta = api.get(urls[0], HTTP_ACCEPT="image/jpeg")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "image/jpeg")
        contenido = b"".join(respuesta.streaming_content)
        self.assertTrue(contenido.startswith(b"\xff\xd8"))

        ajeno = self._cliente_con_token("otro").get(urls[0])
        self.assertEqual(ajeno.status_code, 403)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ModoCampoFlujoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_administrador_crea_y_empleado_escanea_sin_propuesta(self):
        """Con coordenadas fijas desde el campo, el escaneo no propone otras."""
        cliente = Cliente.objects.create(razon_social="ACME")
        User.objects.create_user("adm", password=CLAVE, rol=User.Rol.ADMINISTRADOR)
        empleado = User.objects.create_user(
            "emp", password=CLAVE, rol=User.Rol.EMPLEADO
        )
        tipo = TipoServicio.objects.create(nombre="Desratización", slug="desrat")

        def con_token(usuario):
            api = APIClient()
            respuesta = api.post(
                "/api/v1/auth/token/",
                {"username": usuario, "password": CLAVE},
                format="json",
            )
            self.assertEqual(respuesta.status_code, 200, respuesta.content)
            api.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
            return api

        api_admin = con_token("adm")
        sitio = api_admin.post(
            "/api/v1/sitios/",
            {
                "cliente": cliente.id,
                "nombre": "Galpón",
                "latitud": "-36.100000",
                "longitud": "-57.800000",
                "precision_m": 10,
            },
            format="json",
        )
        self.assertEqual(sitio.status_code, 201, sitio.content)
        punto = api_admin.post(
            f"/api/v1/sitios/{sitio.data['id']}/puntos/",
            {
                "nombre": "Depósito",
                "latitud": "-36.100500",
                "longitud": "-57.800500",
                "precision_m": 10,
            },
            format="json",
        )
        self.assertEqual(punto.status_code, 201, punto.content)
        proyecto = Proyecto.objects.create(
            sitio_id=sitio.data["id"],
            tipo_servicio=tipo,
            titulo="Control",
            encargado_inicial=empleado,
            encargado_actual=empleado,
        )

        api = con_token("emp")
        qr = PuntoControl.objects.get(pk=punto.data["id"]).qr_codigo
        resuelto = api.post(f"/api/v1/qr/{qr}/resolver/")
        self.assertEqual(resuelto.status_code, 200, resuelto.content)
        abierta = api.post(
            "/api/v1/visitas/abrir/",
            {"proyecto": proyecto.id, "qr_codigo": str(qr)},
            format="json",
        )
        self.assertEqual(abierta.status_code, 201, abierta.content)
        creada = api.post(
            "/api/v1/revisiones/",
            {
                "visita": abierta.data["id"],
                "qr_codigo": str(qr),
                "cliente_uuid": str(uuid4()),
                "realizada_en": timezone.now().isoformat(),
                "latitud": "-36.200000",
                "longitud": "-57.900000",
                "precision_m": "8.5",
                "datos": json.dumps({}),
                "fotos": [jpeg("a.jpg", "red")],
            },
            format="multipart",
        )
        self.assertEqual(creada.status_code, 201, creada.content)

        marcador = PuntoControl.objects.get(pk=punto.data["id"])
        self.assertEqual(float(marcador.latitud), -36.1005)
        self.assertEqual(float(marcador.longitud), -57.8005)
