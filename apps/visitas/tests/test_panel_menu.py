"""Menú del panel: secciones y contador de incidencias sin revisar."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.visitas.models import Visita

from .test_models import crear_visita


class MenuTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita(incidencia=True)
        cls.admin = User.objects.create_user(
            "adm-menu", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _menu(self):
        return self.client.get(reverse("panel:sitios:listado"))

    def test_menu_tiene_las_secciones_nuevas(self):
        respuesta = self._menu()
        for nombre in (
            "panel:sitios:listado",
            "panel:mapa",
            "panel:visitas:listado",
            "panel:clientes:listado",
            "panel:servicios:listado",
            "panel:productos:listado",
            "panel:usuarios:listado",
        ):
            self.assertContains(
                respuesta, f'href="{reverse(nombre)}"', msg_prefix=nombre
            )
        for texto in ("Sitios", "Mapa", "Turnos", "Clientes", "Catálogo", "Servicios"):
            self.assertContains(respuesta, texto)
        for texto in ("Productos", "Usuarios"):
            self.assertContains(respuesta, texto)
        for texto in ("Tablero", "Planillas"):
            self.assertNotContains(respuesta, f">{texto}<")

    def test_contador_de_incidencias_sin_revisar(self):
        # Dos sin revisar (la del setUp y otra), una revisada y una sin incidencia.
        otra = crear_visita(incidencia=True)
        crear_visita(incidencia=True, incidencia_revisada_en=timezone.now())
        crear_visita()
        self.assertContains(self._menu(), 'class="contador-menu">2<')
        otra.delete()
        self.assertContains(self._menu(), 'class="contador-menu">1<')
        Visita.objects.filter(pk=self.visita.pk).update(
            incidencia_revisada_en=timezone.now()
        )
        self.assertNotContains(self._menu(), "contador-menu")
