from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import CampoPlanilla, TipoServicio


class CampoPlanillaTests(TestCase):
    def setUp(self):
        self.tipo = TipoServicio.objects.create(
            nombre="Uno", slug="uno", empresa=una_empresa()
        )

    def test_clave_unica_por_tipo_servicio(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo, orden=1, etiqueta="A", clave="a", tipo="texto"
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            CampoPlanilla.objects.create(
                tipo_servicio=self.tipo, orden=2, etiqueta="B", clave="a", tipo="texto"
            )

    def test_misma_clave_en_otro_tipo_servicio_es_valida(self):
        otro = TipoServicio.objects.create(
            nombre="Dos", slug="dos", empresa=una_empresa()
        )
        CampoPlanilla.objects.create(
            tipo_servicio=self.tipo, orden=1, etiqueta="A", clave="a", tipo="texto"
        )
        campo = CampoPlanilla.objects.create(
            tipo_servicio=otro, orden=1, etiqueta="A", clave="a", tipo="texto"
        )
        self.assertEqual(campo.clave, "a")


class TipoServicioTests(TestCase):
    def test_esquema_planilla_respeta_orden(self):
        tipo = TipoServicio.objects.create(
            nombre="Prueba", slug="prueba", empresa=una_empresa()
        )
        for orden in (3, 1, 2):
            CampoPlanilla.objects.create(
                tipo_servicio=tipo,
                orden=orden,
                etiqueta=f"Campo {orden}",
                clave=f"campo-{orden}",
                tipo=CampoPlanilla.Tipo.NUMERO,
            )
        esquema = tipo.esquema_planilla()
        self.assertEqual(
            [c["clave"] for c in esquema], ["campo-1", "campo-2", "campo-3"]
        )
        self.assertEqual(
            set(esquema[0]),
            {"clave", "etiqueta", "tipo", "opciones", "obligatorio", "ayuda", "orden"},
        )

    def test_servicios_creados_en_el_test_se_listan(self):
        empresa = una_empresa()
        for nombre in ("Mantenimiento edilicio", "Roedores"):
            TipoServicio.objects.create(nombre=nombre, empresa=empresa)
        self.assertEqual(TipoServicio.todos.count(), 2)
        self.assertTrue(
            TipoServicio.todos.filter(nombre="Mantenimiento edilicio").exists()
        )


class AmbitoTests(TestCase):
    def test_esquema_filtra_por_ambito(self):
        tipo = TipoServicio.objects.create(
            nombre="Ámbito", slug="ambito", empresa=una_empresa()
        )
        CampoPlanilla.objects.create(
            tipo_servicio=tipo, orden=1, etiqueta="P", clave="p", tipo="texto"
        )
        CampoPlanilla.objects.create(
            tipo_servicio=tipo,
            orden=2,
            etiqueta="V",
            clave="v",
            tipo="texto",
            ambito=CampoPlanilla.Ambito.VISITA,
        )
        tipo = (
            TipoServicio.objects.de_empresa(una_empresa())
            .prefetch_related("campos")
            .get(pk=tipo.pk)
        )
        with self.assertNumQueries(0):
            claves_punto = [c["clave"] for c in tipo.esquema_planilla()]
            claves_visita = [c["clave"] for c in tipo.esquema_planilla("visita")]
        self.assertEqual(claves_punto, ["p"])
        self.assertEqual(claves_visita, ["v"])
        self.assertEqual(
            CampoPlanilla.objects.de_empresa(una_empresa()).get(clave="p").ambito,
            "punto",
        )
