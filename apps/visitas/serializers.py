"""Serializers de la API de Visitas: abrir, revisiones, cerrar y listados."""

import json
from decimal import Decimal

from django.urls import reverse
from rest_framework import serializers

from .models import ProductoAplicado, Revision, Visita
from .planillas import MAX_LARGO_TEXTO
from .services import MAX_FOTOS, MAX_PRODUCTOS

MAX_BYTES_FOTO = 8 * 1024 * 1024
MAX_CARACTERES_JSON = 50_000


def validar_tamano_foto(archivo):
    """Rechaza fotos de más de 8 MB."""
    if archivo.size > MAX_BYTES_FOTO:
        raise serializers.ValidationError("Cada foto puede pesar hasta 8 MB.")


class CampoJSON(serializers.CharField):
    """Texto JSON dentro de un multipart; entrega el valor ya decodificado."""

    default_error_messages = {
        "json": "Debe ser un JSON válido.",
        "tipo": "Debe ser un JSON de tipo {tipo}.",
    }

    def __init__(self, *, tipo, nombre_tipo, **kwargs):
        kwargs.setdefault("max_length", MAX_CARACTERES_JSON)
        super().__init__(**kwargs)
        self.tipo, self.nombre_tipo = tipo, nombre_tipo

    def to_internal_value(self, data):
        texto = super().to_internal_value(data)
        try:
            valor = json.loads(texto)
        except (ValueError, RecursionError):
            self.fail("json")
        if not isinstance(valor, self.tipo):
            self.fail("tipo", tipo=self.nombre_tipo)
        return valor


class AbrirVisitaSerializer(serializers.Serializer):
    """Entrada de `POST visitas/abrir/`: el QR escaneado en el sitio y, opcionales,
    las coordenadas del teléfono para verificar la ubicación."""

    qr_codigo = serializers.UUIDField()
    latitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
        required=False,
        allow_null=True,
        default=None,
    )
    longitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
        required=False,
        allow_null=True,
        default=None,
    )
    precision_m = serializers.DecimalField(
        max_digits=7,
        decimal_places=1,
        min_value=Decimal("0"),
        max_value=Decimal("99999.9"),
        required=False,
        allow_null=True,
        default=None,
    )


class CrearRevisionSerializer(serializers.Serializer):
    """Forma y límites de una revisión; las reglas de negocio (incluido el atraso,
    que respeta la idempotencia) las aplica el servicio."""

    visita = serializers.IntegerField()
    qr_codigo = serializers.UUIDField()
    cliente_uuid = serializers.UUIDField(allow_null=False)
    realizada_en = serializers.DateTimeField()
    latitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
    )
    longitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
    )
    precision_m = serializers.DecimalField(
        max_digits=7,
        decimal_places=1,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        default=None,
    )
    datos = CampoJSON(tipo=dict, nombre_tipo="objeto", default=dict)
    productos_aplicados = CampoJSON(tipo=list, nombre_tipo="lista", default=list)
    fotos = serializers.ListField(
        child=serializers.FileField(
            allow_empty_file=False, validators=[validar_tamano_foto]
        ),
        required=False,
        default=list,
        max_length=MAX_FOTOS,
    )
    observaciones = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=MAX_LARGO_TEXTO
    )
    incidencia = serializers.BooleanField(required=False, default=False)
    incidencia_detalle = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=MAX_LARGO_TEXTO
    )

    def validate_productos_aplicados(self, valor):
        if len(valor) > MAX_PRODUCTOS:
            raise serializers.ValidationError(
                f"Se permiten hasta {MAX_PRODUCTOS} productos por revisión."
            )
        if not all(isinstance(item, dict) for item in valor):
            raise serializers.ValidationError("Cada producto debe ser un objeto.")
        return valor


class SitioResumenSerializer(serializers.Serializer):
    """Sitio sin coordenadas, contactos ni notas."""

    nombre = serializers.CharField()
    direccion = serializers.CharField()
    localidad = serializers.CharField()


class VisitaActivaSerializer(serializers.ModelSerializer):
    """Visita pendiente o abierta, sin coordenadas: lista propia y apertura."""

    sitio = SitioResumenSerializer(read_only=True)

    class Meta:
        model = Visita
        fields = ["id", "estado", "sitio", "programada_para", "abierta_en"]
        read_only_fields = fields


class ProductoAplicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoAplicado
        fields = [
            "producto",
            "lote",
            "dosis",
            "unidad_dosis",
            "cantidad",
            "unidad",
            "cantidad_base",
        ]
        read_only_fields = fields


class PuntoResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class RevisionSerializer(serializers.ModelSerializer):
    """Revisión sin coordenadas ni precisión: no se devuelve la ubicación."""

    punto = PuntoResumenSerializer(read_only=True)
    productos = ProductoAplicadoSerializer(many=True, read_only=True)
    fotos = serializers.SerializerMethodField()

    class Meta:
        model = Revision
        fields = [
            "id",
            "visita",
            "punto",
            "orden",
            "realizada_en",
            "datos",
            "observaciones",
            "incidencia",
            "incidencia_detalle",
            "productos",
            "fotos",
        ]
        read_only_fields = fields

    def get_fotos(self, revision) -> list[str]:
        return [
            reverse("api:visitas:foto", args=[f.codigo]) for f in revision.fotos.all()
        ]


class CerrarVisitaSerializer(serializers.Serializer):
    """Entrada de `POST visitas/<pk>/cerrar/`: planilla de la visita y observaciones."""

    datos = serializers.JSONField(required=False)
    observaciones = serializers.CharField(
        required=False, allow_blank=True, max_length=MAX_LARGO_TEXTO
    )
    incidencia = serializers.BooleanField(required=False)
    incidencia_detalle = serializers.CharField(
        required=False, allow_blank=True, max_length=MAX_LARGO_TEXTO
    )

    def validate_datos(self, valor):
        if not isinstance(valor, dict):
            raise serializers.ValidationError("Debe ser un objeto.")
        return valor


class VisitaRealizadaSerializer(serializers.ModelSerializer):
    """Visita realizada con sus revisiones (sin coordenadas): historial y cierre."""

    sitio = SitioResumenSerializer(read_only=True)
    realizada_en = serializers.DateTimeField(source="cerrada_en", read_only=True)
    revisiones = RevisionSerializer(many=True, read_only=True)

    class Meta:
        model = Visita
        fields = [
            "id",
            "sitio",
            "realizada_en",
            "datos",
            "observaciones",
            "incidencia",
            "incidencia_detalle",
            "revisiones",
        ]
        read_only_fields = fields
