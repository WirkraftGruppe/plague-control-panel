"""Acceso al panel: login, roles y salida."""

import re
import shutil
import tempfile
from io import BytesIO

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import URLResolver, get_resolver
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.panel import urls
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla, TipoServicio
from apps.sitios.models import Plano, PuntoControl, Sitio
from apps.visitas.models import Foto, Revision, Visita

CLAVE = "clave-segura-123"
SENTINELA = "@PK@"
SENTINELA_UUID = "@UUID@"
UUID_VALIDO = "00000000-0000-0000-0000-000000000001"

# Igual para las rutas con uuid: prefijo de ruta -> clave del código real.
UUID_POR_RUTA = ((r"^/panel/visitas/fotos/@UUID@/", "foto"),)

# Prefijo de ruta (con `@PK@` donde va el id) -> clave del objeto real. El orden
# importa: gana la primera coincidencia, por eso van antes las más específicas.
MODELO_POR_RUTA = (
    (r"^/panel/sitios/planos/@PK@/", "plano"),
    (r"^/panel/sitios/puntos/@PK@/", "punto"),
    (r"^/panel/sitios/@PK@/", "sitio"),
    (r"^/panel/clientes/@PK@/", "cliente"),
    (r"^/panel/servicios/campos/@PK@/", "campo"),
    (r"^/panel/servicios/@PK@/", "servicio"),
    (r"^/panel/proyectos/@PK@/", "proyecto"),
    (r"^/panel/productos/@PK@/", "producto"),
    (r"^/panel/visitas/proyectos/@PK@/", "proyecto"),
    (r"^/panel/visitas/@PK@/", "visita"),
    (r"^/panel/usuarios/@PK@/", "usuario"),
)


class AccesoPanelTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user(
            "adm", password=CLAVE, rol=User.Rol.ADMINISTRADOR
        )
        self.empleado = User.objects.create_user("emp", password=CLAVE)

    def test_anonimo_redirige_al_login(self):
        respuesta = self.client.get("/panel/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/?next=/panel/", fetch_redirect_response=False
        )

    def test_empleado_recibe_403(self):
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get("/panel/").status_code, 403)

    def test_administrador_recibe_200(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/panel/").status_code, 200)

    def test_administrador_inicia_sesion_y_entra(self):
        respuesta = self.client.post(
            "/panel/ingresar/", {"username": "adm", "password": CLAVE}
        )
        self.assertRedirects(respuesta, "/panel/", fetch_redirect_response=False)

    def test_empleado_no_inicia_sesion_en_el_panel(self):
        respuesta = self.client.post(
            "/panel/ingresar/", {"username": "emp", "password": CLAVE}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Esta cuenta no tiene acceso al panel.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_salir_cierra_la_sesion(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post("/panel/salir/")
        self.assertRedirects(
            respuesta, "/panel/ingresar/", fetch_redirect_response=False
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get("/panel/salir/").status_code, 405)

    def _ingresar(self, usuario, clave):
        return self.client.post(
            "/panel/ingresar/", {"username": usuario, "password": clave}
        )

    def test_ingreso_limita_intentos_fallidos(self):
        codigos = [self._ingresar("adm", "mala").status_code for _ in range(6)]
        self.assertEqual(codigos[:5], [200] * 5)
        self.assertEqual(codigos[5], 429)
        self.assertEqual(self._ingresar("adm", CLAVE).status_code, 429)

    def test_ingreso_limitado_no_confirma_clave_de_empleado(self):
        for _ in range(5):
            self._ingresar("emp", "mala")
        respuesta = self._ingresar("emp", CLAVE)
        self.assertEqual(respuesta.status_code, 429)
        self.assertNotContains(respuesta, "no tiene acceso", status_code=429)


def _rutas_del_panel(patrones, prefijo="", pk="1", codigo=UUID_VALIDO):
    """Recorre los patrones del namespace `panel` y arma una URL de ejemplo por ruta."""
    for patron in patrones:
        texto = prefijo + str(patron.pattern)
        if isinstance(patron, URLResolver):
            yield from _rutas_del_panel(patron.url_patterns, texto, pk, codigo)
        else:
            ruta = re.sub(r"<(?:uuid:)\w+>", codigo, texto)
            yield "/panel/" + re.sub(r"<(?:\w+:)?\w+>", pk, ruta)


def _rutas_protegidas(pk="1", codigo=UUID_VALIDO):
    """Todas las rutas del panel salvo ingresar y salir, con `pk` y uuid de ejemplo."""
    return [
        ruta
        for ruta in _rutas_del_panel(
            get_resolver(urls).url_patterns, pk=pk, codigo=codigo
        )
        if ruta not in ("/panel/ingresar/", "/panel/salir/")
    ]


def _imagen(nombre):
    """Imagen PNG mínima y válida, lista para guardar en un campo de imagen."""
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, "PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


class AccesoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """Los archivos de `setUpTestData` van a un MEDIA_ROOT temporal."""
        media = tempfile.mkdtemp(prefix="acceso-panel-test-")
        cls.addClassCleanup(shutil.rmtree, media, ignore_errors=True)
        cls.enterClassContext(override_settings(MEDIA_ROOT=media))
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        """Un objeto real de cada modelo al que apuntan las rutas con id."""
        cls.cliente = Cliente.objects.create(razon_social="Cliente SA")
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta")
        cls.servicio = TipoServicio.objects.create(nombre="Desinsectación", slug="d")
        cls.empleado = User.objects.create_user("emp", password=CLAVE)
        cls.proyecto = Proyecto.objects.create(
            sitio=cls.sitio,
            tipo_servicio=cls.servicio,
            titulo="Proyecto",
            encargado_inicial=cls.empleado,
            encargado_actual=cls.empleado,
        )
        visita = Visita.objects.create(
            proyecto=cls.proyecto, empleado=cls.empleado, origen=Visita.Origen.APP
        )
        punto = PuntoControl.objects.get(sitio=cls.sitio, orden=0)
        revision = Revision.objects.create(
            visita=visita,
            punto=punto,
            orden=1,
            realizada_en=visita.creado,
            recibida_en=visita.creado,
        )
        foto = Foto.objects.create(revision=revision, imagen=_imagen("foto.png"))
        cls.ids = {
            "cliente": cls.cliente.pk,
            "sitio": cls.sitio.pk,
            "servicio": cls.servicio.pk,
            "proyecto": cls.proyecto.pk,
            "usuario": cls.empleado.pk,
            "visita": visita.pk,
            "punto": punto.pk,
            "plano": Plano.objects.create(
                sitio=cls.sitio, nombre="Plano", imagen=_imagen("plano.png")
            ).pk,
            "campo": CampoPlanilla.objects.create(
                tipo_servicio=cls.servicio,
                orden=1,
                etiqueta="Dato",
                clave="dato",
                tipo=CampoPlanilla.Tipo.TEXTO,
            ).pk,
            "producto": Producto.objects.create(nombre_comercial="Producto").pk,
        }
        cls.codigos = {"foto": str(foto.codigo)}

    def test_empleado_no_ve_ninguna_ruta_del_panel(self):
        self.client.login(username="emp", password=CLAVE)
        rutas = _rutas_protegidas()

        self.assertIn("/panel/", rutas)
        self.assertIn("/panel/mapa/", rutas)
        self.assertIn("/panel/mapa/datos/", rutas)
        for app in ("sitios", "clientes", "servicios", "proyectos", "productos"):
            self.assertIn(f"/panel/{app}/", rutas)
        self.assertIn("/panel/usuarios/", rutas)
        # GET y POST, con un pk existente y con uno inexistente: el rol se comprueba
        # antes de buscar el objeto, así la respuesta no revela qué ids existen.
        for ruta in rutas + _rutas_protegidas(pk="999999"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 403)
                self.assertEqual(self.client.post(ruta).status_code, 403)

    def _rutas_con_objetos_reales(self):
        """Cada ruta con el id (o uuid) de un objeto real de su propio modelo.

        Falla si aparece una ruta con parámetros que `MODELO_POR_RUTA` no cubre:
        una ruta nueva no puede quedar sin probar en silencio.
        """
        rutas = []
        for ruta in _rutas_protegidas(pk=SENTINELA, codigo=SENTINELA_UUID):
            if SENTINELA_UUID in ruta:
                clave = next((c for p, c in UUID_POR_RUTA if re.match(p, ruta)), None)
                if clave is None:
                    self.fail(f"Ruta con uuid sin objeto real en el test: {ruta}")
                rutas.append(ruta.replace(SENTINELA_UUID, self.codigos[clave]))
            elif SENTINELA in ruta:
                clave = next(
                    (c for patron, c in MODELO_POR_RUTA if re.match(patron, ruta)),
                    None,
                )
                if clave is None:
                    self.fail(f"Ruta con parámetros sin objeto real en el test: {ruta}")
                rutas.append(ruta.replace(SENTINELA, str(self.ids[clave])))
            elif "<" in ruta or "{" in ruta:
                self.fail(f"Ruta con parámetro sin resolver: {ruta}")
            else:
                rutas.append(ruta)
        return rutas

    def test_empleado_no_ve_rutas_con_objetos_reales(self):
        self.client.login(username="emp", password=CLAVE)
        rutas = self._rutas_con_objetos_reales()
        self.assertGreater(len(rutas), 30)
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 403)
                self.assertEqual(self.client.post(ruta).status_code, 403)

    def test_anonimo_post_va_al_login(self):
        for ruta in self._rutas_con_objetos_reales():
            with self.subTest(ruta=ruta):
                respuesta = self.client.post(ruta)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta["Location"].startswith("/panel/ingresar/"))

    def test_anonimo_va_al_login_en_todas_las_rutas(self):
        for ruta in _rutas_protegidas() + _rutas_protegidas(pk="999999"):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(ruta)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta["Location"].startswith("/panel/ingresar/"))
