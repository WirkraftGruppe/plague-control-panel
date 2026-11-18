"""Estado del sitio por sus puntos, última revisión y avance de turnos en la ficha."""

from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.empresas.tests.ayudas import una_empresa
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import ItemTurno, Revision, Visita


class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.empresa = una_empresa()
        cls.cliente = Cliente.objects.create(razon_social="ACME", empresa=cls.empresa)
        cls.servicio = TipoServicio.objects.create(
            nombre="Roedores", slug="roedores-av", empresa=cls.empresa
        )
        cls.admin = User.objects.create_user(
            "adm-av", password="x", rol=User.Rol.ADMINISTRADOR, empresa=cls.empresa
        )
        cls.ana = User.objects.create_user(
            "ana-av",
            password="x",
            rol=User.Rol.EMPLEADO,
            first_name="Ana",
            last_name="Paz",
            empresa=cls.empresa,
        )
        cls.beto = User.objects.create_user(
            "beto-av",
            password="x",
            rol=User.Rol.EMPLEADO,
            first_name="Beto",
            empresa=cls.empresa,
        )
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta")
        cls.punto = cls.sitio.puntos.get()

    def setUp(self):
        self.client.force_login(self.admin)
        self.url_ficha = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        self.url_avance = reverse("panel:sitios:ficha_avance", args=[self.sitio.pk])

    def punto_nuevo(self, nombre, sitio=None, **extra):
        sitio = sitio or self.sitio
        return PuntoControl.objects.create(
            sitio=sitio, nombre=nombre, orden=sitio.puntos.count(), **extra
        )

    def abierta(self, empleado=None, sitio=None, **extra):
        return Visita.objects.create(
            sitio=sitio or self.sitio,
            empleado=empleado or self.ana,
            estado=Visita.Estado.ABIERTA,
            abierta_en=timezone.now(),
            **extra,
        )

    def revision(self, visita, punto, cuando=None):
        cuando = cuando or timezone.now()
        return Revision.objects.create(
            visita=visita,
            punto=punto,
            servicio=self.servicio,
            realizada_en=cuando,
            recibida_en=cuando,
        )

    def item(self, visita, punto):
        return ItemTurno.objects.create(
            visita=visita, punto=punto, servicio=self.servicio
        )

    def fila(self, respuesta, punto):
        return next(p for p in respuesta.context["puntos"] if p.pk == punto.pk)


class EstadoSitioPanelTests(_Base):
    def test_listado_chip_proxima_por_un_punto_que_no_es_el_mas_cercano(self):
        # El más cercano está al día (frecuencia 7: aviso de 2 días); el otro, en aviso.
        PuntoControl.objects.de_empresa(self.empresa).filter(pk=self.punto.pk).update(
            frecuencia_dias=7, proximo_vencimiento=self.hoy + timedelta(days=5)
        )
        self.punto_nuevo(
            "Lejano",
            frecuencia_dias=30,
            proximo_vencimiento=self.hoy + timedelta(days=7),
        )
        respuesta = self.client.get(reverse("panel:sitios:listado"))
        sitio = next(
            s for s in respuesta.context["object_list"] if s.pk == self.sitio.pk
        )
        self.assertEqual(sitio.estado_clave, "semana")
        self.assertEqual(sitio.chip_texto, "Próxima")
        con_estado = self.client.get(
            reverse("panel:sitios:listado"), {"estado": "semana"}
        )
        self.assertIn(sitio, list(con_estado.context["object_list"]))

    def test_estado_de_me_puntos_coincide_con_la_ficha(self):
        PuntoControl.objects.de_empresa(self.empresa).filter(pk=self.punto.pk).update(
            frecuencia_dias=14, proximo_vencimiento=self.hoy + timedelta(days=5)
        )
        self.punto_nuevo(
            "Cerca",
            frecuencia_dias=14,
            proximo_vencimiento=self.hoy + timedelta(days=4),
        )
        Visita.objects.create(
            sitio=self.sitio,
            empleado=self.ana,
            origen=Visita.Origen.MANUAL,
            programada_para=self.hoy,
        )
        api = APIClient()
        api.force_authenticate(self.ana)
        en_api = sorted(p["estado"] for p in api.get("/api/v1/me/puntos/").json())
        ficha = self.client.get(self.url_ficha)
        en_ficha = sorted(p.estado for p in ficha.context["puntos"])
        self.assertEqual(en_api, en_ficha)
        self.assertEqual(en_ficha, ["al_dia", "proxima"])
        self.assertEqual(ficha.context["estado_general"], "semana")


class UltimaRevisionTests(_Base):
    def test_muestra_fecha_hora_y_operario_de_la_ultima_revision(self):
        visita = self.abierta()
        vieja = timezone.now() - timedelta(days=3)
        self.revision(visita, self.punto, vieja)
        ultima = timezone.localtime().replace(hour=9, minute=41)
        otra = self.abierta(self.beto)
        self.revision(otra, self.punto, ultima)
        respuesta = self.client.get(self.url_ficha)
        self.assertContains(respuesta, f"{ultima:%d/%m/%Y} 09:41")
        self.assertEqual(self.fila(respuesta, self.punto).ultimo_operario, "Beto")
        self.assertContains(respuesta, "Beto")

    def test_revision_de_visita_de_administrador_no_cuenta(self):
        propia = self.abierta()
        self.revision(propia, self.punto, timezone.now() - timedelta(days=2))
        delegada = self.abierta(self.admin, cuenta_como_servicio=False)
        self.revision(delegada, self.punto)
        fila = self.fila(self.client.get(self.url_ficha), self.punto)
        self.assertEqual(fila.ultimo_operario, "Ana Paz")

    def test_punto_sin_revisiones_dice_sin_revisiones(self):
        respuesta = self.client.get(self.url_ficha)
        self.assertContains(respuesta, "Sin revisiones")
        self.assertEqual(self.fila(respuesta, self.punto).ultimo_operario, "")

    def test_consultas_iguales_con_5_y_50_puntos(self):
        visita = self.abierta()
        self.item(visita, self.punto)
        self.abierta(self.admin, cuenta_como_servicio=False)

        def agregar(desde, hasta):
            for n in range(desde, hasta):
                punto = self.punto_nuevo(f"P{n}", proximo_vencimiento=self.hoy)
                self.item(visita, punto)
                operario = User.objects.create_user(
                    f"op{n}-av",
                    password="x",
                    rol=User.Rol.EMPLEADO,
                    empresa=self.empresa,
                )
                self.revision(self.abierta(operario, cuenta_como_servicio=True), punto)
                self.revision(
                    Visita.objects.de_empresa(self.empresa).filter(
                        cuenta_como_servicio=False
                    )[0],
                    punto,
                )

        def cantidad(url):
            with CaptureQueriesContext(connection) as capturadas:
                self.assertEqual(self.client.get(url).status_code, 200)
            return len(capturadas)

        agregar(0, 4)
        con_cinco = (cantidad(self.url_ficha), cantidad(self.url_avance))
        agregar(4, 49)
        self.assertEqual(
            (cantidad(self.url_ficha), cantidad(self.url_avance)), con_cinco
        )


class AvanceTurnoTests(_Base):
    def test_turno_abierto_muestra_operario_apertura_y_avance(self):
        otro = self.punto_nuevo("Otro")
        visita = self.abierta()
        self.item(visita, self.punto)
        self.item(visita, otro)
        self.revision(visita, self.punto)
        respuesta = self.client.get(self.url_avance)
        self.assertContains(respuesta, "Ana Paz")
        self.assertContains(respuesta, f"{timezone.localtime(visita.abierta_en):%H:%M}")
        self.assertContains(respuesta, "1 de 2 puntos revisados")

    def test_sin_items_el_total_son_los_puntos_activos(self):
        self.punto_nuevo("Otro")
        self.punto_nuevo("Baja", activo=False)
        self.abierta()
        self.assertContains(self.client.get(self.url_avance), "0 de 2 puntos revisados")

    def test_dos_turnos_abiertos_muestran_dos_bloques(self):
        self.abierta()
        self.abierta(self.beto)
        respuesta = self.client.get(self.url_avance)
        self.assertEqual(len(respuesta.context["turnos_abiertos"]), 2)
        self.assertContains(respuesta, "Turno abierto de", count=2)

    def test_punto_revisado_en_el_turno_queda_marcado(self):
        otro = self.punto_nuevo("Otro")
        visita = self.abierta()
        self.revision(visita, self.punto)
        respuesta = self.client.get(self.url_avance)
        self.assertEqual(self.fila(respuesta, self.punto).revisado_por, ["Ana Paz"])
        self.assertEqual(self.fila(respuesta, otro).revisado_por, [])
        self.assertContains(respuesta, "Revisado en este turno · Ana Paz", count=1)

    def test_sin_turno_abierto_no_hay_actualizacion_de_30_s(self):
        for url in (self.url_ficha, self.url_avance):
            respuesta = self.client.get(url)
            self.assertNotContains(respuesta, "every 30s")
            self.assertNotContains(respuesta, 'hx-get="' + self.url_avance)
        self.assertContains(self.client.get(self.url_ficha), "every 5s")

    def test_avance_tras_cerrar_el_turno_corta_la_actualizacion(self):
        visita = self.abierta()
        self.assertContains(self.client.get(self.url_avance), "every 30s")
        Visita.objects.de_empresa(self.empresa).filter(pk=visita.pk).update(
            estado=Visita.Estado.REALIZADA, cerrada_en=timezone.now()
        )
        respuesta = self.client.get(self.url_avance)
        self.assertNotContains(respuesta, "every 30s")
        self.assertNotContains(respuesta, "data-sondeo")
        self.assertContains(respuesta, 'id="ficha-avance"')

    def test_visita_de_administrador_no_cuenta_como_turno(self):
        visita = self.abierta(self.admin, cuenta_como_servicio=False)
        self.revision(visita, self.punto)
        respuesta = self.client.get(self.url_avance)
        self.assertEqual(respuesta.context["turnos_abiertos"], [])
        self.assertNotContains(respuesta, "Turno abierto de")
        self.assertNotContains(respuesta, "Revisado en este turno")
        self.assertNotContains(respuesta, "every 30s")

    def test_turnos_de_hoy_usan_el_mismo_avance(self):
        otro = self.punto_nuevo("Otro")
        con_items = self.abierta()
        self.item(con_items, self.punto)
        self.item(con_items, otro)
        self.revision(con_items, self.punto)
        self.revision(con_items, self.punto)
        sin_items = self.abierta(self.beto)
        self.revision(sin_items, otro)
        avance = {
            v.pk: (v.revisados, v.total)
            for v in self.client.get(self.url_avance).context["turnos_abiertos"]
        }
        hoy = {
            v.pk: (v.revisados, v.total)
            for v in self.client.get(reverse("panel:sitios:listado")).context[
                "turnos_hoy"
            ]
        }
        self.assertEqual(avance, {con_items.pk: (1, 2), sin_items.pk: (1, 2)})
        self.assertEqual(hoy, avance)

    def test_avance_de_sitio_de_otra_empresa_da_404(self):
        otra = Empresa.objects.create(nombre="Otra empresa")
        cliente = Cliente.objects.create(razon_social="Ajeno", empresa=otra)
        ajeno = Sitio.objects.create(cliente=cliente, nombre="Ajeno")
        respuesta = self.client.get(
            reverse("panel:sitios:ficha_avance", args=[ajeno.pk])
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_avance_pide_administrador(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url_avance).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url_avance).status_code, 302)
