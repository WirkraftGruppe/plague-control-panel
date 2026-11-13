"""Panel transversal por empresa: mapa, estado, contador de vencidos y login."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.sitios.models import PuntoControl, Sitio

CLAVE = "clave-segura-123"
INGRESAR = "/panel/ingresar/"


class PanelTransversalTests(TestCase):
    """Cada empresa ve solo lo suyo; las cuentas sin empresa activa no ingresan."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(nombre="Empresa A")
        cls.empresa_b = Empresa.objects.create(nombre="Empresa B")
        cls.admin_a = cls._usuario("adm-a", User.Rol.ADMINISTRADOR, cls.empresa_a)
        cls.admin_b = cls._usuario("adm-b", User.Rol.ADMINISTRADOR, cls.empresa_b)
        cls.sitio_a = cls._sitio("Planta A", cls.empresa_a, dias=-3)
        cls.sitio_b = cls._sitio("Planta B", cls.empresa_b, dias=-3)
        cls._sitio("Otra planta B", cls.empresa_b, dias=-1)

    @staticmethod
    def _usuario(nombre, rol, empresa):
        return User.objects.create_user(
            nombre, password=CLAVE, rol=rol, empresa=empresa
        )

    @staticmethod
    def _sitio(nombre, empresa, dias):
        cliente = Cliente.objects.create(
            razon_social=f"Cliente {nombre}", empresa=empresa
        )
        sitio = Sitio.objects.create(
            cliente=cliente,
            nombre=nombre,
            latitud=Decimal("-35.1"),
            longitud=Decimal("-57.7"),
        )
        PuntoControl.objects.create(
            sitio=sitio,
            nombre=f"Punto {nombre}",
            proximo_vencimiento=timezone.localdate() + timedelta(days=dias),
        )
        return sitio

    def _ingresar(self, usuario):
        return self.client.post(INGRESAR, {"username": usuario, "password": CLAVE})

    def test_mapa_solo_sitios_de_la_empresa(self):
        self.client.force_login(self.admin_a)
        respuesta = self.client.get("/panel/mapa/datos/")
        nombres = {s["nombre"] for s in respuesta.json()["sitios"]}
        self.assertEqual(nombres, {"Planta A"})

    def test_estado_de_sitio_de_otra_empresa_da_404(self):
        self.client.force_login(self.admin_a)
        propio = self.client.get(reverse("panel:estado_sitio", args=[self.sitio_a.pk]))
        ajeno = self.client.get(reverse("panel:estado_sitio", args=[self.sitio_b.pk]))
        self.assertEqual(propio.status_code, 200)
        self.assertEqual(ajeno.status_code, 404)

    def test_contador_de_sitios_vencidos_cuenta_solo_la_empresa(self):
        self.client.force_login(self.admin_a)
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        self.assertIn('contador-vencidos">1<', html)
        self.client.force_login(self.admin_b)
        html = self.client.get(reverse("panel:sitios:listado")).content.decode()
        self.assertIn('contador-vencidos">2<', html)

    def test_login_con_empresa_inactiva_falla(self):
        Empresa.objects.filter(pk=self.empresa_a.pk).update(activo=False)
        respuesta = self._ingresar("adm-a")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "La empresa de esta cuenta no está activa.")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self._ingresar("adm-b").status_code, 302)

    def test_login_de_plataforma_remite_al_admin(self):
        User.objects.create_superuser("plat", password=CLAVE)
        respuesta = self._ingresar("plat")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, '<a href="/admin/">/admin/</a>', html=False)
        self.assertNotIn("_auth_user_id", self.client.session)
