"""Listados del panel: un orden o una búsqueda inválidos no dan 500."""

from django.test import RequestFactory, TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.empresas.pruebas import crear_empresa
from apps.panel.listados import ListadoPanelMixin

LISTADOS = (
    "panel:usuarios:listado",
    "panel:visitas:listado",
    "panel:productos:listado",
    "panel:servicios:listado",
    "panel:clientes:listado",
    "panel:sitios:listado",
)


class ListadosRobustezTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm-rob", password="x", rol=User.Rol.ADMINISTRADOR, empresa=crear_empresa()
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_orden_con_doble_guion_responde_200_en_todos(self):
        for nombre in LISTADOS:
            with self.subTest(listado=nombre):
                respuesta = self.client.get(reverse(nombre), {"orden": "--creado"})
                self.assertEqual(respuesta.status_code, 200)

    def test_busqueda_con_nul_responde_200_en_todos(self):
        for nombre in LISTADOS:
            with self.subTest(listado=nombre):
                respuesta = self.client.get(reverse(nombre), {"q": "a\x00b"})
                self.assertEqual(respuesta.status_code, 200)

    def test_get_busqueda_descarta_nul(self):
        vista = ListadoPanelMixin()
        vista.request = RequestFactory().get("/", {"q": "\x00ab\x00c "})
        self.assertEqual(vista.get_busqueda(), "abc")
