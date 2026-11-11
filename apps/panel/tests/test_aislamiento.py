"""Aislamiento entre empresas en el panel: un administrador de B no toca objetos de A.

Reutiliza el mapa ruta -> objeto real de `AccesoTests`: los objetos están en la
empresa A y se recorren con el administrador de la empresa B.
"""

from unittest import mock

from django.urls import resolve

from apps.accounts.models import User
from apps.empresas.models import Empresa
from apps.panel.tests import test_acceso
from apps.panel.tests.test_acceso import CLAVE, AccesoTests

# Sin GET/POST propios, las vistas de función se prueban con estos dos métodos.
METODOS_DE_FUNCION = ("get", "post")


def metodos_de_la_vista(ruta):
    """Métodos HTTP que la vista de la ruta implementa, sin OPTIONS.

    `OPTIONS` responde 200 con `Allow` sin buscar el objeto, y los métodos que la
    vista no acepta dan 405 antes de resolverlo: ninguno prueba el aislamiento.
    """
    clase = getattr(resolve(ruta).func, "view_class", None)
    if clase is None:
        return METODOS_DE_FUNCION
    return tuple(
        metodo.lower() for metodo in clase()._allowed_methods() if metodo != "OPTIONS"
    )


class AislamientoPanelTests(AccesoTests):
    """Con `AccesoTests` de base se heredan sus datos; sus tests no se repiten."""

    for _nombre in dir(AccesoTests):
        if _nombre.startswith("test_"):
            locals()[_nombre] = None
    del _nombre

    def setUp(self):
        empresa_b = Empresa.objects.create(nombre="Empresa B")
        self.admin_b = User.objects.create_user(
            "adm-b",
            password=CLAVE,
            rol=User.Rol.ADMINISTRADOR,
            empresa=empresa_b,
        )

    def _rutas_con_identificador(self):
        """Las rutas con id o uuid, ya con el objeto real de la empresa A."""
        plantillas = test_acceso._rutas_protegidas(
            pk=test_acceso.SENTINELA, codigo=test_acceso.SENTINELA_UUID
        )
        reales = self._rutas_con_objetos_reales()
        return [
            real
            for plantilla, real in zip(plantillas, reales, strict=True)
            if test_acceso.SENTINELA in plantilla
            or test_acceso.SENTINELA_UUID in plantilla
        ]

    def test_rutas_con_objeto_de_otra_empresa_dan_404(self):
        self.client.force_login(self.admin_b)
        rutas = self._rutas_con_identificador()
        self.assertGreater(len(rutas), 30)
        for ruta in rutas:
            metodos = metodos_de_la_vista(ruta)
            self.assertTrue(metodos, ruta)
            for metodo in metodos:
                with self.subTest(ruta=ruta, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(ruta)
                    self.assertEqual(respuesta.status_code, 404)

    def test_ruta_sin_objeto_en_el_mapa_hace_fallar_el_recorrido(self):
        with mock.patch.object(test_acceso, "MODELO_POR_RUTA", ()):
            with self.assertRaisesMessage(
                AssertionError, "Ruta con parámetros sin objeto real en el test"
            ):
                self._rutas_con_objetos_reales()
        with mock.patch.object(test_acceso, "UUID_POR_RUTA", ()):
            with self.assertRaisesMessage(
                AssertionError, "Ruta con uuid sin objeto real en el test"
            ):
                self._rutas_con_objetos_reales()
