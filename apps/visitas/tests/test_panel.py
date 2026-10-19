"""Panel de Visitas: listado, ficha, foto, revisión de incidencia y asignación."""

import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import mock
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.productos.models import Producto
from apps.proyectos.models import Proyecto
from apps.servicios.models import CampoPlanilla
from apps.sitios.models import PuntoControl
from apps.visitas.models import Foto, ProductoAplicado, Visita
from apps.visitas.services import registrar_visita_manual

from .test_models import crear_revision, crear_visita, punto_de

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="detach-panel-test-")


def _jpeg():
    salida = BytesIO()
    Image.new("RGB", (40, 30), "red").save(salida, format="JPEG")
    return salida.getvalue()


class BaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.visita = crear_visita(
            estado=Visita.Estado.REALIZADA,
            abierta_en=timezone.now(),
            cerrada_en=timezone.now(),
            cierre=Visita.Cierre.ADMINISTRADOR,
            origen=Visita.Origen.MANUAL,
            motivo_manual="Carga",
        )
        cls.revision = crear_revision(cls.visita)
        cls.punto = punto_de(cls.visita)
        cls.proyecto = cls.visita.proyecto
        cls.empleado = cls.visita.empleado
        cls.admin = User.objects.create_user(
            "adm-pv", password="x", rol=User.Rol.ADMINISTRADOR
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def otra_visita(self, **extra):
        datos = {
            "proyecto": self.proyecto,
            "empleado": self.empleado,
            "origen": Visita.Origen.MANUAL,
            "motivo_manual": "Carga",
            "estado": Visita.Estado.REALIZADA,
            "abierta_en": timezone.now(),
            "cerrada_en": timezone.now(),
        }
        datos.update(extra)
        return Visita.objects.create(**datos)


class ListadoVisitasTests(BaseTests):
    def _pks(self, **parametros):
        respuesta = self.client.get(reverse("panel:visitas:listado"), parametros)
        self.assertEqual(respuesta.status_code, 200)
        return {v.pk for v in respuesta.context["visitas"]}

    def test_filtra_incidencias_sin_revisar(self):
        sin_revisar = self.otra_visita(incidencia=True, incidencia_detalle="Rotura")
        revisada = self.otra_visita(
            incidencia=True,
            incidencia_revisada_por=self.admin,
            incidencia_revisada_en=timezone.now(),
        )
        self.assertEqual(self._pks(incidencia="sin_revisar"), {sin_revisar.pk})
        self.assertEqual(self._pks(incidencia="todas"), {sin_revisar.pk, revisada.pk})
        self.assertIn(self.visita.pk, self._pks())

    def test_filtro_ubicacion_revisadas_lista_solo_revisadas(self):
        sin_revisar = self.otra_visita(incidencia_ubicacion=True)
        revisada = self.otra_visita(
            incidencia_ubicacion=True,
            incidencia_revisada_por=self.admin,
            incidencia_revisada_en=timezone.now(),
        )
        en_revision = self.otra_visita(
            incidencia_revisada_por=self.admin,
            incidencia_revisada_en=timezone.now(),
        )
        crear_revision(en_revision, incidencia_ubicacion=True)
        self.assertEqual(
            self._pks(incidencia="ubicacion_revisadas"),
            {revisada.pk, en_revision.pk},
        )
        self.assertEqual(self._pks(incidencia="ubicacion"), {sin_revisar.pk})
        respuesta = self.client.get(reverse("panel:visitas:listado"))
        self.assertIn(
            "ubicacion_revisadas", [v for v, _ in respuesta.context["incidencias"]]
        )

    def test_filtro_ubicacion_excluye_administradores_y_abiertas(self):
        cuenta = self.otra_visita(incidencia_ubicacion=True)
        de_administrador = self.otra_visita(incidencia_ubicacion=True)
        Visita.objects.filter(pk=de_administrador.pk).update(cuenta_como_servicio=False)
        abierta = self.otra_visita(
            incidencia_ubicacion=True, estado=Visita.Estado.ABIERTA, cerrada_en=None
        )
        self.assertEqual(self._pks(incidencia="ubicacion"), {cuenta.pk})
        self.assertNotIn(abierta.pk, self._pks(incidencia="ubicacion"))

    def test_filtro_numerico_no_ascii_no_da_500(self):
        self.assertIn(self.visita.pk, self._pks(empleado="١٢٣", proyecto="²"))

    def test_filtro_numerico_fuera_de_rango_no_da_500(self):
        for valor in ("9223372036854775808", "9" * 5000, "0" * 25):
            with self.subTest(valor=valor[:25]):
                self.assertIn(self.visita.pk, self._pks(empleado=valor, proyecto=valor))
        self.assertEqual(self._pks(empleado=str(2**63 - 1)), set())

    def test_filtra_por_empleado_proyecto_y_estado(self):
        pendiente = self.otra_visita(
            estado=Visita.Estado.PENDIENTE,
            abierta_en=None,
            cerrada_en=None,
            motivo_manual="",
        )
        self.assertEqual(self._pks(estado="pendiente"), {pendiente.pk})
        self.assertEqual(
            self._pks(empleado=self.empleado.pk, proyecto=self.proyecto.pk),
            {self.visita.pk, pendiente.pk},
        )
        self.assertEqual(self._pks(empleado=self.admin.pk), set())

    def test_filtra_abiertas(self):
        abierta = self.otra_visita(estado=Visita.Estado.ABIERTA, cerrada_en=None)
        self.assertEqual(self._pks(estado="abierta"), {abierta.pk})
        respuesta = self.client.get(reverse("panel:visitas:listado"))
        self.assertIn("abierta", [valor for valor, _ in respuesta.context["estados"]])
        self.assertContains(respuesta, "Abierta")

    def test_parcial_htmx_lleva_id_listado(self):
        respuesta = self.client.get(
            reverse("panel:visitas:listado"), headers={"HX-Request": "true"}
        )
        self.assertContains(respuesta, 'id="listado"')
        self.assertNotContains(respuesta, "<html")


class RevisarIncidenciaTests(BaseTests):
    def test_marca_revisada_por_el_administrador(self):
        visita = self.otra_visita(incidencia=True)
        url = reverse("panel:visitas:revisar_incidencia", args=[visita.pk])
        respuesta = self.client.post(url)
        self.assertRedirects(
            respuesta, reverse("panel:visitas:ficha", args=[visita.pk])
        )
        visita.refresh_from_db()
        self.assertEqual(visita.incidencia_revisada_por, self.admin)
        self.assertIsNotNone(visita.incidencia_revisada_en)

    def test_empleado_no_puede_revisar(self):
        visita = self.otra_visita(incidencia=True)
        self.client.force_login(self.empleado)
        url = reverse("panel:visitas:revisar_incidencia", args=[visita.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        visita.refresh_from_db()
        self.assertIsNone(visita.incidencia_revisada_en)

    def test_sin_incidencia_no_se_marca(self):
        url = reverse("panel:visitas:revisar_incidencia", args=[self.visita.pk])
        self.client.post(url)
        self.visita.refresh_from_db()
        self.assertIsNone(self.visita.incidencia_revisada_en)

    def test_get_no_esta_permitido(self):
        url = reverse("panel:visitas:revisar_incidencia", args=[self.visita.pk])
        self.assertEqual(self.client.get(url).status_code, 405)


class FichaVisitaTests(BaseTests):
    def test_historial_no_muestra_coordenadas(self):
        self.revision.latitud = Decimal("-35.123456")
        self.revision.longitud = Decimal("-57.654321")
        self.revision.precision_m = Decimal("12.5")
        self.revision.datos = {"secreto": "valor-reservado"}
        self.revision.save()
        self.visita.datos = {"secreto": "valor-reservado"}
        self.visita.observaciones = "Cambio visible"
        self.visita.save()
        respuesta = self.client.get(
            reverse("panel:visitas:ficha", args=[self.visita.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        self.assertIn("Historial", contenido)
        self.assertIn("observaciones", contenido)
        for prohibido in ("-35.123456", "-57.654321", "12.5", "valor-reservado"):
            self.assertNotIn(prohibido, contenido)
        for campo in ("latitud", "longitud", "precisión"):
            self.assertNotIn(campo, contenido.lower())

    def test_historial_con_consultas_acotadas(self):
        for i in range(60):
            self.visita.observaciones = f"Cambio {i}"
            self.visita.save()
        url = reverse("panel:visitas:ficha", args=[self.visita.pk])
        with CaptureQueriesContext(connection) as consultas:
            respuesta = self.client.get(url)
        self.assertEqual(len(respuesta.context["historial"]), 50)
        historial = [
            q["sql"] for q in consultas if "historicalvisita" in q["sql"].lower()
        ]
        self.assertEqual(len(historial), 1, historial)

    def test_muestra_incidencia_de_asignacion(self):
        visita = self.otra_visita(incidencia_asignacion=True)
        respuesta = self.client.get(reverse("panel:visitas:ficha", args=[visita.pk]))
        self.assertContains(respuesta, "Incidencia de asignación")
        normal = self.client.get(reverse("panel:visitas:ficha", args=[self.visita.pk]))
        self.assertNotContains(normal, "Incidencia de asignación")

    def test_muestra_planilla_del_esquema_copiado(self):
        self.visita.esquema_planilla = [
            {"clave": "cebos", "etiqueta": "Cantidad de cebos", "tipo": "numero"}
        ]
        self.visita.datos = {"cebos": 7}
        self.visita.save()
        respuesta = self.client.get(
            reverse("panel:visitas:ficha", args=[self.visita.pk])
        )
        self.assertContains(respuesta, "Cantidad de cebos")

    def test_muestra_cada_revision_con_su_planilla_y_su_punto(self):
        self.revision.esquema_planilla = [
            {"clave": "cebos", "etiqueta": "Cebos repuestos", "tipo": "numero"}
        ]
        self.revision.datos = {"cebos": 4}
        self.revision.save()
        respuesta = self.client.get(
            reverse("panel:visitas:ficha", args=[self.visita.pk])
        )
        self.assertContains(respuesta, "General")
        self.assertContains(respuesta, "Cebos repuestos")

    def test_muestra_revisiones_por_punto(self):
        sala = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Sala de máquinas", orden=1
        )
        producto = Producto.objects.create(nombre_comercial="Cebo Z")
        esquema = [{"clave": "cebos", "etiqueta": "Cebos repuestos", "tipo": "numero"}]
        self.revision.esquema_planilla = esquema
        self.revision.datos = {"cebos": 4}
        self.revision.save()
        segunda = crear_revision(
            self.visita, punto=sala, esquema_planilla=esquema, datos={"cebos": 9}
        )
        foto = Foto.objects.create(revision=segunda, imagen="visitas/fotos/z.jpg")
        ProductoAplicado.objects.create(
            revision=segunda, producto=producto, lote="L9", dosis=1, unidad="ml/l"
        )
        self.visita.esquema_planilla = [
            {"clave": "firma", "etiqueta": "Firmó el cliente", "tipo": "texto"}
        ]
        self.visita.datos = {"firma": "Ana"}
        self.visita.save()
        respuesta = self.client.get(
            reverse("panel:visitas:ficha", args=[self.visita.pk])
        )
        self.assertContains(respuesta, "General")
        self.assertContains(respuesta, "Sala de máquinas")
        self.assertContains(respuesta, "<td>4</td>", html=True)
        self.assertContains(respuesta, "<td>9</td>", html=True)
        self.assertContains(respuesta, "Cebo Z")
        self.assertContains(respuesta, "Firmó el cliente")
        self.assertContains(
            respuesta, reverse("panel:visitas:foto", args=[foto.codigo])
        )
        self.assertNotContains(respuesta, "/media/")

    def test_ficha_inexistente_da_404(self):
        respuesta = self.client.get(reverse("panel:visitas:ficha", args=[999999]))
        self.assertEqual(respuesta.status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class FotoPanelTests(BaseTests):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def _foto(self):
        return Foto.objects.create(
            revision=self.revision,
            imagen=SimpleUploadedFile("x.jpg", _jpeg(), content_type="image/jpeg"),
        )

    def test_administrador_recibe_la_imagen_con_cabeceras(self):
        foto = self._foto()
        respuesta = self.client.get(reverse("panel:visitas:foto", args=[foto.codigo]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "image/jpeg")
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertTrue(b"".join(respuesta.streaming_content).startswith(b"\xff\xd8"))

    def test_foto_exige_administrador(self):
        foto = self._foto()
        url = reverse("panel:visitas:foto", args=[foto.codigo])
        self.client.force_login(self.empleado)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn("/panel/ingresar/", respuesta["Location"])

    def test_foto_sin_archivo_da_404(self):
        foto = self._foto()
        foto.imagen.storage.delete(foto.imagen.name)
        url = reverse("panel:visitas:foto", args=[foto.codigo])
        self.assertEqual(self.client.get(url).status_code, 404)
        inexistente = reverse("panel:visitas:foto", args=[uuid4()])
        self.assertEqual(self.client.get(inexistente).status_code, 404)


class AsignarTests(BaseTests):
    def _url(self, proyecto_pk=None):
        return reverse("panel:visitas:asignar", args=[proyecto_pk or self.proyecto.pk])

    def test_crea_pendiente_para_empleado(self):
        fecha = timezone.localdate() + timedelta(days=3)
        respuesta = self.client.post(
            self._url(), {"empleado": self.empleado.pk, "programada_para": fecha}
        )
        self.assertRedirects(
            respuesta, reverse("panel:proyectos:ficha", args=[self.proyecto.pk])
        )
        visita = Visita.objects.get(estado=Visita.Estado.PENDIENTE)
        self.assertEqual(visita.proyecto, self.proyecto)
        self.assertEqual(visita.empleado, self.empleado)
        self.assertEqual(visita.programada_para, fecha)
        self.assertEqual(visita.asignada_por, self.admin)

    def test_rechaza_administrador_inactivo_y_fecha_pasada(self):
        ayer = timezone.localdate() - timedelta(days=1)
        manana = timezone.localdate() + timedelta(days=1)
        inactivo = User.objects.create_user(
            "emp-off", password="x", rol=User.Rol.EMPLEADO, is_active=False
        )
        for datos in (
            {"empleado": self.admin.pk, "programada_para": manana},
            {"empleado": inactivo.pk, "programada_para": manana},
            {"empleado": self.empleado.pk, "programada_para": ayer},
        ):
            respuesta = self.client.post(self._url(), datos)
            self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Visita.objects.filter(estado=Visita.Estado.PENDIENTE))

    def test_rechaza_proyecto_no_activo(self):
        otro = Proyecto.objects.exclude(estado=Proyecto.Estado.ACTIVO).count()
        self.assertEqual(otro, 0)
        estados = [e for e in Proyecto.Estado.values if e != Proyecto.Estado.ACTIVO]
        self.proyecto.estado = estados[0]
        self.proyecto.save()
        manana = timezone.localdate() + timedelta(days=1)
        respuesta = self.client.post(
            self._url(), {"empleado": self.empleado.pk, "programada_para": manana}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Visita.objects.filter(estado=Visita.Estado.PENDIENTE))

    def test_proyecto_inexistente_da_404(self):
        self.assertEqual(self.client.get(self._url(999999)).status_code, 404)

    def test_rechaza_sitio_o_cliente_de_baja(self):
        manana = timezone.localdate() + timedelta(days=1)
        datos = {"empleado": self.empleado.pk, "programada_para": manana}
        sitio = self.proyecto.sitio
        for objeto in (sitio, sitio.cliente):
            with self.subTest(baja=objeto._meta.model_name):
                # `update` evita la cascada de la baja del sitio sobre sus puntos.
                type(objeto).objects.filter(pk=objeto.pk).update(activo=False)
                respuesta = self.client.post(self._url(), datos)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["form"].non_field_errors())
                self.assertFalse(Visita.objects.filter(estado=Visita.Estado.PENDIENTE))
                type(objeto).objects.filter(pk=objeto.pk).update(activo=True)
        respuesta = self.client.post(self._url(), datos)
        self.assertEqual(respuesta.status_code, 302)


MEDIA_MANUAL = tempfile.mkdtemp(prefix="detach-manual-test-")


@override_settings(MEDIA_ROOT=MEDIA_MANUAL)
class ManualTests(BaseTests):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_MANUAL, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("panel:visitas:manual", args=[self.proyecto.pk])
        self.producto = Producto.objects.create(nombre_comercial="Cebo")
        # Las cargas atrasadas son anteriores a hoy: el proyecto ya existía.
        Proyecto.objects.filter(pk=self.proyecto.pk).update(
            creado=timezone.now() - timedelta(days=90)
        )
        self.proyecto.refresh_from_db()

    def _archivos(self):
        return list(Path(MEDIA_MANUAL).rglob("*.jpg"))

    def _datos(self, **extra):
        datos = {
            "empleado": self.empleado.pk,
            "puntos": [self.punto.pk],
            "motivo": "La app no tenía señal",
            "realizada_en": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            "productos-TOTAL_FORMS": 1,
            "productos-INITIAL_FORMS": 0,
            "productos-MIN_NUM_FORMS": 0,
            "productos-MAX_NUM_FORMS": 30,
            "productos-0-producto": self.producto.pk,
            "productos-0-lote": "L1",
            "productos-0-dosis": "2.5",
            "productos-0-unidad": "ml/l",
        }
        datos.update(extra)
        return datos

    def _foto(self):
        return SimpleUploadedFile("f.jpg", _jpeg(), content_type="image/jpeg")

    def _pendiente(self, proyecto=None):
        return Visita.objects.create(
            proyecto=proyecto or self.proyecto,
            empleado=self.empleado,
            origen=Visita.Origen.APP,
            programada_para=timezone.localdate(),
        )

    def _llamar_servicio(self, **extra):
        datos = {
            "proyecto": self.proyecto,
            "empleado": self.empleado,
            "administrador": self.admin,
            "motivo": "x",
            "realizada_en": timezone.now(),
            "puntos": [self.punto],
            "datos": {},
            "productos_aplicados": [],
            "fotos": [],
        }
        datos.update(extra)
        return registrar_visita_manual(**datos)

    def test_hora_futura_marca_el_campo_y_viene_cargada_la_actual(self):
        respuesta = self.client.get(self.url)
        campo = respuesta.context["form"].fields["realizada_en"]
        inicial = campo.initial
        self.assertEqual(campo.widget.attrs["max"], inicial)
        self.assertEqual(inicial, timezone.localtime().strftime("%Y-%m-%dT%H:%M"))
        futura = (timezone.localtime() + timedelta(minutes=30)).strftime(
            "%Y-%m-%dT%H:%M"
        )
        respuesta = self.client.post(self.url, self._datos(realizada_en=futura))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.context["form"].errors["realizada_en"],
            ["La fecha y hora de la visita no puede ser posterior a la hora actual."],
        )
        self.assertEqual(Visita.objects.count(), 1)

    def test_exige_motivo_y_pasa_por_el_servicio(self):
        respuesta = self.client.post(self.url, self._datos(motivo=" "))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("motivo", respuesta.context["form"].errors)
        self.assertEqual(Visita.objects.count(), 1)
        with mock.patch(
            "apps.visitas.panel_views.registrar_visita_manual",
            wraps=registrar_visita_manual,
        ) as servicio:
            respuesta = self.client.post(
                self.url, self._datos(fotos=[self._foto(), self._foto()])
            )
        servicio.assert_called_once()
        visita = Visita.objects.exclude(pk=self.visita.pk).get()
        self.assertRedirects(
            respuesta, reverse("panel:visitas:ficha", args=[visita.pk])
        )
        self.assertEqual(visita.origen, Visita.Origen.MANUAL)
        self.assertEqual(visita.estado, Visita.Estado.REALIZADA)
        self.assertEqual(visita.asignada_por, self.admin)
        self.assertEqual(visita.motivo_manual, "La app no tenía señal")
        self.assertEqual(Foto.objects.filter(revision__visita=visita).count(), 2)
        self.assertEqual(
            visita.revisiones.get().productos.get().producto, self.producto
        )
        with self.assertRaises(ValidationError) as ctx:
            self._llamar_servicio(motivo="")
        self.assertIn("motivo", ctx.exception.message_dict)

    def test_completa_una_pendiente_del_proyecto(self):
        pendiente = self._pendiente()
        self.client.post(self.url, self._datos(pendiente=pendiente.pk))
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Visita.Estado.REALIZADA)
        self.assertEqual(pendiente.origen, Visita.Origen.MANUAL)
        self.assertEqual(pendiente.asignada_por, self.admin)

    def test_exige_al_menos_un_punto_del_sitio(self):
        ajeno = punto_de(crear_visita())
        antes = Visita.objects.count()
        respuesta = self.client.post(self.url, self._datos(puntos=[]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("puntos", respuesta.context["form"].errors)
        respuesta = self.client.post(self.url, self._datos(puntos=[ajeno.pk]))
        self.assertIn("puntos", respuesta.context["form"].errors)
        self.assertEqual(Visita.objects.count(), antes)
        with self.assertRaises(ValidationError) as ctx:
            self._llamar_servicio(puntos=[ajeno])
        self.assertIn("puntos", ctx.exception.message_dict)

    def test_una_revision_por_punto_elegido(self):
        sala = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Sala", orden=1
        )
        self.client.post(self.url, self._datos(puntos=[self.punto.pk, sala.pk]))
        visita = Visita.objects.exclude(pk=self.visita.pk).get()
        self.assertEqual([r.punto for r in visita.revisiones.all()], [self.punto, sala])

    def test_manual_elige_puntos_revisados(self):
        sala = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Sala", orden=1
        )
        inactivo = PuntoControl.objects.create(
            sitio=self.proyecto.sitio, nombre="Baja", orden=2, activo=False
        )
        ajeno = punto_de(crear_visita())
        respuesta = self.client.get(self.url)
        opciones = list(respuesta.context["form"].fields["puntos"].queryset)
        self.assertEqual(opciones, [self.punto, sala])
        self.assertNotIn(inactivo, opciones)
        self.assertNotIn(ajeno, opciones)
        self.assertContains(respuesta, 'type="checkbox" name="puntos"', count=2)
        self.client.post(self.url, self._datos(puntos=[sala.pk]))
        visita = (
            Visita.objects.filter(proyecto=self.proyecto)
            .exclude(pk=self.visita.pk)
            .get()
        )
        self.assertEqual([r.punto for r in visita.revisiones.all()], [sala])

    def test_pendiente_con_revisiones_no_se_ofrece(self):
        con_revisiones = self._pendiente()
        crear_revision(con_revisiones)
        limpia = self._pendiente()
        respuesta = self.client.get(self.url)
        ofrecidas = list(respuesta.context["form"].fields["pendiente"].queryset)
        self.assertEqual(ofrecidas, [limpia])
        respuesta = self.client.post(self.url, self._datos(pendiente=con_revisiones.pk))
        self.assertIn("pendiente", respuesta.context["form"].errors)
        with self.assertRaises(ValidationError) as ctx:
            self._llamar_servicio(pendiente=con_revisiones)
        self.assertIn("pendiente", ctx.exception.message_dict)
        con_revisiones.refresh_from_db()
        self.assertEqual(con_revisiones.estado, Visita.Estado.PENDIENTE)
        self.assertEqual(con_revisiones.revisiones.count(), 1)

    def test_pendiente_de_otro_proyecto_se_rechaza(self):
        otro = Proyecto.objects.create(
            sitio=self.proyecto.sitio,
            tipo_servicio=self.proyecto.tipo_servicio,
            titulo="Otro",
            encargado_inicial=self.empleado,
            encargado_actual=self.empleado,
        )
        ajena = self._pendiente(otro)
        respuesta = self.client.post(self.url, self._datos(pendiente=ajena.pk))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("pendiente", respuesta.context["form"].errors)
        ajena.refresh_from_db()
        self.assertEqual(ajena.estado, Visita.Estado.PENDIENTE)

    def test_atraso_exige_confirmacion_y_queda_anotado(self):
        vieja = (timezone.localtime() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M")
        respuesta = self.client.post(self.url, self._datos(realizada_en=vieja))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("confirmar_atraso", respuesta.context["form"].errors)
        self.assertEqual(Visita.objects.count(), 1)
        self.client.post(
            self.url, self._datos(realizada_en=vieja, confirmar_atraso="on")
        )
        visita = Visita.objects.exclude(pk=self.visita.pk).get()
        self.assertEqual(
            visita.history.first().history_change_reason,
            "Carga manual atrasada confirmada por adm-pv",
        )

    def test_rechaza_fecha_anterior_al_proyecto_y_sitio_de_baja(self):
        anterior = (self.proyecto.creado - timedelta(days=2)).astimezone()
        anterior = anterior.strftime("%Y-%m-%dT%H:%M")
        respuesta = self.client.post(
            self.url, self._datos(realizada_en=anterior, confirmar_atraso="on")
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("realizada_en", respuesta.context["form"].errors)
        self.assertEqual(Visita.objects.count(), 1)
        sitio = self.proyecto.sitio
        for objeto in (sitio, sitio.cliente):
            with self.subTest(baja=objeto._meta.model_name):
                # `update` evita la cascada de la baja del sitio sobre sus puntos.
                type(objeto).objects.filter(pk=objeto.pk).update(activo=False)
                respuesta = self.client.post(self.url, self._datos())
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["form"].non_field_errors())
                self.assertEqual(Visita.objects.count(), 1)
                type(objeto).objects.filter(pk=objeto.pk).update(activo=True)
        respuesta = self.client.post(self.url, self._datos())
        self.assertEqual(respuesta.status_code, 302)

    def test_reasignar_deja_motivo_en_historial(self):
        otro = User.objects.create_user(
            "emp-reasig", password="x", rol=User.Rol.EMPLEADO
        )
        propia = self._pendiente()
        ajena = self._pendiente()
        self.client.post(self.url, self._datos(pendiente=ajena.pk, empleado=otro.pk))
        self.client.post(self.url, self._datos(pendiente=propia.pk))
        motivo = "Reasignada en carga manual por adm-pv"

        def razones(visita):
            return [h.history_change_reason for h in visita.history.all()]

        ajena.refresh_from_db()
        self.assertEqual(ajena.empleado, otro)
        self.assertIn(motivo, razones(ajena))
        propia.refresh_from_db()
        self.assertEqual(propia.estado, Visita.Estado.REALIZADA)
        self.assertNotIn(motivo, razones(propia))

    def test_pide_los_campos_del_esquema_una_sola_vez(self):
        with CaptureQueriesContext(connection) as consultas:
            self.client.get(self.url)
        campos = [
            c
            for c in consultas.captured_queries
            if "servicios_campoplanilla" in c["sql"]
        ]
        self.assertEqual(len(campos), 1, campos)

    def test_planilla_invalida_muestra_errores(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Cebos colocados",
            clave="cebos",
            tipo=CampoPlanilla.Tipo.NUMERO,
            obligatorio=True,
        )
        respuesta = self.client.post(self.url, self._datos(datos_cebos="abc"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("datos_cebos", respuesta.context["form"].errors)
        self.assertContains(respuesta, "Cebos colocados")
        self.assertContains(respuesta, 'class="error"')
        respuesta = self.client.post(self.url, self._datos())
        self.assertIn("datos_cebos", respuesta.context["form"].errors)
        self.assertEqual(Visita.objects.count(), 1)
        self.client.post(self.url, self._datos(datos_cebos="4"))
        visita = Visita.objects.exclude(pk=self.visita.pk).get()
        self.assertEqual(visita.revisiones.get().datos, {"cebos": 4})

    def test_planilla_de_ambito_visita_va_a_la_visita(self):
        CampoPlanilla.objects.create(
            tipo_servicio=self.proyecto.tipo_servicio,
            orden=1,
            etiqueta="Resumen de la jornada",
            clave="resumen",
            tipo=CampoPlanilla.Tipo.TEXTO,
            obligatorio=True,
            ambito=CampoPlanilla.Ambito.VISITA,
        )
        respuesta = self.client.post(self.url, self._datos())
        self.assertIn("datosv_resumen", respuesta.context["form"].errors)
        self.client.post(self.url, self._datos(datosv_resumen="Todo en orden"))
        visita = Visita.objects.exclude(pk=self.visita.pk).get()
        self.assertEqual(visita.datos, {"resumen": "Todo en orden"})
        self.assertEqual(visita.revisiones.get().datos, {})

    def test_foto_invalida_no_deja_visita_ni_archivos(self):
        antes = self._archivos()
        falsa = SimpleUploadedFile("f.jpg", b"no es imagen", content_type="image/jpeg")
        respuesta = self.client.post(self.url, self._datos(fotos=[self._foto(), falsa]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("fotos", respuesta.context["form"].errors)
        self.assertEqual(Visita.objects.count(), 1)
        self.assertEqual(self._archivos(), antes)

    def test_ficha_de_proyecto_ofrece_la_carga_manual(self):
        ficha = reverse("panel:proyectos:ficha", args=[self.proyecto.pk])
        respuesta = self.client.get(ficha)
        self.assertContains(respuesta, f'href="{self.url}"')
        self.assertContains(respuesta, "Registrar visita manual")
