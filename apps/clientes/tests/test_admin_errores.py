"""Admin del operador: el error de un campo ausente es error de formulario."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.pruebas import crear_plataforma
from apps.servicios.models import TipoServicio
from apps.sitios.models import PuntoControl
from apps.sitios.tests.ayudas_empresa import DatosDeDosEmpresas


def _datos_del_formulario(formulario):
    """Valores actuales de los campos del formulario, como los enviaría el navegador."""
    datos = {}
    for nombre, campo in formulario.fields.items():
        valor = formulario.initial.get(nombre, campo.initial)
        if valor in (None, False):
            continue
        datos[nombre] = valor.pk if hasattr(valor, "pk") else valor
    return datos


class AdminErroresTests(DatosDeDosEmpresas, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.crear_empresas(cls)
        cls.plataforma = crear_plataforma()

    def setUp(self):
        self.client.force_login(self.plataforma)

    def _enviar(self, nombre_url, objeto, **cambios):
        url = reverse(f"admin:{nombre_url}_change", args=[objeto.pk])
        formulario = self.client.get(url).context["adminform"].form
        datos = _datos_del_formulario(formulario)
        datos.update(cambios)
        return self.client.post(url, datos)

    def test_padre_de_otra_empresa_da_error_de_formulario(self):
        PuntoControl.todos.filter(pk=self.punto_a.pk).update(sitio=self.sitio_b)
        punto = PuntoControl.todos.get(pk=self.punto_a.pk)
        respuesta = self._enviar("sitios_puntocontrol", punto, nombre="Otro nombre")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Pertenece a otra empresa.")

    def test_slug_repetido_en_la_empresa_da_error_de_formulario(self):
        otro = TipoServicio.objects.create(nombre="Otro", empresa=self.empresa_a)
        respuesta = self._enviar(
            "servicios_tiposervicio", otro, slug=self.servicio_a.slug
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["adminform"].form.errors)
        otro.refresh_from_db()
        self.assertNotEqual(otro.slug, self.servicio_a.slug)

    def test_referencia_plataforma_de_solo_lectura_da_error_de_formulario(self):
        PuntoControl.todos.filter(pk=self.punto_a.pk).update(
            ubicacion_fijada_por=self.plataforma
        )
        punto = PuntoControl.todos.get(pk=self.punto_a.pk)
        respuesta = self._enviar("sitios_puntocontrol", punto, nombre="Otro nombre")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Pertenece a otra empresa.")
