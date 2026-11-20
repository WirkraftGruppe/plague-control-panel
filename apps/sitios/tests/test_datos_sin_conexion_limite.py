"""`GET me/datos-sin-conexion/`: límite de 30 pedidos por hora y usuario."""

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.sitios.tests.ayudas_empresa import DatosDeDosEmpresas

URL = "/api/v1/me/datos-sin-conexion/"


class LimiteDatosSinConexionTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        cache.clear()
        self.crear_empresas()
        self.api = APIClient()
        self.api.force_authenticate(self.empleado_a)

    def test_pedido_31_da_429_con_retry_after(self):
        for _ in range(30):
            self.assertEqual(self.api.get(URL).status_code, 200)
        respuesta = self.api.get(URL)
        self.assertEqual(respuesta.status_code, 429)
        self.assertIn("Retry-After", respuesta)

    def test_304_cuenta_para_el_limite(self):
        etag = self.api.get(URL)["ETag"]
        for _ in range(29):
            respuesta = self.api.get(URL, HTTP_IF_NONE_MATCH=etag)
            self.assertEqual(respuesta.status_code, 304)
        self.assertEqual(self.api.get(URL).status_code, 429)

    def test_cupo_es_por_usuario(self):
        for _ in range(30):
            self.api.get(URL)
        self.assertEqual(self.api.get(URL).status_code, 429)
        otro = APIClient()
        otro.force_authenticate(self.admin_a)
        self.assertEqual(otro.get(URL).status_code, 200)
