from django.contrib import admin
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.tests.ayudas import una_empresa
from apps.sitios import services
from apps.sitios.models import Plano, PuntoControl, Sitio


class SitioAdminTests(TestCase):
    def setUp(self):
        self.administrador = User.objects.create_superuser(
            username="root",
            password="x",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        self.cliente = Cliente.objects.create(
            razon_social="ACME", empresa=una_empresa()
        )
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")
        self.url = reverse("admin:sitios_sitio_changelist")

    def test_suprimir_datos_pide_confirmacion(self):
        self.client.force_login(self.administrador)
        respuesta = self.client.post(
            self.url, {"action": "suprimir_datos", "_selected_action": [self.sitio.pk]}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "admin/sitios/sitio/confirmar_accion.html")
        self.assertTrue(Sitio.objects.filter(pk=self.sitio.pk).exists())

    def test_suprimir_datos_borra_sitio_e_historial(self):
        self.client.force_login(self.administrador)
        pk = self.sitio.pk
        respuesta = self.client.post(
            self.url,
            {"action": "suprimir_datos", "_selected_action": [pk], "confirmado": "si"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Sitio.objects.filter(pk=pk).exists())
        self.assertEqual(Sitio.history.filter(id=pk).count(), 0)

    def test_revertir_sitio_desde_historial_esta_prohibido(self):
        self.client.force_login(self.administrador)
        self.sitio.nombre = "Planta Norte"
        self.sitio.save()
        version_anterior = Sitio.history.filter(id=self.sitio.pk).order_by(
            "history_date", "history_id"
        )[0]
        url = reverse(
            "admin:sitios_sitio_simple_history",
            args=[self.sitio.pk, version_anterior.history_id],
        )
        respuesta = self.client.post(
            url,
            {
                "cliente": self.cliente.pk,
                "nombre": "Planta 1",
                "sector": self.sitio.sector,
                "activo": "on",
            },
        )
        self.assertEqual(respuesta.status_code, 403)
        self.sitio.refresh_from_db()
        self.assertEqual(self.sitio.nombre, "Planta Norte")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_sitio_ya_no_ofrece_regenerar_qr(self):
        request = RequestFactory().get(self.url)
        request.user = self.administrador
        acciones = admin.site._registry[Sitio].get_actions(request)
        self.assertNotIn("regenerar_qr", acciones)


class PuntoControlAdminTests(TestCase):
    def setUp(self):
        self.administrador = User.objects.create_superuser(
            username="root",
            password="x",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        cliente = Cliente.objects.create(razon_social="ACME", empresa=una_empresa())
        self.sitio = Sitio.objects.create(cliente=cliente, nombre="Planta 1")
        self.punto = self.sitio.puntos.get()
        self.url = reverse("admin:sitios_puntocontrol_changelist")

    def _regenerar(self, **extra):
        return self.client.post(
            self.url,
            {"action": "regenerar_qr", "_selected_action": [self.punto.pk], **extra},
        )

    def test_accion_regenerar_qr_cambia_el_codigo(self):
        self.client.force_login(self.administrador)
        anterior = self.punto.qr_codigo
        respuesta = self._regenerar(confirmado="si")
        self.assertEqual(respuesta.status_code, 302)
        self.punto.refresh_from_db()
        self.assertNotEqual(self.punto.qr_codigo, anterior)

    def test_staff_sin_rol_administrador_no_ve_la_accion(self):
        usuario = User.objects.create_user(
            username="staff",
            password="x",
            rol=User.Rol.EMPLEADO,
            is_staff=True,
            empresa=una_empresa(),
        )
        permisos = Permission.objects.filter(
            content_type__app_label="sitios",
            codename__in=["view_puntocontrol", "change_puntocontrol"],
        )
        usuario.user_permissions.add(*permisos)
        request = RequestFactory().get(self.url)
        request.user = User.objects.get(pk=usuario.pk)
        acciones = admin.site._registry[PuntoControl].get_actions(request)
        self.assertNotIn("regenerar_qr", acciones)
        self.client.force_login(usuario)
        anterior = self.punto.qr_codigo
        self._regenerar(confirmado="si")
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.qr_codigo, anterior)

    def test_sitio_y_foto_de_solo_lectura_al_editar(self):
        modelo_admin = admin.site._registry[PuntoControl]
        request = RequestFactory().get(self.url)
        request.user = self.administrador
        alta = modelo_admin.get_readonly_fields(request)
        self.assertNotIn("sitio", alta)
        self.assertNotIn("foto", alta)
        edicion = modelo_admin.get_readonly_fields(request, self.punto)
        for campo in ("sitio", "foto", "qr_codigo", "ubicacion_fijada_en"):
            self.assertIn(campo, edicion)
        self.client.force_login(self.administrador)
        url = reverse("admin:sitios_puntocontrol_change", args=[self.punto.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def _datos_cambio(self, **extra):
        return {
            "nombre": "General",
            "sector": "",
            "orden": 0,
            "activo": "on",
            # La empresa es inmutable: el formulario debe reenviar la actual (T6 la
            # vuelve de solo lectura).
            "empresa": self.punto.empresa_id or "",
            "_save": "Guardar",
            **extra,
        }

    def test_corregir_coordenadas_limpia_fijada_por_escaneo(self):
        self.client.force_login(self.administrador)
        PuntoControl.objects.filter(pk=self.punto.pk).update(
            latitud="-35.100000",
            longitud="-58.100000",
            ubicacion_fijada_en=timezone.now(),
            ubicacion_fijada_por=self.administrador,
        )
        url = reverse("admin:sitios_puntocontrol_change", args=[self.punto.pk])
        respuesta = self.client.post(
            url, self._datos_cambio(latitud="-35.2", longitud="-58.100000")
        )
        self.assertEqual(respuesta.status_code, 302)
        self.punto.refresh_from_db()
        self.assertEqual(str(self.punto.latitud), "-35.200000")
        self.assertIsNone(self.punto.ubicacion_fijada_por)
        self.assertIsNone(self.punto.ubicacion_fijada_en)

    def test_no_desactiva_el_ultimo_punto(self):
        self.client.force_login(self.administrador)
        url = reverse("admin:sitios_puntocontrol_change", args=[self.punto.pk])
        datos = self._datos_cambio()
        del datos["activo"]
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "último punto activo")
        self.punto.refresh_from_db()
        self.assertTrue(self.punto.activo)
        PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302)
        self.punto.refresh_from_db()
        self.assertFalse(self.punto.activo)

    def test_alta_inactiva_con_otro_punto_activo(self):
        self.client.force_login(self.administrador)
        url = reverse("admin:sitios_puntocontrol_add")
        datos = {"sitio": self.sitio.pk, "nombre": "Cocina", "orden": 1}
        respuesta = self.client.post(url, {**datos, "_save": "Guardar"})
        self.assertEqual(respuesta.status_code, 302)
        creado = PuntoControl.objects.get(nombre="Cocina")
        self.assertFalse(creado.activo)

    def test_alta_en_sitio_inactivo(self):
        self.client.force_login(self.administrador)
        Sitio.objects.filter(pk=self.sitio.pk).update(activo=False)
        url = reverse("admin:sitios_puntocontrol_add")
        datos = {"sitio": self.sitio.pk, "nombre": "Cocina", "orden": 1}
        respuesta = self.client.post(url, {**datos, "_save": "Guardar"})
        self.assertEqual(respuesta.status_code, 302)

    def test_regenerar_qr_pide_confirmacion(self):
        self.client.force_login(self.administrador)
        anterior = self.punto.qr_codigo
        respuesta = self._regenerar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "admin/sitios/sitio/confirmar_accion.html")
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.qr_codigo, anterior)

    def test_revertir_punto_desde_historial_esta_prohibido(self):
        self.client.force_login(self.administrador)
        anterior = self.punto.qr_codigo
        nuevo = services.regenerar_qr(self.punto)
        version_anterior = PuntoControl.history.filter(id=self.punto.pk).order_by(
            "history_date", "history_id"
        )[0]
        self.assertEqual(version_anterior.qr_codigo, anterior)
        url = reverse(
            "admin:sitios_puntocontrol_simple_history",
            args=[self.punto.pk, version_anterior.history_id],
        )
        respuesta = self.client.post(
            url,
            {"sitio": self.sitio.pk, "nombre": "General", "orden": 0, "activo": "on"},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.punto.refresh_from_db()
        self.assertEqual(self.punto.qr_codigo, nuevo)
        self.assertEqual(self.client.get(url).status_code, 200)


class PlanoAdminTests(TestCase):
    def test_sitio_de_solo_lectura_al_editar(self):
        administrador = User.objects.create_superuser(
            username="root",
            password="x",
            rol=User.Rol.ADMINISTRADOR,
            empresa=una_empresa(),
        )
        sitio = Sitio.objects.create(
            cliente=Cliente.objects.create(razon_social="ACME", empresa=una_empresa()),
            nombre="Planta 1",
        )
        plano = Plano(
            sitio=sitio, nombre="PB", imagen="p.png", empresa_id=sitio.empresa_id
        )
        plano.ancho_px = plano.alto_px = 10
        Plano.objects.bulk_create([plano])
        modelo_admin = admin.site._registry[Plano]
        request = RequestFactory().get("/")
        request.user = administrador
        self.assertNotIn("sitio", modelo_admin.get_readonly_fields(request))
        edicion = modelo_admin.get_readonly_fields(request, Plano.objects.get())
        self.assertIn("sitio", edicion)
        self.assertIn("ancho_px", edicion)
