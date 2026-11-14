"""Admin de cuentas: la regla de rol y empresa da errores de formulario, no 500."""

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.accounts.pruebas import crear_plataforma
from apps.empresas.pruebas import crear_empresa


class RolPlataformaAdminTests(TestCase):
    def test_plataforma_con_empresa_da_error_que_indica_la_salida(self):
        empresa = crear_empresa()
        cuenta = User.objects.create_user(
            "empleado",
            password="clave-segura-123",
            rol=User.Rol.EMPLEADO,
            empresa=empresa,
        )
        self.client.force_login(crear_plataforma())
        url = reverse("admin:accounts_user_change", args=[cuenta.pk])
        formulario = self.client.get(url).context["adminform"].form
        datos = {
            "username": cuenta.username,
            "rol": User.Rol.PLATAFORMA,
            "first_name": "",
            "last_name": "",
            "email": "",
            "telefono": "",
            "is_active": "on",
            "date_joined_0": "2026-01-01",
            "date_joined_1": "00:00:00",
        }
        self.assertNotIn("empresa", formulario.fields)
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "elija el rol administrador o empleado")
