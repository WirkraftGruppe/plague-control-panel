"""Vistas de la API de Visitas: abrir, revisiones, cerrar, listados y fotos."""

from django.core.exceptions import (
    RequestDataTooBig,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.db.models import F
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permisos import EsAdministrador, EsEmpleado

from .models import Foto, Visita
from .serializers import (
    MAX_BYTES_FOTO,
    MAX_FOTOS,
    AbrirVisitaSerializer,
    CerrarVisitaSerializer,
    CrearRevisionSerializer,
    RevisionSerializer,
    VisitaActivaSerializer,
    VisitaRealizadaSerializer,
)
from .services import (
    RevisionDuplicada,
    VisitaNoEncontrada,
    VisitaYaCerrada,
    abrir_visita,
    cerrar_visita,
    registrar_revision,
)

MENSAJE_DUPLICADA = "La revisión ya fue registrada."
MAX_BYTES_PEDIDO = MAX_FOTOS * MAX_BYTES_FOTO + 1024 * 1024
PRECARGA_REVISIONES = (
    "revisiones__punto",
    "revisiones__fotos",
    "revisiones__productos",
)


class PedidoDemasiadoGrande(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = "El pedido supera el tamaño permitido."
    default_code = "pedido_demasiado_grande"


class VisitaYaCerradaError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La visita ya fue cerrada."
    default_code = "visita_ya_cerrada"


class MisVisitasView(generics.ListAPIView):
    """Visitas pendientes y abiertas del usuario autenticado."""

    permission_classes = [EsEmpleado | EsAdministrador]
    serializer_class = VisitaActivaSerializer

    def get_queryset(self):
        return (
            Visita.objects.filter(
                empleado=self.request.user,
                estado__in=[Visita.Estado.ABIERTA, Visita.Estado.PENDIENTE],
            )
            .select_related("proyecto__sitio")
            .order_by("estado", F("programada_para").asc(nulls_last=True), "id")
        )

    @extend_schema(summary="Mis visitas pendientes y abiertas")
    def get(self, request, *args, **kwargs):
        """Lista paginada; las abiertas van primero y cada una trae su `estado`."""
        return super().get(request, *args, **kwargs)


class AbrirVisitaView(APIView):
    """Abre la jornada del empleado o del administrador en un proyecto (idempotente)."""

    permission_classes = [EsEmpleado | EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Abrir una visita",
        description=(
            "Abre la pendiente asignada o crea una visita nueva. `qr_codigo` es el de "
            "un punto activo del sitio del proyecto. Si el empleado ya tiene una "
            "abierta en el proyecto la devuelve con 200. `latitud`, `longitud` y "
            "`precision_m` son opcionales: con coordenadas se guarda la distancia al "
            "punto y la incidencia de ubicación, sin rechazar nunca por distancia. La "
            "visita de un administrador no toma pendientes."
        ),
        request=AbrirVisitaSerializer,
        responses={
            201: VisitaActivaSerializer,
            200: VisitaActivaSerializer,
            400: OpenApiResponse(
                description="Proyecto inexistente o inactivo, o QR ajeno al sitio."
            ),
        },
    )
    def post(self, request):
        """201 si crea o abre una pendiente, 200 si ya estaba abierta."""
        entrada = AbrirVisitaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        visita, creada = abrir_visita(
            empleado=request.user,
            proyecto=entrada.validated_data["proyecto"],
            qr_codigo=entrada.validated_data["qr_codigo"],
            latitud=entrada.validated_data["latitud"],
            longitud=entrada.validated_data["longitud"],
            precision_m=entrada.validated_data["precision_m"],
        )
        return Response(
            VisitaActivaSerializer(visita).data,
            status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK,
        )


class CrearRevisionView(APIView):
    """Registra el escaneo de un punto en una visita abierta (multipart)."""

    permission_classes = [EsEmpleado | EsAdministrador]
    parser_classes = [MultiPartParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Registrar una revisión",
        description=(
            "Multipart. `qr_codigo` es el del punto escaneado. `datos` y "
            "`productos_aplicados` son texto JSON, una lista donde cada ítem lleva "
            "`producto`, `lote`, `dosis`, `unidad_dosis`, `cantidad` y `unidad` (la "
            "unidad de la cantidad, válida para el producto); `fotos` se repite de 1 "
            "a 10 veces (hasta 8 MB cada una). Un `cliente_uuid` ya registrado "
            "responde 409; "
            "`revision` y `visita` solo vienen si son del mismo empleado. Un "
            "administrador que escanea un punto sin coordenadas, con precisión de a lo "
            "sumo 50 m, las fija."
        ),
        request={"multipart/form-data": CrearRevisionSerializer},
        responses={
            201: RevisionSerializer,
            400: OpenApiResponse(
                description=(
                    "Validación: QR que no es de un punto del sitio, visita no "
                    "abierta, coordenadas o foto faltantes, planilla inválida o "
                    "revisión con más horas de atraso que el máximo (168 por defecto)."
                )
            ),
            404: OpenApiResponse(
                description="La visita no existe o es de otro usuario."
            ),
            409: OpenApiResponse(description="El `cliente_uuid` ya fue registrado."),
            413: OpenApiResponse(description="El pedido supera el tamaño permitido."),
        },
    )
    def post(self, request):
        """Valida la forma y delega en el servicio, que maneja su transacción."""
        try:
            largo = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            largo = 0
        # Se corta antes de leer el cuerpo: Django escribe los archivos a disco.
        if largo > MAX_BYTES_PEDIDO:
            raise PedidoDemasiadoGrande()
        try:
            datos_pedido = request.data
        except (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
            raise PedidoDemasiadoGrande()
        entrada = CrearRevisionSerializer(data=datos_pedido)
        entrada.is_valid(raise_exception=True)
        try:
            revision = registrar_revision(
                empleado=request.user, **entrada.validated_data
            )
        except VisitaNoEncontrada:
            raise NotFound("La visita no existe.")
        except RevisionDuplicada as duplicada:
            cuerpo = {"detalle": MENSAJE_DUPLICADA, "campos": {}}
            # Solo el dueño recibe los ids: no se expone lo de otro empleado.
            if duplicada.revision.visita.empleado_id == request.user.id:
                cuerpo["revision"] = duplicada.revision.id
                cuerpo["visita"] = duplicada.revision.visita_id
            return Response(cuerpo, status=status.HTTP_409_CONFLICT)
        return Response(
            RevisionSerializer(revision).data, status=status.HTTP_201_CREATED
        )


class CerrarVisitaView(APIView):
    """Cierra una visita abierta propia, con al menos una revisión."""

    permission_classes = [EsEmpleado | EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Cerrar una visita",
        description=(
            "`datos` es la planilla de ámbito visita; todo es opcional. Cerrar de "
            "nuevo una visita que ya cerró el mismo usuario devuelve 200 con la "
            "visita; si la cerró el sistema o un administrador, 409. Cerrar la "
            "visita de un administrador no modifica el proyecto."
        ),
        request=CerrarVisitaSerializer,
        responses={
            200: VisitaRealizadaSerializer,
            400: OpenApiResponse(
                description="No está abierta, no tiene revisiones o la planilla "
                "es inválida."
            ),
            404: OpenApiResponse(
                description="La visita no existe o es de otro usuario."
            ),
            409: OpenApiResponse(
                description="La visita ya la cerró el sistema o un administrador."
            ),
        },
    )
    def post(self, request, pk):
        """Cierra con `cierre=empleado`; la visita de otro empleado da 404."""
        visita = Visita.objects.filter(pk=pk, empleado=request.user).first()
        if visita is None:
            raise NotFound("La visita no existe.")
        entrada = CerrarVisitaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            cerrada = cerrar_visita(
                visita,
                quien=request.user,
                cierre=Visita.Cierre.EMPLEADO,
                **entrada.validated_data,
            )
        except VisitaYaCerrada:
            raise VisitaYaCerradaError()
        cerrada = (
            Visita.objects.select_related("proyecto__sitio")
            .prefetch_related(*PRECARGA_REVISIONES)
            .get(pk=cerrada.pk)
        )
        return Response(VisitaRealizadaSerializer(cerrada).data)


class ParametrosHistorialSerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)


class HistorialView(generics.ListAPIView):
    """Visitas realizadas del empleado, con filtro por fecha local."""

    permission_classes = [EsEmpleado]
    serializer_class = VisitaRealizadaSerializer

    def get_queryset(self):
        filtros = ParametrosHistorialSerializer(data=self.request.query_params)
        filtros.is_valid(raise_exception=True)
        fechas = filtros.validated_data
        consulta = Visita.objects.filter(
            empleado=self.request.user, estado=Visita.Estado.REALIZADA
        )
        if "desde" in fechas:
            consulta = consulta.filter(cerrada_en__date__gte=fechas["desde"])
        if "hasta" in fechas:
            consulta = consulta.filter(cerrada_en__date__lte=fechas["hasta"])
        return (
            consulta.select_related("proyecto__sitio")
            .prefetch_related(*PRECARGA_REVISIONES)
            .order_by("-cerrada_en", "-id")
        )

    @extend_schema(
        summary="Mi historial de visitas realizadas",
        parameters=[
            OpenApiParameter("desde", OpenApiTypes.DATE, description="AAAA-MM-DD"),
            OpenApiParameter("hasta", OpenApiTypes.DATE, description="AAAA-MM-DD"),
        ],
    )
    def get(self, request, *args, **kwargs):
        """Lista paginada; `desde` y `hasta` son inclusivos (fecha local)."""
        return super().get(request, *args, **kwargs)


class IgnorarAccept(BaseContentNegotiation):
    """Usa siempre el primer renderer: la imagen no depende del `Accept`."""

    def select_parser(self, request, parsers):
        return parsers[0] if parsers else None

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class FotoView(APIView):
    """Sirve la foto a su empleado o a un administrador."""

    permission_classes = [EsEmpleado | EsAdministrador]
    content_negotiation_class = IgnorarAccept

    @extend_schema(
        summary="Descargar una foto",
        responses={
            (200, "image/jpeg"): OpenApiTypes.BINARY,
            403: OpenApiResponse(description="La foto es de otro empleado."),
            404: OpenApiResponse(description="La foto no existe."),
        },
    )
    def get(self, request, codigo):
        """Devuelve el JPEG; 404 si no existe y 403 si no corresponde."""
        foto = (
            Foto.objects.select_related("revision__visita")
            .filter(codigo=codigo)
            .first()
        )
        if foto is None:
            raise NotFound("La foto no existe.")
        if not (
            request.user.es_administrador
            or foto.revision.visita.empleado_id == request.user.id
        ):
            raise PermissionDenied("No tiene acceso a esta foto.")
        try:
            archivo = foto.imagen.open("rb")
        except FileNotFoundError:
            raise NotFound("La foto no existe.")
        respuesta = FileResponse(archivo, content_type="image/jpeg")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta
