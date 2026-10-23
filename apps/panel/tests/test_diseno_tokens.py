"""Tokens del sistema visual: valores del Adjunto y contraste mínimo de 4,5:1."""

import re
from pathlib import Path

from django.test import SimpleTestCase

RAIZ = Path(__file__).resolve().parents[3]
BASE = (RAIZ / "templates" / "base.html").read_text(encoding="utf-8")

ESPERADOS = {
    "bg": "#F5F6F7",
    "surface": "#FFFFFF",
    "surface-2": "#EEF0F2",
    "border": "#DFE2E6",
    "border-strong": "#C5CAD1",
    "text": "#1A1E23",
    "text-muted": "#545C66",
    "text-faint": "#646C76",
    "accion": "#1F5FD1",
    "accion-hover": "#174AA6",
    "sobre-accion": "#FFFFFF",
    "activo-fondo": "#EAF1FD",
    "activo-texto": "#1F5FD1",
    "vencido-punto": "#D92D20",
    "vencido-fondo": "#FDECEA",
    "vencido-texto": "#B42318",
    "proximo-punto": "#E0A100",
    "proximo-fondo": "#FFF4D6",
    "proximo-texto": "#7A4F00",
    "al-dia-punto": "#2E9E5B",
    "al-dia-fondo": "#E6F4EC",
    "al-dia-texto": "#1B6B3C",
    "sin-fecha-punto": "#9AA1A9",
    "sin-fecha-fondo": "#EEF0F2",
    "sin-fecha-texto": "#4A525B",
    "radio-control": "6px",
    "radio-bloque": "8px",
    "radio-chip": "999px",
    "ancho-barra": "232px",
}


def tokens():
    """Valores literales de las variables declaradas en base.html."""
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", BASE))


def _luz(color):
    canales = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineales = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales
    ]
    return 0.2126 * lineales[0] + 0.7152 * lineales[1] + 0.0722 * lineales[2]


def contraste(a, b):
    """Razón de contraste WCAG entre dos colores #RRGGBB."""
    claro, oscuro = sorted((_luz(a), _luz(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


class ContrasteTokensTests(SimpleTestCase):
    def _verificar(self, pares):
        valores = tokens()
        for texto, fondo in pares:
            with self.subTest(texto=texto, fondo=fondo):
                razon = contraste(valores[texto], valores[fondo])
                self.assertGreaterEqual(
                    razon, 4.5, f"{texto} sobre {fondo}: {razon:.2f}"
                )

    def test_tokens_del_adjunto_en_base(self):
        valores = tokens()
        for nombre, esperado in ESPERADOS.items():
            with self.subTest(token=nombre):
                self.assertEqual(valores.get(nombre), esperado)

    def test_textos_sobre_fondos_cumplen_4_5(self):
        self._verificar(
            (texto, fondo)
            for texto in ("text", "text-muted", "text-faint")
            for fondo in ("bg", "surface")
        )
        self._verificar([("text", "surface-2"), ("text-muted", "surface-2")])

    def test_chips_de_estado_cumplen_4_5(self):
        self._verificar(
            (f"{estado}-texto", f"{estado}-fondo")
            for estado in ("vencido", "proximo", "al-dia", "sin-fecha")
        )

    def test_accion_y_menu_activo_cumplen_4_5(self):
        self._verificar(
            [
                ("sobre-accion", "accion"),
                ("sobre-accion", "accion-hover"),
                ("sobre-accion", "vencido-texto"),
                ("accion", "surface"),
                ("accion", "bg"),
                ("accion-hover", "surface"),
                ("activo-texto", "activo-fondo"),
            ]
        )


class ListadosCssTests(SimpleTestCase):
    def test_buscador_tiene_ancho_minimo(self):
        css = (RAIZ / "static" / "css" / "panel.css").read_text(encoding="utf-8")
        regla = re.search(r"\.buscador input[^{,]*\{[^}]*min-width:\s*\d", css)
        self.assertIsNotNone(regla, "el campo del buscador necesita un min-width")
