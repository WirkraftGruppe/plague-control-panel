"""Pruebas de la dosis habitual y variable del producto y del catálogo de la API."""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.productos.consultas import ultimo_lote_subquery
from apps.productos.models import Producto
from apps.visitas.models import ProductoAplicado, Revision
from apps.visitas.tests.ayudas_empresa import dos_empresas

URL = "/api/v1/productos/"


class DosisHabitualTests(TestCase):
    """Validación del modelo y edición desde el panel."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = una_empresa()
        cls.admin = User.objects.create_user(
            "admin-dosis", password="x", rol=User.Rol.ADMINISTRADOR, empresa=cls.empresa
        )

    def _producto(self, **extra):
        return Producto(empresa=self.empresa, nombre_comercial="Gel", **extra)

    def test_dosis_sin_unidad_no_valida(self):
        producto = self._producto(dosis_habitual=Decimal("5"))
        with self.assertRaises(ValidationError) as error:
            producto.full_clean()
        self.assertIn("unidad_dosis_habitual", error.exception.message_dict)

    def test_sin_dosis_habitual_ni_variable_no_valida(self):
        with self.assertRaises(ValidationError) as error:
            self._producto().full_clean()
        self.assertIn("dosis_habitual", error.exception.message_dict)
        self._producto(dosis_variable=True).full_clean()
        self._producto(
            dosis_habitual=Decimal("5"), unidad_dosis_habitual="ml/l"
        ).full_clean()

    def test_panel_edita_dosis_habitual_y_variable(self):
        producto = Producto.objects.create(
            empresa=self.empresa, nombre_comercial="Gel", dosis_variable=True
        )
        self.client.force_login(self.admin)
        url = reverse("panel:productos:editar", args=[producto.pk])
        datos = {
            "nombre_comercial": "Gel",
            "unidad_base": "unidad",
            "contenido_por_envase": "1",
            "modo_unidad": "unica",
            "activo": "on",
            "dosis_habitual": "5",
            "unidad_dosis_habitual": "ml/l",
        }
        self.assertRedirects(
            self.client.post(url, datos), reverse("panel:productos:listado")
        )
        producto.refresh_from_db()
        self.assertEqual(producto.dosis_habitual, Decimal("5"))
        self.assertEqual(producto.unidad_dosis_habitual, "ml/l")
        self.assertFalse(producto.dosis_variable)

        # Sin dosis y sin marcar variable, el formulario rechaza el guardado.
        sin_dosis = {
            k: v for k, v in datos.items() if not k.startswith(("dosis", "unidad_d"))
        }
        respuesta = self.client.post(url, sin_dosis)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "marcá la dosis como variable")
        self.assertContains(respuesta, "lo que se descuenta del stock")


class CatalogoDosisTests(TestCase):
    """El catálogo trae la dosis habitual y el último lote aplicado."""

    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()
        cls.cliente = APIClient()

    def _catalogo(self, lado):
        self.cliente.force_authenticate(lado.empleado)
        return self.cliente.get(URL)

    def _aplicar(self, lado, producto, lote, hace_dias=0):
        """Aplica el producto en una revisión nueva del lado, `hace_dias` atrás."""
        momento = timezone.now() - timedelta(days=hace_dias)
        revision = Revision.objects.create(
            visita=lado.visita,
            punto=lado.punto,
            servicio=lado.servicio,
            realizada_en=momento,
            recibida_en=momento,
        )
        return ProductoAplicado.objects.create(
            revision=revision,
            producto=producto,
            lote=lote,
            dosis=Decimal("1"),
            unidad_dosis="ml/l",
            unidad="unidad",
            cantidad=Decimal("1"),
            cantidad_base=Decimal("1"),
        )

    def test_catalogo_trae_dosis_y_ultimo_lote_null(self):
        Producto.objects.de_empresa(self.a.empresa).filter(
            pk=self.a.producto.pk
        ).update(dosis_habitual=Decimal("5"), unidad_dosis_habitual="ml/l")
        respuesta = self._catalogo(self.a)
        self.assertEqual(respuesta.status_code, 200)
        (dato,) = respuesta.json()
        self.assertEqual(dato["dosis_habitual"], "5.000")
        self.assertEqual(dato["unidad_dosis_habitual"], "ml/l")
        self.assertFalse(dato["dosis_variable"])
        self.assertIsNone(dato["ultimo_lote"])

    def test_ultimo_lote_L2291_y_etag_cambia(self):
        antes = self._catalogo(self.a)["ETag"]
        self._aplicar(self.a, self.a.producto, "L0001", hace_dias=2)
        self._aplicar(self.a, self.a.producto, "L2291", hace_dias=0)
        # Una aplicación anterior cargada después no pisa a la más reciente.
        self._aplicar(self.a, self.a.producto, "L0002", hace_dias=5)
        respuesta = self._catalogo(self.a)
        self.assertEqual(respuesta.json()[0]["ultimo_lote"], "L2291")
        self.assertNotEqual(respuesta["ETag"], antes)

    def test_ultimo_lote_no_cruza_empresas(self):
        aplicado = self._aplicar(self.b, self.b.producto, "L-AJENO")
        # Se fuerza la referencia cruzada saltando la validación del modelo.
        ProductoAplicado.objects.de_empresa(self.b.empresa).filter(
            pk=aplicado.pk
        ).update(producto=self.a.producto)
        self.assertIsNone(self._catalogo(self.a).json()[0]["ultimo_lote"])
        anotados = Producto.objects.de_empresa(self.a.empresa).annotate(
            ultimo_lote=ultimo_lote_subquery()
        )
        self.assertIsNone(anotados.get().ultimo_lote)

    def test_consultas_iguales_con_5_y_50_productos(self):
        def consultas():
            with CaptureQueriesContext(connection) as capturadas:
                self.assertEqual(self._catalogo(self.a).status_code, 200)
            return len(capturadas)

        Producto.objects.bulk_create(
            Producto(
                empresa=self.a.empresa, nombre_comercial=f"P{n}", dosis_variable=True
            )
            for n in range(4)
        )
        cinco = consultas()
        Producto.objects.bulk_create(
            Producto(
                empresa=self.a.empresa, nombre_comercial=f"Q{n}", dosis_variable=True
            )
            for n in range(45)
        )
        self.assertEqual(Producto.objects.de_empresa(self.a.empresa).count(), 50)
        self.assertEqual(consultas(), cinco)
