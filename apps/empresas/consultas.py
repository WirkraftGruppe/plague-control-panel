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

    def _es_segura(self):
        """True si la consulta ya está acotada a una empresa (o no trae filas).

        El hint `instance` solo vale si la instancia salió de la base: una armada a
        mano (`Modelo(pk=...)`) no prueba nada sobre su empresa.
        """
        instancia = self._hints.get("instance")
        return (
            self._empresa_marcada
            or self.query.is_empty()
            or (instancia is not None and not instancia._state.adding)
        )

    def _combinada(self, resultado, *partes):
        """Quita la marca y el hint al combinar si alguna parte no es segura.

        Si Django devolvió una de las partes tal cual (por ejemplo un `.none()`), se
        respeta: esa parte ya tiene su propio estado.
        """
        if any(resultado is parte for parte in partes):
            return resultado
        if not all(
            isinstance(parte, EmpresaQuerySet) and parte._es_segura()
            for parte in partes
        ):
            resultado._empresa_marcada = False
            # Dict nuevo: `_clone` comparte los hints con el queryset de origen.
            resultado._hints = {
                clave: valor
                for clave, valor in resultado._hints.items()
                if clave != "instance"
            }
        return resultado

    def __or__(self, otro):
        return self._combinada(super().__or__(otro), self, otro)

    def __xor__(self, otro):
        return self._combinada(super().__xor__(otro), self, otro)

    def union(self, *otros, all=False):
        return self._combinada(super().union(*otros, all=all), self, *otros)

    def intersection(self, *otros):
        return self._combinada(super().intersection(*otros), self, *otros)

    def difference(self, *otros):
        return self._combinada(super().difference(*otros), self, *otros)

    def _verificar_empresa(self):
        if _sin_filtro.get() or self._es_segura():
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

    async def aiterator(self, chunk_size=2000):
        # En Django 5.2 no pasa por `_iterator`.
        self._verificar_empresa()
        async for objeto in super().aiterator(chunk_size):
            yield objeto

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
