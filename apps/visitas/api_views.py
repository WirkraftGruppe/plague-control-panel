"""Vistas de la API de Visitas: abrir, revisiones, cerrar, listados y fotos."""

from django.core.exceptions import (
    RequestDataTooBig,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.db.models import F
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import generics, serializers, status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from rest_framework.negotiation import BaseContentNegotiation
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.permisos import EsAdministrador, EsEmpleado
from apps.empresas.consultas import empresa_de

from .models import Foto, Visita
from .serializers import (
    MAX_BYTES_FOTO,
    MAX_FOTOS,
    AbrirVisitaSerializer,
    CerrarVisitaSerializer,
    CrearRevisionSerializer,
    NoRevisadoSerializer,
    ReportarNoRevisadoSerializer,
    RevisionSerializer,
    VisitaActivaSerializer,
    VisitaRealizadaSerializer,
)
from .services import (
    NoRevisadoDuplicado,
    RevisionDuplicada,
    VisitaNoAbierta,
    VisitaNoEncontrada,
    VisitaYaCerrada,
    abrir_visita,
    cerrar_visita,
    registrar_no_revisado,
    registrar_revision,
)

MENSAJE_DUPLICADA = "La revisión ya fue registrada."
MENSAJE_NO_REVISADO_DUPLICADO = "El reporte ya fue registrado."
MAX_BYTES_PEDIDO = MAX_FOTOS * MAX_BYTES_FOTO + 1024 * 1024
PRECARGA_TURNO = ("items__punto", "items__servicio", "revisiones", "no_revisados")
PRECARGA_REVISIONES = (
    "revisiones__punto",
    "revisiones__servicio",
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


class VisitaNoAbiertaError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La visita no está abierta."
    default_code = "visita_no_abierta"


def visitas_activas_del_usuario(request):
    """Turnos pendientes y abiertos del usuario, en su empresa."""
    return (
        Visita.objects.de_empresa(empresa_de(request))
        .filter(
            empleado=request.user,
            estado__in=[Visita.Estado.ABIERTA, Visita.Estado.PENDIENTE],
        )
        .select_related("sitio__cliente")
        .prefetch_related(*PRECARGA_TURNO)
    )


class MisVisitasView(generics.ListAPIView):
    """Visitas pendientes y abiertas del usuario autenticado."""

    permission_classes = [EsEmpleado | EsAdministrador]
    serializer_class = VisitaActivaSerializer

    def get_queryset(self):
        return visitas_activas_del_usuario(self.request).order_by(
            "estado", F("programada_para").asc(nulls_last=True), "id"
        )

    @extend_schema(summary="Mis visitas pendientes y abiertas")
    def get(self, request, *args, **kwargs):
        """Lista paginada; las abiertas van primero y cada una trae su `estado` y
        los `items` (punto y servicio) del turno."""
        return super().get(request, *args, **kwargs)


class MiVisitaDetalleView(generics.RetrieveAPIView):
    """Un turno pendiente o abierto del usuario, con la forma de la lista."""

    permission_classes = [EsEmpleado | EsAdministrador]
    serializer_class = VisitaActivaSerializer

    def get_queryset(self):
        return visitas_activas_del_usuario(self.request)

    @extend_schema(
        summary="Detalle de uno de mis turnos",
        responses={
            200: VisitaActivaSerializer,
            404: OpenApiResponse(
                description="No existe, es de otro empleado o de otra empresa, "
                "o ya está realizada."
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AbrirVisitaView(APIView):
    """Abre la jornada del empleado o del administrador en un sitio (idempotente)."""

    permission_classes = [EsEmpleado | EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Abrir una visita",
        description=(
            "Abre el turno pendiente más antiguo del empleado en el sitio del QR o "
            "crea una visita sin ítems. `qr_codigo` es el de un punto activo. Si el "
            "empleado ya tiene una abierta en el sitio la devuelve con 200. `latitud`, "
            "`longitud` y `precision_m` son opcionales: con coordenadas se guarda la "
            "distancia al punto y la incidencia de ubicación, sin rechazar nunca por "
            "distancia. `abierta_en` (opcional) es la hora en que el empleado abrió "
            "sin conexión: no puede ser futura ni tener más de "
            "`ATRASO_MAXIMO_APP_HORAS` de atraso (`code: atraso_excedido`). La "
            "visita de un administrador no toma pendientes."
        ),
        request=AbrirVisitaSerializer,
        responses={
            201: VisitaActivaSerializer,
            200: VisitaActivaSerializer,
            400: OpenApiResponse(
                description="QR inexistente, de un punto o sitio inactivo, o "
                "`abierta_en` futura o con atraso excedido (`campos.abierta_en`, "
                "con `code: atraso_excedido` en el segundo caso)."
            ),
        },
    )
    def post(self, request):
        """201 si crea o abre una pendiente, 200 si ya estaba abierta."""
        entrada = AbrirVisitaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        visita, creada = abrir_visita(
            empleado=request.user,
            qr_codigo=entrada.validated_data["qr_codigo"],
            latitud=entrada.validated_data["latitud"],
            longitud=entrada.validated_data["longitud"],
            precision_m=entrada.validated_data["precision_m"],
            abierta_en=entrada.validated_data["abierta_en"],
        )
        visita = (
            Visita.objects.de_empresa(empresa_de(request))
            .select_related("sitio__cliente")
            .prefetch_related(*PRECARGA_TURNO)
            .get(pk=visita.pk)
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
            "unidad de la cantidad, válida para el producto); `fotos` se repite de 0 "
            "a 2 veces (hasta 8 MB cada una). Un `cliente_uuid` ya registrado "
            "responde 409; "
            "`revision` y `visita` solo vienen si son del mismo empleado. Un "
            "administrador que escanea un punto sin coordenadas, con precisión de a lo "
            "sumo 50 m, las fija. `servicio` (id, opcional) es el que eligió el "
            "empleado: si difiere del que decide el servidor, la revisión lo usa y "
            "queda con una incidencia."
        ),
        request={
            "multipart/form-data": OpenApiRequest(
                CrearRevisionSerializer,
                # Viaja como una parte JSON, no como campos sueltos.
                encoding={"productos_aplicados": {"contentType": "application/json"}},
            )
        },
        responses={
            201: RevisionSerializer,
            400: OpenApiResponse(
                description=(
                    "Validación: QR que no es de un punto del sitio, visita no "
                    "abierta, coordenadas faltantes, punto sin servicio o con el "
                    "servicio dado de baja, `servicio` inactivo o de otra empresa, "
                    "planilla inválida, hora futura o revisión con más horas de "
                    "atraso que `ATRASO_MAXIMO_APP_HORAS` (`campos.realizada_en` "
                    "con `code: atraso_excedido`)."
                )
            ),
            404: OpenApiResponse(
                description="La visita no existe o es de otro usuario."
            ),
            409: OpenApiResponse(
                description="El `cliente_uuid` ya fue registrado, o la visita propia "
                "no está abierta (`code: visita_no_abierta`: reenviar `abrir`)."
            ),
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
        except VisitaNoAbierta as no_abierta:
            raise VisitaNoAbiertaError(" ".join(no_abierta.messages))
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


class ReportarNoRevisadoView(APIView):
    """Reporta un punto que no se pudo revisar en una visita abierta (multipart)."""

    permission_classes = [EsEmpleado | EsAdministrador]
    parser_classes = [MultiPartParser]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Reportar un punto no revisado",
        description=(
            "Multipart. `punto` es el id de un punto activo del sitio de la visita "
            "y `motivo` uno de `falta_estacion`, `codigo_ilegible`, `sin_acceso` u "
            "`otro`. `foto` es opcional (hasta 8 MB). No es una revisión: no cuenta "
            "para el vencimiento, pero una visita sin revisiones y con al menos un "
            "reporte se puede cerrar (`sin_revisiones`). Un `cliente_uuid` ya "
            "registrado responde 409; `reporte` y `visita` solo vienen si es del "
            "mismo empleado. `reportado_en` (opcional) es la hora del reporte si el "
            "empleado estaba sin conexión, con el mismo límite de atraso."
        ),
        request={"multipart/form-data": ReportarNoRevisadoSerializer},
        responses={
            201: NoRevisadoSerializer,
            400: OpenApiResponse(
                description=(
                    "Punto de otro sitio, inactivo o ya reportado, `reportado_en` "
                    "futura o con atraso excedido (`code: atraso_excedido`), o "
                    "campos inválidos."
                )
            ),
            404: OpenApiResponse(
                description="La visita no existe o es de otro usuario."
            ),
            409: OpenApiResponse(
                description="El `cliente_uuid` ya fue registrado, o la visita propia "
                "no está abierta (`code: visita_no_abierta`: reenviar `abrir`)."
            ),
            413: OpenApiResponse(description="El pedido supera el tamaño permitido."),
        },
    )
    def post(self, request, pk):
        """Busca la visita propia antes de leer el cuerpo; delega en el servicio."""
        try:
            largo = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            largo = 0
        # Se corta antes de leer el cuerpo: Django escribe los archivos a disco.
        if largo > MAX_BYTES_PEDIDO:
            raise PedidoDemasiadoGrande()
        visita = (
            Visita.objects.de_empresa(empresa_de(request))
            .filter(pk=pk, empleado=request.user)
            .first()
        )
        if visita is None:
            raise NotFound("La visita no existe.")
        try:
            datos_pedido = request.data
        except (RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
            raise PedidoDemasiadoGrande()
        entrada = ReportarNoRevisadoSerializer(data=datos_pedido)
        entrada.is_valid(raise_exception=True)
        try:
            reporte = registrar_no_revisado(
                empleado=request.user, visita_pk=visita.pk, **entrada.validated_data
            )
        except VisitaNoEncontrada:
            raise NotFound("La visita no existe.")
        except VisitaNoAbierta as no_abierta:
            raise VisitaNoAbiertaError(" ".join(no_abierta.messages))
        except NoRevisadoDuplicado as duplicado:
            cuerpo = {"detalle": MENSAJE_NO_REVISADO_DUPLICADO, "campos": {}}
            # Solo el dueño recibe los ids: no se expone lo de otro empleado.
            if duplicado.reporte.visita.empleado_id == request.user.id:
                cuerpo["reporte"] = duplicado.reporte.id
                cuerpo["visita"] = duplicado.reporte.visita_id
            return Response(cuerpo, status=status.HTTP_409_CONFLICT)
        return Response(
            NoRevisadoSerializer(reporte).data, status=status.HTTP_201_CREATED
        )


class CerrarVisitaView(APIView):
    """Cierra una visita abierta propia, con al menos una revisión o un reporte de
    punto no revisado."""

    permission_classes = [EsEmpleado | EsAdministrador]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "crear_visita"

    @extend_schema(
        summary="Cerrar una visita",
        description=(
            "`datos` es la planilla de ámbito visita; todo es opcional. Cerrar de "
            "nuevo una visita que ya cerró el mismo usuario devuelve 200 con la "
            "visita; si la cerró el sistema o un administrador, 409. Cerrar la "
            "visita de un administrador no cuenta como servicio. `cerrada_en` "
            "(opcional) es la hora del cierre si el empleado estaba sin conexión: no "
            "puede ser anterior a la apertura, futura ni exceder el atraso máximo."
        ),
        request=CerrarVisitaSerializer,
        responses={
            200: VisitaRealizadaSerializer,
            400: OpenApiResponse(
                description="No tiene al menos una revisión o un reporte de punto "
                "no revisado, la planilla es inválida o `cerrada_en` es inválida "
                "(`code: atraso_excedido` si excede el atraso)."
            ),
            404: OpenApiResponse(
                description="La visita no existe o es de otro usuario."
            ),
            409: OpenApiResponse(
                description="La visita propia no está abierta (`code: "
                "visita_no_abierta`: reenviar `abrir`) o ya la cerró el sistema o un "
                "administrador (`code: visita_ya_cerrada`)."
            ),
        },
    )
    def post(self, request, pk):
        """Cierra con `cierre=empleado`; la visita de otro empleado da 404."""
        empresa = empresa_de(request)
        visita = (
            Visita.objects.de_empresa(empresa)
            .filter(pk=pk, empleado=request.user)
            .first()
        )
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
        except VisitaNoAbierta as no_abierta:
            raise VisitaNoAbiertaError(" ".join(no_abierta.messages))
        cerrada = (
            Visita.objects.de_empresa(empresa)
            .select_related("sitio")
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
        consulta = Visita.objects.de_empresa(empresa_de(self.request)).filter(
            empleado=self.request.user, estado=Visita.Estado.REALIZADA
        )
        if "desde" in fechas:
            consulta = consulta.filter(cerrada_en__date__gte=fechas["desde"])
        if "hasta" in fechas:
            consulta = consulta.filter(cerrada_en__date__lte=fechas["hasta"])
        return (
            consulta.select_related("sitio")
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
            404: OpenApiResponse(description="La foto no existe o es de otra empresa."),
        },
    )
    def get(self, request, codigo):
        """Devuelve el JPEG; 404 si no existe o es de otra empresa, 403 si no
        corresponde."""
        foto = (
            Foto.objects.de_empresa(empresa_de(request))
            .select_related("revision__visita")
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
