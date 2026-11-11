"""Aislamiento entre empresas en la API: lo de A no se ve ni se toca desde B."""

import re
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import get_resolver, resolve
from rest_framework.test import APIClient

from apps.sitios.tests.ayudas_empresa import plano_de
from apps.visitas.models import Visita
from apps.visitas.tests.ayudas_empresa import crear_foto, dos_empresas

SENTINELA = "@PK@"
SENTINELA_UUID = "@UUID@"
UUID_VALIDO = "00000000-0000-0000-0000-000000000001"

# Prefijo de ruta (con `@PK@` o `@UUID@` donde va el identificador) -> clave del
# objeto real de la empresa A. Una ruta con parámetro que no esté acá hace fallar
# el recorrido: una ruta nueva no puede quedar sin probar en silencio. Las rutas que
# reciben el `qr_codigo` en el cuerpo (`/visitas/abrir/`, `/revisiones/`) las cubren
# los tests de 400 de visitas.
OBJETO_POR_RUTA = (
    (r"^/api/v1/qr/@UUID@/resolver/", "qr"),
    (r"^/api/v1/planos/@PK@/imagen/", "plano"),
    (r"^/api/v1/sitios/@PK@/puntos/", "sitio"),
    (r"^/api/v1/puntos/@PK@/ubicacion/", "punto"),
    (r"^/api/v1/visitas/@PK@/cerrar/", "visita"),
    (r"^/api/v1/fotos/@UUID@/", "foto"),
)


def _rutas_con_parametro():
    """Rutas de `get_resolver()` bajo `/api/v1/` con identificador en la URL."""

    def recorrer(patrones, prefijo):
        for patron in patrones:
            ruta = prefijo + str(patron.pattern)
            if hasattr(patron, "url_patterns"):
                yield from recorrer(patron.url_patterns, ruta)
            else:
                yield ruta

    for ruta in recorrer(get_resolver().url_patterns, "/"):
        if ruta.startswith("/api/v1/") and "<" in ruta:
            ruta = re.sub(r"<uuid:\w+>", SENTINELA_UUID, ruta)
            yield re.sub(r"<(?:\w+:)?\w+>", SENTINELA, ruta)


def _usuarios_que_pasan_el_permiso(clase, usuarios):
    """Los usuarios que el permiso de la vista deja pasar (sin mirar el objeto)."""
    permisos = [permiso() for permiso in clase.permission_classes]
    return [
        usuario
        for usuario in usuarios
        if all(
            permiso.has_permission(SimpleNamespace(user=usuario), None)
            for permiso in permisos
        )
    ]


class AislamientoApiTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """Las fotos y los planos de `setUpTestData` van a un MEDIA_ROOT temporal."""
        media = tempfile.mkdtemp(prefix="aislamiento-api-")
        cls.addClassCleanup(shutil.rmtree, media, ignore_errors=True)
        cls.enterClassContext(override_settings(MEDIA_ROOT=media))
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.a, cls.b = dos_empresas()
        plano = plano_de(cls.a.sitio, "Plano A")
        cls.ids = {
            "sitio": cls.a.sitio.pk,
            "punto": cls.a.punto.pk,
            "visita": cls.a.visita.pk,
            "plano": plano.pk,
        }
        cls.codigos = {
            "qr": str(cls.a.punto.qr_codigo),
            "foto": str(crear_foto(cls.a).codigo),
        }

    def _rutas_con_objetos_reales(self):
        """Cada ruta con parámetro, con el id o uuid de un objeto real de A.

        Falla si aparece una ruta con parámetro que `OBJETO_POR_RUTA` no cubre.
        """
        rutas = []
        for ruta in _rutas_con_parametro():
            clave = next(
                (c for patron, c in OBJETO_POR_RUTA if re.match(patron, ruta)), None
            )
            if clave is None:
                self.fail(f"Ruta con parámetro sin objeto real en el test: {ruta}")
            valor = self.codigos[clave] if clave in self.codigos else self.ids[clave]
            sentinela = SENTINELA_UUID if clave in self.codigos else SENTINELA
            rutas.append(ruta.replace(sentinela, str(valor)))
        return rutas

    def test_rutas_con_objeto_de_otra_empresa_dan_404(self):
        rutas = self._rutas_con_objetos_reales()
        self.assertEqual(len(rutas), len(OBJETO_POR_RUTA))
        for ruta in rutas:
            vista = resolve(ruta).func.view_class
            usuarios = _usuarios_que_pasan_el_permiso(
                vista, [self.b.admin, self.b.empleado]
            )
            self.assertTrue(usuarios, f"Ningún usuario de B pasa el permiso de {ruta}")
            # `OPTIONS` responde 200 sin buscar el objeto y los métodos que la vista
            # no acepta dan 405 antes de resolverlo: ninguno prueba el aislamiento.
            metodos = [m.lower() for m in vista()._allowed_methods() if m != "OPTIONS"]
            self.assertTrue(metodos, ruta)
            for usuario in usuarios:
                cliente = APIClient()
                cliente.force_authenticate(usuario)
                for metodo in metodos:
                    with self.subTest(ruta=ruta, usuario=usuario.username, m=metodo):
                        respuesta = getattr(cliente, metodo)(ruta)
                        self.assertEqual(respuesta.status_code, 404)

    def test_ruta_sin_objeto_en_el_mapa_hace_fallar_el_recorrido(self):
        with mock.patch(f"{__name__}.OBJETO_POR_RUTA", ()):
            with self.assertRaisesMessage(
                AssertionError, "Ruta con parámetro sin objeto real en el test"
            ):
                self._rutas_con_objetos_reales()

    def test_listados_de_la_api_solo_de_la_empresa(self):
        esperado = {}
        for nombre, lado in (("a", self.a), ("b", self.b)):
            pendiente = Visita.objects.create(
                sitio=lado.sitio,
                empleado=lado.empleado,
                origen=Visita.Origen.APP,
                estado=Visita.Estado.PENDIENTE,
            )
            esperado[nombre] = {
                "/api/v1/me/visitas/": {lado.visita.pk, pendiente.pk},
                "/api/v1/me/puntos/": {lado.punto.pk},
                "/api/v1/productos/": {lado.producto.pk},
            }
        for nombre, lado in (("a", self.a), ("b", self.b)):
            for usuario in (lado.admin, lado.empleado):
                cliente = APIClient()
                cliente.force_authenticate(usuario)
                for ruta, propios in esperado[nombre].items():
                    with self.subTest(usuario=usuario.username, ruta=ruta):
                        respuesta = cliente.get(ruta)
                        self.assertEqual(respuesta.status_code, 200)
                        datos = respuesta.json()
                        filas = datos["results"] if "results" in datos else datos
                        ids = {fila["id"] for fila in filas}
                        # Nunca una fila de la otra empresa; y la propia, solo la
                        # de este usuario (el listado "me" del administrador la
                        # trae vacía si no tiene visitas propias).
                        ajenos = set().union(
                            *(
                                filas_otra[ruta]
                                for otra, filas_otra in esperado.items()
                                if otra != nombre
                            )
                        )
                        self.assertFalse(ids & ajenos)
                        self.assertLessEqual(ids, propios)
                        if usuario == lado.empleado or ruta.endswith("productos/"):
                            self.assertEqual(ids, propios)
