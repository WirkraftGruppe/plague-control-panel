from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa


class EmpresaDeUsuarioTests(TestCase):
    def test_createsuperuser_crea_plataforma(self):
        with mock.patch.dict("os.environ", {"DJANGO_SUPERUSER_PASSWORD": "clave-123"}):
            call_command(
                "createsuperuser",
                interactive=False,
                username="raiz",
                email="raiz@example.com",
                stdout=StringIO(),
            )
        usuario = User.objects.get(username="raiz")
        self.assertEqual(usuario.rol, User.Rol.PLATAFORMA)
        self.assertTrue(usuario.es_plataforma)
        self.assertTrue(usuario.is_superuser)
        self.assertIsNone(usuario.empresa_id)

    def test_create_superuser_sin_rol_es_plataforma(self):
        usuario = User.objects.create_superuser("raiz", password="clave-123")
        self.assertEqual(usuario.rol, User.Rol.PLATAFORMA)

    def test_create_superuser_respeta_el_rol_explicito(self):
        usuario = User.objects.create_superuser(
            "adm",
            password="clave-123",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        self.assertEqual(usuario.rol, User.Rol.ADMINISTRADOR)
