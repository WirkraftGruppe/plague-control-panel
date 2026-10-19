"""Búsqueda de direcciones en Nominatim para ayudar a cargar coordenadas.

Solo se envía a Nominatim el texto de dirección que escribe el administrador en el
buscador; nunca nombres de clientes, de sitios ni de contactos.
"""

import hashlib
import http.client
import json
import logging
import math
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

URL_NOMINATIM = "https://nominatim.openstreetmap.org/search"
TIMEOUT_SEGUNDOS = 5
LIMITE_TOTAL_SEGUNDOS = 5
MAX_BYTES = 1_000_000
TAMANO_BLOQUE = 16_384
DURACION_CACHE = 24 * 60 * 60
MAX_LARGO_TEXTO = 200
MAX_CANDIDATOS = 5
CLAVE_TURNO = "sitios:geocodificacion:turno"
MENSAJE_CARGA_MANUAL = (
    "No se pudo consultar la ubicación; cárguela a mano en el mapa o en los campos."
)


class GeocodificacionError(Exception):
    """La consulta no se pudo hacer o no devolvió una respuesta utilizable."""


class TextoInvalido(ValueError):
    """El texto de búsqueda está vacío o es demasiado largo."""


def user_agent():
    """User-Agent que exige Nominatim, calculado con los settings vigentes."""
    return f"Detach/1.0 (+{settings.SITE_URL}; {settings.CORREO_CONTACTO})"


def _conexion(host, puerto):
    """Conexión HTTPS con el contexto SSL por defecto (verifica el certificado)."""
    return http.client.HTTPSConnection(host, puerto, timeout=TIMEOUT_SEGUNDOS)


def _abrir(solicitud):
    """Consulta la solicitud sin seguir redirecciones y devuelve los bytes.

    Un vigilante (``threading.Timer``) corta el socket al vencer
    ``LIMITE_TOTAL_SEGUNDOS``: la cota total cubre las cabeceras, las líneas de
    control del chunked (tamaño de trozo y trailer) y el cuerpo, que se lee con
    ``read1``. Fuera de la cota queda la resolución DNS (``getaddrinfo`` no admite
    timeout) y el connect, que acota solo ``TIMEOUT_SEGUNDOS``; si el vigilante
    vence antes de que exista el socket, se detecta apenas la conexión avanza.
    Todo estado distinto de 200 (incluidas las redirecciones) es un error.
    """
    destino = urllib.parse.urlsplit(solicitud.full_url)
    ruta = f"{destino.path}?{destino.query}"
    conexion = _conexion(destino.hostname, destino.port)
    vencido = threading.Event()
    activo = []

    def cortar():
        vencido.set()
        # Referencia propia: con ``Connection: close`` getresponse() deja
        # ``conexion.sock`` en None. El shutdown va al fd sin pasar por
        # ``SSLSocket.shutdown``, que anula ``_sslobj`` mientras otro hilo lee.
        sock = activo[0] if activo else conexion.sock
        if sock is not None:
            try:
                socket.socket.shutdown(sock, socket.SHUT_RDWR)
            except OSError:
                pass

    def comprobar():
        if vencido.is_set():
            raise TimeoutError("se superó el tiempo total de la consulta")

    vigilante = threading.Timer(LIMITE_TOTAL_SEGUNDOS, cortar)
    vigilante.daemon = True
    vigilante.start()
    partes = []
    leidos = 0
    respuesta = None
    try:
        conexion.request("GET", ruta, headers=dict(solicitud.header_items()))
        activo.append(conexion.sock)
        comprobar()
        respuesta = conexion.getresponse()
        comprobar()
        if respuesta.status != 200:
            raise GeocodificacionError(f"estado {respuesta.status}")
        while leidos < MAX_BYTES:
            bloque = respuesta.read1(min(TAMANO_BLOQUE, MAX_BYTES - leidos))
            comprobar()
            if not bloque:
                break
            partes.append(bloque)
            leidos += len(bloque)
    except (OSError, http.client.HTTPException):
        comprobar()
        raise
    finally:
        vigilante.cancel()
        if respuesta is not None:
            respuesta.close()
        conexion.close()
    return b"".join(partes)


def normalizar(texto):
    """Minúsculas y espacios colapsados; valida que no esté vacío ni sea largo."""
    texto = " ".join((texto or "").split())
    if not texto or len(texto) > MAX_LARGO_TEXTO:
        raise TextoInvalido(texto)
    return texto.casefold()


def _coordenada(valor, limite):
    numero = float(valor)
    if not math.isfinite(numero) or abs(numero) > limite:
        raise ValueError(valor)
    return numero


def _candidatos(datos):
    resultado = []
    if not isinstance(datos, list):
        raise GeocodificacionError("respuesta inesperada")
    for item in datos:
        try:
            resultado.append(
                {
                    "nombre": str(item["display_name"])[:300],
                    "lat": _coordenada(item["lat"], 90),
                    "lng": _coordenada(item["lon"], 180),
                }
            )
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if len(resultado) == MAX_CANDIDATOS:
            break
    return resultado


def buscar(texto):
    """Hasta 5 candidatos ``{nombre, lat, lng}`` para el texto de dirección.

    Lanza ``TextoInvalido`` si el texto no sirve y ``GeocodificacionError`` si no se
    pudo consultar (sin red, error, o más de una consulta por segundo).
    """
    normalizado = normalizar(texto)
    clave = "sitios:geocodificacion:" + hashlib.sha256(normalizado.encode()).hexdigest()
    guardado = cache.get(clave)
    if guardado is not None:
        return guardado
    if not cache.add(CLAVE_TURNO, 1, 1):
        raise GeocodificacionError("límite de una consulta por segundo")
    parametros = urllib.parse.urlencode(
        {"q": normalizado, "format": "jsonv2", "limit": MAX_CANDIDATOS}
    )
    solicitud = urllib.request.Request(
        f"{URL_NOMINATIM}?{parametros}",
        headers={"User-Agent": user_agent(), "Accept-Language": "es"},
    )
    try:
        candidatos = _candidatos(json.loads(_abrir(solicitud)))
    except (
        urllib.error.URLError,
        OSError,
        ValueError,
        RecursionError,
        OverflowError,
        http.client.HTTPException,
    ) as error:
        logger.warning("Falló la consulta a Nominatim: %s", type(error).__name__)
        raise GeocodificacionError(str(error)) from error
    cache.set(clave, candidatos, DURACION_CACHE)
    return candidatos
