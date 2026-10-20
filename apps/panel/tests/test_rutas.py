import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.test import TestCase
from django.urls import NoReverseMatch, resolve, reverse

from apps.clientes.models import Cliente
from apps.sitios.models import Sitio
from apps.sitios.qr import contenido_qr


class RutasTests(TestCase):
    """Las rutas raíz: login del panel, QR y API, sin sitio público."""

    def test_raiz_redirige_al_login(self):
        respuesta = self.client.get("/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/", fetch_redirect_response=False
        )
        self.assertEqual(respuesta.status_code, 302)

    def test_q_uuid_lo_sirve_sitios(self):
        codigo = uuid.uuid4()
        self.assertEqual(resolve(f"/q/{codigo}/").view_name, "publico:qr")
        respuesta = self.client.get(f"/q/{codigo}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, settings.NOMBRE_EMPRESA)
        self.assertNotContains(respuesta, str(codigo))

    def test_contenido_del_qr_abre_la_pagina_de_sitios(self):
        cliente = Cliente.objects.create(razon_social="Cliente")
        punto = Sitio.objects.create(cliente=cliente, nombre="Sitio").puntos.get()
        ruta = urlparse(contenido_qr(punto)).path
        self.assertEqual(resolve(ruta).view_name, "publico:qr")
        self.assertEqual(self.client.get(ruta).status_code, 200)

    def test_rutas_del_sitio_publico_dan_404(self):
        for ruta in (
            "/empresa/",
            "/contacto/",
            "/servicio/x/",
            "/sitemap.xml",
            "/robots.txt",
            "/panel/web/",
        ):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 404)

    def test_q_no_uuid_da_404(self):
        self.assertEqual(self.client.get("/q/no-es-uuid/").status_code, 404)

    def test_panel_anonimo_redirige_al_login(self):
        respuesta = self.client.get("/panel/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/?next=/panel/", fetch_redirect_response=False
        )

    def test_api_v1_anonimo_recibe_401(self):
        self.assertEqual(self.client.get("/api/v1/").status_code, 401)

    def test_rutas_con_espacio_de_nombres(self):
        codigo = uuid.uuid4()
        self.assertEqual(reverse("panel:inicio"), "/panel/")
        self.assertEqual(reverse("api:raiz"), "/api/v1/")
        self.assertEqual(reverse("publico:qr", args=[codigo]), f"/q/{codigo}/")

    def test_inicio_sin_espacio_de_nombres_no_resuelve(self):
        with self.assertRaises(NoReverseMatch):
            reverse("inicio")
