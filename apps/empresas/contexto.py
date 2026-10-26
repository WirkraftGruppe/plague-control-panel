def empresa_actual(request):
    """Expone la empresa del pedido a las plantillas como `empresa_actual`."""
    return {"empresa_actual": getattr(request, "empresa", None)}
