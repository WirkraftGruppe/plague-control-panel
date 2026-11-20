"""Dominio del trabajo sin conexión: horas del cliente, servicio enviado y cierre."""

from datetime import timedelta
from io import StringIO
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import CampoPlanilla
from apps.sitios.models import Sitio
from apps.visitas.models import PuntoNoRevisado, Revision, Visita
from apps.visitas.services import (
    NoRevisadoDuplicado,
    RevisionDuplicada,
    VisitaNoAbierta,
    abrir_visita,
    cerrar_visita,
    condicion_incidencia_sin_revisar,
    marcar_incidencia_revisada,
    registrar_no_revisado,
    registrar_visita_manual,
)
from apps.visitas.tests.ayudas_empresa import dos_empresas
from apps.visitas.tests.test_turnos import BaseTurnoTests


def hace(**tiempo):
    return timezone.now() - timedelta(**tiempo)


class BaseSinConexion(BaseTurnoTests):
    def abrir(self, punto=None, **extra):
        return abrir_visita(
            empleado=self.empleado,
            qr_codigo=(punto or self.general).qr_codigo,
            **extra,
        )[0]

    def reportar(self, visita, **extra):
        datos = {
            "empleado": self.empleado,
            "visita_pk": visita.pk,
            "punto": self.sala,
            "motivo": PuntoNoRevisado.Motivo.SIN_ACCESO,
            "cliente_uuid": uuid4(),
        }
        datos.update(extra)
        return registrar_no_revisado(**datos)

    def codigo(self, excepcion, campo):
        return excepcion.error_dict[campo][0].code


class AtrasoAppTests(BaseSinConexion):
    def test_revision_71_horas_se_guarda(self):
        visita = self.abrir(abierta_en=hace(hours=71, minutes=30))
        revision = self.revisar(visita, self.general, realizada_en=hace(hours=71))
        self.assertTrue(
            Revision.objects.de_empresa(una_empresa()).filter(pk=revision.pk).exists()
        )

    def test_revision_73_horas_atraso_excedido(self):
        visita = self.abrir(abierta_en=hace(hours=71, minutes=30))
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, self.general, realizada_en=hace(hours=73))
        self.assertEqual(
            self.codigo(contexto.exception, "realizada_en"), "atraso_excedido"
        )
        self.assertIn("72", str(contexto.exception.message_dict["realizada_en"]))
        self.assertIn("manual", str(contexto.exception.message_dict["realizada_en"]))

    def test_manual_sigue_con_168_horas(self):
        Sitio.objects.de_empresa(una_empresa()).filter(pk=self.sitio.pk).update(
            creado=hace(days=30)
        )
        self.sitio.refresh_from_db()
        argumentos = {
            "sitio": self.sitio,
            "empleado": self.empleado,
            "administrador": self.admin,
            "motivo": "Carga",
            "items": [(self.general, self.roedores)],
            "datos": {},
            "productos_aplicados": [],
            "fotos": [],
        }
        visita = registrar_visita_manual(realizada_en=hace(hours=100), **argumentos)
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        with self.assertRaises(ValidationError) as contexto:
            registrar_visita_manual(realizada_en=hace(hours=169), **argumentos)
        self.assertIn("confirmar_atraso", contexto.exception.message_dict)

    def test_reintento_73_horas_mismo_uuid_es_duplicada(self):
        visita = self.abrir(abierta_en=hace(hours=71, minutes=30))
        cliente_uuid = uuid4()
        original = self.revisar(
            visita, self.general, cliente_uuid=cliente_uuid, realizada_en=hace(hours=71)
        )
        with self.assertRaises(RevisionDuplicada) as contexto:
            self.revisar(
                visita,
                self.general,
                cliente_uuid=cliente_uuid,
                realizada_en=hace(hours=73),
            )
        self.assertEqual(contexto.exception.revision, original)


class HoraClienteTests(BaseSinConexion):
    def test_abrir_pendiente_con_abierta_en_de_ayer(self):
        ayer = hace(hours=24)
        pendiente = self.turno(
            [(self.general, self.roedores)],
            programada_para=timezone.localdate(ayer),
        )
        visita, creada = abrir_visita(
            empleado=self.empleado, qr_codigo=self.general.qr_codigo, abierta_en=ayer
        )
        self.assertTrue(creada)
        self.assertEqual(visita.pk, pendiente.pk)
        self.assertEqual(visita.abierta_en, ayer)
        # Con una abierta, la devuelve sin cambios.
        otra, creada = abrir_visita(
            empleado=self.empleado,
            qr_codigo=self.general.qr_codigo,
            abierta_en=hace(hours=1),
        )
        self.assertFalse(creada)
        self.assertEqual(otra.abierta_en, ayer)

    def test_abrir_con_abierta_en_futura_falla(self):
        with self.assertRaises(ValidationError) as contexto:
            self.abrir(abierta_en=timezone.now() + timedelta(hours=1))
        self.assertIn("abierta_en", contexto.exception.message_dict)
        self.assertFalse(
            Visita.objects.de_empresa(una_empresa())
            .filter(estado=Visita.Estado.ABIERTA)
            .exists()
        )

    def test_abierta_en_futura_tolerada_cuenta_revisiones_al_cerrar(self):
        visita = self.abrir(abierta_en=timezone.now() + timedelta(minutes=5))
        self.assertLessEqual(visita.abierta_en, timezone.now())
        self.revisar(visita, self.general)
        cerrada = cerrar_visita(
            visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        self.assertEqual(cerrada.estado, Visita.Estado.REALIZADA)

    def test_abrir_con_abierta_en_no_toma_pendiente_de_dia_posterior(self):
        pendiente = self.turno(
            [(self.general, self.roedores)],
            programada_para=timezone.localdate() + timedelta(days=1),
        )
        visita, creada = abrir_visita(
            empleado=self.empleado,
            qr_codigo=self.general.qr_codigo,
            abierta_en=hace(hours=1),
        )
        self.assertTrue(creada)
        self.assertNotEqual(visita.pk, pendiente.pk)
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)

    def test_cerrada_en_anterior_a_abierta_se_guarda_con_incidencia(self):
        visita = self.abrir(abierta_en=hace(hours=2))
        self.revisar(visita, self.general)
        hora = hace(hours=3)
        cerrada = cerrar_visita(
            visita,
            quien=self.empleado,
            cierre=Visita.Cierre.EMPLEADO,
            cerrada_en=hora,
        )
        self.assertEqual(cerrada.estado, Visita.Estado.REALIZADA)
        self.assertEqual(cerrada.cerrada_en, hora)
        self.assertTrue(cerrada.incidencia_horas)

    def test_reporte_guarda_reportado_en(self):
        visita = self.abrir(abierta_en=hace(hours=3))
        hora = hace(hours=2)
        reporte = self.reportar(visita, reportado_en=hora)
        self.assertEqual(reporte.reportado_en, hora)
        with self.assertRaises(ValidationError) as contexto:
            self.reportar(visita, punto=self.techo, reportado_en=hace(hours=73))
        self.assertEqual(
            self.codigo(contexto.exception, "reportado_en"), "atraso_excedido"
        )

    def test_reintento_reporte_73_horas_mismo_uuid_es_duplicado(self):
        visita = self.abrir(abierta_en=hace(hours=71, minutes=30))
        cliente_uuid = uuid4()
        original = self.reportar(
            visita, cliente_uuid=cliente_uuid, reportado_en=hace(hours=71)
        )
        with self.assertRaises(NoRevisadoDuplicado) as contexto:
            self.reportar(
                visita, cliente_uuid=cliente_uuid, reportado_en=hace(hours=73)
            )
        self.assertEqual(contexto.exception.reporte, original)

    def test_cierre_por_sistema_usa_reportado_en(self):
        visita = self.abrir(abierta_en=hace(hours=4))
        hora = hace(hours=3)
        self.reportar(visita, reportado_en=hora)
        cerrada = cerrar_visita(visita, quien=None, cierre=Visita.Cierre.SISTEMA)
        self.assertEqual(cerrada.cerrada_en, hora)


class VisitaNoAbiertaTests(BaseSinConexion):
    def test_revision_en_visita_pendiente(self):
        pendiente = self.turno([(self.general, self.roedores)])
        with self.assertRaises(VisitaNoAbierta) as contexto:
            self.revisar(pendiente, self.general)
        self.assertEqual(self.codigo(contexto.exception, "visita"), "visita_no_abierta")
        self.assertIn("La visita no está abierta.", contexto.exception.messages)

    def test_reporte_en_visita_cancelada(self):
        visita = self.turno([(self.general, self.roedores)])
        Visita.objects.de_empresa(una_empresa()).filter(pk=visita.pk).update(
            estado=Visita.Estado.CANCELADA, cierre=Visita.Cierre.SISTEMA
        )
        with self.assertRaises(VisitaNoAbierta) as contexto:
            self.reportar(visita)
        self.assertEqual(self.codigo(contexto.exception, "visita"), "visita_no_abierta")

    def test_cierre_de_visita_pendiente(self):
        pendiente = self.turno([(self.general, self.roedores)])
        with self.assertRaises(VisitaNoAbierta) as contexto:
            cerrar_visita(pendiente, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(contexto.exception.error_list[0].code, "visita_no_abierta")
        self.assertEqual(
            contexto.exception.messages, ["Solo se puede cerrar una visita abierta."]
        )

    def test_cierre_repetido_del_mismo_empleado_sigue_idempotente(self):
        visita = self.abrir()
        self.revisar(visita, self.general)
        primera = cerrar_visita(
            visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        segunda = cerrar_visita(
            visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO
        )
        self.assertEqual(primera.cerrada_en, segunda.cerrada_en)


class ServicioEnviadoTests(BaseSinConexion):
    def test_servicio_distinto_guarda_servicio_e_incidencia(self):
        self.turno([(self.general, self.roedores)])
        visita = self.abrir()
        revision = self.revisar(visita, self.general, servicio=self.insectos.pk)
        self.assertEqual(revision.servicio, self.insectos)
        self.assertTrue(revision.incidencia_servicio)

    def test_servicio_igual_sin_incidencia(self):
        self.turno([(self.general, self.roedores)])
        visita = self.abrir()
        revision = self.revisar(visita, self.general, servicio=self.roedores.pk)
        self.assertEqual(revision.servicio, self.roedores)
        self.assertFalse(revision.incidencia_servicio)
        sin_enviar = self.revisar(visita, self.sala)
        self.assertFalse(sin_enviar.incidencia_servicio)

    def test_servicio_inactivo_o_de_otra_empresa_falla(self):
        visita = self.abrir()
        self.insectos.activo = False
        self.insectos.save()
        _, lado_b = dos_empresas()
        for ajeno in (self.insectos.pk, lado_b.servicio.pk, 999999, "x"):
            with self.subTest(servicio=ajeno):
                with self.assertRaises(ValidationError) as contexto:
                    self.revisar(visita, self.general, servicio=ajeno)
                self.assertIn("servicio", contexto.exception.message_dict)
        self.assertFalse(
            Revision.objects.de_empresa(una_empresa()).filter(visita=visita).exists()
        )

    def test_valida_contra_la_planilla_del_servicio_enviado(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.insectos,
            orden=1,
            etiqueta="Trampas",
            clave="trampas",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        self.turno([(self.general, self.roedores)])
        visita = self.abrir()
        with self.assertRaises(ValidationError) as contexto:
            self.revisar(visita, self.general, servicio=self.insectos.pk)
        self.assertIn("datos", contexto.exception.message_dict)
        revision = self.revisar(
            visita, self.general, servicio=self.insectos.pk, datos={"trampas": 4}
        )
        self.assertEqual(revision.datos, {"trampas": 4})

    def test_visita_nueva_compara_con_servicio_del_punto(self):
        visita = self.abrir()
        self.assertFalse(visita.items.exists())
        igual = self.revisar(visita, self.general, servicio=self.roedores.pk)
        self.assertFalse(igual.incidencia_servicio)
        self.assertTrue(igual.fuera_de_turno)
        distinta = self.revisar(visita, self.sala, servicio=self.insectos.pk)
        self.assertTrue(distinta.incidencia_servicio)
        self.assertEqual(distinta.servicio, self.insectos)


class IncidenciaServicioTests(BaseSinConexion):
    def sin_revisar(self):
        return (
            Visita.objects.de_empresa(una_empresa())
            .filter(condicion_incidencia_sin_revisar())
            .count()
        )

    def test_cuenta_sin_revisar_y_marcar_revisada_la_saca(self):
        visita = self.abrir()
        self.revisar(visita, self.general, servicio=self.insectos.pk)
        # Con la visita abierta todavía no cuenta.
        self.assertEqual(self.sin_revisar(), 0)
        cerrar_visita(visita, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(self.sin_revisar(), 1)
        marcar_incidencia_revisada(visita, self.admin)
        self.assertEqual(self.sin_revisar(), 0)
        # Una visita sin incidencia no cuenta ni se puede marcar.
        limpia = self.abrir(self.sala)
        self.revisar(limpia, self.sala)
        cerrar_visita(limpia, quien=self.empleado, cierre=Visita.Cierre.EMPLEADO)
        self.assertEqual(self.sin_revisar(), 0)
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(limpia, self.admin)


class CierreNocturnoTests(BaseSinConexion):
    def ejecutar(self):
        call_command("cerrar_visitas_abiertas", stdout=StringIO())

    def abierta_vieja(self):
        visita = self.abrir(abierta_en=hace(hours=30))
        return visita

    def envejecer(self, visita):
        """Lleva la actividad de la visita a antes del límite de 16 horas."""
        Visita.objects.de_empresa(una_empresa()).filter(pk=visita.pk).update(
            actualizado=hace(hours=20)
        )
        Revision.objects.de_empresa(una_empresa()).filter(visita=visita).update(
            recibida_en=hace(hours=20)
        )
        PuntoNoRevisado.objects.de_empresa(una_empresa()).filter(visita=visita).update(
            creado=hace(hours=20)
        )

    def test_no_cierra_visita_con_actividad_reciente(self):
        # Cada actividad reciente, por separado, evita el cierre.
        casos = {
            "visita guardada": lambda v: (
                Visita.objects.de_empresa(una_empresa())
                .filter(pk=v.pk)
                .update(actualizado=timezone.now())
            ),
            "revisión recibida": lambda v: (
                Revision.objects.de_empresa(una_empresa())
                .filter(visita=v)
                .update(recibida_en=timezone.now())
            ),
            "reporte creado": lambda v: (
                PuntoNoRevisado.objects.de_empresa(una_empresa())
                .filter(visita=v)
                .update(creado=timezone.now())
            ),
        }
        for nombre, actividad in casos.items():
            with self.subTest(nombre):
                visita = self.abierta_vieja()
                self.revisar(visita, self.general)
                self.reportar(visita)
                self.envejecer(visita)
                actividad(visita)
                self.ejecutar()
                visita.refresh_from_db()
                self.assertEqual(visita.estado, Visita.Estado.ABIERTA)
                self.assertFalse(
                    Visita.objects.de_empresa(una_empresa())
                    .filter(pk=visita.pk, cierre=Visita.Cierre.SISTEMA)
                    .exists()
                )
                Visita.objects.de_empresa(una_empresa()).filter(pk=visita.pk).update(
                    estado=Visita.Estado.CANCELADA, cierre=Visita.Cierre.SISTEMA
                )

    def test_cierra_visita_vieja_sin_actividad(self):
        visita = self.abierta_vieja()
        self.revisar(visita, self.general)
        self.envejecer(visita)
        self.ejecutar()
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.cierre, Visita.Cierre.SISTEMA)
