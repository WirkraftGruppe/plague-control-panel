"""Mapa del panel: datos JSON, permisos, consultas y CSP."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel.mapa import ORIGEN_TESELAS
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl, Sitio

DATOS = "/panel/mapa/datos/"


class MapaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        cls.empleado = User.objects.create_user("emp", password="clave-segura-123")
        cls.cliente = Cliente.objects.create(razon_social="Cliente SA")
        cls.servicio = TipoServicio.objects.create(nombre="Desinsectación", slug="d")
        cls.otro_servicio = TipoServicio.objects.create(nombre="Roedores", slug="r")
        cls.hoy = timezone.localdate()

    def sitio(self, nombre="Planta", cliente=None, **campos):
        campos.setdefault("latitud", Decimal("-35.100000"))
        campos.setdefault("longitud", Decimal("-57.700000"))
        return Sitio.objects.create(
            cliente=cliente or self.cliente, nombre=nombre, **campos
        )

    def punto(self, sitio, dias, servicio=None, **campos):
        """Punto del sitio que vence dentro de `dias` días (`None`: sin programar)."""
        vence = None if dias is None else self.hoy + timedelta(days=dias)
        return PuntoControl.objects.create(
            sitio=sitio,
            nombre=f"Punto {sitio.nombre} {dias}",
            servicio=servicio,
            proximo_vencimiento=vence,
            **campos,
        )

    def datos(self, **filtros):
        self.client.force_login(self.admin)
        respuesta = self.client.get(DATOS, filtros)
        self.assertEqual(respuesta.status_code, 200)
        return {s["nombre"]: s for s in respuesta.json()["sitios"]}

    def test_muestra_atribucion_osm(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/panel/mapa/")

        self.assertContains(respuesta, "colaboradores de OpenStreetMap")
        self.assertContains(respuesta, "https://www.openstreetmap.org/copyright")

    def test_color_es_peor_estado_de_puntos(self):
        sitio = self.sitio("Mezclado")
        self.punto(sitio, 60)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "sin_programar")
        PuntoControl.objects.filter(sitio=sitio, proximo_vencimiento=None).update(
            activo=False
        )
        self.assertEqual(self.datos()["Mezclado"]["estado"], "al_dia")
        self.punto(sitio, 3)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "proxima")
        self.punto(sitio, -1)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "vencida")
        self.assertEqual(set(self.datos(estado="vencida")), {"Mezclado"})
        self.assertEqual(set(self.datos(estado="al_dia")), set())
        self.punto(sitio, None)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "vencida")
        PuntoControl.objects.filter(sitio=sitio).update(activo=False)
        self.assertEqual(self.datos()["Mezclado"]["estado"], "sin_programar")
        self.assertEqual(set(self.datos(estado="sin_programar")), {"Mezclado"})

    def test_datos_lista_sitios_activos_con_coordenadas(self):
        mezclado = self.sitio("Mezclado")
        self.punto(mezclado, 60)
        self.punto(mezclado, -1)
        self.sitio("SinProgramar")
        self.sitio("Inactivo", activo=False)
        self.sitio("SinCoordenadas", latitud=None, longitud=None)

        sitios = self.datos()

        self.assertEqual(
            {n: s["estado"] for n, s in sitios.items()},
            {"Mezclado": "vencida", "SinProgramar": "sin_programar"},
        )
        self.assertEqual(sitios["Mezclado"]["lat"], -35.1)
        self.assertEqual(sitios["Mezclado"]["lng"], -57.7)
        self.assertEqual(sitios["Mezclado"]["cliente"], "Cliente SA")
        self.assertIsNone(sitios["SinProgramar"]["vencimiento"])

    def test_datos_incluye_vencimiento_mas_cercano_y_enlaces(self):
        sitio = self.sitio()
        self.punto(sitio, 30)
        self.punto(sitio, 5)
        inactivo = self.punto(sitio, -9)
        PuntoControl.objects.filter(pk=inactivo.pk).update(activo=False)

        sitio_json = self.datos()["Planta"]

        self.assertEqual(
            sitio_json["vencimiento"], (self.hoy + timedelta(days=5)).isoformat()
        )
        self.assertEqual(sitio_json["url_ficha"], f"/panel/sitios/{sitio.pk}/")
        self.assertEqual(
            sitio_json["url_nuevo_turno"],
            f"/panel/visitas/sitios/{sitio.pk}/turnos/nuevo/",
        )

    def test_datos_filtra_por_cliente_servicio_y_estado(self):
        otro = Cliente.objects.create(razon_social="Otro SA")
        a = self.sitio("A")
        self.punto(a, -1, servicio=self.servicio)
        b = self.sitio("B", cliente=otro)
        self.punto(b, 60, servicio=self.otro_servicio)

        self.assertEqual(set(self.datos(cliente=otro.pk)), {"B"})
        self.assertEqual(set(self.datos(servicio=self.otro_servicio.pk)), {"B"})
        self.assertEqual(set(self.datos(servicio=self.servicio.pk)), {"A"})
        self.assertEqual(set(self.datos(estado="vencida")), {"A"})
        self.assertEqual(set(self.datos(estado="sin_programar")), {"B"})
        self.assertEqual(set(self.datos(estado="no_existe", cliente="x")), {"A", "B"})

    def test_datos_exige_administrador(self):
        self.assertEqual(self.client.get(DATOS).status_code, 302)
        self.assertEqual(self.client.get("/panel/mapa/").status_code, 302)
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(DATOS).status_code, 403)
        self.assertEqual(self.client.get("/panel/mapa/").status_code, 403)

    def test_datos_consultas_constantes(self):
        def consultas():
            self.client.force_login(self.admin)
            with self.assertNumQueries(4):
                # sesión, usuario, sitios y los puntos de `resumen_de_sitios`
                self.client.get(DATOS)

        self.punto(self.sitio("Uno"), 1)
        consultas()
        for n in range(5):
            otro = self.sitio(f"Sitio {n}")
            self.punto(otro, n)
            self.punto(otro, None)
        consultas()

    def test_mapa_permite_teselas_osm_en_csp(self):
        self.client.force_login(self.admin)
        politica = self.client.get("/panel/mapa/").headers["Content-Security-Policy"]
        img = next(d for d in politica.split(";") if d.strip().startswith("img-src"))
        self.assertIn(ORIGEN_TESELAS, img)
        # Las demás páginas del panel no reciben el origen de teselas.
        politica = self.client.get("/panel/").headers["Content-Security-Policy"]
        self.assertNotIn(ORIGEN_TESELAS, politica)

    def test_datos_del_mapa_sin_csp_de_teselas(self):
        self.client.force_login(self.admin)
        politica = self.client.get(DATOS).headers["Content-Security-Policy"]
        self.assertNotIn(ORIGEN_TESELAS, politica)

    def _sitios_con_filtro(self, valor):
        respuesta = self.client.get(DATOS, {"cliente": valor, "servicio": valor})
        self.assertEqual(respuesta.status_code, 200)
        return [s["nombre"] for s in respuesta.json()["sitios"]]

    def test_filtro_numerico_no_ascii_no_da_500(self):
        self.sitio("Uno")
        self.client.force_login(self.admin)
        for valor in ("\u00b2", "\u0663", "\uff11\uff12"):  # isdigit() sí, ASCII no
            with self.subTest(valor=valor):
                self.assertIn("Uno", self._sitios_con_filtro(valor))

    def test_filtro_numerico_fuera_de_rango_no_da_500(self):
        self.sitio("Uno")
        self.client.force_login(self.admin)
        for valor in ("9" * 5000, "9" * 20, str(2**63), "0" * 30 + "1"):
            with self.subTest(largo=len(valor)):
                self.assertIn("Uno", self._sitios_con_filtro(valor))
        # El máximo de BigAutoField sigue siendo un filtro válido (no hay cliente así).
        self.assertEqual(self._sitios_con_filtro(str(2**63 - 1)), [])

    def test_mapa_carga_leaflet_y_el_script_propio(self):
        self.client.force_login(self.admin)
        html = self.client.get("/panel/mapa/").content.decode()
        self.assertIn("vendor/leaflet/leaflet.js", html)
        self.assertIn("panel/mapa.js", html)
