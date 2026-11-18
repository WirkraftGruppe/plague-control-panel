"""El estado del punto de un turno usa los días de aviso según su frecuencia."""

from datetime import date, timedelta

from django.utils import timezone

from apps.sitios.estado import estados_por_vencimiento
from apps.visitas.services import crear_turno
from apps.visitas.tests.test_api import ApiVisitasBase


class EstadoAvisoApiTests(ApiVisitasBase):
    def test_estado_del_punto_del_turno_usa_la_frecuencia(self):
        hoy = timezone.localdate()
        self.punto.frecuencia_dias = 7
        self.punto.proximo_vencimiento = hoy + timedelta(days=5)
        self.punto.save()
        crear_turno(
            sitio=self.sitio,
            empleado=self.empleado,
            programada_para=date(2026, 9, 1),
            items=[(self.punto, self.tipo)],
            asignada_por=self.admin,
        )
        r = self.api.get("/api/v1/me/visitas/")
        self.assertEqual(r.status_code, 200, r.content)
        (cuerpo,) = r.json()["results"]
        estado = cuerpo["items"][0]["punto"]["estado"]
        self.assertEqual(estado, "al_dia")
        self.punto.refresh_from_db()
        self.assertEqual(
            estado, estados_por_vencimiento([self.punto], hoy)[self.punto.id]
        )
