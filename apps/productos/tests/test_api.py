"""Pruebas de la API del catálogo de productos."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.productos.models import Producto

User = get_user_model()
URL = "/api/v1/productos/"


class CatalogoTests(TestCase):
    """Catálogo: permisos, filtrado de activos, formato y ETag."""

    @classmethod
    def setUpTestData(cls):
        cls.empleado = User.objects.create_user(
            "emp", password="clave-segura-123", rol="empleado"
        )
        cls.activo = Producto.objects.create(
            nombre_comercial="Cebo X",
            principio_activo="Brodifacoum",
            registro="ANMAT 123",
            presentacion="Bidón 5 l",
            unidad_dosis_por_defecto="ml/l",
        )
        Producto.objects.create(nombre_comercial="Viejo", activo=False)

    def setUp(self):
        self.cliente = APIClient()

    def test_solo_activos_y_requiere_auth(self):
        """Anónimo recibe 401; el empleado ve solo activos con el formato esperado."""
        self.assertEqual(self.cliente.get(URL).status_code, 401)

        self.cliente.force_authenticate(self.empleado)
        respuesta = self.cliente.get(URL)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.json(),
            [
                {
                    "id": self.activo.id,
                    "nombre_comercial": "Cebo X",
                    "principio_activo": "Brodifacoum",
                    "registro": "ANMAT 123",
                    "presentacion": "Bidón 5 l",
                    "unidad_dosis_por_defecto": "ml/l",
                    "unidad_base": "unidad",
                    "modo_unidad": "unica",
                    "unidades_permitidas": ["unidad"],
                }
            ],
        )

    def test_if_none_match_igual_da_304(self):
        """Con el ETag vigente responde 304; si el catálogo cambia, 200 y otro ETag."""
        self.cliente.force_authenticate(self.empleado)
        primera = self.cliente.get(URL)
        etag = primera["ETag"]

        igual = self.cliente.get(URL, headers={"If-None-Match": etag})
        self.assertEqual(igual.status_code, 304)
        self.assertEqual(igual["ETag"], etag)

        Producto.objects.create(nombre_comercial="Nuevo")
        cambiado = self.cliente.get(URL, headers={"If-None-Match": etag})
        self.assertEqual(cambiado.status_code, 200)
        self.assertNotEqual(cambiado["ETag"], etag)


class CatalogoUnidadesTests(TestCase):
    """El catálogo expone la unidad base, el modo y las unidades permitidas."""

    def test_expone_unidad_base_modo_y_unidades_permitidas(self):
        empleado = User.objects.create_user(
            "emp-uni", password="clave-segura-123", rol="empleado"
        )
        Producto.objects.create(
            nombre_comercial="Líquido", unidad_base="l", modo_unidad="equivalentes"
        )
        Producto.objects.create(nombre_comercial="Sólido", unidad_base="kg")
        cliente = APIClient()
        cliente.force_authenticate(empleado)
        datos = {p["nombre_comercial"]: p for p in cliente.get(URL).json()}
        self.assertEqual(datos["Líquido"]["unidad_base"], "l")
        self.assertEqual(datos["Líquido"]["modo_unidad"], "equivalentes")
        self.assertEqual(datos["Líquido"]["unidades_permitidas"], ["ml", "l", "gal"])
        self.assertEqual(datos["Sólido"]["unidades_permitidas"], ["kg"])
