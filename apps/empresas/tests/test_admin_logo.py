"""Admin de empresas: el logo pasa por `procesar_logo`."""

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from apps.accounts.pruebas import crear_plataforma
from apps.empresas.pruebas import crear_empresa


def _imagen(formato, lado):
    buffer = io.BytesIO()
    Image.new("RGB", (lado, lado), "red").save(buffer, formato)
    return buffer.getvalue()


class EmpresaAdminLogoTests(TestCase):
    def setUp(self):
        self.empresa = crear_empresa()
        self.client.force_login(crear_plataforma())
        self.url = reverse("admin:empresas_empresa_change", args=[self.empresa.pk])

    def _enviar(self, archivo):
        return self.client.post(
            self.url, {"nombre": self.empresa.nombre, "activo": "on", "logo": archivo}
        )

    def test_logo_del_admin_se_guarda_procesado(self):
        archivo = SimpleUploadedFile("grande.jpg", _imagen("JPEG", 1500))
        respuesta = self._enviar(archivo)
        self.assertEqual(respuesta.status_code, 302)
        self.empresa.refresh_from_db()
        with Image.open(self.empresa.logo) as logo:
            self.assertEqual(logo.format, "PNG")
            self.assertLessEqual(max(logo.size), 1000)

    def test_logo_invalido_da_error_de_formulario(self):
        archivo = SimpleUploadedFile("anim.gif", _imagen("GIF", 50))
        respuesta = self._enviar(archivo)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no es una imagen JPG o PNG")
