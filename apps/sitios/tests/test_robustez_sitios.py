import json
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import TipoServicio
from apps.sitios import geocodificacion
from apps.sitios.models import Sitio

ABRIR = "apps.sitios.geocodificacion._abrir"


class ProgramacionRobustezTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        self.client.force_login(self.admin)
        cliente = Cliente.objects.create(razon_social="ACME", empresa=una_empresa())
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        self.punto = self.sitio.puntos.get()
        self.viejo = TipoServicio.objects.create(
            nombre="Viejo", empresa=una_empresa(), activo=False
        )
        self.punto.servicio = self.viejo
        self.punto.save(update_fields=["servicio"])
        self.url = reverse("panel:sitios:punto_programacion", args=[self.punto.pk])

    def test_servicio_desactivado_se_conserva_al_editar_la_fila(self):
        fila = self.client.get(self.url).content.decode()
        self.assertIn(f'<option value="{self.viejo.pk}" selected>', fila)
        respuesta = self.client.post(
            self.url,
            {
                "servicio": self.viejo.pk,
                "frecuencia_dias": "15",
                "proximo_vencimiento": "2026-12-01",
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.servicio, self.viejo)
        self.assertEqual(self.punto.frecuencia_dias, 15)

    def test_punto_inactivo_no_se_programa(self):
        self.punto.activo = False
        self.punto.save(update_fields=["activo"])
        respuesta = self.client.post(
            self.url, {"servicio": "", "frecuencia_dias": "15"}
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_no_se_asigna_otro_servicio_inactivo(self):
        otro = TipoServicio.objects.create(
            nombre="Otro", empresa=una_empresa(), activo=False
        )
        respuesta = self.client.post(
            self.url, {"servicio": otro.pk, "frecuencia_dias": "15"}
        )
        self.assertEqual(respuesta.status_code, 422)
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.servicio, self.viejo)


class GeocodificacionEmpresaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_cache_de_una_empresa_no_responde_a_otra(self):
        otra = Empresa.objects.create(nombre="Otra empresa")
        datos = json.dumps(
            [{"display_name": "Castelli", "lat": "-36", "lon": "-57"}]
        ).encode()
        with mock.patch(ABRIR, return_value=datos) as abrir:
            geocodificacion.buscar("Castelli", una_empresa().pk)
            cache.delete(geocodificacion.CLAVE_TURNO)
            geocodificacion.buscar("Castelli", una_empresa().pk)
            self.assertEqual(abrir.call_count, 1)
            cache.delete(geocodificacion.CLAVE_TURNO)
            geocodificacion.buscar("Castelli", otra.pk)
        self.assertEqual(abrir.call_count, 2)


class ResolverRobustezTests(TestCase):
    def test_codigo_mal_formado_da_404_json(self):
        empleado = User.objects.create_user(
            "emp", password="x", rol=User.Rol.EMPLEADO, empresa=una_empresa()
        )
        api = APIClient()
        api.force_authenticate(empleado)
        r = api.post("/api/v1/qr/no-es-un-uuid/resolver/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r["Content-Type"], "application/json")
        self.assertIn("detalle", r.json())
