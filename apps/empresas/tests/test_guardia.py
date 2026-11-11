"""La guardia cubre todos los modelos de empresa y el panel y la API no la evitan."""

import re
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import TestCase

from apps.empresas.consultas import ConsultaSinEmpresa
from apps.empresas.models import ModeloDeEmpresa

# Archivos de las apps de dominio donde `.todos` (el manager sin guardia) no va.
ARCHIVOS_SIN_TODOS = (
    "panel_views.py",
    "api_views.py",
    "serializers.py",
    "panel_forms.py",
)
USO_DE_TODOS = re.compile(r"\.todos\b")


def _modelos_de_empresa():
    return [
        modelo
        for modelo in apps.get_models()
        if issubclass(modelo, ModeloDeEmpresa) and not modelo._meta.abstract
    ]


def _archivos_sin_todos():
    """Código de producción del panel y la API: ningún `.todos` permitido."""
    raiz = Path(settings.BASE_DIR) / "apps"
    archivos = set()
    for ruta in raiz.rglob("*.py"):
        relativa = ruta.relative_to(raiz)
        if "tests" in relativa.parts:
            continue
        if (
            ruta.name in ARCHIVOS_SIN_TODOS
            or "templatetags" in relativa.parts
            or relativa.parts[0] in ("panel", "api")
        ):
            archivos.add(ruta)
    return sorted(archivos)


class GuardiaModelosTests(TestCase):
    def test_objects_all_sin_empresa_lanza_en_todos_los_modelos(self):
        modelos = _modelos_de_empresa()
        # Los 13 modelos de empresa (`User` queda fuera de la guardia): si aparece
        # uno nuevo, entra solo en el recorrido.
        self.assertGreaterEqual(len(modelos), 13)
        for modelo in modelos:
            with self.subTest(modelo=modelo.__name__):
                with self.assertRaises(ConsultaSinEmpresa):
                    list(modelo.objects.all())
                self.assertEqual(modelo._default_manager.name, "objects")

    def test_panel_y_api_no_usan_el_manager_sin_filtro(self):
        archivos = _archivos_sin_todos()
        self.assertTrue(archivos)
        for ruta in archivos:
            texto = ruta.read_text(encoding="utf-8")
            with self.subTest(archivo=str(ruta.relative_to(settings.BASE_DIR))):
                self.assertIsNone(USO_DE_TODOS.search(texto))
