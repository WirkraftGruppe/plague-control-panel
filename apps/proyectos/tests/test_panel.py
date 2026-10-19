"""Panel de Proyectos: listado filtrable, alta, edición y ficha."""

from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.proyectos.consultas import filtrar_por_estado_visita
from apps.proyectos.models import Proyecto
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita

ESQUEMA = [
    {"clave": "cebaderos", "etiqueta": "Cebaderos revisados", "tipo": "numero"},
    {"clave": "hubo_consumo", "etiqueta": "Hubo consumo", "tipo": "booleano"},
]


class ProyectoPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cliente = Cliente.objects.create(razon_social="ACME")
        cls.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        cls.tipo = TipoServicio.objects.create(nombre="Roedores", slug="roedores-t8")
        cls.empleado = User.objects.create_user(
            "emp8", password="x", rol=User.Rol.EMPLEADO
        )
        cls.admin = User.objects.create_user(
            "adm8", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _proyecto(self, titulo, dias=None, **extra):
        hoy = timezone.localdate()
        return Proyecto.objects.create(
            sitio=self.sitio,
            tipo_servicio=self.tipo,
            titulo=titulo,
            proxima_visita=None if dias is None else hoy + timedelta(days=dias),
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
            **extra,
        )

    def _titulos(self, **parametros):
        respuesta = self.client.get(reverse("panel:proyectos:listado"), parametros)
        self.assertEqual(respuesta.status_code, 200)
        return [p.titulo for p in respuesta.context["proyectos"]]

    def test_filtros_solo_activos_con_tope(self):
        Cliente.objects.create(razon_social="Inactivo SA", activo=False)
        Sitio.objects.create(cliente=self.sitio.cliente, nombre="Cerrado", activo=False)
        TipoServicio.objects.create(nombre="Viejo", slug="viejo-t2", activo=False)
        respuesta = self.client.get(reverse("panel:proyectos:listado"))
        self.assertEqual(
            [c.razon_social for c in respuesta.context["clientes"]], ["ACME"]
        )
        self.assertEqual([s.nombre for s in respuesta.context["sitios"]], ["Planta 1"])
        self.assertEqual(
            [t.nombre for t in respuesta.context["servicios"]], ["Roedores"]
        )
        with patch("apps.proyectos.panel_views.FILTRO_MAXIMO_OPCIONES", 2):
            Cliente.objects.bulk_create(
                Cliente(razon_social=f"Extra {i}") for i in range(3)
            )
            respuesta = self.client.get(reverse("panel:proyectos:listado"))
        self.assertEqual(len(respuesta.context["clientes"]), 2)

    def test_listado_filtra_vencidos(self):
        self._proyecto("vencido", -3)
        self._proyecto("proximo", 2)
        self._proyecto("al dia", 30)
        self._proyecto("sin programar")
        self.assertEqual(self._titulos(estado_visita="vencida"), ["vencido"])
        self.assertEqual(self._titulos(estado_visita="proxima"), ["proximo"])
        self.assertEqual(self._titulos(estado_visita="al_dia"), ["al dia"])
        self.assertEqual(
            self._titulos(estado_visita="sin_programar"), ["sin programar"]
        )

    def test_filtro_numerico_no_ascii_no_da_500(self):
        self._proyecto("Uno")
        for valor in ("²", "٣", "1٣"):
            for parametro in ("cliente", "sitio", "servicio", "encargado"):
                with self.subTest(parametro=parametro, valor=valor):
                    self.assertEqual(self._titulos(**{parametro: valor}), ["Uno"])

    def test_filtro_numerico_fuera_de_rango_no_da_500(self):
        self._proyecto("Uno")
        for valor in ("9" * 4301, "9223372036854775808", "9" * 20):
            for parametro in ("cliente", "sitio", "servicio", "encargado"):
                with self.subTest(parametro=parametro, valor=valor[:25]):
                    self.assertEqual(self._titulos(**{parametro: valor}), ["Uno"])

    def test_filtro_coincide_con_la_propiedad_del_modelo(self):
        for dias in (-1, 0, 7, 8, None):
            self._proyecto(f"p{dias}", dias)
        for estado in ("vencida", "proxima", "al_dia", "sin_programar"):
            esperados = {
                p.pk for p in Proyecto.objects.all() if p.estado_visita == estado
            }
            obtenidos = set(
                filtrar_por_estado_visita(Proyecto.objects.all(), estado).values_list(
                    "pk", flat=True
                )
            )
            self.assertEqual(obtenidos, esperados, estado)

    def test_listado_ordena_por_proxima_visita(self):
        self._proyecto("tarde", 20)
        self._proyecto("sin fecha")
        self._proyecto("pronto", -2)
        self._proyecto("medio", 5)
        self.assertEqual(self._titulos(), ["pronto", "medio", "tarde", "sin fecha"])

    def test_listado_exige_administrador(self):
        self.client.force_login(self.empleado)
        respuesta = self.client.get(reverse("panel:proyectos:listado"))
        self.assertEqual(respuesta.status_code, 403)

    def test_alta_asigna_encargado_actual(self):
        respuesta = self.client.post(
            reverse("panel:proyectos:alta"),
            {
                "sitio": self.sitio.pk,
                "tipo_servicio": self.tipo.pk,
                "titulo": "Nuevo",
                "estado": "activo",
                "encargado_inicial": self.empleado.pk,
            },
        )
        proyecto = Proyecto.objects.get(titulo="Nuevo")
        self.assertRedirects(
            respuesta, reverse("panel:proyectos:ficha", args=[proyecto.pk])
        )
        self.assertEqual(proyecto.encargado_actual, self.empleado)

    def test_edicion_cambia_titulo(self):
        proyecto = self._proyecto("viejo")
        self.client.post(
            reverse("panel:proyectos:editar", args=[proyecto.pk]),
            {
                "sitio": self.sitio.pk,
                "tipo_servicio": self.tipo.pk,
                "titulo": "cambiado",
                "estado": "pausado",
                "encargado_actual": self.empleado.pk,
            },
        )
        proyecto.refresh_from_db()
        self.assertEqual((proyecto.titulo, proyecto.estado), ("cambiado", "pausado"))

    def _visita(self, proyecto, producto, **extra):
        ahora = timezone.now()
        visita = Visita.objects.create(
            proyecto=proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            estado=Visita.Estado.REALIZADA,
            abierta_en=ahora,
            cerrada_en=ahora,
            **extra,
        )
        revision = Revision.objects.create(
            visita=visita,
            punto=proyecto.sitio.puntos.get(orden=0),
            orden=1,
            realizada_en=ahora,
            recibida_en=ahora,
            esquema_planilla=ESQUEMA,
            datos={"cebaderos": 12, "hubo_consumo": True},
        )
        Foto.objects.create(revision=revision, imagen="visitas/fotos/x.jpg")
        Foto.objects.create(revision=revision, imagen="visitas/fotos/y.jpg")
        ProductoAplicado.objects.create(
            revision=revision,
            producto=producto,
            lote="L1",
            dosis=1,
            unidad_dosis="ml/l",
            cantidad=2,
            unidad="unidad",
            cantidad_base=2,
        )
        return visita

    def test_ficha_muestra_linea_de_tiempo_con_planilla(self):
        proyecto = self._proyecto("ficha", 10)
        producto = Producto.objects.create(nombre_comercial="Cebo X")
        self._visita(proyecto, producto, incidencia=True, incidencia_detalle="Nido")
        respuesta = self.client.get(
            reverse("panel:proyectos:ficha", args=[proyecto.pk])
        )
        self.assertContains(respuesta, "Línea de tiempo")
        self.assertContains(respuesta, "Cebaderos revisados")
        self.assertContains(respuesta, "<td>12</td>", html=True)
        self.assertContains(respuesta, "<td>Sí</td>", html=True)
        self.assertContains(respuesta, "Cebo X")
        self.assertContains(respuesta, "Nido")

    def test_ficha_consultas_constantes(self):
        proyecto = self._proyecto("constantes")
        producto = Producto.objects.create(nombre_comercial="Cebo Y")
        url = reverse("panel:proyectos:ficha", args=[proyecto.pk])
        for _ in range(2):
            self._visita(proyecto, producto)
        self.client.get(url)  # calienta cachés (sesión, contenttypes)
        with CaptureQueriesContext(connection) as contador:
            self.client.get(url)
        base = len(contador)
        for _ in range(4):
            self._visita(proyecto, producto)
        with self.assertNumQueries(base):
            self.client.get(url)

    def test_ficha_lista_revisiones_consultas_constantes(self):
        proyecto = self._proyecto("revisiones")
        producto = Producto.objects.create(nombre_comercial="Cebo W")
        url = reverse("panel:proyectos:ficha", args=[proyecto.pk])

        def visita_con_revisiones(cantidad):
            visita = self._visita(proyecto, producto)
            for orden in range(2, cantidad + 1):
                punto = PuntoControl.objects.create(
                    sitio=self.sitio, nombre=f"Punto {visita.pk}-{orden}", orden=orden
                )
                ahora = timezone.now()
                revision = Revision.objects.create(
                    visita=visita,
                    punto=punto,
                    orden=orden,
                    realizada_en=ahora,
                    recibida_en=ahora,
                    esquema_planilla=ESQUEMA,
                    datos={"cebaderos": orden},
                )
                Foto.objects.create(revision=revision, imagen="visitas/fotos/w.jpg")
                ProductoAplicado.objects.create(
                    revision=revision,
                    producto=producto,
                    lote="L",
                    dosis=1,
                    unidad_dosis="u",
                    cantidad=1,
                    unidad="unidad",
                    cantidad_base=1,
                )

        visita_con_revisiones(2)
        self.client.get(url)  # calienta cachés (sesión, contenttypes)
        with CaptureQueriesContext(connection) as contador:
            respuesta = self.client.get(url)
        base = len(contador)
        self.assertContains(respuesta, "<details")
        for _ in range(3):
            visita_con_revisiones(3)
        with self.assertNumQueries(base):
            respuesta = self.client.get(url)
        self.assertContains(respuesta, "<summary>Punto ", count=7)
