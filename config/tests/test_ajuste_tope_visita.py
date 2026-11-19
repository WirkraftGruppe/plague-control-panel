"""Ajuste `VISITA_ABIERTA_TOPE_HORAS`: tope absoluto del cierre nocturno."""

import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import base


class AjusteTopeVisitaTests(SimpleTestCase):
    def test_default_36_y_rango_1_a_8760(self):
        nombre = "VISITA_ABIERTA_TOPE_HORAS"
        entorno = {k: v for k, v in os.environ.items() if k != nombre}
        with mock.patch.dict(os.environ, entorno, clear=True):
            self.assertEqual(base.leer_horas(nombre, "36"), 36)

        for valor in ("1", "8760"):
            with mock.patch.dict(os.environ, {nombre: valor}):
                self.assertEqual(base.leer_horas(nombre, "36"), int(valor))

        for valor in ("0", "8761", "abc", ""):
            with mock.patch.dict(os.environ, {nombre: valor}):
                with self.assertRaisesMessage(ImproperlyConfigured, nombre):
                    base.leer_horas(nombre, "36")

        self.assertEqual(settings.VISITA_ABIERTA_TOPE_HORAS, 36)
        self.assertEqual(settings.VISITA_ABIERTA_MAXIMO_HORAS, 16)

    def test_tope_menor_que_el_maximo_falla(self):
        mensaje = "VISITA_ABIERTA_TOPE_HORAS"
        with self.assertRaisesMessage(ImproperlyConfigured, mensaje):
            base.validar_tope_visita(15, 16)
        base.validar_tope_visita(16, 16)
        base.validar_tope_visita(36, 16)
