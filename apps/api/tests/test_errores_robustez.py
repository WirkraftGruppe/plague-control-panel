"""Errores de la API: rutas anidadas, `__all__`, `Retry-After` y 404 JSON."""

import json

from django.core.cache import cache
from django.core.exceptions import ValidationError as ErrorDjango
from django.http import Http404
from django.test import RequestFactory, TestCase
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.api.excepciones import manejar_excepcion
from apps.api.views import no_encontrado
from apps.empresas.tests.ayudas import una_empresa


class ErroresRobustezTests(TestCase):
    def test_non_field_errors_anidado_conserva_ruta(self):
        class Producto(serializers.Serializer):
            dosis = serializers.FloatField()

            def validate(self, attrs):
                raise serializers.ValidationError("Producto repetido.")

        class Visita(serializers.Serializer):
            productos_aplicados = Producto(many=True)

        serializador = Visita(data={"productos_aplicados": [{"dosis": 1}]})
        self.assertFalse(serializador.is_valid())
        respuesta = manejar_excepcion(ValidationError(serializador.errors), {})
        self.assertEqual(
            respuesta.data["campos"], {"productos_aplicados.0": ["Producto repetido."]}
        )
        self.assertNotIn("ErrorDetail", str(respuesta.data))

    def test_non_field_errors_de_primer_nivel_sigue_en_detalle(self):
        respuesta = manejar_excepcion(
            ValidationError({"non_field_errors": ["Mal."]}), {}
        )
        self.assertEqual(respuesta.data, {"detalle": "Mal.", "campos": {}})

    def test_all_de_django_va_a_detalle(self):
        error = ErrorDjango({"__all__": ["Combinación mala."]})
        respuesta = manejar_excepcion(error, {})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.data["detalle"], "Combinación mala.")
        self.assertEqual(respuesta.data["campos"], {})

    def test_429_del_balde_lleva_retry_after(self):
        cache.clear()
        self.addCleanup(cache.clear)
        User.objects.create_user(
            "emp", password="clave-segura-123", empresa=una_empresa()
        )
        datos = {"username": "emp", "password": "mala"}
        for _ in range(5):
            self.client.post(
                "/api/v1/auth/token/", datos, content_type="application/json"
            )
        respuesta = self.client.post(
            "/api/v1/auth/token/", datos, content_type="application/json"
        )
        self.assertEqual(respuesta.status_code, 429)
        self.assertGreaterEqual(int(respuesta["Retry-After"]), 1)

    def test_no_encontrado_bajo_api_devuelve_json(self):
        fabrica = RequestFactory()
        respuesta = no_encontrado(fabrica.get("/api/v1/nada/"), Http404())
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertEqual(
            json.loads(respuesta.content), {"detalle": "No encontrado.", "campos": {}}
        )
        otra = no_encontrado(fabrica.get("/otra/"), Http404())
        self.assertEqual(otra.status_code, 404)
        self.assertIn("text/html", otra["Content-Type"])
