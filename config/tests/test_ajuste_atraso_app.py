"""Ajuste `ATRASO_MAXIMO_APP_HORAS`: atraso máximo de lo que manda la app sin conexión."""

import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import base


class AjusteAtrasoAppTests(SimpleTestCase):
    def test_default_72_y_rango_1_a_8760(self):
        entorno = {
            k: v for k, v in os.environ.items() if k != "ATRASO_MAXIMO_APP_HORAS"
        }
        with mock.patch.dict(os.environ, entorno, clear=True):
            self.assertEqual(base.leer_horas("ATRASO_MAXIMO_APP_HORAS", "72"), 72)

        for valor in ("1", "8760"):
            with mock.patch.dict(os.environ, {"ATRASO_MAXIMO_APP_HORAS": valor}):
                self.assertEqual(
                    base.leer_horas("ATRASO_MAXIMO_APP_HORAS", "72"), int(valor)
                )

        for valor in ("0", "8761", "-5", "abc", "1.5", ""):
            with mock.patch.dict(os.environ, {"ATRASO_MAXIMO_APP_HORAS": valor}):
                with self.assertRaisesMessage(
                    ImproperlyConfigured, "ATRASO_MAXIMO_APP_HORAS"
                ):
                    base.leer_horas("ATRASO_MAXIMO_APP_HORAS", "72")

        # La carga manual sigue con su propio límite, independiente del de la app.
        self.assertEqual(settings.ATRASO_MAXIMO_APP_HORAS, 72)
        self.assertEqual(settings.ATRASO_MAXIMO_HORAS, 168)
