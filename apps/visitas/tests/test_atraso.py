import json
from datetime import timedelta
from uuid import uuid4

from django.test import override_settings
from django.utils import timezone

from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.models import Revision, Visita
from apps.visitas.tests.test_api import MEDIA_TEMPORAL, BaseApiTests, jpeg_chico


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class AtrasoMaximoTests(BaseApiTests):
    def setUp(self):
        super().setUp()
        self.visita = self._visita(
            self.empleado,
            origen=Visita.Origen.APP,
            motivo_manual="",
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now() - timedelta(days=30),
        )

    def _post_con_atraso(self, horas, cliente_uuid=None):
        cuerpo = {
            "visita": self.visita.id,
            "qr_codigo": str(self.punto.qr_codigo),
            "cliente_uuid": str(cliente_uuid or uuid4()),
            "realizada_en": (timezone.now() - timedelta(hours=horas)).isoformat(),
            "latitud": "-36.100000",
            "longitud": "-57.800000",
            "precision_m": "8.5",
            "datos": json.dumps({"cebos": 3}),
            "fotos": [jpeg_chico()],
        }
        return self.api.post("/api/v1/revisiones/", cuerpo, format="multipart")

    def test_realizada_en_mas_antigua_que_el_limite_da_400(self):
        r = self._post_con_atraso(169)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("168", str(r.data["campos"]["realizada_en"]))
        self.assertFalse(Revision.objects.de_empresa(una_empresa()).exists())

    def test_realizada_en_dentro_del_limite_se_acepta(self):
        r = self._post_con_atraso(167)
        self.assertEqual(r.status_code, 201, r.content)

    @override_settings(ATRASO_MAXIMO_HORAS=24)
    def test_limite_de_atraso_sigue_el_setting(self):
        r = self._post_con_atraso(30)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("24", str(r.data["campos"]["realizada_en"]))

    def test_reintento_fuera_del_limite_responde_409(self):
        cliente_uuid = uuid4()
        with override_settings(ATRASO_MAXIMO_HORAS=168):
            r = self._post_con_atraso(167, cliente_uuid)
        self.assertEqual(r.status_code, 201, r.content)
        with override_settings(ATRASO_MAXIMO_HORAS=1):
            r = self._post_con_atraso(167, cliente_uuid)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(Revision.objects.de_empresa(una_empresa()).count(), 1)
        self.assertEqual(
            r.data["revision"], Revision.objects.de_empresa(una_empresa()).get().id
        )
        self.assertEqual(r.data["visita"], self.visita.id)
