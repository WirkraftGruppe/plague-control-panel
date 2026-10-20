"""Pruebas del editor de planillas en el panel."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Revision, Visita


class PlanillaPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="admin-plan", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            username="emp-plan", password="x", rol=User.Rol.EMPLEADO
        )
        cls.tipo = TipoServicio.objects.create(nombre="Roedores", slug="roedores-pl")
        cls.campo = CampoPlanilla.objects.create(
            tipo_servicio=cls.tipo,
            orden=1,
            etiqueta="Cebos",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_empleado_no_accede(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse("panel:servicios:listado"))
        self.assertEqual(respuesta.status_code, 403)

    def test_alta_de_campo(self):
        respuesta = self.client.post(
            reverse("panel:servicios:campo_alta", args=[self.tipo.pk]),
            {
                "orden": 2,
                "etiqueta": "Estado",
                "clave": "estado",
                "tipo": "opcion",
                "ambito": "punto",
                "opciones": "Bueno\n\nMalo\n",
            },
        )
        self.assertRedirects(
            respuesta, reverse("panel:servicios:campos", args=[self.tipo.pk])
        )
        nuevo = CampoPlanilla.objects.get(clave="estado")
        self.assertEqual(nuevo.opciones, ["Bueno", "Malo"])
        self.assertTrue(nuevo.activo)

    def test_opcion_exige_opciones(self):
        respuesta = self.client.post(
            reverse("panel:servicios:campo_alta", args=[self.tipo.pk]),
            {"orden": 2, "etiqueta": "E", "clave": "e", "tipo": "opcion"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(CampoPlanilla.objects.filter(clave="e").exists())

    def test_desactivar_saca_el_campo_del_esquema(self):
        url = reverse("panel:servicios:campo_desactivar", args=[self.campo.pk])
        self.assertContains(self.client.get(url), "Desactivar campo")
        self.assertEqual(len(self.tipo.esquema_planilla()), 1)
        self.client.post(url)
        self.campo.refresh_from_db()
        self.assertFalse(self.campo.activo)
        self.assertEqual(self.tipo.esquema_planilla(), [])
        self.assertTrue(CampoPlanilla.objects.filter(pk=self.campo.pk).exists())

    def test_reactivar_campo_vuelve_al_esquema(self):
        self.campo.activo = False
        self.campo.save(update_fields=["activo"])
        self.assertEqual(self.tipo.esquema_planilla(), [])
        url = reverse("panel:servicios:campo_reactivar", args=[self.campo.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        respuesta = self.client.post(url)
        self.assertRedirects(
            respuesta, reverse("panel:servicios:campos", args=[self.tipo.pk])
        )
        self.campo.refresh_from_db()
        self.assertTrue(self.campo.activo)
        self.assertEqual(self.tipo.esquema_planilla()[0]["clave"], "cebos")

    def test_clave_y_tipo_fijos_si_una_visita_los_uso(self):
        url = reverse("panel:servicios:campo_editar", args=[self.campo.pk])
        envio = {
            "orden": 5,
            "etiqueta": "Cebos nuevos",
            "clave": "otra",
            "tipo": "texto",
            "obligatorio": "on",
        }
        # Sin visitas, clave y tipo todavía se pueden cambiar.
        formulario = self.client.get(url).context["form"]
        self.assertFalse(formulario.fields["clave"].disabled)

        cliente = Cliente.objects.create(razon_social="ACME")
        sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        Visita.objects.create(
            sitio=sitio,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            datos={self.tipo.slug: {"cebos": 3}},
        )
        formulario = self.client.get(url).context["form"]
        self.assertTrue(formulario.fields["clave"].disabled)
        self.assertTrue(formulario.fields["tipo"].disabled)

        self.client.post(url, envio)
        self.campo.refresh_from_db()
        self.assertEqual(self.campo.clave, "cebos")
        self.assertEqual(self.campo.tipo, "numero")
        self.assertEqual(self.campo.etiqueta, "Cebos nuevos")
        self.assertEqual(self.campo.orden, 5)

    def test_clave_fija_si_una_revision_la_uso(self):
        url = reverse("panel:servicios:campo_editar", args=[self.campo.pk])
        sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME"), nombre="P"
        )
        visita = Visita.objects.create(
            sitio=sitio, empleado=self.empleado, origen=Visita.Origen.APP
        )
        formulario = self.client.get(url).context["form"]
        self.assertFalse(formulario.fields["clave"].disabled)
        Revision.objects.create(
            visita=visita,
            punto=sitio.puntos.get(orden=0),
            servicio=self.tipo,
            orden=1,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
            datos={"cebos": 3},
        )
        formulario = self.client.get(url).context["form"]
        for nombre in ("clave", "tipo", "ambito"):
            self.assertTrue(formulario.fields[nombre].disabled, nombre)

    def test_ambito_fijo_si_una_visita_uso_la_clave(self):
        url = reverse("panel:servicios:campo_editar", args=[self.campo.pk])
        formulario = self.client.get(url).context["form"]
        self.assertIn("ambito", formulario.fields)
        self.assertFalse(formulario.fields["ambito"].disabled)

        cliente = Cliente.objects.create(razon_social="ACME")
        sitio = Sitio.objects.create(cliente=cliente, nombre="Planta")
        Visita.objects.create(
            sitio=sitio,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            datos={self.tipo.slug: {"cebos": 3}},
        )
        formulario = self.client.get(url).context["form"]
        self.assertTrue(formulario.fields["ambito"].disabled)

        self.client.post(
            url,
            {
                "orden": 1,
                "etiqueta": "Cebos",
                "clave": "cebos",
                "tipo": "numero",
                "ambito": "visita",
            },
        )
        self.campo.refresh_from_db()
        self.assertEqual(self.campo.ambito, "punto")

    def test_no_hay_ruta_de_borrado(self):
        for nombre in ("campo_editar", "campo_desactivar"):
            url = reverse(f"panel:servicios:{nombre}", args=[self.campo.pk])
            self.client.delete(url)
        self.assertTrue(CampoPlanilla.objects.filter(pk=self.campo.pk).exists())
