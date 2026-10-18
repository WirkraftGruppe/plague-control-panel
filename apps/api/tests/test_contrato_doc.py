"""`docs/contrato-api.md` describe exactamente las rutas que resuelve `/api/v1/`."""

import re
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import get_resolver

DOC = Path(__file__).resolve().parents[3] / "docs" / "contrato-api.md"
COLUMNAS = ["Método", "Ruta", "Auth", "Throttle", "Respuesta"]


def _filas_del_documento():
    """Filas de la tabla del contrato, como listas de celdas sin los bordes."""
    filas = []
    for linea in DOC.read_text(encoding="utf-8").splitlines():
        if linea.startswith("|"):
            filas.append([celda.strip() for celda in linea.strip("|").split("|")])
    return filas[2:]  # sin el encabezado ni la línea de guiones


def _rutas_de_la_api():
    """Rutas resueltas bajo `/api/v1/`, con `<int:pk>` normalizado a `<pk>`."""

    def recorrer(patrones, prefijo):
        for patron in patrones:
            ruta = prefijo + str(patron.pattern)
            if hasattr(patron, "url_patterns"):
                yield from recorrer(patron.url_patterns, ruta)
            else:
                yield ruta

    rutas = recorrer(get_resolver().url_patterns, "/")
    return {
        re.sub(r"<\w+:(\w+)>", r"<\1>", ruta)
        for ruta in rutas
        if ruta.startswith("/api/v1/")
    }


class ContratoDocTests(SimpleTestCase):
    def test_rutas_del_contrato_coinciden_con_las_de_la_api(self):
        en_documento = [fila[1].strip("`") for fila in _filas_del_documento()]
        self.assertEqual(len(en_documento), len(set(en_documento)))
        self.assertEqual(set(en_documento), _rutas_de_la_api())
        self.assertEqual(len(en_documento), 18)

    def test_cada_ruta_declara_metodo_auth_throttle_y_respuesta(self):
        filas = _filas_del_documento()
        self.assertTrue(filas)
        encabezado = DOC.read_text(encoding="utf-8")
        self.assertIn("| " + " | ".join(COLUMNAS) + " |", encabezado)
        self.assertRegex(encabezado, r"(?m)^Actualizado: \d{4}-\d{2}-\d{2}$")
        for fila in filas:
            self.assertEqual(len(fila), len(COLUMNAS), fila)
            for columna, celda in zip(COLUMNAS, fila):
                self.assertTrue(celda, f"{fila[1]}: celda vacía en {columna}")
            self.assertIn(fila[0], {"GET", "POST", "PUT", "PATCH", "DELETE"}, fila)
            self.assertRegex(fila[1], r"^`/api/v1/[^`]*`$")
