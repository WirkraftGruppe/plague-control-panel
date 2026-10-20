"""Panel: nuevo turno (plano, atajos, servicio por punto) y carga de visita."""

import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.productos.models import MovimientoStock, Producto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Visita

from .test_models import crear_visita, punto_de

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="detach-turnos-panel-")


def _png():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "white").save(salida, format="PNG")
    return salida.getvalue()


class BaseTurnosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        visita = crear_visita()
        cls.sitio = visita.sitio
        cls.roedores = visita.tipo
        cls.insectos = TipoServicio.objects.create(
            nombre="Insectos", slug="insectos-t8"
        )
        cls.general = punto_de(visita)
        cls.sala = PuntoControl.objects.create(
            sitio=cls.sitio, nombre="Sala", orden=1, servicio=cls.roedores
        )
        cls.techo = PuntoControl.objects.create(
            sitio=cls.sitio, nombre="Techo", orden=2, servicio=cls.roedores
        )
        cls.empleado = visita.empleado
        cls.admin = User.objects.create_user(
            "adm-t8", password="x", rol=User.Rol.ADMINISTRADOR
        )
        visita.delete()

    def setUp(self):
        self.client.force_login(self.admin)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class NuevoTurnoPanelTests(BaseTurnosTests):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])

    def _datos(self, puntos, **extra):
        datos = {
            "empleado": self.empleado.pk,
            "programada_para": timezone.localdate() + timedelta(days=2),
            "puntos": [p.pk for p in puntos],
        }
        for punto in puntos:
            datos[f"servicio_{punto.pk}"] = punto.servicio_id
        datos.update(extra)
        return datos

    def test_tres_puntos_uno_con_servicio_cambiado_guarda_tres_items(self):
        puntos = [self.general, self.sala, self.techo]
        datos = self._datos(puntos, **{f"servicio_{self.techo.pk}": self.insectos.pk})
        respuesta = self.client.post(self.url, datos)
        self.assertRedirects(
            respuesta, reverse("panel:sitios:ficha", args=[self.sitio.pk])
        )
        turno = Visita.objects.get(estado=Visita.Estado.PENDIENTE)
        servicios = {i.punto_id: i.servicio_id for i in turno.items.all()}
        self.assertEqual(
            servicios,
            {
                self.general.pk: self.roedores.pk,
                self.sala.pk: self.roedores.pk,
                self.techo.pk: self.insectos.pk,
            },
        )

    def test_cero_puntos_da_error_de_formulario(self):
        respuesta = self.client.post(self.url, self._datos([]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("puntos", respuesta.context["form"].errors)
        self.assertFalse(Visita.objects.exists())

    def test_punto_tildado_sin_servicio_da_error(self):
        datos = self._datos([self.sala], **{f"servicio_{self.sala.pk}": ""})
        respuesta = self.client.post(self.url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(f"servicio_{self.sala.pk}", respuesta.context["form"].errors)
        self.assertContains(respuesta, "El punto no tiene servicio asignado.")
        self.assertFalse(Visita.objects.exists())

    def test_html_expone_estado_y_servicio_de_cada_punto(self):
        ayer = timezone.localdate() - timedelta(days=1)
        PuntoControl.objects.filter(pk=self.sala.pk).update(proximo_vencimiento=ayer)
        Plano.objects.create(
            sitio=self.sitio,
            nombre="Planta",
            imagen=SimpleUploadedFile("p.png", _png()),
        )
        respuesta = self.client.get(self.url)
        self.assertContains(
            respuesta,
            f'data-punto="{self.sala.pk}" data-estado="vencida" '
            f'data-servicio="{self.roedores.pk}"',
        )
        self.assertContains(
            respuesta,
            f'data-punto="{self.general.pk}" data-estado="sin_programar"',
        )
        for atajo in ("todos", "vencidos", "ninguno"):
            self.assertContains(respuesta, f'data-atajo="{atajo}"')
        self.assertContains(respuesta, 'id="datos-turno-plano"')
        self.assertContains(respuesta, "nuevo_turno.js")

    def test_sin_plano_muestra_solo_la_lista(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, f'data-punto="{self.sala.pk}"')
        self.assertNotContains(respuesta, 'id="turno-plano"')
        self.assertNotContains(respuesta, 'id="datos-turno-plano"')


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class CargarVisitaPanelTests(BaseTurnosTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("panel:visitas:cargar", args=[self.sitio.pk])
        # Las cargas son de ahora: el sitio ya existía.
        Sitio.objects.filter(pk=self.sitio.pk).update(
            creado=timezone.now() - timedelta(days=90)
        )

    def _datos(self, puntos, **extra):
        datos = {
            "empleado": self.empleado.pk,
            "motivo": "Sin señal",
            "realizada_en": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "puntos": [p.pk for p in puntos],
            "productos-TOTAL_FORMS": 0,
            "productos-INITIAL_FORMS": 0,
            "productos-MIN_NUM_FORMS": 0,
            "productos-MAX_NUM_FORMS": 30,
        }
        for punto in puntos:
            datos[f"servicio_{punto.pk}"] = punto.servicio_id
        datos.update(extra)
        return datos

    def test_carga_con_servicio_por_punto(self):
        datos = self._datos(
            [self.general, self.sala], **{f"servicio_{self.sala.pk}": self.insectos.pk}
        )
        respuesta = self.client.post(self.url, datos)
        visita = Visita.objects.get()
        self.assertRedirects(
            respuesta, reverse("panel:visitas:ficha", args=[visita.pk])
        )
        servicios = {r.punto_id: r.servicio_id for r in visita.revisiones.all()}
        self.assertEqual(
            servicios,
            {self.general.pk: self.roedores.pk, self.sala.pk: self.insectos.pk},
        )
        self.assertEqual(visita.items.count(), 2)

    def test_cantidad_desbordada_da_error_en_el_producto(self):
        producto = Producto.objects.create(
            nombre_comercial="Cebo", unidad_base="ml", modo_unidad="equivalentes"
        )
        datos = self._datos(
            [self.general],
            **{
                "productos-TOTAL_FORMS": 1,
                "productos-0-producto": producto.pk,
                "productos-0-lote": "L1",
                "productos-0-dosis": "1",
                "productos-0-unidad_dosis": "ml/l",
                "productos-0-cantidad": "9999999",
                "productos-0-unidad": "gal",
            },
        )
        respuesta = self.client.post(self.url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("cantidad", respuesta.context["productos"][0].errors)
        self.assertFalse(Visita.objects.exists())
        self.assertFalse(MovimientoStock.objects.exists())
