"""La API de visitas separa las empresas: QR, fotos, productos, uuid y listados."""

import json
import shutil
import tempfile
from datetime import timedelta
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.visitas.models import Revision, Visita

from .ayudas_empresa import crear_foto, dos_empresas, jpeg_chico

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="visitas-api-empresa-")


def _api(usuario):
    api = APIClient()
    api.force_authenticate(usuario)
    return api


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class ApiVisitasPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()
        for lado in (cls.a, cls.b):
            Visita.objects.de_empresa(lado.empresa).update(
                estado=Visita.Estado.ABIERTA,
                abierta_en=timezone.now() - timedelta(hours=1),
                incidencia=False,
            )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        cache.clear()

    def _cuerpo(self, lado, **cambios):
        cuerpo = {
            "visita": lado.visita.pk,
            "qr_codigo": str(lado.punto.qr_codigo),
            "cliente_uuid": str(uuid4()),
            "realizada_en": (timezone.now() - timedelta(minutes=1)).isoformat(),
            "latitud": "-36.100000",
            "longitud": "-57.800000",
            "precision_m": "8.5",
            "datos": json.dumps({}),
            "fotos": [jpeg_chico()],
        }
        cuerpo.update(cambios)
        return cuerpo

    def _revisar(self, lado, **cambios):
        return _api(lado.empleado).post(
            "/api/v1/revisiones/", self._cuerpo(lado, **cambios), format="multipart"
        )

    def test_abrir_con_qr_de_otra_empresa_da_el_mismo_400_que_uno_inexistente(self):
        api = _api(self.a.empleado)
        ajeno = api.post(
            "/api/v1/visitas/abrir/",
            {"qr_codigo": str(self.b.punto.qr_codigo)},
            format="json",
        )
        inexistente = api.post(
            "/api/v1/visitas/abrir/", {"qr_codigo": str(uuid4())}, format="json"
        )
        self.assertEqual(ajeno.status_code, 400, ajeno.content)
        self.assertEqual(inexistente.status_code, 400)
        self.assertEqual(ajeno.json(), inexistente.json())

    def test_foto_de_otra_empresa_da_404(self):
        propia = crear_foto(self.a)
        ajena = crear_foto(self.b)
        for usuario in (self.a.empleado, self.a.admin):
            r = _api(usuario).get(f"/api/v1/fotos/{ajena.codigo}/")
            self.assertEqual(r.status_code, 404, usuario)
        self.assertEqual(
            _api(self.b.empleado).get(f"/api/v1/fotos/{ajena.codigo}/").status_code,
            200,
        )
        # Otro empleado de la misma empresa sigue recibiendo 403.
        otro = User.objects.create_user(
            "otro-a",
            password="clave-segura-123",
            rol=User.Rol.EMPLEADO,
            empresa=self.a.empresa,
        )
        r = _api(otro).get(f"/api/v1/fotos/{propia.codigo}/")
        self.assertEqual(r.status_code, 403)

    def test_producto_de_otra_empresa_en_la_revision_da_400(self):
        def productos(producto):
            return json.dumps(
                [
                    {
                        "producto": producto.pk,
                        "lote": "L1",
                        "dosis": "1",
                        "unidad_dosis": "ml",
                        "cantidad": "1",
                        "unidad": "unidad",
                    }
                ]
            )

        r = self._revisar(self.a, productos_aplicados=productos(self.b.producto))
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("productos_aplicados.0.producto", r.json()["campos"])
        self.assertFalse(Revision.todos.exists())
        r = self._revisar(self.a, productos_aplicados=productos(self.a.producto))
        self.assertEqual(r.status_code, 201, r.content)

    def test_cliente_uuid_de_otra_empresa_crea_la_revision_con_201(self):
        repetido = str(uuid4())
        r = self._revisar(self.b, cliente_uuid=repetido)
        self.assertEqual(r.status_code, 201, r.content)
        r = self._revisar(self.a, cliente_uuid=repetido)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Revision.todos.filter(cliente_uuid=repetido).count(), 2)
        r = self._revisar(self.a, cliente_uuid=repetido)
        self.assertEqual(r.status_code, 409, r.content)

    def test_mis_visitas_e_historial_solo_de_la_empresa(self):
        # Caso cruzado armado por ORM: visita de A con el empleado de B.
        cruzada = Visita.objects.create(
            sitio=self.a.sitio,
            empleado=self.b.empleado,
            origen=Visita.Origen.MANUAL,
            motivo_manual="Cruzada",
            estado=Visita.Estado.REALIZADA,
            abierta_en=timezone.now(),
            cerrada_en=timezone.now(),
            cierre=Visita.Cierre.EMPLEADO,
        )
        pendiente = Visita.objects.create(
            sitio=self.a.sitio,
            empleado=self.b.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.PENDIENTE,
        )
        propia = Visita.objects.create(
            sitio=self.b.sitio,
            empleado=self.b.empleado,
            origen=Visita.Origen.MANUAL,
            motivo_manual="Propia",
            estado=Visita.Estado.REALIZADA,
            abierta_en=timezone.now(),
            cerrada_en=timezone.now(),
            cierre=Visita.Cierre.EMPLEADO,
        )
        api = _api(self.b.empleado)
        ids = [v["id"] for v in api.get("/api/v1/me/visitas/").json()["results"]]
        self.assertIn(self.b.visita.pk, ids)
        self.assertNotIn(pendiente.pk, ids)
        historial = api.get("/api/v1/me/historial/").json()["results"]
        self.assertEqual([v["id"] for v in historial], [propia.pk])
        self.assertNotIn(cruzada.pk, [v["id"] for v in historial])
