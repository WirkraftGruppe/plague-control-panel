"""Serializers de la API de Sitios: resolver un QR, puntos y alta en campo."""

from django.conf import settings
from rest_framework import serializers

from apps.clientes.models import Cliente
from apps.visitas.serializers import validar_tamano_foto


class SitioQRSerializer(serializers.Serializer):
    """Datos mínimos del sitio; sin coordenadas, contactos, notas ni horario."""

    nombre = serializers.CharField()
    direccion = serializers.CharField()
    localidad = serializers.CharField()


class ClienteQRSerializer(serializers.Serializer):
    razon_social = serializers.CharField()


class PuntoPlanoSerializer(serializers.Serializer):
    """Marcador de un punto sobre el plano, con su estado de revisión."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    x = serializers.FloatField()
    y = serializers.FloatField()
    estado = serializers.CharField()


class PlanoSerializer(serializers.Serializer):
    """Plano del punto escaneado; `url` apunta al endpoint autenticado de la imagen."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    url = serializers.CharField()
    ancho_px = serializers.IntegerField()
    alto_px = serializers.IntegerField()
    puntos = PuntoPlanoSerializer(many=True)


class PuntoQRSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    sector = serializers.CharField()
    plano = PlanoSerializer(allow_null=True)


class ResolverQRSerializer(serializers.Serializer):
    punto = PuntoQRSerializer()
    sitio = SitioQRSerializer()
    cliente = ClienteQRSerializer()
    visita_pendiente_propia = serializers.IntegerField(allow_null=True)
    visita_abierta_propia = serializers.IntegerField(allow_null=True)


class SitioPuntoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()


class MiPuntoSerializer(serializers.Serializer):
    """Punto activo de un sitio donde el empleado tiene trabajo, con su estado."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    sector = serializers.CharField()
    sitio = SitioPuntoSerializer()
    plano = serializers.IntegerField(source="plano_id", allow_null=True)
    x = serializers.FloatField(allow_null=True)
    y = serializers.FloatField(allow_null=True)
    latitud = serializers.FloatField(allow_null=True)
    longitud = serializers.FloatField(allow_null=True)
    estado = serializers.CharField()


class MisPuntosParametrosSerializer(serializers.Serializer):
    """Parámetros de consulta de `GET me/puntos/`."""

    sitio = serializers.IntegerField(required=False, min_value=1, max_value=2**31 - 1)


class _PrecisionMixin(serializers.Serializer):
    """Precisión del GPS: peor que el máximo no fija coordenadas."""

    def validate_precision_m(self, valor):
        if valor > settings.PRECISION_MAXIMA_M:
            raise serializers.ValidationError(
                f"La precisión debe ser de {settings.PRECISION_MAXIMA_M} m o mejor."
            )
        return valor


def _latitud(**extra):
    return serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-90, max_value=90, **extra
    )


def _longitud(**extra):
    return serializers.DecimalField(
        max_digits=9, decimal_places=6, min_value=-180, max_value=180, **extra
    )


class AltaSitioSerializer(_PrecisionMixin):
    """Alta de un sitio por un administrador en campo; coordenadas obligatorias."""

    cliente = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.filter(activo=True)
    )
    nombre = serializers.CharField(max_length=200)
    direccion = serializers.CharField(max_length=255, required=False, allow_blank=True)
    localidad = serializers.CharField(max_length=100, required=False, allow_blank=True)
    latitud = _latitud()
    longitud = _longitud()
    precision_m = serializers.FloatField(min_value=0)


class AltaPuntoSerializer(_PrecisionMixin):
    """Alta de un punto; las coordenadas (con su precisión) y la foto son opcionales."""

    nombre = serializers.CharField(max_length=100)
    sector = serializers.CharField(max_length=100, default="", allow_blank=True)
    latitud = _latitud(required=False)
    longitud = _longitud(required=False)
    precision_m = serializers.FloatField(min_value=0, required=False)
    foto = serializers.ImageField(required=False, validators=[validar_tamano_foto])

    def validate(self, datos):
        con_coordenadas = [c for c in ("latitud", "longitud") if c in datos]
        if con_coordenadas and len(con_coordenadas) != 2:
            raise serializers.ValidationError("Latitud y longitud van juntas.")
        if con_coordenadas and "precision_m" not in datos:
            raise serializers.ValidationError(
                {"precision_m": "Es obligatoria al enviar coordenadas."}
            )
        return datos


class UbicacionPuntoSerializer(_PrecisionMixin):
    """Ubicación del punto tomada con el GPS del administrador."""

    latitud = _latitud()
    longitud = _longitud()
    precision_m = serializers.FloatField(min_value=0)


class PuntoCampoSerializer(serializers.Serializer):
    """Punto creado o ubicado en campo; el QR lo ve solo el administrador."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    sector = serializers.CharField()
    sitio = serializers.IntegerField(source="sitio_id")
    latitud = serializers.FloatField(allow_null=True)
    longitud = serializers.FloatField(allow_null=True)
    qr_codigo = serializers.UUIDField()
    tiene_foto = serializers.SerializerMethodField()

    def get_tiene_foto(self, punto) -> bool:
        return bool(punto.foto)


class SitioCampoSerializer(serializers.Serializer):
    """Sitio creado en campo, con su punto General."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    cliente = serializers.IntegerField(source="cliente_id")
    direccion = serializers.CharField()
    localidad = serializers.CharField()
    latitud = serializers.FloatField()
    longitud = serializers.FloatField()
    puntos = PuntoCampoSerializer(many=True)
