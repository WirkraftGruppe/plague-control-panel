"""API del trabajo sin conexión: horas del cliente, 409 con `code`, servicio enviado."""

from datetime import timedelta
from io import StringIO
from uuid import uuid4

from django.core.management import call_command
from django.utils import timezone

from apps.api.excepciones import CODIGOS_PUBLICOS
from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl
from apps.visitas.models import PuntoNoRevisado, Revision, Visita
from apps.visitas.tests.ayudas_empresa import dos_empresas
from apps.visitas.tests.test_api import ApiVisitasBase


def hace(**tiempo):
    return timezone.now() - timedelta(**tiempo)


class BaseSinConexionApi(ApiVisitasBase):
    def _abrir(self, **extra):
        cuerpo = {"qr_codigo": str(self.punto.qr_codigo)}
        cuerpo.update(extra)
        return self.api.post("/api/v1/visitas/abrir/", cuerpo, format="json")

    def _reportar(self, visita, **cambios):
        sala = getattr(self, "sala", None) or PuntoControl.objects.create(
            sitio=self.sitio, nombre="Sala", servicio=self.tipo
        )
        self.sala = sala
        cuerpo = {
            "punto": sala.id,
            "motivo": "sin_acceso",
            "cliente_uuid": str(uuid4()),
        }
        cuerpo.update(cambios)
        return self.api.post(
            f"/api/v1/visitas/{visita.id}/no-revisados/", cuerpo, format="multipart"
        )

    def _revisiones(self, visita=None):
        consulta = Revision.objects.de_empresa(una_empresa())
        return consulta.filter(visita=visita) if visita else consulta


class AtrasoApiTests(BaseSinConexionApi):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta(abierta_en=hace(days=30))

    def test_revision_71_horas_201(self):
        r = self._post(self.visita, realizada_en=hace(hours=71).isoformat())
        self.assertEqual(r.status_code, 201, r.content)

    def test_revision_73_horas_400_atraso_excedido(self):
        r = self._post(self.visita, realizada_en=hace(hours=73).isoformat())
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.data["code"], "atraso_excedido")
        self.assertIn("72", str(r.data["campos"]["realizada_en"]))
        self.assertFalse(self._revisiones().exists())

    def test_reporte_73_horas_400_atraso_excedido(self):
        r = self._reportar(self.visita, reportado_en=hace(hours=73).isoformat())
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.data["code"], "atraso_excedido")
        self.assertIn("reportado_en", r.data["campos"])
        self.assertFalse(PuntoNoRevisado.objects.de_empresa(una_empresa()).exists())


class AbrirCerrarApiTests(BaseSinConexionApi):
    def test_abrir_con_abierta_en_de_ayer_abre_el_pendiente(self):
        ayer = hace(hours=24)
        pendiente = self._visita(
            self.empleado, programada_para=timezone.localdate(ayer)
        )
        r = self._abrir(abierta_en=ayer.isoformat())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["id"], pendiente.id)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.ABIERTA)
        self.assertEqual(pendiente.abierta_en, ayer)

    def test_abrir_con_hora_futura_400(self):
        r = self._abrir(abierta_en=(timezone.now() + timedelta(hours=2)).isoformat())
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("abierta_en", r.data["campos"])
        self.assertFalse(Visita.objects.de_empresa(una_empresa()).exists())

    def test_cancelado_por_cierre_nocturno_abrir_y_revisiones_201(self):
        vieja = self._abierta(abierta_en=hace(hours=30))
        Visita.objects.de_empresa(una_empresa()).filter(pk=vieja.pk).update(
            actualizado=hace(hours=20)
        )
        call_command("cerrar_visitas_abiertas", stdout=StringIO())
        vieja.refresh_from_db()
        self.assertEqual(vieja.estado, Visita.Estado.CANCELADA)
        r = self._post(vieja)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.data["code"], "visita_no_abierta")
        r = self._abrir(abierta_en=hace(hours=2).isoformat())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotEqual(r.data["id"], vieja.id)
        nueva = Visita.objects.de_empresa(una_empresa()).get(pk=r.data["id"])
        self.assertEqual(self._post(nueva).status_code, 201)

    def test_realizada_por_sistema_revision_409_y_abrir_crea_visita_nueva(self):
        cerrada = self._abierta(
            estado=Visita.Estado.REALIZADA,
            cierre=Visita.Cierre.SISTEMA,
            cerrada_en=hace(minutes=30),
        )
        r = self._post(cerrada)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.data["code"], "visita_no_abierta")
        r = self._abrir()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertNotEqual(r.data["id"], cerrada.id)

    def test_reporte_y_cierre_en_visita_no_abierta_409(self):
        pendiente = self._visita(self.empleado)
        r = self._reportar(pendiente)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.data["code"], "visita_no_abierta")
        r = self._cerrar(pendiente)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.data["code"], "visita_no_abierta")

    def test_cerrar_dos_veces_200(self):
        visita = self._abierta()
        self.assertEqual(self._post(visita).status_code, 201)
        self.assertEqual(self._cerrar(visita).status_code, 200)
        r = self._cerrar(visita)
        self.assertEqual(r.status_code, 200, r.content)

    def test_cerrar_con_cerrada_en_del_cliente(self):
        visita = self._abierta(abierta_en=hace(hours=5))
        self._post(visita, realizada_en=hace(hours=3).isoformat())
        cerrada_en = hace(hours=2)
        r = self._cerrar(visita, cuerpo={"cerrada_en": cerrada_en.isoformat()})
        self.assertEqual(r.status_code, 200, r.content)
        visita.refresh_from_db()
        self.assertEqual(visita.cerrada_en, cerrada_en)
        r = self._cerrar(visita, cuerpo={"cerrada_en": hace(hours=73).isoformat()})
        self.assertEqual(r.status_code, 200, r.content)

    def test_cierre_de_visita_cerrada_por_sistema_409_visita_ya_cerrada(self):
        visita = self._abierta(
            estado=Visita.Estado.REALIZADA,
            cierre=Visita.Cierre.SISTEMA,
            cerrada_en=hace(minutes=30),
        )
        r = self._cerrar(visita)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.data["code"], "visita_ya_cerrada")


class ServicioApiTests(BaseSinConexionApi):
    def setUp(self):
        super().setUp()
        self.otro_tipo = TipoServicio.objects.create(
            nombre="Insectos", slug="insectos", empresa=una_empresa()
        )
        self.visita = self._abierta()

    def test_servicio_distinto_201_con_incidencia(self):
        r = self._post(self.visita, servicio=self.otro_tipo.id, datos="{}")
        self.assertEqual(r.status_code, 201, r.content)
        revision = self._revisiones(self.visita).get()
        self.assertEqual(revision.servicio, self.otro_tipo)
        self.assertTrue(revision.incidencia_servicio)

    def test_servicio_inactivo_o_de_otra_empresa_400(self):
        _, lado_b = dos_empresas()
        inactivo = TipoServicio.objects.create(
            nombre="Baja", slug="baja", empresa=una_empresa(), activo=False
        )
        for ajeno in (lado_b.servicio.id, inactivo.id, 999999):
            with self.subTest(servicio=ajeno):
                r = self._post(self.visita, servicio=ajeno)
                self.assertEqual(r.status_code, 400, r.content)
                self.assertIn("servicio", r.data["campos"])
        self.assertFalse(self._revisiones().exists())


class IdempotenciaApiTests(BaseSinConexionApi):
    def setUp(self):
        super().setUp()
        self.visita = self._abierta(abierta_en=hace(days=30))

    def test_mismo_uuid_no_duplica_revision(self):
        cliente_uuid = str(uuid4())
        r = self._post(self.visita, cliente_uuid=cliente_uuid)
        self.assertEqual(r.status_code, 201, r.content)
        r = self._post(self.visita, cliente_uuid=cliente_uuid)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(self._revisiones().count(), 1)
        self.assertEqual(r.data["visita"], self.visita.id)

    def test_mismo_uuid_no_duplica_reporte(self):
        cliente_uuid = str(uuid4())
        self.assertEqual(
            self._reportar(self.visita, cliente_uuid=cliente_uuid).status_code, 201
        )
        r = self._reportar(self.visita, cliente_uuid=cliente_uuid)
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(PuntoNoRevisado.objects.de_empresa(una_empresa()).count(), 1)

    def test_reintento_73_horas_mismo_uuid_409(self):
        cliente_uuid = str(uuid4())
        r = self._post(
            self.visita,
            cliente_uuid=cliente_uuid,
            realizada_en=hace(hours=71).isoformat(),
        )
        self.assertEqual(r.status_code, 201, r.content)
        r = self._post(
            self.visita,
            cliente_uuid=cliente_uuid,
            realizada_en=hace(hours=73).isoformat(),
        )
        self.assertEqual(r.status_code, 409, r.content)
        self.assertNotIn("code", r.data)
        self.assertEqual(self._revisiones().count(), 1)


class EsquemaTests(BaseSinConexionApi):
    def test_enum_code_coincide_con_codigos_publicos(self):
        r = self.api.get("/api/v1/schema/?format=json")
        self.assertEqual(r.status_code, 200)
        enum = r.json()["components"]["schemas"]["Error"]["properties"]["code"]["enum"]
        self.assertEqual(enum, sorted(CODIGOS_PUBLICOS))
        self.assertEqual(len(enum), 4)
