"""Consultas reutilizables del catálogo de productos."""

from django.db.models import OuterRef, Subquery

from apps.visitas.models import ProductoAplicado


def ultimo_lote_subquery():
    """Subquery con el lote más reciente aplicado de cada producto, o `null`.

    Sale de `ProductoAplicado` de la misma empresa que el producto, ordenado por
    la fecha de la revisión y, a igualdad, por la pk. Se usa con `annotate`.
    """
    aplicados = (
        ProductoAplicado.objects.de_empresa(OuterRef("empresa_id"))
        .filter(producto=OuterRef("pk"))
        .order_by("-revision__realizada_en", "-pk")
    )
    return Subquery(aplicados.values("lote")[:1])
