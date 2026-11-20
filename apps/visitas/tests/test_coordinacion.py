"""Coordinación entre operarios: revisiones del día y puntos asignados a otros."""

from datetime import timedelta

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.coordinacion import (
    nombre_de_empleado,
    puntos_asignados_a_otros,
    revisiones_de_hoy,
    revisiones_del_dia,
)
from apps.visitas.models import ItemTurno, Revision, Visita
from apps.visitas.tests.ayudas_empresa import dos_empresas
from apps.visitas.tests.test_turnos import BaseTurnoTests


class BaseCoordinacion(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.otro = User.objects.create_user(
            "otro",
            password="x",
            rol=User.Rol.EMPLEADO,
            empresa=una_empresa(),
            first_name="Ana",
            last_name="Pérez",
        )

    def visita(self, empleado, estado=Visita.Estado.ABIERTA, **extra):
        datos = {
            "sitio": self.sitio,
            "empleado": empleado,
            "origen": Visita.Origen.APP,
            "estado": estado,
        }
        if estado == Visita.Estado.ABIERTA:
            datos["abierta_en"] = timezone.now() - timedelta(hours=2)
        datos.update(extra)
        return Visita.objects.create(**datos)

    def revision(self, visita, punto, realizada_en=None):
        ahora = timezone.now()
        return Revision.objects.create(
            visita=visita,
            punto=punto,
            servicio=self.roedores,
            orden=visita.revisiones.count() + 1,
            realizada_en=realizada_en or ahora,
            recibida_en=ahora,
        )


class RevisionesDeHoyTests(BaseCoordinacion):
    def test_solo_hoy_y_que_cuentan_como_servicio(self):
        ayer = timezone.now() - timedelta(days=1)
        abierta = self.visita(self.otro)
        self.revision(abierta, self.general)
        self.revision(abierta, self.sala, realizada_en=ayer)
        del_admin = self.visita(self.admin, cuenta_como_servicio=False)
        self.revision(del_admin, self.techo)
        cancelada = self.visita(self.empleado, Visita.Estado.CANCELADA)
        self.revision(cancelada, self.techo)
        ids = [self.general.pk, self.sala.pk, self.techo.pk]
        resultado = revisiones_de_hoy(una_empresa(), ids)
        self.assertEqual(list(resultado), [self.general.pk])
        (empleado_id, nombre, _) = resultado[self.general.pk][0]
        self.assertEqual((empleado_id, nombre), (self.otro.pk, "Ana Pérez"))
        self.assertEqual(
            list(revisiones_del_dia(una_empresa(), ids, timezone.localdate(ayer))),
            [self.sala.pk],
        )

    def test_ordena_por_hora_y_usa_el_usuario_sin_nombre(self):
        propia = self.visita(self.empleado)
        ajena = self.visita(self.otro)
        ahora = timezone.now()
        self.revision(ajena, self.general, realizada_en=ahora)
        self.revision(propia, self.general, realizada_en=ahora - timedelta(minutes=5))
        horas = revisiones_de_hoy(una_empresa(), [self.general.pk])[self.general.pk]
        self.assertEqual([h[1] for h in horas], ["emp", "Ana Pérez"])
        self.assertEqual(nombre_de_empleado(self.empleado), "emp")

    def test_no_cruza_empresas(self):
        a, b = dos_empresas()
        b.visita.estado = Visita.Estado.ABIERTA
        b.visita.abierta_en = timezone.now()
        b.visita.save()
        self.revision_ajena = Revision.objects.create(
            visita=b.visita,
            punto=b.punto,
            servicio=b.servicio,
            orden=1,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
        )
        self.assertEqual(revisiones_de_hoy(a.empresa, [b.punto.pk]), {})
        self.assertEqual(list(revisiones_de_hoy(b.empresa, [b.punto.pk])), [b.punto.pk])

    def test_una_consulta(self):
        visita = self.visita(self.otro)
        for punto in (self.general, self.sala, self.techo):
            self.revision(visita, punto)
        ids = [self.general.pk, self.sala.pk, self.techo.pk]
        empresa = una_empresa()
        with CaptureQueriesContext(connection) as consultas:
            revisiones_de_hoy(empresa, ids)
        self.assertEqual(len(consultas), 1)


class AsignadosAOtrosTests(BaseCoordinacion):
    def asignar(self, visita, *puntos):
        for punto in puntos:
            ItemTurno.objects.create(
                visita=visita,
                punto=punto,
                servicio=self.roedores,
                empresa_id=visita.empresa_id,
            )

    def test_pendiente_o_abierta_de_otro_empleado(self):
        self.asignar(self.visita(self.otro, Visita.Estado.PENDIENTE), self.general)
        self.asignar(self.visita(self.otro), self.sala)
        ids = [self.general.pk, self.sala.pk, self.techo.pk]
        empresa = una_empresa()
        with CaptureQueriesContext(connection) as consultas:
            resultado = puntos_asignados_a_otros(empresa, ids, self.empleado.pk)
        self.assertEqual(
            resultado, {self.general.pk: "Ana Pérez", self.sala.pk: "Ana Pérez"}
        )
        self.assertEqual(len(consultas), 1)
        # Sin empleado, cuenta a cualquiera.
        self.assertEqual(len(puntos_asignados_a_otros(una_empresa(), ids, None)), 2)

    def test_excluye_realizadas_canceladas_y_propias(self):
        for estado in (Visita.Estado.CANCELADA,):
            self.asignar(self.visita(self.otro, estado), self.general)
        realizada = self.visita(
            self.otro, Visita.Estado.REALIZADA, cerrada_en=timezone.now()
        )
        self.asignar(realizada, self.sala)
        self.asignar(self.visita(self.empleado), self.techo)
        ids = [self.general.pk, self.sala.pk, self.techo.pk]
        self.assertEqual(
            puntos_asignados_a_otros(una_empresa(), ids, self.empleado.pk), {}
        )
