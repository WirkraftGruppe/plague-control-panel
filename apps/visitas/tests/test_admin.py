import shutil
import tempfile
from io import BytesIO

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.visitas.admin import (
    CAMPOS_EVIDENCIA,
    FotoInline,
    ProductoAplicadoInline,
    RevisionInline,
)
from apps.visitas.models import Foto, ProductoAplicado, Revision, Visita

from .test_models import crear_revision, crear_visita

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="detach-test-admin-")


def _imagen_real():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "blue").save(salida, format="JPEG")
    return SimpleUploadedFile("f.jpg", salida.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class VisitaAdminTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def _request(self):
        request = RequestFactory().get("/admin/")
        request.user = self.administrador
        return request

    def _realizada_con_foto(self):
        ahora = timezone.now()
        visita = crear_visita(
            estado=Visita.Estado.REALIZADA, abierta_en=ahora, cerrada_en=ahora
        )
        revision = crear_revision(visita)
        foto = Foto.objects.create(revision=revision, imagen=_imagen_real())
        return visita, revision, foto

    def _pendiente_de(self, otra):
        return Visita.objects.create(
            proyecto=otra.proyecto, empleado=otra.empleado, origen=Visita.Origen.APP
        )

    def setUp(self):
        self.administrador = User.objects.create_superuser(
            username="root", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def test_changelist_responde_200(self):
        self.client.force_login(self.administrador)
        for modelo in ("visita", "revision", "foto", "productoaplicado"):
            respuesta = self.client.get(reverse(f"admin:visitas_{modelo}_changelist"))
            self.assertEqual(respuesta.status_code, 200, modelo)

    def test_estado_y_cerrada_en_son_solo_lectura(self):
        solo_lectura = admin.site._registry[Visita].get_readonly_fields(self._request())
        for campo in (
            "estado",
            "abierta_en",
            "cerrada_en",
            "cierre",
            "esquema_planilla",
        ):
            self.assertIn(campo, solo_lectura)

    def test_visita_realizada_tiene_evidencia_de_solo_lectura(self):
        realizada, _, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        solo_lectura = modeladmin.get_readonly_fields(self._request(), realizada)
        for campo in CAMPOS_EVIDENCIA:
            self.assertIn(campo, solo_lectura)
        solo_lectura = modeladmin.get_readonly_fields(self._request(), pendiente)
        for campo in ("proyecto", "empleado"):
            self.assertNotIn(campo, solo_lectura)

    def test_no_se_borran_visitas_revisiones_ni_fotos(self):
        visita, revision, foto = self._realizada_con_foto()
        self.client.force_login(self.administrador)
        for modelo, objeto in (
            ("visita", visita),
            ("revision", revision),
            ("foto", foto),
        ):
            url = reverse(f"admin:visitas_{modelo}_delete", args=[objeto.pk])
            respuesta = self.client.post(url, {"post": "yes"})
            self.assertEqual(respuesta.status_code, 403, modelo)
        self.assertTrue(Visita.objects.filter(pk=visita.pk).exists())
        self.assertTrue(Revision.objects.filter(pk=revision.pk).exists())
        self.assertTrue(Foto.objects.filter(pk=foto.pk).exists())
        request = self._request()
        for modelo in (Visita, Revision, Foto, ProductoAplicado):
            self.assertFalse(
                admin.site._registry[modelo].has_delete_permission(request)
            )

    def test_inlines_de_revision_son_de_solo_lectura(self):
        realizada, revision, _ = self._realizada_con_foto()
        request = self._request()
        inlines = admin.site._registry[Visita].get_inline_instances(request, realizada)
        self.assertEqual([type(i) for i in inlines], [RevisionInline])
        inlines += admin.site._registry[Revision].get_inline_instances(
            request, revision
        )
        self.assertEqual(
            [type(i) for i in inlines],
            [RevisionInline, FotoInline, ProductoAplicadoInline],
        )
        for inline in inlines:
            self.assertFalse(inline.has_add_permission(request, realizada))
            self.assertFalse(inline.has_change_permission(request, realizada))
            self.assertFalse(inline.has_delete_permission(request, realizada))

    def test_la_evidencia_no_se_agrega_ni_se_cambia_desde_el_admin(self):
        _, revision, foto = self._realizada_con_foto()
        request = self._request()
        for modelo in (Revision, Foto, ProductoAplicado):
            modeladmin = admin.site._registry[modelo]
            self.assertFalse(modeladmin.has_add_permission(request))
            self.assertFalse(modeladmin.has_change_permission(request))
        self.client.force_login(self.administrador)
        url = reverse("admin:visitas_foto_change", args=[foto.pk])
        self.assertEqual(
            self.client.post(url, {"orden": 9, "imagen": _imagen_real()}).status_code,
            403,
        )
        foto.refresh_from_db()
        self.assertEqual(foto.orden, 0)
        url = reverse("admin:visitas_revision_change", args=[revision.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"orden": 9}).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("admin:visitas_foto_add")).status_code, 403
        )

    def test_revertir_desde_historial_esta_prohibido(self):
        visita = crear_visita()
        visita.estado = Visita.Estado.REALIZADA
        visita.abierta_en = visita.cerrada_en = timezone.now()
        visita.save()
        cerrada_en = visita.cerrada_en
        version_pendiente = visita.history.get(estado=Visita.Estado.PENDIENTE)
        self.client.force_login(self.administrador)
        url = reverse(
            "admin:visitas_visita_simple_history",
            args=[visita.pk, version_pendiente.pk],
        )
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context["adminform"].form
        datos = {
            nombre: ("" if valor is None else valor)
            for nombre, valor in formulario.initial.items()
            if nombre in formulario.fields
        }
        datos["observaciones"] = "reescrita"
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 403)
        visita.refresh_from_db()
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.cerrada_en, cerrada_en)
        self.assertEqual(visita.observaciones, "")

    def test_revertir_historial_de_revision_esta_prohibido(self):
        _, revision, _ = self._realizada_con_foto()
        version = revision.history.get()
        self.client.force_login(self.administrador)
        url = reverse(
            "admin:visitas_revision_simple_history", args=[revision.pk, version.pk]
        )
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"observaciones": "x"}).status_code, 403)
        revision.refresh_from_db()
        self.assertEqual(revision.observaciones, "")

    def test_pendiente_no_muestra_inlines_de_revision(self):
        realizada, _, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        request = self._request()
        self.assertEqual(modeladmin.get_inlines(request, None), ())
        self.assertEqual(modeladmin.get_inlines(request, pendiente), ())
        self.assertEqual(modeladmin.get_inlines(request, realizada), (RevisionInline,))
        self.client.force_login(self.administrador)
        for url in (
            reverse("admin:visitas_visita_change", args=[pendiente.pk]),
            reverse("admin:visitas_visita_add"),
        ):
            respuesta = self.client.get(url)
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.context["inline_admin_formsets"], [])

    def test_datos_solo_lectura_en_pendiente(self):
        realizada, _, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        request = self._request()
        for obj in (None, pendiente):
            self.assertIn("datos", modeladmin.get_readonly_fields(request, obj))

    def test_programada_para_solo_lectura_en_realizada(self):
        """La planificación es de solo lectura en visitas cerradas."""
        realizada, _, _ = self._realizada_con_foto()
        pendiente = self._pendiente_de(realizada)
        modeladmin = admin.site._registry[Visita]
        request = self._request()
        cerrada = modeladmin.get_readonly_fields(request, realizada)
        abierta = modeladmin.get_readonly_fields(request, pendiente)
        for campo in ("programada_para", "asignada_por"):
            self.assertIn(campo, cerrada)
            self.assertNotIn(campo, abierta)
        for campo in ("observaciones", "incidencia", "incidencia_detalle"):
            self.assertNotIn(campo, cerrada)


class FormVisitaTests(TestCase):
    def test_form_de_visita_declara_campos(self):
        modeladmin = admin.site._registry[Visita]
        self.assertNotEqual(modeladmin.fields, "__all__")
        editables = {
            f.name for f in Visita._meta.get_fields() if getattr(f, "editable", False)
        }
        editables -= {"id"}
        self.assertEqual(set(modeladmin.fields), editables)
        self.assertIn("incidencia_asignacion", modeladmin.readonly_fields)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class AdminPendienteTests(TestCase):
    def test_post_forjado_sobre_pendiente_no_cierra_ni_carga_datos(self):
        pendiente = crear_visita()
        administrador = User.objects.create_superuser(
            username="root-pend", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(administrador)
        url = reverse("admin:visitas_visita_change", args=[pendiente.pk])
        self.client.post(
            url,
            {
                "estado": Visita.Estado.REALIZADA,
                "cerrada_en_0": "2026-10-01",
                "cerrada_en_1": "10:00:00",
                "datos": '{"a": 1}',
                "proyecto": pendiente.proyecto_id,
                "empleado": pendiente.empleado_id,
                "origen": Visita.Origen.APP,
            },
        )
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)
        self.assertIsNone(pendiente.cerrada_en)
        self.assertEqual(pendiente.datos, {})
        self.assertFalse(pendiente.revisiones.exists())

    def test_post_forjado_sobre_pendiente_muestra_el_rechazo(self):
        pendiente = crear_visita()
        crear_revision(pendiente)
        administrador = User.objects.create_superuser(
            username="root-rech", password="x", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(administrador)
        url = reverse("admin:visitas_visita_change", args=[pendiente.pk])
        respuesta = self.client.post(
            url,
            {
                "proyecto": pendiente.proyecto_id,
                "empleado": pendiente.empleado_id,
                "origen": Visita.Origen.APP,
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Una visita pendiente no tiene revisiones.")
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.PENDIENTE)

    def test_pendiente_no_asignable_a_administrador(self):
        administrador = User.objects.create_superuser(
            username="root-asig", password="x", rol=User.Rol.ADMINISTRADOR
        )
        base = crear_visita()
        empleado = base.empleado
        # El modelo lo rechaza aunque no pase por el admin.
        base.empleado = administrador
        with self.assertRaises(ValidationError) as ctx:
            base.full_clean()
        self.assertIn("empleado", ctx.exception.message_dict)
        # El admin ofrece solo empleados al crear una pendiente.
        self.client.force_login(administrador)
        url = reverse("admin:visitas_visita_add")
        form = self.client.get(url).context["adminform"].form
        self.assertEqual(set(form.fields["empleado"].queryset), {empleado})
        antes = Visita.objects.count()
        datos = {
            "proyecto": base.proyecto_id,
            "empleado": administrador.pk,
            "origen": Visita.Origen.APP,
        }
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("empleado", respuesta.context["adminform"].form.errors)
        self.assertEqual(Visita.objects.count(), antes)
        # Con un empleado el mismo alta funciona.
        respuesta = self.client.post(url, {**datos, "empleado": empleado.pk})
        self.assertEqual(respuesta.status_code, 302, respuesta.content[:300])
        self.assertEqual(Visita.objects.count(), antes + 1)
