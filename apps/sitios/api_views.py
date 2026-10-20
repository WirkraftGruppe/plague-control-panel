"""Vistas de la API de Sitios: resolver QR, imagen del plano y puntos del empleado."""

from django.core.exceptions import (
    RequestDataTooBig,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.core.exceptions import ValidationError as ErrorDeValidacion
from django.db.models import F
from django.http import FileResponse
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permisos import EsAdministrador, EsEmpleado
from apps.servicios.models import TipoServicio
from apps.visitas.models import ItemTurno, Visita
from apps.visitas.serializers import MAX_BYTES_FOTO

from . import services
from .estado import estado_por_vencimiento, estados_por_vencimiento
from .models import Plano, PuntoControl, Sitio
from .serializers import (
    AltaPuntoSerializer,
    AltaSitioSerializer,
    MiPuntoSerializer,
    MisPuntosParametrosSerializer,
    PuntoCampoSerializer,
    ResolverQRSerializer,
    SitioCampoSerializer,
    UbicacionPuntoSerializer,
)

ESTADOS_CON_TRABAJO = (Visita.Estado.PENDIENTE, Visita.Estado.ABIERTA)
MAX_BYTES_PEDIDO_PUNTO = MAX_BYTES_FOTO + 1024 * 1024
MENSAJE_PEDIDO_GRANDE = "El pedido supera el tamaño permitido."


def _datos_plano(punto):
    """Plano activo del punto con los marcadores de sus puntos activos ubicados."""
    plano = punto.plano
    if plano is None or not plano.activo:
        return None
    marcadores = list(
        plano.puntos.filter(activo=True, x__isnull=False, y__isnull=False).order_by(
            "orden", "id"
        )
    )
    estados = estados_por_vencimiento(marcadores, timezone.localdate())
    return {
        "id": plano.id,
        "nombre": plano.nombre,
        "url": reverse("api:sitios:plano-imagen", kwargs={"pk": plano.id}),
        "ancho_px": plano.ancho_px,
        "alto_px": plano.alto_px,
        "puntos": [
            {
                "id": m.id,
                "nombre": m.nombre,
                "x": m.x,
                "y": m.y,
                "estado": estados[m.id],
            }
            for m in marcadores
        ],
    }


def _servicio_del_punto(punto, empleado):
    """``(servicio, en_turno)`` del punto para el empleado.

    El servicio es el del ítem del turno propio (abierto antes que pendiente, y el
    más antiguo primero) en el sitio; sin ítem, el del punto, o ``None``.
    """
    item = (
        ItemTurno.objects.filter(
            punto=punto,
            visita__empleado=empleado,
            visita__estado__in=ESTADOS_CON_TRABAJO,
        )
        .select_related("servicio")
        .prefetch_related("servicio__campos")
        .order_by(
            "visita__estado", F("visita__programada_para").asc(nulls_last=True), "id"
        )
        .first()
    )
    if item is not None:
        return item.servicio, True
    if punto.servicio_id is None:
        return None, False
    servicio = TipoServicio.objects.prefetch_related("campos").get(pk=punto.servicio_id)
    return servicio, False


def _datos_servicio(servicio):
    if servicio is None:
        return None
    return {
        "id": servicio.id,
        "nombre": servicio.nombre,
        "slug": servicio.slug,
        "esquema_punto": servicio.esquema_planilla("punto"),
        "esquema_visita": servicio.esquema_planilla("visita"),
    }


class ResolverQRView(APIView):
    """Dado el UUID de un QR, devuelve el punto, su plano, el sitio y mis visitas."""

    permission_classes = [EsEmpleado | EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr"

    @extend_schema(
        request=None,
        responses={200: ResolverQRSerializer},
        summary="Resolver un código QR",
        description=(
            "Empleados y administradores. Un QR inexistente, de un punto o sitio "
            "inactivo o de un cliente inactivo responde el mismo 404. El punto trae "
            "su `estado` y `proximo_vencimiento`, `en_turno` (tiene un ítem en un "
            "turno propio pendiente o abierto) y el `servicio` con sus esquemas de "
            "planilla: el del ítem del turno o, fuera de turno, el del punto "
            "(`null` si no tiene)."
        ),
    )
    def post(self, request, codigo):
        punto = (
            PuntoControl.objects.select_related("sitio__cliente", "plano")
            .filter(
                qr_codigo=codigo,
                activo=True,
                sitio__activo=True,
                sitio__cliente__activo=True,
            )
            .first()
        )
        if punto is None:
            raise NotFound("El código QR no corresponde a un sitio activo.")
        sitio = punto.sitio

        # Una sola consulta para las visitas propias; la pendiente más antigua gana.
        pendiente, abierta = None, None
        visitas = (
            Visita.objects.filter(
                empleado=request.user, estado__in=ESTADOS_CON_TRABAJO, sitio=sitio
            )
            .order_by(F("programada_para").asc(nulls_last=True), "id")
            .values_list("id", "estado")
        )
        for visita_id, estado in visitas:
            if estado == Visita.Estado.ABIERTA:
                abierta = abierta or visita_id
            else:
                pendiente = pendiente or visita_id

        servicio, en_turno = _servicio_del_punto(punto, request.user)
        datos = {
            "punto": {
                "id": punto.id,
                "nombre": punto.nombre,
                "sector": punto.sector,
                "plano": _datos_plano(punto),
                "estado": estado_por_vencimiento(
                    punto.proximo_vencimiento, timezone.localdate()
                ),
                "proximo_vencimiento": punto.proximo_vencimiento,
                "servicio": _datos_servicio(servicio),
                "en_turno": en_turno,
            },
            "sitio": sitio,
            "cliente": sitio.cliente,
            "visita_pendiente_propia": pendiente,
            "visita_abierta_propia": abierta,
        }
        return Response(ResolverQRSerializer(datos).data)


class IgnorarAccept(BaseContentNegotiation):
    """Usa siempre el primer renderer: la imagen no depende del `Accept`."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class PlanoImagenView(APIView):
    """Sirve la imagen de un plano activo a quien tiene trabajo en su sitio."""

    permission_classes = [EsEmpleado | EsAdministrador]
    content_negotiation_class = IgnorarAccept

    @extend_schema(
        summary="Descargar la imagen de un plano",
        description=(
            "Administradores, o empleados con una visita propia pendiente o abierta "
            "en el sitio. Sin acceso, plano inactivo o inexistente: "
            "el mismo 404."
        ),
        responses={
            (200, "image/png"): OpenApiTypes.BINARY,
            404: OpenApiResponse(description="El plano no existe o no es accesible."),
        },
    )
    def get(self, request, pk):
        plano = Plano.objects.filter(pk=pk, activo=True).first()
        if plano is None:
            raise NotFound("El plano no existe.")
        if (
            not request.user.es_administrador
            and not Visita.objects.filter(
                empleado=request.user,
                estado__in=ESTADOS_CON_TRABAJO,
                sitio_id=plano.sitio_id,
                sitio__activo=True,
                sitio__cliente__activo=True,
            ).exists()
        ):
            raise NotFound("El plano no existe.")
        try:
            archivo = plano.imagen.open("rb")
        except FileNotFoundError:
            raise NotFound("El plano no existe.")
        respuesta = FileResponse(archivo, content_type="image/png")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta


class MisPuntosView(APIView):
    """Puntos activos de los sitios donde el empleado tiene visitas por hacer."""

    permission_classes = [EsEmpleado | EsAdministrador]

    @extend_schema(
        summary="Mis puntos de control",
        description=(
            "Puntos activos, con coordenadas y estado, de los sitios activos (de "
            "clientes activos) donde el empleado tiene visitas pendientes o "
            "abiertas. `sitio` filtra por id; un sitio ajeno devuelve lista vacía."
        ),
        parameters=[
            OpenApiParameter("sitio", OpenApiTypes.INT, description="Id del sitio.")
        ],
        responses={200: MiPuntoSerializer(many=True)},
    )
    def get(self, request):
        parametros = MisPuntosParametrosSerializer(data=request.query_params)
        parametros.is_valid(raise_exception=True)
        sitio = parametros.validated_data.get("sitio")
        sitios = Visita.objects.filter(
            empleado=request.user,
            estado__in=ESTADOS_CON_TRABAJO,
            sitio__activo=True,
            sitio__cliente__activo=True,
        )
        if sitio is not None:
            sitios = sitios.filter(sitio_id=sitio)
        puntos = list(
            PuntoControl.objects.filter(
                activo=True, sitio_id__in=sitios.values("sitio_id")
            )
            .select_related("sitio")
            .order_by("sitio__nombre", "sitio_id", "orden", "id")
        )
        estados = estados_por_vencimiento(puntos, timezone.localdate())
        for punto in puntos:
            punto.estado = estados[punto.id]
        return Response(MiPuntoSerializer(puntos, many=True).data)


def _a_400(error):
    """Convierte la validación de un servicio en el 400 de la API."""
    return ValidationError(error.messages)


_RESPUESTAS_CAMPO = {
    400: OpenApiResponse(
        description="Datos inválidos o precisión de GPS insuficiente."
    ),
    403: OpenApiResponse(description="Solo administradores."),
    404: OpenApiResponse(description="No existe."),
}


class AltaSitioView(APIView):
    """Alta de un sitio con las coordenadas del GPS del administrador."""

    permission_classes = [EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "alta_campo"

    @extend_schema(
        request=AltaSitioSerializer,
        responses={201: SitioCampoSerializer, **_RESPUESTAS_CAMPO},
        summary="Crear un sitio en campo",
        description=(
            "Solo administradores. Cliente activo, coordenadas y `precision_m` "
            "obligatorios; la precisión no puede superar `PRECISION_MAXIMA_M`."
        ),
    )
    def post(self, request):
        serializer = AltaSitioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        try:
            sitio = services.crear_sitio_en_campo(
                administrador=request.user,
                nombre=datos["nombre"],
                direccion=datos.get("direccion", ""),
                localidad=datos.get("localidad", ""),
                cliente=datos["cliente"],
                latitud=datos["latitud"],
                longitud=datos["longitud"],
                precision_m=datos["precision_m"],
            )
        except ErrorDeValidacion as error:
            raise _a_400(error)
        return Response(
            SitioCampoSerializer(sitio).data, status=status.HTTP_201_CREATED
        )


class AltaPuntoView(APIView):
    """Alta de un punto de control en un sitio activo, con o sin coordenadas y foto."""

    permission_classes = [EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "alta_campo"
    parser_classes = [MultiPartParser, JSONParser]

    @extend_schema(
        request=AltaPuntoSerializer,
        responses={201: PuntoCampoSerializer, **_RESPUESTAS_CAMPO},
        summary="Crear un punto de control en campo",
        description=(
            "Solo administradores. Sin coordenadas el punto nace sin ubicación; con "
            "ellas, `precision_m` es obligatoria y no puede superar "
            "`PRECISION_MAXIMA_M`. La foto es opcional (multipart). Un pedido "
            "mayor que una foto más 1 MiB, o con demasiados campos, da 400."
        ),
    )
    def post(self, request, pk):
        sitio = Sitio.objects.select_related("cliente").filter(pk=pk).first()
        if sitio is None:
            raise NotFound("El sitio no existe.")
        try:
            largo = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            largo = 0
        # Se corta antes de leer el cuerpo: Django escribe los archivos a disco.
        if largo > MAX_BYTES_PEDIDO_PUNTO:
            raise ValidationError(MENSAJE_PEDIDO_GRANDE)
        try:
            datos_pedido = request.data
        except (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
            raise ValidationError(MENSAJE_PEDIDO_GRANDE)
        serializer = AltaPuntoSerializer(data=datos_pedido)
        serializer.is_valid(raise_exception=True)
        try:
            punto = services.crear_punto_en_campo(
                administrador=request.user, sitio=sitio, **serializer.validated_data
            )
        except ErrorDeValidacion as error:
            raise _a_400(error)
        return Response(
            PuntoCampoSerializer(punto).data, status=status.HTTP_201_CREATED
        )


class UbicacionPuntoView(APIView):
    """Fija las coordenadas de un punto con el GPS del administrador."""

    permission_classes = [EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "alta_campo"

    @extend_schema(
        request=UbicacionPuntoSerializer,
        responses={200: PuntoCampoSerializer, **_RESPUESTAS_CAMPO},
        summary="Fijar la ubicación de un punto en campo",
        description=(
            "Solo administradores. Reemplaza las coordenadas y descarta la ubicación "
            "propuesta; `precision_m` no puede superar `PRECISION_MAXIMA_M`."
        ),
    )
    def post(self, request, pk):
        punto = (
            PuntoControl.objects.select_related("sitio__cliente").filter(pk=pk).first()
        )
        if punto is None:
            raise NotFound("El punto no existe.")
        serializer = UbicacionPuntoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.fijar_ubicacion_en_campo(
                administrador=request.user, punto=punto, **serializer.validated_data
            )
        except ErrorDeValidacion as error:
            raise _a_400(error)
        return Response(PuntoCampoSerializer(punto).data)
