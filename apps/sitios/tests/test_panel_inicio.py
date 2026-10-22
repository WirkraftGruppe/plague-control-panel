"""Inicio del panel en /panel/sitios/: turnos de hoy, atención y todos los sitios."""

import re
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import ItemTurno, Revision, Visita


class InicioSitiosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.cliente = Cliente.objects.create(razon_social="ACME")
        cls.servicio = TipoServicio.objects.create(nombre="Roedores", slug="roedores-i")
        cls.admin = User.objects.create_user(
            "adm-inicio", password="x", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user(
            "emp-inicio", password="x", rol=User.Rol.EMPLEADO, first_name="Ana"
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("panel:sitios:listado")

    def sitio(self, nombre, dias=None, activo=True):
        """Sitio con su punto General; ``dias`` es el vencimiento relativo a hoy."""
        sitio = Sitio.objects.create(cliente=self.cliente, nombre=nombre)
        vencimiento = None if dias is None else self.hoy + timedelta(days=dias)
        sitio.puntos.update(proximo_vencimiento=vencimiento)
        if not activo:
            sitio.activo = False
            sitio.save()
        return sitio

    def turno(self, sitio, estado=Visita.Estado.PENDIENTE, dias=0, **extra):
        datos = {"sitio": sitio, "empleado": self.empleado, "estado": estado}
        if estado == Visita.Estado.PENDIENTE:
            datos["programada_para"] = self.hoy + timedelta(days=dias)
        elif estado == Visita.Estado.ABIERTA:
            datos["abierta_en"] = timezone.now()
        elif estado == Visita.Estado.REALIZADA:
            datos.update(
                origen=Visita.Origen.MANUAL,
                motivo_manual="Carga",
                abierta_en=timezone.now() - timedelta(days=-dias, hours=1),
                cerrada_en=timezone.now() + timedelta(days=dias),
            )
        datos.update(extra)
        return Visita.objects.create(**datos)

    def test_turnos_de_hoy_lista_pendientes_abiertos_y_realizados_hoy(self):
        a, b, c, d, e, f = (self.sitio(n) for n in "ABCDEF")
        pendiente = self.turno(a, dias=0)
        self.turno(b, dias=1)
        abierta = self.turno(c, Visita.Estado.ABIERTA)
        realizada = self.turno(d, Visita.Estado.REALIZADA, dias=0)
        self.turno(e, Visita.Estado.REALIZADA, dias=-2)
        self.turno(f, Visita.Estado.CANCELADA)
        item = ItemTurno.objects.create(
            visita=abierta, punto=c.puntos.get(), servicio=self.servicio
        )
        otro = PuntoControl.objects.create(sitio=c, nombre="Sala", orden=1)
        ItemTurno.objects.create(visita=abierta, punto=otro, servicio=self.servicio)
        Revision.objects.create(
            visita=abierta,
            punto=item.punto,
            servicio=self.servicio,
            realizada_en=timezone.now(),
            recibida_en=timezone.now(),
        )
        respuesta = self.client.get(self.url)
        self.assertEqual(
            {v.pk for v in respuesta.context["turnos_hoy"]},
            {pendiente.pk, abierta.pk, realizada.pk},
        )
        self.assertContains(respuesta, "Turnos de hoy")
        self.assertContains(respuesta, "Ana")
        por_pk = {v.pk: v for v in respuesta.context["turnos_hoy"]}
        self.assertEqual(
            (por_pk[abierta.pk].revisados, por_pk[abierta.pk].total), (1, 2)
        )
        self.assertContains(respuesta, "1 / 2")
        self.assertContains(
            respuesta, reverse("panel:visitas:ficha", args=[pendiente.pk])
        )

    def test_conteos_de_cada_filtro(self):
        self.sitio("Vencido", -3)
        self.sitio("Vencido 2", -1)
        self.sitio("Semana hoy", 0)
        self.sitio("Semana borde", 7)
        self.sitio("Al dia", 8)
        self.sitio("Sin fecha")
        self.sitio("Inactivo", -9, activo=False)
        respuesta = self.client.get(self.url)
        self.assertEqual(
            {k.value: v for k, v in respuesta.context["conteos"].items()},
            {"vencidos": 2, "semana": 2, "al_dia": 1, "sin_fechas": 1},
        )
        esperado = {
            "vencidos": {"Vencido", "Vencido 2"},
            "semana": {"Semana hoy", "Semana borde"},
            "al_dia": {"Al dia"},
            "sin_fechas": {"Sin fecha"},
        }
        for estado, nombres in esperado.items():
            r = self.client.get(self.url, {"estado": estado})
            listados = {s.nombre for s in r.context["object_list"]}
            self.assertEqual(listados, nombres, estado)
        self.assertContains(self.client.get(self.url), "Ver sitios inactivos")
        inactivos = self.client.get(self.url, {"activo": "0"})
        self.assertEqual(
            [s.nombre for s in inactivos.context["object_list"]], ["Inactivo"]
        )

    def test_contador_de_la_barra_lateral_coincide_con_vencidos(self):
        self.sitio("V1", -2)
        self.sitio("V2", -1)
        self.sitio("Al dia", 20)
        html = self.client.get(self.url).content.decode()
        lateral = re.search(r'contador-vencidos">(\d+)<', html)
        self.assertEqual(lateral.group(1), "2")
        vencidos = self.client.get(self.url).context["conteos"]
        self.assertEqual(vencidos["vencidos"], int(lateral.group(1)))

    def test_requieren_atencion_solo_vencidos_sin_turno_pendiente_ni_abierto(self):
        libre = self.sitio("Libre", -5)
        con_pendiente = self.sitio("Con pendiente", -5)
        con_abierta = self.sitio("Con abierta", -5)
        con_realizada = self.sitio("Con realizada", -5)
        self.sitio("Esta semana", 3)
        self.sitio("Inactivo vencido", -5, activo=False)
        self.turno(con_pendiente, dias=4)
        self.turno(con_abierta, Visita.Estado.ABIERTA)
        self.turno(con_realizada, Visita.Estado.REALIZADA, dias=0)
        respuesta = self.client.get(self.url)
        self.assertEqual(
            {s.pk for s in respuesta.context["requieren_atencion"]},
            {libre.pk, con_realizada.pk},
        )
        self.assertContains(respuesta, "Requieren atención")

    def test_requieren_atencion_lista_incidencias_sin_revisar(self):
        sitio = self.sitio("Con incidencia")
        sin_revisar = self.turno(
            sitio, Visita.Estado.REALIZADA, incidencia=True, incidencia_detalle="Puerta"
        )
        self.turno(
            sitio,
            Visita.Estado.REALIZADA,
            incidencia=True,
            incidencia_revisada_en=timezone.now(),
        )
        self.turno(sitio, Visita.Estado.REALIZADA, incidencia=False)
        respuesta = self.client.get(self.url)
        self.assertEqual(
            [v.pk for v in respuesta.context["incidencias"]], [sin_revisar.pk]
        )
        self.assertContains(
            respuesta, reverse("panel:visitas:ficha", args=[sin_revisar.pk])
        )
        self.assertContains(respuesta, "Revisar")

    def test_proximo_vencimiento_es_el_minimo_de_puntos_activos(self):
        sitio = self.sitio("Varios", 10)
        general = sitio.puntos.get()
        PuntoControl.objects.create(
            sitio=sitio,
            nombre="Cerca",
            orden=1,
            proximo_vencimiento=self.hoy + timedelta(days=2),
        )
        PuntoControl.objects.create(sitio=sitio, nombre="Sin fecha", orden=2)
        PuntoControl.objects.create(
            sitio=sitio,
            nombre="Baja",
            orden=3,
            activo=False,
            proximo_vencimiento=self.hoy - timedelta(days=30),
        )
        respuesta = self.client.get(self.url)
        [fila] = [s for s in respuesta.context["object_list"] if s.pk == sitio.pk]
        self.assertEqual(fila.proximo_vencimiento, self.hoy + timedelta(days=2))
        self.assertEqual(fila.estado_clave, "semana")
        self.assertEqual(general.proximo_vencimiento, self.hoy + timedelta(days=10))

    def test_orden_por_proximo_vencimiento_ascendente(self):
        self.sitio("Sin fecha")
        self.sitio("Tercero", 30)
        self.sitio("Primero", -4)
        self.sitio("Segundo", 5)
        nombres = [s.nombre for s in self.client.get(self.url).context["object_list"]]
        self.assertEqual(nombres, ["Primero", "Segundo", "Tercero", "Sin fecha"])
        descendente = self.client.get(self.url, {"orden": "-proximo_vencimiento"})
        self.assertEqual(
            [s.nombre for s in descendente.context["object_list"]],
            ["Tercero", "Segundo", "Primero", "Sin fecha"],
        )

    def test_mismas_consultas_con_5_y_50_sitios(self):
        def cantidad():
            with CaptureQueriesContext(connection) as capturadas:
                self.assertEqual(self.client.get(self.url).status_code, 200)
            return len(capturadas)

        for n in range(5):
            sitio = self.sitio(f"S{n}", n - 2)
            self.turno(sitio, dias=0)
        con_cinco = cantidad()
        for n in range(5, 50):
            sitio = self.sitio(f"S{n}", n - 2)
            self.turno(sitio, dias=n)
        self.assertEqual(cantidad(), con_cinco)

    def test_nuevo_turno_abre_el_panel_lateral(self):
        sitio = self.sitio("Vencido", -2)
        url = reverse("panel:visitas:nuevo_turno", args=[sitio.pk])
        html = self.client.get(self.url).content.decode()
        enlace = (
            f'href="{url}" hx-get="{url}" hx-target="#panel-lateral" data-abre-panel'
        )
        # "Requieren atención" y la fila de "Todos los sitios".
        self.assertEqual(html.count(enlace), 2)
        self.assertIn("vendor/leaflet/leaflet.js", html)
        self.assertIn("visitas/nuevo_turno.js", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("style=", html)


class TurnosAtrasadosInicioTests(InicioSitiosTests):
    def filas_de_turnos(self):
        html = self.client.get(self.url).content.decode()
        seccion = html.split('id="titulo-hoy"')[1].split("</section>")[0]
        return re.findall(r"<tr>.*?</tr>", seccion.split("<tbody>")[-1], re.S)

    def test_atrasados_primero_en_turnos_de_hoy_con_chip(self):
        de_hoy = self.sitio("Aaa de hoy")
        atrasado = self.sitio("Zzz atrasado")
        self.turno(de_hoy, dias=0)
        self.turno(atrasado, dias=-3)
        filas = self.filas_de_turnos()
        self.assertEqual(len(filas), 2)
        self.assertIn("Zzz atrasado", filas[0])
        self.assertRegex(filas[0], r'etiqueta-estado etiqueta-danger">Atrasado</span>')
        self.assertNotIn("Pendiente", filas[0])
        self.assertIn("Aaa de hoy", filas[1])
        self.assertIn("Pendiente", filas[1])
        self.assertNotIn("Atrasado", filas[1])

    def test_realizados_de_dias_anteriores_no_aparecen(self):
        sitio = self.sitio("Cerrado ayer")
        self.turno(sitio, estado=Visita.Estado.REALIZADA, dias=-2)
        self.assertEqual(self.filas_de_turnos(), [])
