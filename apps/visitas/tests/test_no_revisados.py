"""Reporte de punto no revisado: servicio, vista de la API e incidencia."""

from datetime import date
from io import BytesIO
from unittest import mock
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.pruebas import crear_empresa
from apps.empresas.tests.ayudas import una_empresa
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.api_views import MAX_BYTES_PEDIDO, ReportarNoRevisadoView
from apps.visitas.models import PuntoNoRevisado, Revision, Visita
from apps.visitas.services import (
    condicion_incidencia_sin_revisar,
    crear_turno,
    marcar_incidencia_revisada,
)
from apps.visitas.tests.test_api import ApiVisitasBase, jpeg_chico


class NoRevisadosApiTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.fabrica = APIRequestFactory()
        self.sala = PuntoControl.objects.create(sitio=self.sitio, nombre="Sala")

    def _reportar(self, visita_pk, usuario=None, extra=None, **cambios):
        cuerpo = {
            "punto": self.sala.id,
            "motivo": "falta_estacion",
            "cliente_uuid": str(uuid4()),
        }
        cuerpo.update(cambios)
        cuerpo = {k: v for k, v in cuerpo.items() if v is not None}
        pedido = self.fabrica.post(
            f"/visitas/{visita_pk}/no-revisados/",
            cuerpo,
            format="multipart",
            **(extra or {}),
        )
        force_authenticate(pedido, usuario or self.empleado)
        return ReportarNoRevisadoView.as_view()(pedido, pk=visita_pk)

    def _visita_de_otra_empresa(self):
        otra = crear_empresa("Otra empresa")
        cliente = Cliente.objects.create(empresa=otra, razon_social="Ajena")
        sitio = Sitio.objects.create(cliente=cliente, nombre="Planta ajena")
        empleado = User.objects.create_user(
            username="ajeno", password="x", rol=User.Rol.EMPLEADO, empresa=otra
        )
        return Visita.objects.create(
            sitio=sitio,
            empleado=empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
        )

    def test_reporte_en_visita_abierta_propia_da_201(self):
        visita = self._abierta()
        r = self._reportar(
            visita.id,
            motivo="codigo_ilegible",
            detalle="Etiqueta borrada",
            latitud="-36.100000",
            longitud="-57.800000",
            precision_m="8.5",
        )
        self.assertEqual(r.status_code, 201, r.data)
        reporte = PuntoNoRevisado.objects.de_empresa(una_empresa()).get()
        self.assertEqual(reporte.visita, visita)
        self.assertEqual(reporte.punto, self.sala)
        self.assertEqual(reporte.motivo, "codigo_ilegible")
        self.assertEqual(reporte.detalle, "Etiqueta borrada")
        self.assertIsNotNone(reporte.distancia_m)
        self.assertEqual(r.data["id"], reporte.id)
        self.assertEqual(r.data["punto"], {"id": self.sala.id, "nombre": "Sala"})

    def test_visita_ajena_inexistente_o_de_otra_empresa_da_404(self):
        ajena = self._abierta(self.otro)
        otra_empresa = self._visita_de_otra_empresa()
        for pk in (ajena.id, 999999, otra_empresa.id):
            with self.subTest(pk=pk):
                r = self._reportar(pk)
                self.assertEqual(r.status_code, 404, r.data)
        self.assertFalse(PuntoNoRevisado.objects.de_empresa(una_empresa()).exists())

    def test_visita_de_otra_empresa_con_cuerpo_vacio_da_404(self):
        otra_empresa = self._visita_de_otra_empresa()
        pedido = self.fabrica.post(
            f"/visitas/{otra_empresa.id}/no-revisados/", {}, format="multipart"
        )
        force_authenticate(pedido, self.empleado)
        r = ReportarNoRevisadoView.as_view()(pedido, pk=otra_empresa.id)
        self.assertEqual(r.status_code, 404, r.data)

    def test_visita_propia_cerrada_da_409(self):
        visita = self._realizada(self.empleado, 5)
        r = self._reportar(visita.id)
        self.assertEqual(r.status_code, 409, r.data)
        self.assertEqual(r.data["code"], "visita_no_abierta")
        self.assertIn("La visita no está abierta.", str(r.data))
        self.assertFalse(PuntoNoRevisado.objects.de_empresa(una_empresa()).exists())

    def test_punto_de_otro_sitio_da_400(self):
        otro_sitio = Sitio.objects.create(
            cliente=self.sitio.cliente, nombre="Planta 2", direccion="Calle 2"
        )
        ajeno = otro_sitio.puntos.get(orden=0)
        r = self._reportar(self._abierta().id, punto=ajeno.id)
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("punto", r.data["campos"])
        r = self._reportar(self._abierta(self.otro).id, usuario=self.otro, punto=9999)
        self.assertEqual(r.status_code, 400, r.data)

    def test_punto_inactivo_o_ya_reportado_da_400(self):
        visita = self._abierta()
        inactivo = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Baja", activo=False
        )
        r = self._reportar(visita.id, punto=inactivo.id)
        self.assertEqual(r.status_code, 400, r.data)
        self.assertEqual(self._reportar(visita.id).status_code, 201)
        r = self._reportar(visita.id)
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("ya fue reportado", str(r.data))
        self.assertEqual(visita.no_revisados.count(), 1)

    def test_respuesta_sin_coordenadas_ni_foto(self):
        r = self._reportar(
            self._abierta().id,
            latitud="-36.100000",
            longitud="-57.800000",
            precision_m="8.5",
            foto=jpeg_chico(),
        )
        self.assertEqual(r.status_code, 201, r.data)
        for campo in (
            "latitud",
            "longitud",
            "precision_m",
            "distancia_m",
            "foto",
            "foto_codigo",
            "cliente_uuid",
        ):
            self.assertNotIn(campo, r.data)

    def test_reporte_no_crea_revision_ni_cambia_vencimiento(self):
        self.sala.frecuencia_dias = 30
        self.sala.save()
        antes = (
            PuntoControl.objects.de_empresa(una_empresa())
            .get(pk=self.sala.pk)
            .proximo_vencimiento
        )
        visita = self._abierta()
        with mock.patch("apps.visitas.services.actualizar_vencimiento") as actualizar:
            r = self._reportar(visita.id)
        self.assertEqual(r.status_code, 201, r.data)
        actualizar.assert_not_called()
        self.assertFalse(Revision.objects.de_empresa(una_empresa()).exists())
        despues = (
            PuntoControl.objects.de_empresa(una_empresa())
            .get(pk=self.sala.pk)
            .proximo_vencimiento
        )
        self.assertEqual(antes, despues)

    def test_mismo_cliente_uuid_no_duplica(self):
        visita = self._abierta()
        clave = str(uuid4())
        self.assertEqual(self._reportar(visita.id, cliente_uuid=clave).status_code, 201)
        r = self._reportar(visita.id, cliente_uuid=clave)
        self.assertEqual(r.status_code, 409, r.data)
        self.assertEqual(r.data["reporte"], visita.no_revisados.get().id)
        self.assertEqual(r.data["visita"], visita.id)
        self.assertEqual(visita.no_revisados.count(), 1)

    def test_409_no_expone_datos_de_otro_empleado(self):
        clave = str(uuid4())
        ajena = self._abierta(self.otro)
        r = self._reportar(ajena.id, usuario=self.otro, cliente_uuid=clave)
        self.assertEqual(r.status_code, 201, r.data)
        r = self._reportar(self._abierta().id, cliente_uuid=clave)
        self.assertEqual(r.status_code, 409, r.data)
        self.assertEqual(set(r.data), {"detalle", "campos"})
        self.assertEqual(PuntoNoRevisado.objects.de_empresa(una_empresa()).count(), 1)

    def test_foto_se_procesa_y_respeta_el_limite(self):
        grande = BytesIO()
        Image.new("RGB", (3000, 2000), "red").save(grande, "JPEG")
        foto = SimpleUploadedFile("o.jpg", grande.getvalue(), "image/jpeg")
        r = self._reportar(self._abierta().id, foto=foto)
        self.assertEqual(r.status_code, 201, r.data)
        reporte = PuntoNoRevisado.objects.de_empresa(una_empresa()).get()
        self.assertTrue(reporte.foto.name.startswith("visitas/fotos/"))
        self.assertNotIn("o.jpg", reporte.foto.name)
        with Image.open(reporte.foto.path) as guardada:
            self.assertEqual(max(guardada.size), 1600)
        # Más de 8 MB: 400 sin guardar nada.
        pesada = SimpleUploadedFile("p.jpg", b"0" * (8 * 1024 * 1024 + 1))
        r = self._reportar(self._abierta(self.otro).id, self.otro, foto=pesada)
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn("foto", r.data["campos"])
        # No es una imagen: el servicio la rechaza y no deja el reporte.
        falsa = SimpleUploadedFile("f.jpg", b"no soy una imagen")
        r = self._reportar(self._abierta().id, foto=falsa)
        self.assertEqual(r.status_code, 400, r.data)
        self.assertEqual(PuntoNoRevisado.objects.de_empresa(una_empresa()).count(), 1)
        # Pedido por encima del tope: 413 antes de leer el cuerpo.
        r = self._reportar(
            self._abierta().id, extra={"CONTENT_LENGTH": str(MAX_BYTES_PEDIDO + 1)}
        )
        self.assertEqual(r.status_code, 413, r.data)

    def test_mis_visitas_trae_no_revisado(self):
        turno = crear_turno(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=date(2026, 9, 1),
            items=[(self.punto, self.tipo), (self.sala, self.tipo)],
            asignada_por=self.admin,
        )
        Visita.objects.de_empresa(una_empresa()).filter(pk=turno.pk).update(
            estado=Visita.Estado.ABIERTA, abierta_en=timezone.now()
        )
        self.assertEqual(self._reportar(turno.id, motivo="sin_acceso").status_code, 201)
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 200, r.content)
        (cuerpo,) = r.json()["results"]
        motivos = {i["punto"]["id"]: i["no_revisado"] for i in cuerpo["items"]}
        self.assertEqual(motivos, {self.punto.id: None, self.sala.id: "sin_acceso"})


class IncidenciaNoRevisadoTests(ApiVisitasBase):
    def _reporte(self, visita, **extra):
        return PuntoNoRevisado.objects.create(
            visita=visita,
            punto=self.punto,
            motivo=PuntoNoRevisado.Motivo.SIN_ACCESO,
            cliente_uuid=uuid4(),
            **extra,
        )

    def _cerrada(self, dia, **extra):
        return self._visita(
            self.empleado,
            estado=Visita.Estado.REALIZADA,
            abierta_en=timezone.now(),
            cerrada_en=timezone.now(),
            cierre=Visita.Cierre.EMPLEADO,
            programada_para=date(2026, 9, dia),
            **extra,
        )

    def test_condicion_cuenta_solo_visitas_realizadas_con_reporte(self):
        con_reporte = self._cerrada(1)
        self._reporte(con_reporte)
        sin_reporte = self._cerrada(2)
        abierta = self._abierta()
        self._reporte(abierta)
        revisada = self._cerrada(3, incidencia_revisada_en=timezone.now())
        self._reporte(revisada)
        declarada = self._cerrada(4, incidencia=True)
        revisada_declarada = self._cerrada(
            5, incidencia=True, incidencia_revisada_en=timezone.now()
        )
        self.assertTrue(sin_reporte and revisada_declarada)
        encontradas = Visita.objects.de_empresa(una_empresa()).filter(
            condicion_incidencia_sin_revisar()
        )
        self.assertCountEqual(
            encontradas.values_list("pk", flat=True), [con_reporte.pk, declarada.pk]
        )

    def test_marcar_revisada_acepta_visita_solo_con_reportes(self):
        visita = self._cerrada(1)
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(visita, self.admin)
        self._reporte(visita)
        revisada = marcar_incidencia_revisada(visita, self.admin)
        self.assertEqual(revisada.incidencia_revisada_por, self.admin)
        self.assertIsNotNone(revisada.incidencia_revisada_en)
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(visita, self.admin)
