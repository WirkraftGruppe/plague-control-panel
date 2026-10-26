"""Guardia de consultas por empresa: ningún queryset se evalúa sin saber de quién es."""

import warnings
from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings
from django.db import models


class ConsultaSinEmpresa(Exception):
    """Se evaluó una consulta de un modelo de empresa sin filtrar por empresa."""


class ConsultaSinEmpresaAdvertencia(UserWarning):
    """Lo mismo que `ConsultaSinEmpresa`, en el modo `advertir` de la guardia."""


# True dentro de `sin_filtro_empresa()`: las consultas no se verifican.
_sin_filtro = ContextVar("sin_filtro_empresa", default=False)


@contextmanager
def sin_filtro_empresa():
    """Desactiva la guardia en el bloque (admin, validaciones de unicidad, comandos)."""
    marca = _sin_filtro.set(True)
    try:
        yield
    finally:
        _sin_filtro.reset(marca)


def empresa_de(request):
    """Empresa del usuario autenticado del pedido, o `None`."""
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return None
    return usuario.empresa


class EmpresaQuerySet(models.QuerySet):
    """Queryset que exige `de_empresa()` antes de evaluarse.

    Quedan fuera de la guardia `.none()`, los querysets de un manager relacionado o
    de `prefetch_related` (traen la instancia en los hints) y `sin_filtro_empresa()`.
    """

    _empresa_marcada = False

    def _clone(self):
        clon = super()._clone()
        clon._empresa_marcada = self._empresa_marcada
        return clon

    def de_empresa(self, empresa):
        """Filtra por empresa y marca el queryset como seguro de evaluar."""
        if empresa is None:
            raise ConsultaSinEmpresa("de_empresa() exige una empresa, no None.")
        consulta = self.filter(empresa=empresa)
        consulta._empresa_marcada = True
        return consulta

    def _verificar_empresa(self):
        if (
            self._empresa_marcada
            or _sin_filtro.get()
            or self.query.is_empty()
            or self._hints.get("instance") is not None
        ):
            return
        mensaje = (
            f"Consulta de {self.model.__name__} sin filtrar por empresa: "
            "use .de_empresa(empresa)."
        )
        if getattr(settings, "EMPRESA_GUARDIA", "advertir") == "exigir":
            raise ConsultaSinEmpresa(mensaje)
        warnings.warn(mensaje, ConsultaSinEmpresaAdvertencia, stacklevel=3)

    def _fetch_all(self):
        if self._result_cache is None:
            self._verificar_empresa()
        super()._fetch_all()

    def _iterator(self, use_chunked_fetch, chunk_size):
        self._verificar_empresa()
        return super()._iterator(use_chunked_fetch, chunk_size)

    def count(self):
        if self._result_cache is None:
            self._verificar_empresa()
        return super().count()

    def exists(self):
        if self._result_cache is None:
            self._verificar_empresa()
        return super().exists()

    def aggregate(self, *args, **kwargs):
        self._verificar_empresa()
        return super().aggregate(*args, **kwargs)

    def update(self, **kwargs):
        self._verificar_empresa()
        return super().update(**kwargs)

    def delete(self):
        self._verificar_empresa()
        return super().delete()

    def explain(self, *, format=None, **opciones):
        self._verificar_empresa()
        return super().explain(format=format, **opciones)
