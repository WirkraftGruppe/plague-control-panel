from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.visitas.models import Visita
from apps.visitas.planillas import filas_planilla
from apps.visitas.services import marcar_incidencia_revisada
from apps.visitas.tests.test_models import crear_visita


class RevisionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="adm-rev",
            password="x",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )

    def visita_realizada(self, **extra):
        return crear_visita(
            estado=Visita.Estado.REALIZADA,
            cerrada_en=timezone.now(),
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
            **extra,
        )

    def test_marca_revisor_y_fecha(self):
        visita = self.visita_realizada(incidencia=True, incidencia_detalle="Rotura")
        antes = timezone.now()
        marcar_incidencia_revisada(visita, self.admin)
        visita.refresh_from_db()
        self.assertEqual(visita.incidencia_revisada_por, self.admin)
        self.assertGreaterEqual(visita.incidencia_revisada_en, antes)
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)

    def test_rechaza_visita_sin_incidencia_o_ya_revisada(self):
        sin = self.visita_realizada()
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(sin, self.admin)
        sin.refresh_from_db()
        self.assertIsNone(sin.incidencia_revisada_en)
        sin.incidencia = True
        sin.save()
        marcar_incidencia_revisada(sin, self.admin)
        with self.assertRaises(ValidationError):
            marcar_incidencia_revisada(sin, self.admin)


class FilasPlanillaTests(SimpleTestCase):
    def test_usa_etiquetas_del_esquema_copiado(self):
        esquema = [
            {"clave": "cebos", "etiqueta": "Cantidad de cebos", "tipo": "numero"},
            {"clave": "limpio", "etiqueta": "Zona limpia", "tipo": "booleano"},
            {"clave": "mal", "etiqueta": "Sin cumplir", "tipo": "booleano"},
            {
                "clave": "plagas",
                "etiqueta": "Plagas vistas",
                "tipo": "opcion_multiple",
                "opciones": ["rata", "cucaracha"],
            },
            {"clave": "nota", "etiqueta": "Nota", "tipo": "texto"},
        ]
        datos = {
            "cebos": 4,
            "limpio": True,
            "mal": False,
            "plagas": ["rata", "cucaracha"],
        }
        self.assertEqual(
            filas_planilla(esquema, datos),
            [
                ("Cantidad de cebos", "4"),
                ("Zona limpia", "Sí"),
                ("Sin cumplir", "No"),
                ("Plagas vistas", "rata, cucaracha"),
                ("Nota", "—"),
            ],
        )
