"""Servicios de visitas entre empresas: turnos y carga manual."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.sitios.models import PuntoControl
from apps.visitas.models import Visita
from apps.visitas.services import crear_turno, registrar_visita_manual

from .ayudas_empresa import dos_empresas


class TurnosPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()

    def _turno(self, **cambios):
        datos = {
            "sitio": self.a.sitio,
            "empleado": self.a.empleado,
            "programada_para": timezone.localdate(),
            "items": [(self.a.punto, self.a.servicio)],
            "asignada_por": self.a.admin,
        }
        datos.update(cambios)
        return crear_turno(**datos)

    def test_crear_turno_rechaza_punto_o_empleado_de_otra_empresa(self):
        casos = {
            "empleado": {"empleado": self.b.empleado},
            "servicios": {"items": [(self.a.punto, self.b.servicio)]},
            "puntos": {"items": [(self.b.punto, self.a.servicio)]},
        }
        antes = Visita.todos.count()
        for campo, cambios in casos.items():
            with self.assertRaises(ValidationError) as contexto:
                self._turno(**cambios)
            self.assertIn(campo, contexto.exception.message_dict, campo)
        self.assertEqual(Visita.todos.count(), antes)
        self.assertEqual(self._turno().empresa_id, self.a.empresa.pk)

    def test_carga_manual_rechaza_empleado_servicio_y_producto_de_otra_empresa(self):
        sala = PuntoControl.objects.create(
            sitio=self.a.sitio, nombre="Sala", orden=1, servicio=self.a.servicio
        )
        base = {
            "sitio": self.a.sitio,
            "empleado": self.a.empleado,
            "administrador": self.a.admin,
            "motivo": "Carga",
            "realizada_en": timezone.now() - timedelta(minutes=5),
            "items": [(sala, self.a.servicio)],
            "datos": {},
            "productos_aplicados": [],
            "fotos": [],
        }
        producto_ajeno = {
            "producto": self.b.producto.pk,
            "lote": "L",
            "dosis": "1",
            "unidad_dosis": "ml",
            "cantidad": "1",
            "unidad": "unidad",
        }
        otros = {
            "empleado": {"empleado": self.b.empleado},
            "servicios": {"items": [(sala, self.b.servicio)]},
            "puntos": {"items": [(self.b.punto, self.a.servicio)]},
            "productos_aplicados.0.producto": {"productos_aplicados": [producto_ajeno]},
        }
        antes = Visita.todos.count()
        for campo, cambios in otros.items():
            with self.assertRaises(ValidationError) as contexto:
                registrar_visita_manual(**{**base, **cambios})
            self.assertIn(campo, contexto.exception.message_dict, campo)
        self.assertEqual(Visita.todos.count(), antes)
