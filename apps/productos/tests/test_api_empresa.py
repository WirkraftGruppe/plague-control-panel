"""El catálogo de la API es el de la empresa del operario."""

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.empresas.models import Empresa
from apps.productos.models import Producto


class CatalogoPorEmpresaTests(TestCase):
    def test_catalogo_solo_de_la_empresa_del_operario(self):
        empresa_a = Empresa.objects.create(nombre="Empresa A")
        empresa_b = Empresa.objects.create(nombre="Empresa B")
        operario = User.objects.create_user(
            "emp", password="clave-segura-123", rol="empleado", empresa=empresa_a
        )
        Producto.objects.create(nombre_comercial="Cebo propio", empresa=empresa_a)
        Producto.objects.create(nombre_comercial="Gel ajeno", empresa=empresa_b)
        cliente = APIClient()
        cliente.force_authenticate(operario)

        respuesta = cliente.get("/api/v1/productos/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            [p["nombre_comercial"] for p in respuesta.json()], ["Cebo propio"]
        )
