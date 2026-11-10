"""El panel de Visitas resuelve todo por la empresa del administrador."""

import shutil
import tempfile

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.visitas.models import Visita

from .ayudas_empresa import crear_foto, dos_empresas

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-panel-empresa-")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class VisitasPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.a.admin)

    def test_listado_solo_de_la_empresa(self):
        respuesta = self.client.get(reverse("panel:visitas:listado"))
        self.assertContains(respuesta, "Sitio A")
        self.assertNotContains(respuesta, "Sitio B")
        # Los filtros no ofrecen empleados de la otra empresa.
        self.assertContains(respuesta, "emp-a")
        self.assertNotContains(respuesta, "emp-b")

    def test_rutas_de_visita_foto_y_turno_de_otra_empresa_dan_404(self):
        foto = crear_foto(self.b)
        pk = self.b.visita.pk
        urls = [
            reverse("panel:visitas:ficha", args=[pk]),
            reverse("panel:visitas:foto", args=[foto.codigo]),
            reverse("panel:visitas:nuevo_turno", args=[self.b.sitio.pk]),
            reverse("panel:visitas:cargar", args=[self.b.sitio.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404, url)
        url = reverse("panel:visitas:revisar_incidencia", args=[pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        propia = crear_foto(self.a)
        url = reverse("panel:visitas:foto", args=[propia.codigo])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_formularios_ofrecen_solo_opciones_de_la_empresa(self):
        for nombre in ("nuevo_turno", "cargar"):
            url = reverse(f"panel:visitas:{nombre}", args=[self.a.sitio.pk])
            form = self.client.get(url).context["form"]
            self.assertEqual(
                list(form.fields["empleado"].queryset), [self.a.empleado], nombre
            )
            servicios = [
                campo.queryset
                for campo in form.fields.values()
                if getattr(campo, "queryset", None) is not None
                and campo.queryset.model.__name__ == "TipoServicio"
            ]
            self.assertTrue(servicios, nombre)
            for queryset in servicios:
                self.assertEqual(list(queryset), [self.a.servicio], nombre)
        url = reverse("panel:visitas:cargar", args=[self.a.sitio.pk])
        productos = self.client.get(url).context["productos"]
        for formulario in productos:
            self.assertEqual(
                list(formulario.fields["producto"].queryset), [self.a.producto]
            )

    def test_contador_de_incidencias_cuenta_solo_la_empresa(self):
        # Cada empresa tiene una incidencia sin revisar.
        respuesta = self.client.get(reverse("panel:sitios:listado"))
        self.assertContains(respuesta, 'class="contador-menu">1<')
        Visita.objects.de_empresa(self.a.empresa).update(
            incidencia_revisada_en=timezone.now()
        )
        respuesta = self.client.get(reverse("panel:sitios:listado"))
        self.assertNotContains(respuesta, "contador-menu")
