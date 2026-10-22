"""Ficha rediseñada del sitio: cabecera, plano con lista, pestañas y aviso."""

import re
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import TipoServicio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import ItemTurno, Visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sitios-ficha-rediseno-")


def _png():
    buffer = BytesIO()
    Image.new("RGB", (300, 200), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FichaRedisenoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.admin = User.objects.create_user(
            "adm-rediseno", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            "emp-rediseno", password="x", rol=User.Rol.EMPLEADO, first_name="Ana"
        )
        cls.cliente = Cliente.objects.create(razon_social="ACME")
        cls.servicio = TipoServicio.objects.create(nombre="Roedores", slug="roedores-r")
        cls.sitio = Sitio.objects.create(
            cliente=cls.cliente,
            nombre="Planta Sur",
            direccion="Calle 1 123",
            localidad="La Plata",
            responsable=User.objects.create_user(
                "resp-rediseno",
                password="x",
                rol=User.Rol.ADMINISTRADOR,
                first_name="Rosa",
                last_name="Gómez",
            ),
            contacto_en_sitio="Luis Pérez",
            telefono_en_sitio="221-555-0101",
            latitud=Decimal("-34.9"),
            longitud=Decimal("-57.9"),
        )
        cls.general = cls.sitio.puntos.get()

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        self.url_turno = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])

    def vencer(self, dias):
        PuntoControl.objects.filter(pk=self.general.pk).update(
            proximo_vencimiento=self.hoy + timedelta(days=dias)
        )

    def test_cabecera_con_datos_y_acciones(self):
        self.vencer(-2)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "<h1>Planta Sur</h1>", html=True)
        self.assertEqual(respuesta.context["estado_general"], "vencidos")
        self.assertContains(respuesta, "etiqueta-danger")
        for texto in (
            "ACME",
            "Calle 1 123",
            "Rosa Gómez",
            "Luis Pérez",
            "221-555-0101",
        ):
            self.assertContains(respuesta, texto)
        self.assertContains(
            respuesta, reverse("panel:sitios:editar", args=[self.sitio.pk])
        )
        self.assertContains(respuesta, "Editar sitio")
        self.assertContains(
            respuesta, reverse("panel:visitas:cargar", args=[self.sitio.pk])
        )
        self.assertContains(respuesta, "Cargar visita")
        self.assertContains(
            respuesta,
            f'class="boton boton-primario" href="{self.url_turno}" '
            f'hx-get="{self.url_turno}" hx-target="#panel-lateral" data-abre-panel',
        )
        html = respuesta.content.decode()
        self.assertIn("vendor/leaflet/leaflet.js", html)
        self.assertIn("visitas/nuevo_turno.js", html)
        self.assertNotIn("<script>", html)

    def test_plano_y_lista_comparten_numero_de_punto(self):
        plano = Plano.objects.create(
            sitio=self.sitio,
            nombre="Planta baja",
            imagen=SimpleUploadedFile("p.png", _png()),
        )
        PuntoControl.objects.filter(pk=self.general.pk).update(
            plano=plano, x=Decimal("0.2"), y=Decimal("0.3"), orden=0
        )
        segundo = PuntoControl.objects.create(
            sitio=self.sitio,
            nombre="Cocina",
            orden=1,
            plano=plano,
            x=Decimal("0.6"),
            y=Decimal("0.7"),
        )
        PuntoControl.objects.create(
            sitio=self.sitio, nombre="Baja", orden=2, activo=False
        )
        respuesta = self.client.get(self.url)
        [datos] = respuesta.context["datos_ficha_plano"]
        self.assertEqual(
            [(p["id"], p["numero"]) for p in datos["puntos"]],
            [(self.general.pk, 1), (segundo.pk, 2)],
        )
        html = respuesta.content.decode()
        self.assertIn('id="datos-ficha-plano"', html)
        self.assertIn("sitios/ficha_plano.js", html)
        for punto, numero in ((self.general, 1), (segundo, 2)):
            fila = re.search(
                rf'<li[^>]*data-punto="{punto.pk}"[^>]*>(.*?)</li>', html, re.S
            )
            self.assertIsNotNone(fila, punto.nombre)
            self.assertRegex(
                fila.group(1), rf'class="numero-punto"[^>]*>{numero}<', punto.nombre
            )
            self.assertIn(
                reverse("panel:sitios:punto_editar", args=[punto.pk]), fila.group(1)
            )
        self.assertContains(respuesta, "Baja")

    def test_pestanas_turnos_planos_y_datos(self):
        por_defecto = self.client.get(self.url)
        self.assertEqual(por_defecto.context["pestana"], "turnos")
        self.assertContains(por_defecto, "Turnos pendientes")
        self.assertNotContains(por_defecto, "Subir plano")
        for vieja in ("mapa", "puntos", "invalida"):
            self.assertEqual(
                self.client.get(self.url, {"pestana": vieja}).context["pestana"],
                "turnos",
            )
        planos = self.client.get(self.url, {"pestana": "planos"})
        self.assertEqual(planos.context["pestana"], "planos")
        self.assertContains(planos, "Subir plano")
        self.assertContains(planos, "sitios/plano_editor.js")
        datos = self.client.get(self.url, {"pestana": "datos"})
        self.assertEqual(datos.context["pestana"], "datos")
        self.assertContains(datos, 'id="mapa-sitio"')
        self.assertContains(datos, "sitios/sitio_ficha_mapa.js")
        self.assertContains(datos, "Horario de acceso")
        self.assertContains(datos, "Descargar QR")
        self.assertNotContains(datos, "Turnos pendientes")
        for clave in ("turnos", "planos", "datos"):
            self.assertContains(
                self.client.get(self.url, {"pestana": clave}),
                f'href="?pestana={clave}"',
            )

    def test_aviso_sin_turnos_con_puntos_vencidos(self):
        self.vencer(-1)
        respuesta = self.client.get(self.url)
        self.assertContains(respuesta, "No hay turnos pendientes y hay puntos vencidos")
        self.assertContains(respuesta, 'class="mensaje mensaje-warning"')
        # Con un turno pendiente el aviso desaparece.
        turno = Visita.objects.create(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=self.hoy + timedelta(days=1),
        )
        ItemTurno.objects.create(
            visita=turno, punto=self.general, servicio=self.servicio
        )
        self.assertNotContains(
            self.client.get(self.url), "No hay turnos pendientes y hay puntos vencidos"
        )
        # Sin vencidos tampoco hay aviso.
        turno.delete()
        self.vencer(10)
        self.assertNotContains(
            self.client.get(self.url), "No hay turnos pendientes y hay puntos vencidos"
        )
