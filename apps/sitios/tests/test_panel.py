import tempfile
from decimal import Decimal
from io import BytesIO

import pypdfium2
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from PIL import Image

from apps.clientes.models import Cliente
from apps.sitios import qr
from apps.sitios.models import Plano, PuntoControl, Sitio

User = get_user_model()

MEDIA_TEMPORAL = tempfile.mkdtemp(prefix="sitios-panel-test-")


def _png(tamano=(300, 200)):
    buffer = BytesIO()
    Image.new("RGB", tamano, "white").save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf():
    documento = pypdfium2.PdfDocument.new()
    documento.new_page(400, 200)
    buffer = BytesIO()
    documento.save(buffer)
    return buffer.getvalue()


class SitioPanelTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.admin)
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta Ñandú 1")

    def _datos(self, **extra):
        datos = {
            "cliente": self.cliente.pk,
            "nombre": "Depósito Norte",
            "sector": Sitio.Sector.OTRO,
            "latitud": "-35.123456",
            "longitud": "-57.654321",
            "activo": "on",
        }
        datos.update(extra)
        return datos

    def test_filtro_cliente_no_ascii_no_da_500(self):
        # "²" y los dígitos árabes pasan isdigit() pero no son enteros para la base.
        for valor in ("²", "٣", "1²"):
            r = self.client.get(reverse("panel:sitios:listado"), {"cliente": valor})
            self.assertEqual(r.status_code, 200, valor)
        r = self.client.get(
            reverse("panel:sitios:listado"), {"cliente": str(self.cliente.pk)}
        )
        self.assertContains(r, "Planta Ñandú 1")

    def test_filtro_cliente_fuera_de_rango_no_da_500(self):
        # Más de 4300 dígitos rompe int(); más de 2**63 - 1 desborda la base.
        for valor in ("9" * 4301, "9223372036854775808", "0" * 25):
            r = self.client.get(reverse("panel:sitios:listado"), {"cliente": valor})
            self.assertEqual(r.status_code, 200, valor[:30])
        r = self.client.get(
            reverse("panel:sitios:listado"), {"cliente": "9223372036854775807"}
        )
        self.assertEqual(r.status_code, 200)

    def test_ficha_muestra_atribucion_osm(self):
        url = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        r = self.client.get(url, {"pestana": "datos"})
        self.assertContains(r, "colaboradores de OpenStreetMap</a>")
        r = self.client.get(reverse("panel:sitios:alta"))
        self.assertContains(r, "https://www.openstreetmap.org/copyright")

    def test_pestana_datos_muestra_el_mapa_del_sitio_y_no_los_puntos(self):
        url = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        r = self.client.get(url, {"pestana": "datos"})
        self.assertContains(r, "El sitio no tiene ubicación cargada.")
        self.assertNotContains(r, 'id="mapa-sitio"')
        self.sitio.latitud = Decimal("-35.123456")
        self.sitio.longitud = Decimal("-57.654321")
        self.sitio.save()
        r = self.client.get(url, {"pestana": "datos"})
        self.assertContains(r, "Ubicación del sitio")
        self.assertContains(r, 'id="mapa-sitio"')
        self.assertContains(r, "sitios/sitio_ficha_mapa.js")
        self.assertContains(
            r,
            reverse("panel:sitios:editar", args=[self.sitio.pk]) + '">Editar ubicación',
        )
        self.assertEqual(
            r.context["datos_mapa"],
            {
                "sitio": {
                    "nombre": "Planta Ñandú 1",
                    "lat": -35.123456,
                    "lng": -57.654321,
                }
            },
        )
        for ausente in ("mapa-punto", "puntos_mapa.js", "propuesta"):
            self.assertNotContains(r, ausente)

    def test_descargar_qr_png_con_nombre(self):
        r = self.client.get(
            reverse("panel:sitios:punto_qr_png", args=[self.sitio.puntos.get().pk])
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(
            r["Content-Disposition"],
            'attachment; filename="qr-planta-nandu-1-general.png"',
        )
        self.assertEqual(Image.open(BytesIO(r.content)).format, "PNG")
        self.assertEqual(
            r.content,
            qr.png_qr(self.sitio.puntos.get()),
            "El PNG es el del punto General",
        )

    def test_regenerar_qr_invalida_el_anterior(self):
        general = self.sitio.puntos.get()
        url = reverse("panel:sitios:punto_regenerar_qr", args=[general.pk])
        anterior = general.qr_codigo
        self.assertEqual(self.client.get(url).status_code, 200)
        general.refresh_from_db()
        self.assertEqual(general.qr_codigo, anterior)
        self.client.post(url)
        general.refresh_from_db()
        self.assertNotEqual(general.qr_codigo, anterior)
        self.assertFalse(PuntoControl.objects.filter(qr_codigo=anterior).exists())

    def test_alta_y_edicion_guardan_lat_lng(self):
        r = self.client.post(reverse("panel:sitios:alta"), self._datos())
        self.assertEqual(r.status_code, 302)
        nuevo = Sitio.objects.get(nombre="Depósito Norte")
        self.assertEqual(nuevo.latitud, Decimal("-35.123456"))
        self.assertEqual(nuevo.longitud, Decimal("-57.654321"))
        self.client.post(
            reverse("panel:sitios:editar", args=[nuevo.pk]),
            self._datos(latitud="-36.5", longitud="-58.25"),
        )
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.latitud, Decimal("-36.5"))
        self.assertEqual(nuevo.longitud, Decimal("-58.25"))

    @override_settings(SITE_URL="https://ejemplo.test")
    def test_contenido_qr_usa_site_url(self):
        general = self.sitio.puntos.get()
        self.assertEqual(
            qr.contenido_qr(general),
            f"https://ejemplo.test/q/{general.qr_codigo}/",
        )

    def test_listado_filtra_y_exige_administrador(self):
        otro = Cliente.objects.create(razon_social="Otra")
        Sitio.objects.create(cliente=otro, nombre="Silo", activo=False)
        url = reverse("panel:sitios:listado")
        r = self.client.get(url, {"cliente": otro.pk, "activo": "0"})
        self.assertContains(r, "Silo")
        self.assertNotContains(r, "Planta")
        self.assertEqual(self.client.get(url, {"q": "Planta"}).status_code, 200)
        self.client.force_login(
            User.objects.create_user("emp", password="clave-segura-123")
        )
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_ficha_muestra_el_qr(self):
        r = self.client.get(
            reverse("panel:sitios:ficha", args=[self.sitio.pk]), {"pestana": "datos"}
        )
        general = self.sitio.puntos.get()
        self.assertContains(r, reverse("panel:sitios:punto_qr_png", args=[general.pk]))


class _BaseAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.client.force_login(self.admin)
        self.cliente = Cliente.objects.create(razon_social="ACME")
        self.sitio = Sitio.objects.create(cliente=self.cliente, nombre="Planta 1")
        self.general = self.sitio.puntos.get()

    def _entrar_como_empleado(self):
        self.client.force_login(
            User.objects.create_user("emp", password="clave-segura-123")
        )


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL)
class PlanoPanelTests(_BaseAdminTests):
    def setUp(self):
        super().setUp()
        self.plano = Plano.objects.create(
            sitio=self.sitio,
            nombre="Planta baja",
            imagen=SimpleUploadedFile("p.png", _png()),
        )
        self.general.plano = self.plano
        self.general.save()

    def _subir(self, contenido, nombre="plano.bin"):
        return self.client.post(
            reverse("panel:sitios:plano_alta", args=[self.sitio.pk]),
            {"nombre": "Primer piso", "imagen": SimpleUploadedFile(nombre, contenido)},
        )

    def test_arrastrar_marcador_guarda_xy(self):
        url = reverse("panel:sitios:punto_posicion", args=[self.general.pk])
        r = self.client.post(url, {"x": "0.25", "y": "0.7500"})
        self.assertEqual(r.status_code, 200)
        self.general.refresh_from_db()
        self.assertEqual(
            (self.general.x, self.general.y), (Decimal("0.25"), Decimal("0.75"))
        )
        for x, y in (("1.5", "0.5"), ("-0.1", "0.5"), ("0.5", "x"), ("0.5", "")):
            self.assertEqual(self.client.post(url, {"x": x, "y": y}).status_code, 400)
        self.general.refresh_from_db()
        self.assertEqual(
            (self.general.x, self.general.y), (Decimal("0.25"), Decimal("0.75"))
        )
        self.assertEqual(self.client.get(url).status_code, 405)
        self._entrar_como_empleado()
        self.assertEqual(
            self.client.post(url, {"x": "0.1", "y": "0.1"}).status_code, 403
        )

    def test_ubicar_punto_sin_plano_con_clic(self):
        suelto = PuntoControl.objects.create(sitio=self.sitio, nombre="Suelto")
        url = reverse("panel:sitios:punto_posicion", args=[suelto.pk])
        self.assertEqual(
            self.client.post(url, {"x": "0.3", "y": "0.4"}).status_code, 400
        )
        r = self.client.post(url, {"plano": self.plano.pk, "x": "0.3", "y": "0.4"})
        self.assertEqual(r.status_code, 200)
        suelto.refresh_from_db()
        self.assertEqual(
            (suelto.plano, suelto.x, suelto.y),
            (self.plano, Decimal("0.3"), Decimal("0.4")),
        )

    def test_plano_ofrece_crear_y_lista_sin_ubicar(self):
        suelto = PuntoControl.objects.create(sitio=self.sitio, nombre="Suelto")
        sin_xy = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Sin xy", plano=self.plano
        )
        inactivo = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Baja", activo=False
        )
        r = self.client.get(
            reverse("panel:sitios:ficha", args=[self.sitio.pk]),
            {"pestana": "planos", "plano": self.plano.pk},
        )
        self.assertContains(r, "Crear nuevo punto")
        self.assertContains(r, "Sin ubicar en este plano")
        self.assertContains(r, "Suelto")
        sin_ubicar = {p["id"] for p in r.context["datos_plano"]["sin_ubicar"]}
        self.assertEqual(sin_ubicar, {self.general.pk, suelto.pk, sin_xy.pk})
        self.assertNotIn(inactivo.pk, sin_ubicar)

    def test_ubicar_en_plano_de_otro_sitio_da_400(self):
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Otra")
        ajeno = Plano.objects.create(
            sitio=otro, nombre="Ajeno", imagen=SimpleUploadedFile("a.png", _png())
        )
        url = reverse("panel:sitios:punto_posicion", args=[self.general.pk])
        for plano in (ajeno.pk, 999999, "x"):
            r = self.client.post(url, {"plano": plano, "x": "0.9", "y": "0.9"})
            self.assertEqual(r.status_code, 400)
        self.general.refresh_from_db()
        self.assertEqual(self.general.plano, self.plano)
        self.assertIsNone(self.general.x)

    def test_plano_invalido_o_inactivo_da_400(self):
        inactivo = Plano.objects.create(
            sitio=self.sitio,
            nombre="Viejo",
            imagen=SimpleUploadedFile("v.png", _png()),
            activo=False,
        )
        suelto = PuntoControl.objects.create(sitio=self.sitio, nombre="Suelto")
        url = reverse("panel:sitios:punto_posicion", args=[suelto.pk])
        for plano in ("²", "٣", inactivo.pk, ""):
            r = self.client.post(url, {"plano": plano, "x": "0.9", "y": "0.9"})
            self.assertEqual(r.status_code, 400, plano)
        suelto.refresh_from_db()
        self.assertIsNone(suelto.plano)

    def test_subir_pdf_crea_plano_y_rechaza_otro_formato(self):
        r = self._subir(_pdf(), "plano.pdf")
        self.assertEqual(r.status_code, 302)
        nuevo = Plano.objects.get(nombre="Primer piso")
        self.assertEqual((nuevo.ancho_px, nuevo.alto_px), (4000, 2000))
        buffer = BytesIO()
        Image.new("RGB", (30, 30)).save(buffer, format="GIF")
        for invalido in (buffer.getvalue(), b"no es un plano"):
            r = self._subir(invalido)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "no es una imagen JPG, PNG ni un PDF")
        self.assertEqual(Plano.objects.count(), 2)

    def test_imagen_del_plano_la_sirve_el_panel_solo_al_administrador(self):
        url = reverse("panel:sitios:plano_imagen", args=[self.plano.pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(r["Cache-Control"], "private, no-store")
        ficha = self.client.get(
            reverse("panel:sitios:ficha", args=[self.sitio.pk]),
            {"pestana": "planos", "plano": self.plano.pk},
        )
        self.assertContains(ficha, url)
        self.assertNotContains(ficha, "/media/")
        self._entrar_como_empleado()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_clic_en_el_plano_da_de_alta_un_punto(self):
        url = reverse("panel:sitios:punto_alta", args=[self.sitio.pk])
        r = self.client.post(
            url,
            {
                "nombre": "Cocina",
                "activo": "on",
                "plano": self.plano.pk,
                "x": "0.4",
                "y": "0.6",
                "orden": 1,
            },
        )
        self.assertEqual(r.status_code, 302)
        punto = self.sitio.puntos.get(nombre="Cocina")
        self.assertEqual(
            (punto.plano, punto.x, punto.y),
            (self.plano, Decimal("0.4"), Decimal("0.6")),
        )
        otro = Sitio.objects.create(cliente=self.cliente, nombre="Otra")
        ajeno = Plano.objects.create(
            sitio=otro, nombre="Ajeno", imagen=SimpleUploadedFile("a.png", _png())
        )
        r = self.client.post(url, {"nombre": "Mal", "plano": ajeno.pk, "orden": 0})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.sitio.puntos.filter(nombre="Mal").exists())


class PuntoPanelTests(_BaseAdminTests):
    def test_alta_sin_campos_de_coordenadas(self):
        r = self.client.get(reverse("panel:sitios:punto_alta", args=[self.sitio.pk]))
        self.assertContains(r, "La ubicación se toma del primer escaneo")
        self.assertNotIn("latitud", r.context["form"].fields)
        self.assertNotIn("longitud", r.context["form"].fields)
        r = self.client.get(
            reverse("panel:sitios:punto_editar", args=[self.general.pk])
        )
        self.assertIn("latitud", r.context["form"].fields)

    def test_aviso_punto_fijado_por_escaneo(self):
        otro = PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        ficha = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        editar = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        for url in (ficha, editar):
            self.assertNotContains(self.client.get(url), "Punto fijado por escaneo")
        PuntoControl.objects.filter(pk=self.general.pk).update(
            ubicacion_fijada_en=timezone.now(), ubicacion_fijada_por=self.admin
        )
        r = self.client.get(ficha, {"pestana": "datos"})
        self.assertContains(r, "Punto fijado por escaneo", count=1)
        self.assertContains(self.client.get(editar), "Punto fijado por escaneo")
        editar_otro = reverse("panel:sitios:punto_editar", args=[otro.pk])
        self.assertNotContains(self.client.get(editar_otro), "Punto fijado por escaneo")

    def test_desactivar_el_ultimo_punto_se_rechaza_con_aviso(self):
        baja = reverse("panel:sitios:punto_desactivar", args=[self.general.pk])
        r = self.client.post(baja, follow=True)
        self.assertContains(r, "último punto activo")
        self.general.refresh_from_db()
        self.assertTrue(self.general.activo)

    def _datos_edicion(self, **extra):
        return {"nombre": "General", "orden": 0, "activo": "on", **extra}

    def _fijar_por_escaneo(self):
        PuntoControl.objects.filter(pk=self.general.pk).update(
            latitud="-35.100000",
            longitud="-58.100000",
            ubicacion_fijada_en=timezone.now(),
            ubicacion_fijada_por=self.admin,
        )

    def test_corregir_coordenadas_limpia_fijada_por_escaneo(self):
        self._fijar_por_escaneo()
        url = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        r = self.client.post(
            url, self._datos_edicion(latitud="-35.2", longitud="-58.100000")
        )
        self.assertEqual(r.status_code, 302)
        self.general.refresh_from_db()
        self.assertEqual(str(self.general.latitud), "-35.200000")
        self.assertIsNone(self.general.ubicacion_fijada_por)
        self.assertIsNone(self.general.ubicacion_fijada_en)

    def test_corregir_coordenadas_limpia_precision(self):
        self._fijar_por_escaneo()
        PuntoControl.objects.filter(pk=self.general.pk).update(precision_m=12)
        url = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        self.client.post(
            url, self._datos_edicion(latitud="-35.2", longitud="-58.100000")
        )
        self.general.refresh_from_db()
        self.assertIsNone(self.general.precision_m)

    def test_editar_sin_cambiar_coordenadas_conserva_fijada(self):
        self._fijar_por_escaneo()
        url = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        r = self.client.post(
            url,
            self._datos_edicion(
                nombre="Entrada", latitud="-35.100000", longitud="-58.100000"
            ),
        )
        self.assertEqual(r.status_code, 302)
        self.general.refresh_from_db()
        self.assertEqual(self.general.nombre, "Entrada")
        self.assertEqual(self.general.ubicacion_fijada_por, self.admin)
        self.assertIsNotNone(self.general.ubicacion_fijada_en)

    def test_destildar_activo_del_ultimo_punto_se_rechaza(self):
        url = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        datos = self._datos_edicion(nombre="Otro nombre")
        del datos["activo"]
        r = self.client.post(url, datos)
        self.assertEqual(r.status_code, 200)
        self.assertIn(
            "último punto activo", " ".join(r.context["form"].errors["activo"])
        )
        self.general.refresh_from_db()
        self.assertTrue(self.general.activo)
        self.assertEqual(self.general.nombre, "General")

    def test_destildar_activo_con_otro_activo_desactiva(self):
        PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        url = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        datos = self._datos_edicion()
        del datos["activo"]
        r = self.client.post(url, datos)
        self.assertEqual(r.status_code, 302)
        self.general.refresh_from_db()
        self.assertFalse(self.general.activo)

    def test_qr_png_por_punto_y_regenerar(self):
        punto = PuntoControl.objects.create(
            sitio=self.sitio, nombre="Cocina", sector="Planta alta", orden=1
        )
        r = self.client.get(reverse("panel:sitios:punto_qr_png", args=[punto.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertEqual(r.content, qr.png_qr(punto))
        self.assertNotEqual(r.content, qr.png_qr(self.general))
        self.assertGreater(
            Image.open(BytesIO(r.content)).height,
            Image.open(BytesIO(qr.png_qr(self.general))).height,
            "El sector suma una línea al pie",
        )
        url = reverse("panel:sitios:punto_regenerar_qr", args=[punto.pk])
        anterior = punto.qr_codigo
        self.assertContains(self.client.get(url), "Regenerar")
        punto.refresh_from_db()
        self.assertEqual(punto.qr_codigo, anterior)
        self.assertEqual(self.client.post(url).status_code, 302)
        punto.refresh_from_db()
        self.assertNotEqual(punto.qr_codigo, anterior)
        self.assertFalse(PuntoControl.objects.filter(qr_codigo=anterior).exists())

    def test_editar_punto_con_qr_impreso_y_desactivar(self):
        url = reverse("panel:sitios:punto_editar", args=[self.general.pk])
        r = self.client.post(
            url,
            {
                "nombre": "Entrada",
                "sector": "Hall",
                "orden": 0,
                "activo": "on",
                "qr_impreso_el": "2026-10-01",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.general.refresh_from_db()
        self.assertEqual(self.general.nombre, "Entrada")
        self.assertEqual(str(self.general.qr_impreso_el), "2026-10-01")
        PuntoControl.objects.create(sitio=self.sitio, nombre="Cocina", orden=1)
        baja = reverse("panel:sitios:punto_desactivar", args=[self.general.pk])
        self.assertContains(self.client.get(baja), "Desactivar")
        self.client.post(baja)
        self.general.refresh_from_db()
        self.assertFalse(self.general.activo)

    def test_ficha_con_pestanas_sondeo_y_leaflet(self):
        ficha = reverse("panel:sitios:ficha", args=[self.sitio.pk])
        for pestana in ("turnos", "planos", "datos", "invalida"):
            self.assertEqual(
                self.client.get(ficha, {"pestana": pestana}).status_code, 200
            )
        r = self.client.get(ficha, {"pestana": "datos"})
        self.assertIn("tile.openstreetmap.org", r["Content-Security-Policy"])
        try:
            url_estado = reverse("panel:estado_sitio", args=[self.sitio.pk])
        except NoReverseMatch:
            # La URL la crea apps/panel; sin ella el contenedor no se dibuja.
            self.assertNotContains(r, "hx-get")
        else:
            self.assertContains(r, f'hx-get="{url_estado}" hx-trigger="every 5s"')
        self.assertContains(r, "sitios/sondeo.js")
        self.assertNotContains(r, "<script>")
        r = self.client.get(ficha, {"pestana": "turnos"})
        self.assertContains(r, "Sin programar", msg_prefix="Punto sin vencimiento")
        self._entrar_como_empleado()
        self.assertEqual(self.client.get(ficha).status_code, 403)


class HistorialSitioTests(TestCase):
    def test_notas_y_horario_no_van_al_historial(self):
        modelo = Sitio.history.model
        for campo in ("notas", "horario_acceso"):
            with self.assertRaises(FieldDoesNotExist):
                modelo._meta.get_field(campo)
