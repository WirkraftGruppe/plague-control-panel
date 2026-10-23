"""Barra lateral: ítem activo, grupos, contador de sitios vencidos y panel lateral."""

import datetime
import re

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.sitios.models import PuntoControl, Sitio

ENLACES = {
    "sitios": "panel:sitios:listado",
    "turnos": "panel:visitas:listado",
    "mapa": "panel:mapa",
    "clientes": "panel:clientes:listado",
    "catalogo": "panel:servicios:listado",
    "usuarios": "panel:usuarios:listado",
}


class MenuActivoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-barra", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.cliente = Cliente.objects.create(razon_social="Cliente SA")

    def setUp(self):
        self.client.force_login(self.admin)

    def _marcados(self, nombre_ruta):
        """Hrefs de la barra con aria-current="page" al abrir la ruta."""
        html = self.client.get(reverse(nombre_ruta)).content.decode()
        enlaces = re.findall(
            r'<a class="menu-enlace[^"]*" href="([^"]+)"([^>]*)>', html
        )
        return [h for h, atributos in enlaces if 'aria-current="page"' in atributos]

    def _sitio(self, nombre, dias=-1, activo=True):
        sitio = Sitio.objects.create(cliente=self.cliente, nombre=nombre, activo=activo)
        PuntoControl.objects.filter(sitio=sitio).update(
            proximo_vencimiento=timezone.localdate() + datetime.timedelta(days=dias)
        )
        return sitio

    def test_cada_ruta_marca_solo_su_entrada(self):
        casos = {
            "panel:sitios:listado": "sitios",
            "panel:visitas:listado": "turnos",
            "panel:mapa": "mapa",
            "panel:clientes:listado": "clientes",
            "panel:usuarios:listado": "usuarios",
        }
        for ruta, clave in casos.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(self._marcados(ruta), [reverse(ENLACES[clave])])

    def test_servicios_y_productos_marcan_catalogo(self):
        esperado = [reverse("panel:servicios:listado")]
        for ruta in ("panel:servicios:listado", "panel:productos:listado"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self._marcados(ruta), esperado)

    def test_grupos_trabajo_y_administracion(self):
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        trabajo = html.index(">Trabajo<")
        administracion = html.index(">Administración<")
        self.assertLess(trabajo, administracion)
        orden = [
            reverse(ENLACES[c])
            for c in ("sitios", "turnos", "mapa", "clientes", "catalogo", "usuarios")
        ]
        posiciones = [html.index(f'href="{href}"') for href in orden]
        self.assertEqual(posiciones, sorted(posiciones))
        self.assertTrue(all(trabajo < p < administracion for p in posiciones[:3]))
        self.assertTrue(all(p > administracion for p in posiciones[3:]))
        self.assertNotIn(f'href="{reverse("panel:productos:listado")}"', html)

    def test_contador_de_sitios_vencidos(self):
        url = reverse("panel:sitios:listado")
        self.assertNotContains(self.client.get(url), "contador-vencidos")
        self._sitio("Vencido uno")
        self._sitio("Vencido dos")
        self._sitio("Al día", dias=30)
        self._sitio("Inactivo", activo=False)
        self.assertContains(self.client.get(url), 'contador-vencidos">2<')

    def test_logo_con_alt_nombre_empresa_y_pie_con_salir(self):
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        self.assertIn(f'alt="{settings.NOMBRE_EMPRESA}"', html)
        self.assertIn("img/logo.png", html)
        pie = html[html.index('class="barra-pie"') :]
        self.assertIn("adm-barra", pie)
        self.assertIn(f'action="{reverse("panel:salir")}"', pie)
        self.assertIn('method="post"', pie)
        self.assertIn(">Salir<", pie)
        self.assertIn(">Detach<", pie)

    def test_base_trae_contenedor_y_script_del_panel_lateral(self):
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        self.assertRegex(
            html,
            r'<div id="panel-lateral" role="dialog" aria-modal="true"[^>]*\bhidden>',
        )
        self.assertIn("panel/panel_lateral.js", html)
        self.assertNotIn("block tema", html)
