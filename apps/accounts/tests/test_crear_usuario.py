from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa

GETPASS = "apps.accounts.management.commands.crear_usuario.getpass"


class CrearUsuarioTests(TestCase):
    def test_crea_empleado_sin_is_staff(self):
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            call_command("crear_usuario", "ana", rol="empleado", nombre="Ana")
        usuario = User.objects.get(username="ana")
        self.assertEqual(usuario.rol, User.Rol.EMPLEADO)
        self.assertEqual(usuario.first_name, "Ana")
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertTrue(usuario.check_password("clave-segura-123"))

    def test_crea_usuario_en_la_empresa_indicada(self):
        empresa = una_empresa()
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            call_command("crear_usuario", "ana", rol="empleado", empresa=empresa.pk)
        self.assertEqual(User.objects.get(username="ana").empresa_id, empresa.pk)

    def test_rechaza_empresa_inexistente(self):
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            with self.assertRaises(CommandError):
                call_command("crear_usuario", "ana", rol="empleado", empresa=9999)

    def test_rechaza_contrasena_de_11_caracteres(self):
        with mock.patch(GETPASS, return_value="clave-corta"):
            with self.assertRaises(CommandError):
                call_command("crear_usuario", "ana", rol="empleado")
        self.assertFalse(User.objects.filter(username="ana").exists())

    def test_rechaza_usuario_existente(self):
        User.objects.create_user(
            "ana", password="clave-segura-123", empresa=una_empresa()
        )
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            with self.assertRaises(CommandError):
                call_command("crear_usuario", "ana", rol="empleado")

    def test_rechaza_contrasenas_distintas(self):
        with mock.patch(GETPASS, side_effect=["clave-segura-123", "otra-clave-123"]):
            with self.assertRaises(CommandError):
                call_command("crear_usuario", "ana", rol="empleado")

    def test_normaliza_el_nombre(self):
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            call_command("crear_usuario", " ＡＮＡ ", rol="empleado")
        self.assertTrue(User.objects.filter(username="ana").exists())

    def test_rechaza_variante_unicode_de_usuario_existente(self):
        User.objects.create_user(
            "ana", password="clave-segura-123", empresa=una_empresa()
        )
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            with self.assertRaises(CommandError):
                call_command("crear_usuario", "ＡNA", rol="empleado")
        self.assertEqual(User.objects.count(), 1)

    def test_rechaza_nombre_invalido(self):
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            with self.assertRaises(CommandError):
                call_command("crear_usuario", "ana perez", rol="empleado")
        self.assertEqual(User.objects.count(), 0)

    def test_carrera_de_unicidad_es_un_error_de_comando(self):
        with mock.patch(GETPASS, return_value="clave-segura-123"):
            with mock.patch.object(User, "save", side_effect=IntegrityError):
                with self.assertRaises(CommandError):
                    call_command("crear_usuario", "ana", rol="empleado")
