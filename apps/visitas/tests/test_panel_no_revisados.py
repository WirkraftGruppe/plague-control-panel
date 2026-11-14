"""Panel de Visitas: reportes de puntos no revisados en la ficha y el contador."""

import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.empresas.pruebas import crear_empresa
from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.models import PuntoNoRevisado, Visita

from .test_models import crear_visita, punto_de

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="detach-no-revisados-test-")


def _jpeg():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "red").save(salida, format="JPEG")
    return SimpleUploadedFile("x.jpg", salida.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class NoRevisadosPanelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-nr", password="x", rol=User.Rol.ADMINISTRADOR, empresa=una_empresa()
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _visita(self, estado=Visita.Estado.REALIZADA):
        ahora = timezone.now()
        extra = {}
        if estado == Visita.Estado.REALIZADA:
            extra = {
                "abierta_en": ahora,
                "cerrada_en": ahora,
                "cierre": Visita.Cierre.ADMINISTRADOR,
            }
        elif estado == Visita.Estado.ABIERTA:
            extra = {"abierta_en": ahora}
        return crear_visita(
            estado=estado, origen=Visita.Origen.MANUAL, motivo_manual="Carga", **extra
        )

    def _reporte(self, visita, **extra):
        return PuntoNoRevisado.objects.create(
            visita=visita,
            punto=punto_de(visita),
            motivo=PuntoNoRevisado.Motivo.SIN_ACCESO,
            **extra,
        )

    def _menu(self):
        return self.client.get(reverse("panel:sitios:listado"))

    def test_contador_cuenta_visita_realizada_con_reporte(self):
        self._reporte(self._visita())
        self.assertContains(self._menu(), 'class="contador-menu">1<')
        filtrado = self.client.get(
            reverse("panel:visitas:listado"), {"incidencia": "sin_revisar"}
        )
        self.assertEqual(len(filtrado.context["incidencias_sin_revisar"]), 1)

    def test_visita_abierta_con_reporte_no_cuenta(self):
        self._reporte(self._visita(Visita.Estado.ABIERTA))
        self.assertNotContains(self._menu(), "contador-menu")

    def test_marcar_revisada_la_saca_del_contador(self):
        visita = self._visita()
        self._reporte(visita)
        self.assertContains(self._menu(), 'class="contador-menu">1<')
        ficha = self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))
        self.assertContains(ficha, "Marcar como revisada")
        respuesta = self.client.post(
            reverse("panel:visitas:revisar_incidencia", args=[visita.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotContains(self._menu(), "contador-menu")
        ficha = self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))
        self.assertNotContains(ficha, "Marcar como revisada")
        self.assertContains(ficha, "Revisada por")

    def test_ficha_del_turno_lista_los_reportes(self):
        visita = self._visita()
        reporte = self._reporte(visita, detalle="Puerta con candado", foto=_jpeg())
        ficha = self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))
        self.assertContains(ficha, "Puntos no revisados")
        self.assertContains(ficha, punto_de(visita).nombre)
        self.assertContains(ficha, "Sin acceso")
        self.assertContains(ficha, "Puerta con candado")
        url = reverse("panel:visitas:foto_no_revisado", args=[reporte.foto_codigo])
        self.assertContains(ficha, url)
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "image/jpeg")
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        sin_foto = self._reporte(self._visita())
        url = reverse("panel:visitas:foto_no_revisado", args=[sin_foto.foto_codigo])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_foto_de_reporte_de_otra_empresa_da_404(self):
        otra = crear_empresa("Otra empresa")
        ajeno = User.objects.create_user(
            "adm-ajeno", password="x", rol=User.Rol.ADMINISTRADOR, empresa=otra
        )
        reporte = self._reporte(self._visita(), foto=_jpeg())
        url = reverse("panel:visitas:foto_no_revisado", args=[reporte.foto_codigo])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(ajeno)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_empleado_no_ve_la_foto(self):
        visita = self._visita()
        reporte = self._reporte(visita, foto=_jpeg())
        url = reverse("panel:visitas:foto_no_revisado", args=[reporte.foto_codigo])
        self.client.force_login(visita.empleado)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/panel/ingresar/", respuesta["Location"])
