import http.client
import json
import socket
import threading
import time
import urllib.error
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.sitios import geocodificacion

ABRIR = "apps.sitios.geocodificacion._abrir"


def _respuesta(*items):
    return json.dumps(list(items)).encode()


class GeocodificacionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.admin = User.objects.create_user(
            "adm", password="clave-segura-123", rol=User.Rol.ADMINISTRADOR
        )
        self.url = reverse("panel:sitios:geocodificar")

    def test_exige_administrador(self):
        with mock.patch(ABRIR) as abrir:
            self.assertEqual(self.client.post(self.url, {"q": "x"}).status_code, 302)
            empleado = User.objects.create_user("emp", password="clave-segura-123")
            self.client.force_login(empleado)
            self.assertEqual(self.client.post(self.url, {"q": "x"}).status_code, 403)
        abrir.assert_not_called()

    def test_solo_post_y_texto_fuera_de_la_url(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=b"[]") as abrir:
            self.assertEqual(self.client.get(self.url, {"q": "x"}).status_code, 405)
            abrir.assert_not_called()
            self.assertEqual(self.client.post(self.url, {"q": "x"}).status_code, 200)
        self.assertNotIn("?q=", self.url)
        cliente = self.client_class(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        self.assertEqual(cliente.post(self.url, {"q": "x"}).status_code, 403)

    def test_devuelve_candidatos_validados(self):
        datos = _respuesta(
            {"display_name": "Castelli", "lat": "-36.09", "lon": "-57.79"},
            {"display_name": "Fuera de rango", "lat": "95", "lon": "0"},
            {"display_name": "No numérico", "lat": "abc", "lon": "0"},
        )
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=datos):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json()["resultados"],
            [{"nombre": "Castelli", "lat": -36.09, "lng": -57.79}],
        )

    def test_url_usa_host_fijo_y_solo_el_texto(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=b"[]") as abrir:
            self.client.post(self.url, {"q": "Calle 1 & x=y"})
        solicitud = abrir.call_args.args[0]
        self.assertTrue(
            solicitud.full_url.startswith(
                "https://nominatim.openstreetmap.org/search?q=calle+1+%26+x%3Dy"
            )
        )
        self.assertIn("format=jsonv2", solicitud.full_url)
        self.assertIn("limit=5", solicitud.full_url)
        self.assertEqual(
            solicitud.get_header("User-agent"), geocodificacion.user_agent()
        )

    def test_texto_vacio_o_largo_responde_400(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR) as abrir:
            self.assertEqual(self.client.post(self.url, {"q": "  "}).status_code, 400)
            largo = self.client.post(self.url, {"q": "a" * 201})
            self.assertEqual(largo.status_code, 400)
        abrir.assert_not_called()

    def test_sin_red_responde_503_con_mensaje(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, side_effect=urllib.error.URLError("sin red")):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)

    def test_segunda_consulta_sale_de_la_cache(self):
        self.client.force_login(self.admin)
        datos = _respuesta({"display_name": "Castelli", "lat": "-36", "lon": "-57"})
        with mock.patch(ABRIR, return_value=datos) as abrir:
            primera = self.client.post(self.url, {"q": "Castelli"})
            segunda = self.client.post(self.url, {"q": "  CASTELLI "})
        self.assertEqual(abrir.call_count, 1)
        self.assertEqual(primera.json(), segunda.json())

    def test_limite_de_una_consulta_por_segundo(self):
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=b"[]") as abrir:
            self.client.post(self.url, {"q": "uno"})
            r = self.client.post(self.url, {"q": "dos"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)
        self.assertEqual(abrir.call_count, 1)

    def test_formulario_de_alta_permite_teselas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("panel:sitios:alta"))
        self.assertIn("tile.openstreetmap.org", r["Content-Security-Policy"])
        self.assertContains(r, reverse("panel:sitios:geocodificar"))

    def test_json_muy_anidado_responde_503(self):
        self.client.force_login(self.admin)
        anidado = b"[" * 100_000
        with mock.patch(ABRIR, return_value=anidado):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)

    @override_settings(
        SITE_URL="https://ejemplo.test", CORREO_CONTACTO="a@ejemplo.test"
    )
    def test_user_agent_usa_producto_y_correo_de_settings(self):
        self.assertEqual(
            geocodificacion.user_agent(),
            "Detach/1.0 (+https://ejemplo.test; a@ejemplo.test)",
        )
        with mock.patch(ABRIR, return_value=_respuesta()) as abrir:
            geocodificacion.buscar("Castelli")
        cabeceras = dict(abrir.call_args.args[0].header_items())
        self.assertEqual(
            cabeceras["User-agent"],
            "Detach/1.0 (+https://ejemplo.test; a@ejemplo.test)",
        )

    def test_respuesta_lenta_corta_por_tiempo_total(self):
        class Lenta:
            status = 200

            def read1(self, cantidad):
                time.sleep(0.05)
                return b" "

            def close(self):
                pass

        class Conexion:
            sock = None

            def __init__(self, *args, **kwargs):
                pass

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                return Lenta()

            def close(self):
                pass

        self.client.force_login(self.admin)
        inicio = time.monotonic()
        with (
            mock.patch.object(geocodificacion, "_conexion", Conexion),
            mock.patch.object(geocodificacion, "LIMITE_TOTAL_SEGUNDOS", 0.3),
        ):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
        self.assertLess(time.monotonic() - inicio, 2)

    def _consultar_con(self, guion):
        """Consulta a un servidor local de un solo uso; ``guion`` hace de Nominatim.

        La consulta va por HTTP plano al servidor local (127.0.0.1, puerto efímero);
        el código de producción sigue construyendo una conexión HTTPS.
        """
        servidor = socket.socket()
        servidor.bind(("127.0.0.1", 0))
        servidor.listen(1)
        self.addCleanup(servidor.close)

        def atender():
            try:
                conexion, _ = servidor.accept()
            except OSError:
                return
            try:
                conexion.recv(4096)
                guion(conexion)
            except OSError:
                pass
            finally:
                conexion.close()

        threading.Thread(target=atender, daemon=True).start()
        url = f"http://127.0.0.1:{servidor.getsockname()[1]}/search"

        def conexion_plana(host, puerto):
            return http.client.HTTPConnection(host, puerto, timeout=1)

        self.client.force_login(self.admin)
        inicio = time.monotonic()
        with (
            mock.patch.object(geocodificacion, "URL_NOMINATIM", url),
            mock.patch.object(geocodificacion, "_conexion", conexion_plana),
            mock.patch.object(geocodificacion, "LIMITE_TOTAL_SEGUNDOS", 1),
            mock.patch.object(geocodificacion, "TIMEOUT_SEGUNDOS", 1),
        ):
            r = self.client.post(self.url, {"q": "Castelli"})
        return r, time.monotonic() - inicio

    @staticmethod
    def _gotear(conexion, texto, veces=20):
        for _ in range(veces):
            conexion.sendall(texto)
            time.sleep(0.2)

    def test_cuerpo_goteado_por_socket_real_corta_a_tiempo(self):
        def guion(conexion):
            conexion.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 100000\r\n\r\n")
            self._gotear(conexion, b" ")

        r, duracion = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)
        self.assertLess(duracion, 2.5)

    def test_cabeceras_goteadas_cortan_por_tiempo_total(self):
        def guion(conexion):
            conexion.sendall(b"HTTP/1.1 200 OK\r\nX-Lento: ")
            self._gotear(conexion, b"a")

        r, duracion = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)
        self.assertLess(duracion, 2.5)

    def test_linea_de_trozo_goteada_corta_por_tiempo_total(self):
        def guion(conexion):
            conexion.sendall(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
            self._gotear(conexion, b"0")

        r, duracion = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)
        self.assertLess(duracion, 2.5)

    def test_linea_de_trozo_goteada_con_connection_close_corta_por_tiempo_total(self):
        def guion(conexion):
            conexion.sendall(
                b"HTTP/1.1 200 OK\r\nConnection: close\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n"
            )
            self._gotear(conexion, b"0")

        r, duracion = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)
        self.assertLess(duracion, 2.5)

    def test_trailer_goteado_con_connection_close_corta_por_tiempo_total(self):
        def guion(conexion):
            conexion.sendall(
                b"HTTP/1.1 200 OK\r\nConnection: close\r\n"
                b"Transfer-Encoding: chunked\r\n\r\n0\r\nX-Lento: "
            )
            self._gotear(conexion, b"a")

        r, duracion = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)
        self.assertLess(duracion, 2.5)

    def test_vigilante_corta_con_socket_socket_shutdown(self):
        class Lenta:
            status = 200

            def read1(self, cantidad):
                time.sleep(0.05)
                return b" "

            def close(self):
                pass

        sock = mock.Mock()

        class Conexion:
            def __init__(self, *args, **kwargs):
                self.sock = sock

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                self.sock = None  # como con ``Connection: close``
                return Lenta()

            def close(self):
                pass

        self.client.force_login(self.admin)
        with (
            mock.patch.object(geocodificacion, "_conexion", Conexion),
            mock.patch.object(geocodificacion, "LIMITE_TOTAL_SEGUNDOS", 0.2),
            mock.patch.object(socket.socket, "shutdown") as apagar,
        ):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
        apagar.assert_called_once_with(sock, socket.SHUT_RDWR)
        sock.shutdown.assert_not_called()

    def test_redireccion_responde_503(self):
        recibidas = []

        def guion(conexion):
            recibidas.append(1)
            conexion.sendall(
                b"HTTP/1.1 302 Found\r\nLocation: http://127.0.0.1:1/otro\r\n"
                b"Content-Length: 0\r\n\r\n"
            )

        r, _ = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["error"], geocodificacion.MENSAJE_CARGA_MANUAL)
        self.assertEqual(len(recibidas), 1)

    def test_estado_distinto_de_200_responde_503(self):
        def guion(conexion):
            conexion.sendall(b"HTTP/1.1 500 Error\r\nContent-Length: 2\r\n\r\n[]")

        r, _ = self._consultar_con(guion)
        self.assertEqual(r.status_code, 503)

    def test_numero_enorme_no_da_500(self):
        datos = json.dumps([{"display_name": "x", "lat": 10**400, "lon": 1}]).encode()
        self.client.force_login(self.admin)
        with mock.patch(ABRIR, return_value=datos):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["resultados"], [])

    def test_error_de_protocolo_http_responde_503(self):
        self.client.force_login(self.admin)
        error = http.client.IncompleteRead(b"abc", 10)
        with mock.patch(ABRIR, side_effect=error):
            r = self.client.post(self.url, {"q": "Castelli"})
        self.assertEqual(r.status_code, 503)
