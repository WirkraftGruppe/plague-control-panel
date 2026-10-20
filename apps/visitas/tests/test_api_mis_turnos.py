"""Turnos propios con sus ítems y respuesta de la revisión con su servicio."""

from datetime import date

from django.utils import timezone

from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl
from apps.visitas.models import Revision, Visita
from apps.visitas.services import crear_turno
from apps.visitas.tests.test_api import ApiVisitasBase


class MisTurnosApiTests(ApiVisitasBase):
    def setUp(self):
        super().setUp()
        self.fumiga = TipoServicio.objects.create(nombre="Fumigación", slug="fumiga")
        self.deposito = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Depósito", sector="Fondo", orden=1
        )

    def _turno(self, empleado, items, dia=1):
        return crear_turno(
            sitio=self.sitio,
            empleado=empleado,
            programada_para=date(2026, 9, dia),
            items=items,
            asignada_por=self.admin,
        )

    def test_devuelve_los_items_de_cada_turno(self):
        turno = self._turno(
            self.empleado, [(self.punto, self.tipo), (self.deposito, self.fumiga)]
        )
        Revision.objects.create(
            visita=turno,
            punto=self.deposito,
            servicio=self.fumiga,
            orden=1,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
        )
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 200, r.content)
        (cuerpo,) = r.json()["results"]
        self.assertEqual(cuerpo["id"], turno.id)
        self.assertEqual(cuerpo["sitio"]["id"], self.sitio.id)
        self.assertEqual(cuerpo["sitio"]["nombre"], "Planta 1")
        self.assertEqual(
            cuerpo["items"],
            [
                {
                    "punto": {"id": self.punto.id, "nombre": "General", "sector": ""},
                    "servicio": {"id": self.tipo.id, "nombre": "Desratización"},
                    "revisado": False,
                },
                {
                    "punto": {
                        "id": self.deposito.id,
                        "nombre": "Depósito",
                        "sector": "Fondo",
                    },
                    "servicio": {"id": self.fumiga.id, "nombre": "Fumigación"},
                    "revisado": True,
                },
            ],
        )

    def test_no_devuelve_turnos_de_otro_empleado(self):
        propio = self._turno(self.empleado, [(self.punto, self.tipo)])
        self._turno(self.otro, [(self.deposito, self.fumiga)], dia=2)
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual([v["id"] for v in r.json()["results"]], [propio.id])
        self.assertNotIn("Depósito", r.content.decode())


class RevisionRespuestaTests(ApiVisitasBase):
    def test_incluye_servicio_y_fuera_de_turno(self):
        turno = self._abierta()
        r = self._post(turno)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(
            r.data["servicio"], {"id": self.tipo.id, "nombre": self.tipo.nombre}
        )
        self.assertIs(r.data["fuera_de_turno"], True)
        # Con ítem para el punto, la revisión va dentro del turno.
        dentro = crear_turno(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=date(2026, 9, 3),
            items=[(self.punto, self.tipo)],
            asignada_por=self.admin,
        )
        Visita.objects.filter(pk=turno.pk).update(estado=Visita.Estado.REALIZADA)
        Visita.objects.filter(pk=dentro.pk).update(estado=Visita.Estado.ABIERTA)
        r = self._post(dentro)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertIs(r.data["fuera_de_turno"], False)
