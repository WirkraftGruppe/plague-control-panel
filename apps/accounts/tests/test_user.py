from django.test import TestCase

from apps.accounts.models import User
from apps.empresas.tests.ayudas import una_empresa


class UserTests(TestCase):
    def test_rol_por_defecto_es_empleado(self):
        usuario = User.objects.create_user(
            "ana", password="clave-segura-123", empresa=una_empresa()
        )
        self.assertEqual(usuario.rol, User.Rol.EMPLEADO)
        self.assertTrue(usuario.es_empleado)
        self.assertEqual(usuario.telefono, "")

    def test_rol_administrador_y_empleado_son_excluyentes(self):
        admin = User(username="adm", rol=User.Rol.ADMINISTRADOR)
        empleado = User(username="emp", rol=User.Rol.EMPLEADO)
        self.assertTrue(admin.es_administrador)
        self.assertFalse(admin.es_empleado)
        self.assertTrue(empleado.es_empleado)
        self.assertFalse(empleado.es_administrador)

    def test_is_staff_no_implica_administrador(self):
        usuario = User.objects.create_user(
            "staff", password="clave-segura-123", is_staff=True, empresa=una_empresa()
        )
        self.assertTrue(usuario.is_staff)
        self.assertFalse(usuario.es_administrador)
