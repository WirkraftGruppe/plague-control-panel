"""El panel de Servicios resuelve todo por la empresa del administrador."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.empresas.models import Empresa
from apps.servicios.models import CampoPlanilla, TipoServicio


class ServiciosPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre="Empresa A")
        cls.empresa_b = Empresa.objects.create(nombre="Empresa B")
        cls.admin_a = User.objects.create_user(
            "adm-a",
            password="clave-segura-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=cls.empresa_a,
        )
        cls.propio = TipoServicio.objects.create(
            nombre="Desratizacion", empresa=cls.empresa_a
        )
        cls.ajeno = TipoServicio.objects.create(
            nombre="Fumigacion", empresa=cls.empresa_b
        )
        cls.campo_ajeno = CampoPlanilla.objects.create(
            tipo_servicio=cls.ajeno,
            orden=1,
            etiqueta="Dosis",
            clave="dosis",
            tipo="texto",
        )

    def setUp(self):
        self.client.force_login(self.admin_a)

    def test_listado_solo_de_la_empresa(self):
        respuesta = self.client.get(reverse("panel:servicios:listado"))
        self.assertContains(respuesta, "Desratizacion")
        self.assertNotContains(respuesta, "Fumigacion")

    def test_rutas_de_servicio_y_campo_de_otra_empresa_dan_404(self):
        pk = self.ajeno.pk
        campo = self.campo_ajeno.pk
        urls = [
            reverse("panel:servicios:servicio_editar", args=[pk]),
            reverse("panel:servicios:campos", args=[pk]),
            reverse("panel:servicios:campo_alta", args=[pk]),
            reverse("panel:servicios:campo_editar", args=[campo]),
            reverse("panel:servicios:campo_desactivar", args=[campo]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404, url)
        for nombre in ("campo_reactivar", "campo_desactivar"):
            url = reverse(f"panel:servicios:{nombre}", args=[campo])
            self.assertEqual(self.client.post(url).status_code, 404, nombre)
        self.campo_ajeno.refresh_from_db()
        self.assertTrue(self.campo_ajeno.activo)
        ok = reverse("panel:servicios:campos", args=[self.propio.pk])
        self.assertEqual(self.client.get(ok).status_code, 200)

    def test_alta_con_el_nombre_de_un_servicio_de_otra_empresa_queda_en_la_empresa_del_administrador(  # noqa: E501
        self,
    ):
        respuesta = self.client.post(
            reverse("panel:servicios:servicio_alta"),
            {"nombre": "Fumigacion", "activo": "on"},
        )
        self.assertEqual(respuesta.status_code, 302)
        nuevo = TipoServicio.todos.get(nombre="Fumigacion", empresa=self.empresa_a)
        self.assertEqual(nuevo.slug, "fumigacion")
        self.assertEqual(TipoServicio.todos.filter(slug="fumigacion").count(), 2)
