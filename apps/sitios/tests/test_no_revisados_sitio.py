from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.visitas.models import PuntoNoRevisado, Visita

from .ayudas_empresa import DatosDeDosEmpresas


class NoRevisadosSitioTests(DatosDeDosEmpresas, TestCase):
    def setUp(self):
        self.crear_empresas()
        self.client.force_login(self.admin_a)

    def _reporte(self, visita, punto, motivo=PuntoNoRevisado.Motivo.SIN_ACCESO):
        return PuntoNoRevisado.objects.create(visita=visita, punto=punto, motivo=motivo)

    def test_ficha_del_sitio_lista_los_reportes(self):
        self._reporte(self.visita_a, self.punto_a)
        self._reporte(self.visita_b, self.punto_b)
        url = reverse("panel:sitios:ficha", args=[self.sitio_a.pk])
        respuesta = self.client.get(url, {"pestana": "datos"})
        reportes = list(respuesta.context["no_revisados"])
        self.assertEqual([r.punto for r in reportes], [self.punto_a])
        self.assertContains(respuesta, "Sin acceso")
        self.assertContains(
            respuesta, reverse("panel:visitas:ficha", args=[self.visita_a.pk])
        )

    def test_inicio_lista_la_visita_en_incidencias(self):
        Visita.objects.de_empresa(self.empresa_a).filter(pk=self.visita_a.pk).update(
            estado=Visita.Estado.REALIZADA, cerrada_en=timezone.now()
        )
        self._reporte(self.visita_a, self.punto_a)
        respuesta = self.client.get(reverse("panel:sitios:listado"))
        self.assertEqual(
            [v.pk for v in respuesta.context["incidencias"]], [self.visita_a.pk]
        )
