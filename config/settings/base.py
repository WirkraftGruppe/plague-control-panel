"""Settings compartidos por todos los entornos. Las variables salen del entorno."""

from datetime import timedelta
from pathlib import Path

import environ
from csp.constants import NONCE, NONE, SELF
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Solo se lee del entorno del proceso; no se carga ningún archivo .env.
env = environ.Env()


def leer_num_proxies():
    """Cantidad de proxies inversos de confianza (entero >= 0; default 0)."""
    crudo = env("NUM_PROXIES", default="0")
    try:
        valor = int(crudo)
    except ValueError:
        valor = -1
    if valor < 0:
        raise ImproperlyConfigured("NUM_PROXIES debe ser un entero mayor o igual a 0.")
    return valor


# Proxies inversos de confianza delante de Django; define la IP real del cliente.
NUM_PROXIES = leer_num_proxies()

# Cupos del login del panel y del admin: solo cuentan los intentos fallidos.
INTENTOS_FALLIDOS_POR_IP = 20  # fallos por IP dentro de la ventana
VENTANA_MINUTOS = 15  # ventana de los cupos por IP y por (usuario, IP)
FALLOS_POR_USUARIO_E_IP = 5  # fallos por par (usuario, IP) dentro de la ventana
FALLOS_POR_USUARIO = 50  # fallos globales por usuario, desde cualquier IP
VENTANA_USUARIO_MINUTOS = 60  # ventana del cupo global por usuario


def leer_atraso_maximo_horas():
    """Atraso máximo de `realizada_en` en una visita desde la app, en horas.

    Entero entre 1 y 8760 (un año); default 168 (una semana). El tope evita que un
    valor enorme desborde la fecha al validar y dé 500 recién en el primer uso.
    """
    crudo = env("ATRASO_MAXIMO_HORAS", default="168")
    try:
        valor = int(crudo)
    except ValueError:
        valor = 0
    if not 1 <= valor <= 8760:
        raise ImproperlyConfigured(
            "ATRASO_MAXIMO_HORAS debe ser un entero entre 1 y 8760."
        )
    return valor


# Una visita desde la app con `realizada_en` más atrasada da 400: la carga el
# administrador como manual (P-api-movil-16).
ATRASO_MAXIMO_HORAS = leer_atraso_maximo_horas()

# Una visita abierta desde hace más horas la cierra `cerrar_visitas_abiertas` con
# cierre "sistema" (plan puntos-control).
VISITA_ABIERTA_MAXIMO_HORAS = 16


def leer_distancia_maxima_m():
    """Metros entre un escaneo y el punto a partir de los cuales hay incidencia.

    Entero entre 50 y 5000; default 300. Por debajo de 50 el error del GPS de un
    teléfono marcaría incidencias falsas; por encima de 5000 la verificación deja de
    decir algo.
    """
    crudo = env("DISTANCIA_MAXIMA_M", default="300")
    try:
        valor = int(crudo)
    except ValueError:
        valor = 0
    if not 50 <= valor <= 5000:
        raise ImproperlyConfigured(
            "DISTANCIA_MAXIMA_M debe ser un entero entre 50 y 5000."
        )
    return valor


# Nombre de la empresa en el admin, la API y la página del QR; provisoria hasta
# multiempresa. Un valor vacío cae al valor por defecto.
NOMBRE_EMPRESA = env("NOMBRE_EMPRESA", default="").strip() or "MAControl S.A."

# Correo de contacto del User-Agent de las consultas a Nominatim, que lo exige;
# provisorio hasta multiempresa, como NOMBRE_EMPRESA.
CORREO_CONTACTO = (
    env("CORREO_CONTACTO", default="").strip() or "administracion@macontrol.com.ar"
)

# Una revisión o una apertura a más metros del punto (o del sitio, si el punto no
# tiene coordenadas) marca `incidencia_ubicacion`; nunca se rechaza
# (plan cierre-puntos).
DISTANCIA_MAXIMA_M = leer_distancia_maxima_m()

# Precisión del GPS, en metros, a partir de la cual una lectura ya no fija ni propone
# coordenadas de un sitio o de un punto (plan cierre-puntos).
PRECISION_MAXIMA_M = 50


INSTALLED_APPS = [
    "config.apps.AdminDetachConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "csp",
    "simple_history",
    "apps.accounts",
    "apps.clientes",
    "apps.sitios",
    "apps.servicios",
    "apps.proyectos",
    "apps.visitas",
    "apps.productos",
    "apps.informes",
    "apps.panel",
    "apps.api",
    "apps.web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.contexto.empresa",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/panel/ingresar/"
LOGIN_REDIRECT_URL = "/panel/"

# Origen público del proyecto; arma el contenido de los QR (`SITE_URL` + `/q/<uuid>/`).
# Un `SITE_URL=` vacío (como en `.env.example`) cae al origen local de desarrollo;
# producción la exige (prod.py): un QR con un dominio ajeno o local no lo abre nadie.
SITE_URL = env("SITE_URL", default="").strip() or "http://localhost:8000"
SITE_URL = SITE_URL.rstrip("/")
LOGOUT_REDIRECT_URL = "/panel/ingresar/"

# Explícito aunque coincide con el valor por defecto de Django: la vista de Swagger
# (`?script` de drf-spectacular) incrusta el token CSRF y depende de esta política.
SESSION_COOKIE_SAMESITE = "Lax"

# Las teselas de OpenStreetMap exigen la cabecera Referer: con `same-origin` (el valor
# por defecto de Django) OSM responde 403. Hacia otros orígenes solo viaja el origen.
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Un POST de visita lleva como máximo MAX_FOTOS (10) archivos; 12 deja margen.
DATA_UPLOAD_MAX_NUMBER_FILES = 12

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.api.paginacion.PaginacionEstandar",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.api.excepciones.manejar_excepcion",
    "DEFAULT_THROTTLE_RATES": {
        "token": "10/min",
        "qr": "30/min",
        "crear_visita": "120/hour",
        # Altas de campo (sitio, punto, ubicación): no agotan crear_visita.
        "alta_campo": "300/hour",
    },
    "NUM_PROXIES": NUM_PROXIES,
}

# `SpectacularSwaggerSplitView` con `?script` incrusta el token CSRF en JS; no es
# explotable mientras `SESSION_COOKIE_SAMESITE` siga en "Lax" (ver arriba).
SPECTACULAR_SETTINGS = {
    "TITLE": "API de Detach",
    # Sin doble punto cuando el nombre termina en "S.A." o similar.
    "DESCRIPTION": "API de la app móvil de los empleados de "
    f"{NOMBRE_EMPRESA.rstrip('.')}.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
    "SERVE_AUTHENTICATION": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "CHECK_REVOKE_TOKEN": True,
}

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "style-src": [SELF, NONCE],
        "script-src": [SELF],
        "img-src": [SELF, "data:"],
        "font-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
        "form-action": [SELF],
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "datos_personales": {"()": "config.registro.FiltroDatosPersonales"},
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "filters": ["datos_personales"],
        },
    },
    "root": {"handlers": ["consola"], "level": "INFO"},
    # Sin los handlers por defecto de Django (sin filtro, con mail_admins).
    "loggers": {
        "django": {"handlers": ["consola"], "level": "INFO", "propagate": False},
        "django.server": {
            "handlers": ["consola"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
