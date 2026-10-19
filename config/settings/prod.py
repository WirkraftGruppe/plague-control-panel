"""Settings de producción: piden SECRET_KEY, DATABASE_URL, SITE_URL y NOMBRE_EMPRESA."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import MIDDLEWARE, env

DEBUG = False

SECRET_KEY = env("SECRET_KEY")

# Recortados y sin vacíos: un host con espacios nunca coincide con el Host pedido.
ALLOWED_HOSTS = [h.strip() for h in env.list("ALLOWED_HOSTS", default=[]) if h.strip()]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS está vacío con DJANGO_ENV=production: definí al menos un "
        "host (separados por comas) o toda petición daría 400."
    )

# Sin SITE_URL, base.py cae a http://localhost:8000 y los QR impresos en producción
# apuntarían a una dirección local que ningún teléfono abre.
if not env("SITE_URL", default="").strip():
    raise ImproperlyConfigured(
        "SITE_URL está vacía con DJANGO_ENV=production: definí el origen público "
        "(por ejemplo https://dominio.com.ar), que arma el contenido de los QR."
    )

# Sin NOMBRE_EMPRESA, base.py cae a un nombre por defecto y el panel, la API y la
# página del QR mostrarían el nombre de otra empresa.
if not env("NOMBRE_EMPRESA", default="").strip():
    raise ImproperlyConfigured(
        "NOMBRE_EMPRESA está vacía con DJANGO_ENV=production: definí el nombre de "
        "la empresa, que aparece en el panel, la API y la página del QR."
    )

# Orígenes https que Django acepta en los POST (el dominio público del hosting).
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in env.list("CSRF_TRUSTED_ORIGINS", default=[]) if o.strip()
]

# WhiteNoise sirve los estáticos de collectstatic, justo después de SecurityMiddleware.
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DATABASES = {"default": env.db("DATABASE_URL")}

# HTTPS detrás del proxy del hosting
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# HSTS reversible: se suben después de verificar los subdominios de la empresa
# (ver docs/decisiones.md, "HSTS reversible").
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
