"""Pruebas del alta y la edición de tipos de servicio en el panel."""

from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import User
from apps.servicios.models import TipoServicio


class TipoServicioAbmTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-abm", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            username="emp-abm", password="x", rol=User.Rol.EMPLEADO
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def alta(self, nombre="Control de roedores"):
        return self.client.post(
            reverse("panel:servicios:servicio_alta"),
            {"nombre": nombre, "activo": "on"},
        )

    def test_alta_genera_slug(self):
        respuesta = self.alta()
        self.assertRedirects(respuesta, reverse("panel:servicios:listado"))
        servicio = TipoServicio.objects.get()
        self.assertEqual(servicio.slug, "control-de-roedores")
        self.assertTrue(servicio.activo)

    def test_dos_servicios_con_el_mismo_nombre_tienen_slugs_distintos(self):
        self.alta()
        self.alta()
        self.alta()
        slugs = set(TipoServicio.objects.values_list("slug", flat=True))
        self.assertEqual(
            slugs,
            {"control-de-roedores", "control-de-roedores-2", "control-de-roedores-3"},
        )

    def test_edicion_no_cambia_el_slug(self):
        servicio = TipoServicio.objects.create(nombre="Roedores")
        respuesta = self.client.post(
            reverse("panel:servicios:servicio_editar", args=[servicio.pk]),
            {"nombre": "Roedores y aves", "activo": "on"},
        )
        self.assertRedirects(respuesta, reverse("panel:servicios:listado"))
        servicio.refresh_from_db()
        self.assertEqual(servicio.nombre, "Roedores y aves")
        self.assertEqual(servicio.slug, "roedores")

    def test_desactivar_desde_la_edicion(self):
        servicio = TipoServicio.objects.create(nombre="Roedores")
        self.client.post(
            reverse("panel:servicios:servicio_editar", args=[servicio.pk]),
            {"nombre": "Roedores"},
        )
        servicio.refresh_from_db()
        self.assertFalse(servicio.activo)

    def test_empleado_no_accede_a_alta_ni_edicion(self):
        servicio = TipoServicio.objects.create(nombre="Roedores")
        self.client.force_login(self.empleado)
        rutas = [
            reverse("panel:servicios:servicio_alta"),
            reverse("panel:servicios:servicio_editar", args=[servicio.pk]),
        ]
        for ruta in rutas:
            self.assertEqual(self.client.get(ruta).status_code, 403)
            envio = self.client.post(ruta, {"nombre": "X", "activo": "on"})
            self.assertEqual(envio.status_code, 403)
        self.assertEqual(TipoServicio.objects.count(), 1)

    def test_no_hay_ruta_de_borrado_de_servicio(self):
        servicio = TipoServicio.objects.create(nombre="Roedores")
        for nombre in ("servicio_borrar", "servicio_eliminar"):
            with self.assertRaises(NoReverseMatch):
                reverse(f"panel:servicios:{nombre}", args=[servicio.pk])
        for sufijo in ("borrar", "eliminar"):
            ruta = f"{reverse('panel:servicios:listado')}{servicio.pk}/{sufijo}/"
            self.assertEqual(self.client.post(ruta).status_code, 404)

    def test_el_listado_enlaza_a_editar_y_a_nuevo(self):
        servicio = TipoServicio.objects.create(nombre="Roedores")
        respuesta = self.client.get(reverse("panel:servicios:listado"))
        self.assertContains(
            respuesta, reverse("panel:servicios:servicio_editar", args=[servicio.pk])
        )
        self.assertContains(respuesta, reverse("panel:servicios:servicio_alta"))
        self.assertContains(respuesta, "<h1>Servicios</h1>", html=True)
