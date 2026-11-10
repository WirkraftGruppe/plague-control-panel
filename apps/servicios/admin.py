from django.contrib import admin

from apps.clientes.empresa import AdminHijoMixin, AdminRaizMixin

from .models import CampoPlanilla, TipoServicio


class CampoPlanillaInline(admin.TabularInline):
    model = CampoPlanilla
    extra = 0
    fields = (
        "orden",
        "etiqueta",
        "clave",
        "tipo",
        "ambito",
        "opciones",
        "obligatorio",
        "ayuda",
    )


@admin.register(TipoServicio)
class TipoServicioAdmin(AdminRaizMixin, admin.ModelAdmin):
    list_display = ("nombre", "slug", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "slug")
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [CampoPlanillaInline]


@admin.register(CampoPlanilla)
class CampoPlanillaAdmin(AdminHijoMixin, admin.ModelAdmin):
    list_display = (
        "etiqueta",
        "clave",
        "tipo_servicio",
        "tipo",
        "obligatorio",
        "orden",
    )
    list_filter = ("tipo", "ambito", "obligatorio")
    search_fields = ("etiqueta", "clave", "tipo_servicio__nombre")
