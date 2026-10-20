"""Recorrido del administrador por el panel integrado, de punta a punta."""

import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Foto, Visita


def _jpeg():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "blue").save(salida, format="JPEG")
    return salida.getvalue()


class RecorridoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media = tempfile.mkdtemp(prefix="detach-recorrido-test-")
        cls._ajuste = override_settings(MEDIA_ROOT=cls.media)
        cls._ajuste.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._ajuste.disable()
        shutil.rmtree(cls.media, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-rec", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            "emp-rec", password="x", rol=User.Rol.EMPLEADO
        )
        cliente = Cliente.objects.create(razon_social="Cliente Recorrido")
        cls.sitio = Sitio.objects.create(
            cliente=cliente,
            nombre="Depósito central",
            latitud=Decimal("-34.603700"),
            longitud=Decimal("-58.381600"),
        )
        cls.tipo = TipoServicio.objects.create(nombre="Desinsectación", slug="des-rec")
        cls.sitio.puntos.filter(orden=0).update(servicio=cls.tipo, frecuencia_dias=30)
        cls.producto = Producto.objects.create(nombre_comercial="Gel cucarachicida")

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client.force_login(self.admin)

    def _get_200(self, url):
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200, url)
        return respuesta

    def test_administrador_recorre_el_panel(self):
        # El inicio lleva al listado de sitios; el mapa enlaza a la ficha y al turno.
        self.assertRedirects(
            self.client.get(reverse("panel:inicio")),
            reverse("panel:sitios:listado"),
        )
        self._get_200(reverse("panel:mapa"))
        datos = self._get_200(reverse("panel:mapa_datos")).json()
        url_sitio = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        sitio = next(s for s in datos["sitios"] if s["id"] == self.sitio.pk)
        self.assertEqual(sitio["url_ficha"], url_sitio)

        self.assertEqual(
            sitio["url_nuevo_turno"],
            reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk]),
        )

        # Ficha del sitio y turno nuevo para el empleado con el punto General.
        self._get_200(url_sitio)
        general = self.sitio.puntos.get(orden=0)
        url_asignar = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])
        url_manual = reverse("panel:visitas:cargar", args=[self.sitio.pk])
        self._get_200(url_asignar)
        respuesta = self.client.post(
            url_asignar,
            {
                "empleado": self.empleado.pk,
                "programada_para": timezone.localdate() + timedelta(days=1),
                "puntos": [general.pk],
                f"servicio_{general.pk}": self.tipo.pk,
            },
        )
        self.assertRedirects(respuesta, url_sitio)
        pendiente = Visita.objects.get(sitio=self.sitio, estado=Visita.Estado.PENDIENTE)

        # Completar esa pendiente con la carga manual.
        self._get_200(url_manual)
        respuesta = self.client.post(
            url_manual,
            {
                "empleado": self.empleado.pk,
                "puntos": [general.pk],
                f"servicio_{general.pk}": self.tipo.pk,
                "pendiente": pendiente.pk,
                "motivo": "El empleado no tenía conexión",
                "realizada_en": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "productos-TOTAL_FORMS": 1,
                "productos-INITIAL_FORMS": 0,
                "productos-MIN_NUM_FORMS": 0,
                "productos-MAX_NUM_FORMS": 30,
                "productos-0-producto": self.producto.pk,
                "productos-0-lote": "L7",
                "productos-0-dosis": "1.5",
                "productos-0-unidad_dosis": "g",
                "productos-0-cantidad": "2",
                "productos-0-unidad": "unidad",
                "fotos": [
                    SimpleUploadedFile("f.jpg", _jpeg(), content_type="image/jpeg")
                ],
            },
        )
        url_visita = reverse("panel:visitas:ficha", args=[pendiente.pk])
        self.assertRedirects(respuesta, url_visita)

        # La visita final quedó realizada y su ficha y su foto se ven.
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.REALIZADA)
        self.assertEqual(pendiente.origen, Visita.Origen.MANUAL)
        self.assertEqual(pendiente.asignada_por, self.admin)
        self._get_200(url_visita)
        foto = Foto.objects.get(revision__visita=pendiente)
        self._get_200(reverse("panel:visitas:foto", args=[foto.codigo]))
        # La ficha de la visita muestra la revisión del punto con su foto.
        ficha = self._get_200(url_visita)
        self.assertContains(ficha, general.nombre)
        self.assertContains(ficha, reverse("panel:visitas:foto", args=[foto.codigo]))
        # La carga fijó el vencimiento del punto y el estado del sitio lo refleja.
        general.refresh_from_db()
        self.assertEqual(
            general.proximo_vencimiento, timezone.localdate() + timedelta(days=30)
        )
        estado = self._get_200(reverse("panel:estado_sitio", args=[self.sitio.pk]))
        self.assertContains(estado, 'id="estado-puntos"')

    def test_administrador_recorre_puntos_y_planos(self):
        sitio = self.sitio
        for pestana in ("puntos", "planos", "mapa"):
            self._get_200(
                f"{reverse('panel:sitios:ficha', args=[sitio.pk])}?pestana={pestana}"
            )

        # Subir un plano: la ficha queda en la pestaña del plano nuevo.
        url_plano = reverse("panel:sitios:plano_alta", args=[sitio.pk])
        self._get_200(url_plano)
        imagen = BytesIO()
        Image.new("RGB", (80, 60), "gray").save(imagen, format="PNG")
        respuesta = self.client.post(
            url_plano,
            {
                "nombre": "Planta baja",
                "orden": 0,
                "imagen": SimpleUploadedFile(
                    "p.png", imagen.getvalue(), content_type="image/png"
                ),
            },
        )
        plano = Plano.objects.get(sitio=sitio)
        self.assertRedirects(
            respuesta,
            f"{reverse('panel:sitios:ficha', args=[sitio.pk])}"
            f"?pestana=planos&plano={plano.pk}",
        )
        self._get_200(reverse("panel:sitios:plano_imagen", args=[plano.pk]))

        # Un punto nuevo sobre el plano, y su marcador se mueve.
        url_punto = reverse("panel:sitios:punto_alta", args=[sitio.pk])
        self._get_200(url_punto)
        respuesta = self.client.post(
            url_punto,
            {
                "nombre": "Cocina",
                "orden": 1,
                "activo": "on",
                "plano": plano.pk,
                "x": "0.2000",
                "y": "0.3000",
            },
        )
        punto = PuntoControl.objects.get(sitio=sitio, nombre="Cocina")
        self.assertEqual(respuesta.status_code, 302)
        movido = self.client.post(
            reverse("panel:sitios:punto_posicion", args=[punto.pk]),
            {"x": "0.5000", "y": "0.2500"},
        )
        self.assertEqual(movido.status_code, 200)
        punto.refresh_from_db()
        self.assertEqual((punto.x, punto.y), (Decimal("0.5"), Decimal("0.25")))

        # El estado del sitio lista los puntos activos con su posición.
        estado = self._get_200(reverse("panel:estado_sitio", args=[sitio.pk]))
        self.assertContains(estado, f'data-punto="{punto.pk}"')
        self.assertContains(estado, 'data-x="0.5000"')

        # Carga de visita por dos puntos: una revisión por punto.
        general = sitio.puntos.get(orden=0)
        url_manual = reverse("panel:visitas:cargar", args=[sitio.pk])
        respuesta = self.client.post(
            url_manual,
            {
                "empleado": self.empleado.pk,
                "puntos": [general.pk, punto.pk],
                f"servicio_{general.pk}": self.tipo.pk,
                f"servicio_{punto.pk}": self.tipo.pk,
                "motivo": "Carga de prueba por puntos",
                "realizada_en": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "productos-TOTAL_FORMS": 0,
                "productos-INITIAL_FORMS": 0,
                "productos-MIN_NUM_FORMS": 0,
                "productos-MAX_NUM_FORMS": 30,
                "fotos": [
                    SimpleUploadedFile("f.jpg", _jpeg(), content_type="image/jpeg")
                ],
            },
        )
        visita = Visita.objects.get(sitio=self.sitio)
        self.assertRedirects(
            respuesta, reverse("panel:visitas:ficha", args=[visita.pk])
        )
        self.assertEqual(visita.revisiones.count(), 2)

        # La ficha de la visita lista las revisiones de ambos puntos.
        ficha = self._get_200(reverse("panel:visitas:ficha", args=[visita.pk]))
        self.assertContains(ficha, "Cocina")
        self.assertContains(ficha, general.nombre)
