"""El arranque de Django no depende de WeasyPrint."""

import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

RAIZ = Path(__file__).resolve().parents[3]

CODIGO = """
import os
import sys

sys.modules["weasyprint"] = None
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

import config.urls  # noqa: F401
from django.core.management import call_command

call_command("check")
"""


class SinWeasyprintTests(SimpleTestCase):
    def test_check_pasa_con_weasyprint_bloqueado(self):
        resultado = subprocess.run(
            [sys.executable, "-c", CODIGO],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            resultado.returncode,
            0,
            f"check falló sin weasyprint:\n{resultado.stderr}",
        )
