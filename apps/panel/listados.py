"""Listado base del panel: búsqueda, orden por lista blanca y parcial HTMX."""

from functools import reduce
from operator import or_
from urllib.parse import urlencode

from django.db.models import Q
from django.views.generic import ListView


class ListadoPanelMixin(ListView):
    """Listado paginado con búsqueda (`q`) y orden (`orden`) seguros.

    El orden solo acepta campos de `orden_permitido` (con un `-` opcional); cualquier
    otro valor se ignora. Con el encabezado `HX-Request` se usa `template_parcial`.
    """

    paginate_by = 25
    orden_permitido = ()
    campos_busqueda = ()
    template_parcial = None

    def get_orden(self):
        """Devuelve el parámetro `orden` si está en la lista blanca, o ''."""
        orden = self.request.GET.get("orden", "")
        campo = orden.removeprefix("-")
        return orden if campo in self.orden_permitido else ""

    def get_busqueda(self):
        """Devuelve `q` sin el carácter NUL (PostgreSQL lo rechaza)."""
        return self.request.GET.get("q", "").replace("\x00", "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.get_busqueda()
        if q and self.campos_busqueda:
            filtros = (Q(**{f"{c}__icontains": q}) for c in self.campos_busqueda)
            queryset = queryset.filter(reduce(or_, filtros))
        orden = self.get_orden()
        return queryset.order_by(orden) if orden else queryset

    def get_template_names(self):
        if self.template_parcial and self.request.headers.get("HX-Request"):
            return [self.template_parcial]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        parametros = {"q": self.get_busqueda(), "orden": self.get_orden()}
        contexto["q"] = parametros["q"]
        contexto["orden"] = parametros["orden"]
        contexto["querystring"] = urlencode({k: v for k, v in parametros.items() if v})
        return contexto
