"""Robustez de visitas: JSON exacto, incidencia de asignación, servicio de baja,
consultas del resolver, visita destino y esquema de revisiones."""

import json
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import CampoPlanilla
from apps.sitios.models import Sitio
from apps.visitas.models import ProductoAplicado, Revision, Visita
from apps.visitas.services import abrir_visita, servicio_para_punto, visita_destino
from apps.visitas.tests.test_api import ApiVisitasBase
from apps.visitas.tests.test_turnos import BaseTurnoTests


def _producto(producto, **cambios):
    item = {
        "producto": producto.id,
        "lote": "L1",
        "dosis": "2.5",
        "unidad_dosis": "ml/l",
        "cantidad": "10",
        "unidad": "unidad",
    }
    item.update(cambios)
    return item


class CantidadNumericaTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        # La dosis enviada solo se guarda en los productos con dosis variable.
        self.producto.dosis_variable = True
        self.producto.save()
        self.visita = self._abierta()

    def test_cantidad_como_numero_json_da_201_y_valor_exacto(self):
        texto = json.dumps([_producto(self.producto)]).replace(
            '"cantidad": "10"', '"cantidad": 0.1'
        )
        texto = texto.replace('"dosis": "2.5"', '"dosis": 2.5')
        r = self._post(self.visita, productos_aplicados=texto)
        self.assertEqual(r.status_code, 201, r.content)
        aplicado = ProductoAplicado.objects.de_empresa(una_empresa()).get(
            revision_id=r.data["id"]
        )
        self.assertEqual(aplicado.cantidad, Decimal("0.100"))
        self.assertEqual(aplicado.dosis, Decimal("2.500"))

    def test_datos_con_decimales_siguen_guardandose(self):
        r = self._post(self.visita, datos='{"cebos": 3.5}')
        self.assertEqual(r.status_code, 201, r.content)

    def test_nan_se_rechaza(self):
        for constante in ("NaN", "Infinity", "-Infinity"):
            texto = json.dumps([_producto(self.producto)]).replace(
                '"cantidad": "10"', f'"cantidad": {constante}'
            )
            with self.subTest(constante=constante):
                r = self._post(self.visita, productos_aplicados=texto)
                self.assertEqual(r.status_code, 400, r.content)
                self.assertIn("productos_aplicados", r.data["campos"])
        self.assertFalse(Revision.objects.de_empresa(una_empresa()).exists())


class IncidenciaAsignacionTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.otro = User.objects.create_user(
            "otro", password="x", rol=User.Rol.EMPLEADO, empresa=una_empresa()
        )

    def _abrir(self, punto):
        visita, creada = abrir_visita(empleado=self.empleado, qr_codigo=punto.qr_codigo)
        self.assertTrue(creada)
        return visita

    def test_turno_ajeno_sin_el_punto_no_marca(self):
        self.turno([(self.sala, self.roedores)], empleado=self.otro)
        visita = self._abrir(self.techo)
        self.assertFalse(visita.incidencia_asignacion)

    def test_turno_ajeno_con_el_punto_marca(self):
        self.turno([(self.techo, self.insectos)], empleado=self.otro)
        visita = self._abrir(self.techo)
        self.assertTrue(visita.incidencia_asignacion)


class ServicioDadoDeBajaTests(ApiVisitasBase):
    def test_revision_con_servicio_dado_de_baja_da_400(self):
        visita = self._abierta()
        self.tipo.activo = False
        self.tipo.save()
        r = self._post(visita)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("dado de baja", str(r.data["campos"]["qr_codigo"]))
        self.assertFalse(Revision.objects.de_empresa(una_empresa()).exists())


class ResolverConsultasTests(BaseTurnoTests):
    def test_resolver_precarga_campos_del_servicio(self):
        for orden in (1, 2, 3):
            CampoPlanilla.objects.create(
                tipo_servicio=self.roedores,
                orden=orden,
                etiqueta=f"Campo {orden}",
                clave=f"campo{orden}",
                tipo=CampoPlanilla.Tipo.NUMERO,
            )
        for visita in (None, self.turno([(self.general, self.roedores)])):
            servicio, _ = servicio_para_punto(visita=visita, punto=self.general)
            with self.subTest(visita=visita), self.assertNumQueries(0):
                self.assertEqual(len(servicio.esquema_planilla("punto")), 3)
                self.assertEqual(servicio.esquema_planilla("visita"), [])

        api = APIClient()
        api.force_authenticate(self.empleado)
        with CaptureQueriesContext(connection) as consultas:
            r = api.post(f"/api/v1/qr/{self.general.qr_codigo}/resolver/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.data["punto"]["servicio"]["esquema_punto"]), 3)
        de_campos = [
            c["sql"] for c in consultas if "servicios_campoplanilla" in c["sql"]
        ]
        self.assertEqual(len(de_campos), 1, de_campos)


class VisitaDestinoAjenaTests(BaseTurnoTests):
    def _resolver(self, punto):
        api = APIClient()
        api.force_authenticate(self.empleado)
        r = api.post(f"/api/v1/qr/{punto.qr_codigo}/resolver/")
        self.assertEqual(r.status_code, 200, r.content)
        return r.data

    def test_visita_de_otro_empleado_no_es_destino(self):
        otro = User.objects.create_user(
            "otro", password="x", rol=User.Rol.EMPLEADO, empresa=una_empresa()
        )
        self.turno([(self.general, self.roedores)], empleado=otro)
        self.assertIsNone(visita_destino(empleado=self.empleado, sitio=self.sitio))
        datos = self._resolver(self.general)
        self.assertIsNone(datos["visita_destino"])
        self.assertFalse(datos["punto"]["en_turno"])

    def test_visita_propia_en_otro_sitio_no_es_destino(self):
        otro_sitio = Sitio.objects.create(cliente=self.sitio.cliente, nombre="Depósito")
        propia = Visita.objects.create(
            sitio=otro_sitio,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.PENDIENTE,
        )
        self.assertIsNone(visita_destino(empleado=self.empleado, sitio=self.sitio))
        datos = self._resolver(self.general)
        self.assertIsNone(datos["visita_destino"])
        self.assertNotEqual(datos["visita_pendiente_propia"], propia.id)


class EsquemaRevisionesTests(TestCase):
    def test_productos_aplicados_tiene_esquema_de_item(self):
        esquema = SchemaGenerator().get_schema(request=None, public=True)
        cuerpo = esquema["paths"]["/api/v1/revisiones/"]["post"]["requestBody"]
        multipart = cuerpo["content"]["multipart/form-data"]
        self.assertEqual(
            multipart["encoding"]["productos_aplicados"]["contentType"],
            "application/json",
        )
        propiedad = None
        for componente in esquema["components"]["schemas"].values():
            if "productos_aplicados" in componente.get("properties", {}):
                propiedad = componente["properties"]["productos_aplicados"]
        self.assertIsNotNone(propiedad)
        self.assertEqual(propiedad["type"], "array")
        self.assertEqual(propiedad["items"]["type"], "object")
        self.assertIn("cantidad", propiedad["items"]["properties"])
