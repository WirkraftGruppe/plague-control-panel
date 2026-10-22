"""Panel de Visitas rediseñado: nuevo turno en panel lateral y turnos agrupados."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl
from apps.visitas.models import Visita

from .test_models import crear_visita, punto_de

HTMX = {"HX-Request": "true"}


class NuevoTurnoLateralTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        visita = crear_visita()
        cls.sitio = visita.sitio
        cls.roedores = visita.tipo
        cls.insectos = TipoServicio.objects.create(
            nombre="Insectos", slug="insectos-lateral"
        )
        cls.general = punto_de(visita)
        cls.sala = PuntoControl.objects.create(
            sitio=cls.sitio, nombre="Sala", orden=1, servicio=cls.roedores
        )
        cls.empleado = visita.empleado
        cls.admin = User.objects.create_user(
            "adm-lateral", password="x", rol=User.Rol.ADMINISTRADOR
        )
        visita.delete()

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("panel:visitas:nuevo_turno", args=[self.sitio.pk])

    def _datos(self, **extra):
        datos = {
            "empleado": self.empleado.pk,
            "programada_para": timezone.localdate() + timedelta(days=2),
            "puntos": [self.general.pk, self.sala.pk],
            f"servicio_{self.general.pk}": self.roedores.pk,
            f"servicio_{self.sala.pk}": self.insectos.pk,
        }
        datos.update(extra)
        return datos

    def test_con_hx_request_devuelve_parcial(self):
        respuesta = self.client.get(self.url, headers=HTMX)
        self.assertTemplateUsed(respuesta, "visitas/panel/_nuevo_turno_lateral.html")
        self.assertTemplateNotUsed(respuesta, "visitas/panel/nuevo_turno.html")
        self.assertNotContains(respuesta, "<html")
        self.assertContains(respuesta, 'aria-label="Cerrar"')
        self.assertContains(respuesta, "data-cierra-panel")
        self.assertContains(respuesta, 'hx-target="#panel-lateral"')
        self.assertContains(respuesta, "panel-lateral-pie")

    def test_sin_hx_request_devuelve_pagina_completa(self):
        respuesta = self.client.get(self.url)
        self.assertTemplateUsed(respuesta, "visitas/panel/nuevo_turno.html")
        self.assertTemplateUsed(respuesta, "visitas/panel/_nuevo_turno_lateral.html")
        self.assertContains(respuesta, "<html")
        self.assertContains(respuesta, "nuevo_turno.js")
        self.assertNotContains(respuesta, "hx-post")

    def test_post_htmx_crea_turno_y_responde_hx_redirect(self):
        respuesta = self.client.post(self.url, self._datos(), headers=HTMX)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta["HX-Redirect"],
            reverse("panel:sitios:ficha", args=[self.sitio.pk]),
        )
        self.assertEqual(
            Visita.objects.filter(estado=Visita.Estado.PENDIENTE).count(), 1
        )

    def test_post_sin_htmx_crea_el_mismo_turno(self):
        respuesta = self.client.post(self.url, self._datos())
        self.assertRedirects(
            respuesta, reverse("panel:sitios:ficha", args=[self.sitio.pk])
        )
        turno = Visita.objects.get(estado=Visita.Estado.PENDIENTE)
        self.assertEqual(turno.items.count(), 2)

    def test_post_htmx_con_errores_devuelve_el_parcial(self):
        respuesta = self.client.post(self.url, self._datos(puntos=[]), headers=HTMX)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("HX-Redirect", respuesta)
        self.assertTemplateUsed(respuesta, "visitas/panel/_nuevo_turno_lateral.html")
        self.assertIn("puntos", respuesta.context["form"].errors)
        self.assertFalse(Visita.objects.exists())

    def test_todos_los_puntos_tildados(self):
        respuesta = self.client.get(self.url, headers=HTMX)
        formulario = respuesta.context["form"]
        self.assertEqual(
            {f["punto"].pk for f in formulario.filas() if f["marcado"]},
            {self.general.pk, self.sala.pk},
        )
        self.assertContains(respuesta, 'type="checkbox"', count=2)
        self.assertContains(respuesta, " checked", count=2)

    def test_responsable_es_la_primera_opcion_de_operario(self):
        otro = User.objects.create_user("aaa-otro", password="x", rol=User.Rol.EMPLEADO)
        self.sitio.responsable = self.empleado
        self.sitio.save()
        respuesta = self.client.get(self.url, headers=HTMX)
        campo = respuesta.context["form"].fields["empleado"]
        opciones = [valor.value for valor, _ in campo.choices]
        self.assertEqual(opciones[:2], [self.empleado.pk, otro.pk])
        self.assertEqual(
            respuesta.context["form"]["empleado"].value(), self.empleado.pk
        )

    def test_crear_deshabilitado_sin_puntos_activos(self):
        self.sitio.puntos.update(activo=False)
        respuesta = self.client.get(self.url, headers=HTMX)
        self.assertContains(respuesta, "data-crear disabled")
        self.sitio.puntos.update(activo=True)
        respuesta = self.client.get(self.url, headers=HTMX)
        self.assertNotContains(respuesta, "data-crear disabled")

    def test_atajos_y_resumen_presentes(self):
        respuesta = self.client.get(self.url, headers=HTMX)
        for atajo in ("todos", "vencidos", "ninguno"):
            self.assertContains(respuesta, f'data-atajo="{atajo}"')
        self.assertContains(respuesta, "Vencidos y próximos")
        self.assertNotContains(respuesta, "Solo vencidos")
        self.assertContains(respuesta, 'aria-live="polite"')
        self.assertContains(respuesta, "data-resumen")


class TurnosAgrupadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        base = crear_visita()
        cls.sitio = base.sitio
        cls.empleado = base.empleado
        base.delete()
        cls.admin = User.objects.create_user(
            "adm-grupos", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.hoy = timezone.localdate()

    def _turno(self, dias=None, **extra):
        datos = {
            "sitio": self.sitio,
            "empleado": self.empleado,
            "estado": Visita.Estado.PENDIENTE,
            "origen": Visita.Origen.MANUAL,
            "motivo_manual": "Prueba",
            "programada_para": None
            if dias is None
            else timezone.localdate() + timedelta(days=dias),
        }
        datos.update(extra)
        return Visita.objects.create(**datos)

    def _grupos(self, **parametros):
        respuesta = self.client.get(reverse("panel:visitas:listado"), parametros)
        self.assertEqual(respuesta.status_code, 200)
        grupos = {
            titulo: [v.pk for v in lista]
            for _, titulo, lista in respuesta.context["grupos"]
        }
        return grupos, respuesta

    def test_agrupa_por_programada_para(self):
        hoy, manana = self._turno(0), self._turno(1)
        semana_a, semana_b = self._turno(2), self._turno(7)
        despues, sin_fecha = self._turno(8), self._turno(None)
        abierta = self._turno(
            3, estado=Visita.Estado.ABIERTA, abierta_en=timezone.now()
        )
        grupos, _ = self._grupos()
        self.assertEqual(grupos["Hoy"], [hoy.pk, abierta.pk])
        self.assertEqual(grupos["Mañana"], [manana.pk])
        self.assertEqual(grupos["Esta semana"], [semana_a.pk, semana_b.pk])
        self.assertEqual(grupos["Más adelante"], [despues.pk, sin_fecha.pk])

    def test_atrasados_primero_en_hoy_con_chip(self):
        hoy = self._turno(0)
        atrasado = self._turno(-3)
        grupos, respuesta = self._grupos()
        self.assertEqual(grupos["Hoy"], [atrasado.pk, hoy.pk])
        self.assertContains(respuesta, "Atrasado", count=1)

    def test_realizados_incluye_cancelados_y_pagina(self):
        ahora = timezone.now()
        cancelado = self._turno(-1, estado=Visita.Estado.CANCELADA)
        for i in range(25):
            self._turno(
                None,
                estado=Visita.Estado.REALIZADA,
                abierta_en=ahora,
                cerrada_en=ahora - timedelta(hours=i + 1),
            )
        respuesta = self.client.get(reverse("panel:visitas:listado"))
        # El cancelado no tiene cierre: se ordena por `creado`, el más reciente.
        self.assertEqual(len(respuesta.context["realizados"]), 25)
        self.assertEqual(respuesta.context["realizados"][0].pk, cancelado.pk)
        self.assertEqual(respuesta.context["page_obj"].paginator.num_pages, 2)
        self.assertEqual(respuesta.context["grupos"], [])
        self.assertNotContains(respuesta, "Atrasado")
        segunda = self.client.get(reverse("panel:visitas:listado"), {"page": 2})
        self.assertEqual(len(segunda.context["realizados"]), 1)

    def test_incidencias_sin_revisar_arriba(self):
        con_incidencia = self._turno(0, incidencia=True, incidencia_detalle="Rotura")
        normal = self._turno(0)
        revisada = self._turno(
            0,
            incidencia=True,
            incidencia_revisada_por=self.admin,
            incidencia_revisada_en=timezone.now(),
        )
        grupos, respuesta = self._grupos()
        self.assertEqual(
            [v.pk for v in respuesta.context["incidencias_sin_revisar"]],
            [con_incidencia.pk],
        )
        self.assertEqual(grupos["Hoy"], [normal.pk, revisada.pk])
        contenido = respuesta.content.decode()
        self.assertLess(
            contenido.index("Incidencias sin revisar <span"),
            contenido.index("Hoy <span"),
        )

    def test_los_filtros_aplican_a_todos_los_grupos(self):
        otro = User.objects.create_user(
            "emp-otro-g", password="x", rol=User.Rol.EMPLEADO
        )
        propio = self._turno(1)
        self._turno(1, empleado=otro)
        grupos, _ = self._grupos(empleado=self.empleado.pk)
        self.assertEqual(grupos["Mañana"], [propio.pk])
