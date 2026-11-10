"""El panel de Sitios resuelve todo por la empresa del administrador."""

import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.sitios.models import Sitio
from apps.sitios.panel_forms import (
    PlanoForm,
    PosicionForm,
    ProgramacionForm,
    PuntoForm,
    SitioForm,
)

from .ayudas_empresa import DatosDeDosEmpresas

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sitios-empresa-test-")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class SitiosPorEmpresaTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        self.crear_empresas()
        self.client.force_login(self.admin_a)

    def test_inicio_y_listado_solo_de_la_empresa(self):
        respuesta = self.client.get(reverse("panel:sitios:listado"))
        self.assertContains(respuesta, "Sitio Empresa A")
        self.assertNotContains(respuesta, "Sitio Empresa B")
        self.assertNotContains(respuesta, "Cliente Empresa B")
        self.assertEqual(
            [s.pk for s in respuesta.context["object_list"]], [self.sitio_a.pk]
        )
        self.assertEqual(list(respuesta.context["clientes"]), [self.cliente_a])
        self.assertEqual(
            [v.pk for v in respuesta.context["turnos_hoy"]], [self.visita_a.pk]
        )
        filtrado = self.client.get(
            reverse("panel:sitios:listado"), {"cliente": self.cliente_b.pk}
        )
        self.assertNotContains(filtrado, "Sitio Empresa B")

    def test_rutas_de_sitio_punto_y_plano_de_otra_empresa_dan_404(self):
        pk_sitio, pk_punto, pk_plano = (
            self.sitio_b.pk,
            self.punto_b.pk,
            self.plano_b.pk,
        )
        rutas_get = (
            ("ficha", pk_sitio),
            ("editar", pk_sitio),
            ("punto_alta", pk_sitio),
            ("plano_alta", pk_sitio),
            ("plano_imagen", pk_plano),
            ("punto_editar", pk_punto),
            ("punto_desactivar", pk_punto),
            ("punto_qr_png", pk_punto),
            ("punto_regenerar_qr", pk_punto),
            ("punto_programacion", pk_punto),
        )
        for nombre, pk in rutas_get:
            with self.subTest(ruta=nombre):
                url = reverse(f"panel:sitios:{nombre}", args=[pk])
                self.assertEqual(self.client.get(url).status_code, 404)
        rutas_post = (
            ("editar", pk_sitio, {"nombre": "Cambio"}),
            ("punto_alta", pk_sitio, {"nombre": "Intruso"}),
            ("plano_alta", pk_sitio, {"nombre": "Intruso"}),
            ("punto_editar", pk_punto, {"nombre": "Cambio"}),
            ("punto_desactivar", pk_punto, {}),
            ("punto_regenerar_qr", pk_punto, {}),
            ("punto_programacion", pk_punto, {"frecuencia_dias": "30"}),
            ("punto_posicion", pk_punto, {"x": "0.5", "y": "0.5"}),
        )
        for nombre, pk, datos in rutas_post:
            with self.subTest(ruta=nombre, metodo="POST"):
                url = reverse(f"panel:sitios:{nombre}", args=[pk])
                self.assertEqual(self.client.post(url, datos).status_code, 404)
        self.sitio_b.refresh_from_db()
        self.punto_b.refresh_from_db()
        self.assertEqual(self.sitio_b.nombre, "Sitio Empresa B")
        self.assertTrue(self.punto_b.activo)
        self.assertEqual(self.sitio_b.puntos.count(), 1)
        self.assertEqual(self.sitio_b.planos.count(), 1)
        propia = reverse("panel:sitios:ficha", args=[self.sitio_a.pk])
        self.assertEqual(self.client.get(propia).status_code, 200)

    def test_formularios_ofrecen_solo_opciones_de_la_empresa(self):
        formulario = SitioForm(empresa=self.empresa_a)
        self.assertEqual(list(formulario.fields["cliente"].queryset), [self.cliente_a])
        self.assertEqual(
            list(formulario.fields["responsable"].queryset), [self.empleado_a]
        )
        punto = PuntoForm(sitio=self.sitio_a)
        self.assertEqual(list(punto.fields["plano"].queryset), [self.plano_a])
        posicion = PosicionForm(empresa=self.empresa_a)
        self.assertEqual(list(posicion.fields["plano"].queryset), [self.plano_a])
        programacion = ProgramacionForm(empresa=self.empresa_a)
        self.assertEqual(
            list(programacion.fields["servicio"].queryset), [self.servicio_a]
        )
        plano = PlanoForm(sitio=self.sitio_a)
        self.assertEqual(plano.instance.empresa, self.empresa_a)
        # Un cliente o un responsable de otra empresa no pasa la validación.
        datos = {
            "cliente": self.cliente_a.pk,
            "nombre": "Nuevo",
            "sector": Sitio.Sector.OTRO,
            "activo": "on",
        }
        for campo, ajeno in (
            ("cliente", self.cliente_b.pk),
            ("responsable", self.empleado_b.pk),
        ):
            with self.subTest(campo=campo):
                respuesta = self.client.post(
                    reverse("panel:sitios:alta"), {**datos, campo: ajeno}
                )
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn(campo, respuesta.context["form"].errors)
        self.assertFalse(Sitio.todos.filter(nombre="Nuevo").exists())

    def test_alta_de_sitio_asigna_la_empresa(self):
        respuesta = self.client.post(
            reverse("panel:sitios:alta"),
            {
                "cliente": self.cliente_a.pk,
                "nombre": "Nuevo",
                "sector": Sitio.Sector.OTRO,
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        nuevo = Sitio.todos.get(nombre="Nuevo")
        self.assertEqual(nuevo.empresa_id, self.empresa_a.pk)
        self.assertEqual(nuevo.puntos.get().empresa_id, self.empresa_a.pk)
