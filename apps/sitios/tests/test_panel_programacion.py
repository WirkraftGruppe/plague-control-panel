import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.clientes.models import Cliente
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio

User = get_user_model()


class ProgramacionPuntoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.admin)
        cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        self.punto = self.sitio.puntos.get()
        self.servicio = TipoServicio.objects.create(nombre="Desinsectación")
        self.url = reverse("panel:sitios:punto_programacion", args=[self.punto.pk])

    def _post(self, **extra):
        datos = {
            "servicio": self.servicio.pk,
            "frecuencia_dias": "30",
            "proximo_vencimiento": "2026-12-01",
        }
        datos.update(extra)
        return self.client.post(self.url, datos, headers={"HX-Request": "true"})

    def test_htmx_guarda_servicio_frecuencia_y_vencimiento(self):
        respuesta = self._post()
        self.assertEqual(respuesta.status_code, 200)
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.servicio, self.servicio)
        self.assertEqual(self.punto.frecuencia_dias, 30)
        self.assertEqual(self.punto.proximo_vencimiento, datetime.date(2026, 12, 1))

    def test_devuelve_la_fila_parcial(self):
        respuesta = self._post()
        contenido = respuesta.content.decode()
        self.assertTrue(contenido.lstrip().startswith("<tr"))
        self.assertIn(f'id="punto-{self.punto.pk}"', contenido)
        self.assertNotIn("<html", contenido)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_frecuencia_cero_da_error(self):
        respuesta = self._post(frecuencia_dias="0")
        self.assertEqual(respuesta.status_code, 422)
        self.assertIn('role="alert"', respuesta.content.decode())
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.frecuencia_dias)

    def test_cambio_queda_en_el_historial(self):
        self._post()
        ultimo = self.punto.history.first()
        self.assertEqual(ultimo.history_change_reason, "Programación editada")
        self.assertEqual(ultimo.history_user, self.admin)
        self.assertEqual(ultimo.frecuencia_dias, 30)

    def test_empleado_no_accede(self):
        empleado = User.objects.create_user(
            "emp", password="clave-segura-123", rol=User.Rol.EMPLEADO
        )
        self.client.force_login(empleado)
        self.assertEqual(self._post().status_code, 403)
        self.punto.refresh_from_db()
        self.assertIsNone(self.punto.servicio)


class ResponsableSitioTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.admin)
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.empleado = User.objects.create_user(
            "emp", password="clave-segura-123", rol=User.Rol.EMPLEADO
        )

    def _datos(self, responsable):
        return {
            "cliente": self.cliente.pk,
            "nombre": "Depósito",
            "sector": Sitio.Sector.OTRO,
            "responsable": responsable.pk,
            "activo": "on",
        }

    def test_formulario_guarda_responsable_empleado(self):
        respuesta = self.client.post(
            reverse("panel:sitios:alta"), self._datos(self.empleado)
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(Sitio.objects.get().responsable, self.empleado)

    def test_administrador_no_puede_ser_responsable(self):
        respuesta = self.client.post(
            reverse("panel:sitios:alta"), self._datos(self.admin)
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("responsable", respuesta.context["form"].errors)
        self.assertFalse(Sitio.objects.exists())
