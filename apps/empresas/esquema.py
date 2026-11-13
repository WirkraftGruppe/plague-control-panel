"""Extensión de drf-spectacular: el esquema `jwtAuth` también vale con empresa."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class JWTEmpresaScheme(SimpleJWTScheme):
    # `SimpleJWTScheme` no cubre subclases (`match_subclasses = False`).
    target_class = "apps.empresas.autenticacion.JWTAutenticacionEmpresa"
    name = "jwtAuth"
