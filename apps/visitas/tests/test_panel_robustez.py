"""Robustez del panel de visitas: mapa del panel lateral, filtros, tarjeta y admin."""

import re
from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.pruebas import crear_plataforma
from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.models import ItemTurno

from .test_models import crear_visita

RUTA_JS = Path(__file__).resolve().parent.parent / "static/visitas/nuevo_turno.js"
HTMX = {"HX-Request": "true"}


def _administrador(username):
    return User.objects.create_user(
        username, password="x", rol=User.Rol.ADMINISTRADOR, empresa=una_empresa()
    )


class MapaPanelLateralTests(TestCase):
    def test_mapa_del_panel_lateral_sin_teclado(self):
        codigo = RUTA_JS.read_text(encoding="utf-8")
        opciones = re.search(r"L\.map\([^{]*\{([^}]*)\}", codigo)
        self.assertIsNotNone(opciones)
        self.assertRegex(opciones.group(1), r"keyboard:\s*false")


class AnchoPanelNuevoTurnoTests(TestCase):
    def test_panel_de_nuevo_turno_tiene_ancho_ajustable(self):
        codigo = RUTA_JS.read_text(encoding="utf-8")
        estilos = RUTA_JS.with_suffix(".css").read_text(encoding="utf-8")
        # El tirador solo se crea dentro del panel lateral y solo cambia el ancho.
        self.assertIn('raiz.closest("#panel-lateral")', codigo)
        self.assertIn('setAttribute("role", "separator")', codigo)
        self.assertIn('"--ancho-nuevo-turno"', codigo)
        self.assertNotRegex(codigo, r"style\.height|--alto")
        self.assertRegex(codigo, r"ArrowLeft|ArrowRight")
        self.assertIn("invalidateSize", codigo)
        # El ancho propio se aplica solo con un nuevo turno; los demás paneles, 520 px.
        self.assertIn(
            "#panel-lateral:has(.nuevo-turno) "
            "{ width: var(--ancho-nuevo-turno, 520px); }",
            estilos,
        )
        self.assertIn("cursor: ew-resize", estilos)


class FiltrosTurnosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita()
        cls.admin = _administrador("adm-filtros")

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("panel:visitas:listado")

    def test_listado_de_turnos_usa_la_fila_filtros(self):
        html = self.client.get(self.url, {"q": "Planta", "orden": "creado"}).content
        html = html.decode()
        self.assertRegex(html, r'<form class="filtros"[^>]*hx-trigger="change"')
        filtros = html.split('<form class="filtros"')[1].split("</form>")[0]
        for nombre in ("empleado", "sitio", "estado", "incidencia"):
            self.assertIn(f'name="{nombre}"', filtros)
        self.assertIn('name="orden" value="creado"', filtros)
        self.assertLess(html.index('class="filtros"'), html.index('id="listado"'))
        self.assertEqual(html.count('class="buscador"'), 1)
        parcial = self.client.get(self.url, headers=HTMX).content.decode()
        self.assertIn('id="listado"', parcial)
        self.assertNotIn('class="filtros"', parcial)
        self.assertNotIn('class="buscador"', parcial)

    def test_filtros_y_busqueda_se_combinan(self):
        respuesta = self.client.get(
            self.url, {"q": "Planta", "empleado": self.visita.empleado_id}
        )
        self.assertContains(respuesta, "Planta 1")
        respuesta = self.client.get(
            self.url, {"q": "Nada", "empleado": self.visita.empleado_id}
        )
        self.assertContains(respuesta, "No hay turnos que coincidan.")


class NuevoTurnoTarjetaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        visita = crear_visita()
        cls.sitio = visita.sitio
        cls.admin = _administrador("adm-tarjeta")
        visita.delete()

    def test_sitio_dentro_de_la_tarjeta(self):
        self.client.force_login(self.admin)
        url = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])
        for cabeceras in ({}, HTMX):
            html = self.client.get(url, headers=cabeceras).content.decode()
            formulario = html.split('<form id="form-turno"')[1].split("</form>")[0]
            self.assertIn("Sitio: Planta 1", formulario)
            self.assertEqual(html.count("Sitio: Planta 1"), 1)


class AdminSitioConItemsTests(TestCase):
    def test_sitio_de_solo_lectura_en_pendiente_con_items(self):
        con_items = crear_visita()
        punto = con_items.sitio.puntos.first()
        ItemTurno.objects.create(visita=con_items, punto=punto, servicio=con_items.tipo)
        sin_items = crear_visita()
        self.client.force_login(crear_plataforma(username="root-items"))
        url = reverse("admin:visitas_visita_change", args=[con_items.pk])
        html = self.client.get(url).content.decode()
        self.assertNotIn('name="sitio"', html)
        otro = crear_visita()
        self.client.post(
            url,
            {
                "sitio": otro.sitio_id,
                "empleado": con_items.empleado_id,
                "origen": "app",
            },
        )
        con_items.refresh_from_db()
        self.assertNotEqual(con_items.sitio_id, otro.sitio_id)
        url = reverse("admin:visitas_visita_change", args=[sin_items.pk])
        self.assertIn('name="sitio"', self.client.get(url).content.decode())
