"""Inicio del panel sin tablero y mapa por vencimiento de los puntos."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios.models import Sitio

RAIZ_APP = Path(__file__).resolve().parents[1]


class BasePanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-ini", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente Inicio")

    def setUp(self):
        self.client.force_login(self.admin)


class InicioTests(BasePanelTests):
    def test_panel_redirige_a_sitios(self):
        respuesta = self.client.get("/panel/")
        self.assertRedirects(
            respuesta, reverse("panel:sitios:listado"), fetch_redirect_response=False
        )
        self.assertEqual(self.client.get("/panel/sitios/").status_code, 200)

    def test_rutas_del_tablero_y_de_proyectos_dan_404(self):
        for ruta in (
            "/panel/tablero/",
            "/panel/proyectos/",
            "/panel/proyectos/1/",
            "/panel/visitas/proyectos/1/asignar/",
            "/panel/visitas/proyectos/1/manual/",
        ):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_empleado_no_entra_al_inicio(self):
        self.client.force_login(
            User.objects.create_user("emp-ini", password="x", rol=User.Rol.EMPLEADO)
        )
        self.assertEqual(self.client.get("/panel/").status_code, 403)


class MapaVencimientoTests(BasePanelTests):
    def sitio_con_punto(self, dias, nombre="Planta"):
        """Sitio con coordenadas cuyo único punto activo vence en `dias` días."""
        sitio = Sitio.objects.create(
            cliente=self.cliente,
            nombre=nombre,
            latitud=Decimal("-35.1"),
            longitud=Decimal("-57.7"),
        )
        sitio.puntos.update(
            proximo_vencimiento=timezone.localdate() + timedelta(days=dias)
        )
        return sitio

    def sitios(self):
        respuesta = self.client.get(reverse("panel:mapa_datos"))
        self.assertEqual(respuesta.status_code, 200)
        return {s["nombre"]: s for s in respuesta.json()["sitios"]}

    def test_punto_vencido_ayer_pinta_el_sitio_vencido(self):
        self.sitio_con_punto(-1, "Ayer")
        self.sitio_con_punto(0, "Hoy")
        self.sitio_con_punto(30, "Lejos")
        sitios = self.sitios()
        self.assertEqual(sitios["Ayer"]["estado"], "vencida")
        self.assertEqual(sitios["Hoy"]["estado"], "proxima")
        self.assertEqual(sitios["Lejos"]["estado"], "al_dia")

    def test_popup_trae_vencimiento_y_enlace_a_nuevo_turno(self):
        sitio = self.sitio_con_punto(4)
        datos = self.sitios()["Planta"]
        self.assertEqual(
            datos["vencimiento"], (timezone.localdate() + timedelta(days=4)).isoformat()
        )
        self.assertEqual(
            datos["url_nuevo_turno"],
            reverse("panel:visitas:nuevo_turno", args=[sitio.pk]),
        )
        self.assertEqual(
            datos["url_ficha"], reverse("panel:sitios:ficha", args=[sitio.pk])
        )
        # La página del mapa carga el script que arma el popup con esos datos.
        self.assertContains(self.client.get(reverse("panel:mapa")), "panel/mapa.js")
        script = (RAIZ_APP / "static/panel/mapa.js").read_text(encoding="utf-8")
        for clave in ("sitio.vencimiento", "sitio.url_nuevo_turno", "Nuevo turno"):
            self.assertIn(clave, script)
