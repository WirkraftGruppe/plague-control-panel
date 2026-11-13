from django.contrib import admin

from apps.clientes.empresa import AdminHijoMixin, AdminRaizMixin

from .models import MovimientoStock, Producto


@admin.register(Producto)
class ProductoAdmin(AdminRaizMixin, admin.ModelAdmin):
    list_display = ("nombre_comercial", "principio_activo", "registro", "activo")
    search_fields = ("nombre_comercial", "principio_activo", "registro")
    list_filter = ("activo",)

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        if obj is not None and obj.movimientos.exists():
            return (*campos, "unidad_base", "modo_unidad")
        return campos


@admin.register(MovimientoStock)
class MovimientoStockAdmin(AdminHijoMixin, admin.ModelAdmin):
    list_display = ("producto", "tipo", "cantidad_base", "usuario", "creado")
    list_filter = ("tipo",)
    readonly_fields = ("producto", "tipo", "cantidad_base", "usuario", "creado", "nota")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
