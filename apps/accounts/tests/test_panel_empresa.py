from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.empresas.pruebas import crear_empresa

User = get_user_model()
CLAVE = "Clave-Segura-2026"


class UsuariosPorEmpresaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.una = crear_empresa("Una")
        cls.otra = crear_empresa("Otra")
        cls.admin = User.objects.create_user(
            "admin-una", password=CLAVE, rol=User.Rol.ADMINISTRADOR, empresa=cls.una
        )
        cls.propio = User.objects.create_user(
            "emp-una", password=CLAVE, rol=User.Rol.EMPLEADO, empresa=cls.una
        )
        cls.ajeno = User.objects.create_user(
            "emp-otra", password=CLAVE, rol=User.Rol.EMPLEADO, empresa=cls.otra
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def _datos(self, **extra):
        return {
            "username": "nuevo",
            "first_name": "Luis",
            "last_name": "Paz",
            "email": "luis@example.com",
            "telefono": "",
            "rol": User.Rol.EMPLEADO,
            "password1": CLAVE,
            "password2": CLAVE,
            **extra,
        }

    def test_listado_muestra_solo_usuarios_de_la_empresa(self):
        respuesta = self.client.get(reverse("panel:usuarios:listado"))
        nombres = {u.username for u in respuesta.context["object_list"]}
        self.assertEqual(nombres, {"admin-una", "emp-una"})

    def test_rutas_de_usuario_de_otra_empresa_dan_404(self):
        for nombre in ("editar", "desactivar", "contrasena"):
            url = reverse(f"panel:usuarios:{nombre}", args=[self.ajeno.pk])
            self.assertEqual(self.client.get(url).status_code, 404, nombre)
            self.assertEqual(self.client.post(url, {}).status_code, 404, nombre)
        url = reverse("panel:usuarios:reactivar", args=[self.ajeno.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.ajeno.refresh_from_db()
        self.assertTrue(self.ajeno.is_active)
        self.assertEqual(self.ajeno.username, "emp-otra")

    def test_alta_asigna_la_empresa_del_administrador(self):
        respuesta = self.client.post(reverse("panel:usuarios:alta"), self._datos())
        self.assertRedirects(respuesta, reverse("panel:usuarios:listado"))
        self.assertEqual(User.objects.get(username="nuevo").empresa, self.una)

    def test_alta_no_ofrece_rol_plataforma(self):
        formulario = self.client.get(reverse("panel:usuarios:alta")).context["form"]
        roles = [valor for valor, _ in formulario.fields["rol"].choices]
        self.assertNotIn(User.Rol.PLATAFORMA, roles)
        respuesta = self.client.post(
            reverse("panel:usuarios:alta"), self._datos(rol=User.Rol.PLATAFORMA)
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("rol", respuesta.context["form"].errors)
        self.assertFalse(User.objects.filter(username="nuevo").exists())

    def test_edicion_no_ofrece_rol_plataforma(self):
        url = reverse("panel:usuarios:editar", args=[self.propio.pk])
        formulario = self.client.get(url).context["form"]
        roles = [valor for valor, _ in formulario.fields["rol"].choices]
        self.assertNotIn(User.Rol.PLATAFORMA, roles)
        datos = {"username": "emp-una", "email": "", "rol": User.Rol.PLATAFORMA}
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.propio.refresh_from_db()
        self.assertEqual(self.propio.rol, User.Rol.EMPLEADO)
