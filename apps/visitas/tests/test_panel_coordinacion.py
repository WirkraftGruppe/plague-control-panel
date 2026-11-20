"""Panel de visitas: coordinación entre operarios (nuevo turno, ficha y carga)."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa
from apps.productos.models import Producto
from apps.visitas.models import ProductoAplicado, Revision, Visita
from apps.visitas.tests.test_models import crear_revision
from apps.visitas.tests.test_turnos import BaseTurnoTests


class NuevoTurnoAsignadoTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.url = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])
        self.otro = User.objects.create_user(
            "otro",
            password="x",
            rol=User.Rol.EMPLEADO,
            empresa=una_empresa(),
            first_name="Ana",
            last_name="Pérez",
        )
        self.turno(
            [(self.sala, self.roedores)],
            empleado=self.otro,
        )

    def test_punto_de_turno_pendiente_de_otro_destildado_con_nombre(self):
        respuesta = self.client.get(self.url)
        filas = {f["punto"].pk: f for f in respuesta.context["form"].filas()}
        self.assertFalse(filas[self.sala.pk]["marcado"])
        self.assertTrue(filas[self.general.pk]["marcado"])
        self.assertEqual(filas[self.sala.pk]["asignado_a"], "Ana Pérez")
        self.assertContains(respuesta, "Asignado a Ana Pérez")
        self.assertContains(respuesta, 'data-asignado="1"', count=1)

    def test_turno_se_crea_incluyendo_punto_asignado(self):
        respuesta = self.client.post(
            self.url,
            {
                "empleado": self.empleado.pk,
                "programada_para": timezone.localdate() + timedelta(days=2),
                "puntos": [self.sala.pk],
                f"servicio_{self.sala.pk}": self.roedores.pk,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        turno = Visita.objects.de_empresa(una_empresa()).get(empleado=self.empleado)
        self.assertEqual([i.punto_id for i in turno.items.all()], [self.sala.pk])

    def test_atajo_vencidos_excluye_asignados(self):
        ruta = Path(__file__).parents[1] / "static/visitas/nuevo_turno.js"
        codigo = ruta.read_text(encoding="utf-8")
        self.assertIn("!fila.dataset.asignado", codigo)


class FichaTurnoIncidenciasTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.visita = Visita.objects.create(
            sitio=self.sitio,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.REALIZADA,
            abierta_en=timezone.now() - timedelta(hours=2),
            cerrada_en=timezone.now() - timedelta(hours=1),
        )

    def ficha(self):
        return self.client.get(reverse("panel:visitas:ficha", args=[self.visita.pk]))

    def test_revision_sin_coordenadas_senalada(self):
        crear_revision(self.visita, incidencia_sin_ubicacion=True)
        self.assertContains(self.ficha(), "Sin ubicación")

    def test_horas_apertura_y_duplicada_senaladas(self):
        Visita.objects.de_empresa(una_empresa()).filter(pk=self.visita.pk).update(
            incidencia_horas=True, incidencia_apertura_sin_escaneo=True
        )
        crear_revision(self.visita, incidencia_duplicada=True)
        respuesta = self.ficha()
        self.assertContains(respuesta, "Horas inconsistentes")
        self.assertContains(respuesta, "Apertura sin escaneo")
        self.assertContains(respuesta, "Punto revisado por otro operario el mismo día")
        self.assertContains(respuesta, "Marcar como revisada")

    def test_sin_incidencias_nuevas_no_senala_nada(self):
        crear_revision(self.visita)
        respuesta = self.ficha()
        for texto in ("Horas inconsistentes", "Apertura sin escaneo", "Sin ubicación"):
            self.assertNotContains(respuesta, texto)

    def test_dosis_vacia_no_muestra_none(self):
        revision = crear_revision(self.visita)
        producto = Producto.objects.create(
            nombre_comercial="Cebo",
            unidad_base="ml",
            modo_unidad="equivalentes",
            empresa=una_empresa(),
        )
        ProductoAplicado.objects.create(
            revision=revision,
            producto=producto,
            lote="L1",
            dosis=None,
            unidad_dosis="",
            cantidad=Decimal("2"),
            cantidad_base=Decimal("2"),
            unidad="ml",
        )
        respuesta = self.ficha()
        self.assertContains(respuesta, "lote L1")
        self.assertNotContains(respuesta, "None")
        self.assertNotContains(respuesta, "dosis")
        self.assertEqual(Revision.objects.de_empresa(una_empresa()).count(), 1)


class CargarVisitaDosisTests(BaseTurnoTests):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)
        self.fijo = Producto.objects.create(
            nombre_comercial="Fijo",
            unidad_base="ml",
            modo_unidad="equivalentes",
            empresa=una_empresa(),
            dosis_habitual=Decimal("5"),
            unidad_dosis_habitual="ml/l",
        )
        self.variable = Producto.objects.create(
            nombre_comercial="Variable",
            unidad_base="ml",
            modo_unidad="equivalentes",
            empresa=una_empresa(),
            dosis_variable=True,
            dosis_habitual=Decimal("2"),
            unidad_dosis_habitual="g/l",
        )
        revision = crear_revision(
            Visita.objects.create(
                sitio=self.sitio,
                empleado=self.empleado,
                origen=Visita.Origen.APP,
                estado=Visita.Estado.REALIZADA,
            )
        )
        for lote in ("VIEJO", "NUEVO"):
            ProductoAplicado.objects.create(
                revision=revision,
                producto=self.variable,
                lote=lote,
                cantidad=Decimal("1"),
                cantidad_base=Decimal("1"),
                unidad="ml",
            )

    def test_lote_precargado_y_dosis_solo_en_variable(self):
        url = reverse("panel:visitas:cargar", args=[self.sitio.pk])
        respuesta = self.client.get(url)
        html = respuesta.content.decode()
        self.assertIn('data-lote="NUEVO"', html)
        self.assertNotIn("VIEJO", html)
        self.assertIn('data-dosis-variable="1"', html)
        self.assertIn('data-dosis-variable="0"', html)
        self.assertIn('data-dosis="2.000"', html)
        self.assertIn('data-unidad-dosis="g/l"', html)
        self.assertIn("visitas/cargar_visita.js", html)
        self.assertEqual(html.count("data-dosis-campo"), 6)
