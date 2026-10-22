"""Vistas del panel de Sitios (solo administradores)."""

from urllib.parse import urlencode

from csp.decorators import csp_update
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    BooleanField,
    Case,
    Count,
    Exists,
    F,
    Min,
    OuterRef,
    Q,
    Subquery,
    Value,
    When,
)
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.clientes.models import Cliente
from apps.panel.listados import ListadoPanelMixin
from apps.panel.mapa import ORIGEN_TESELAS
from apps.servicios.models import TipoServicio
from apps.visitas.models import Visita

from . import geocodificacion, qr, services
from .estado import (
    CHIP_ESTADO_SITIO,
    EstadoSitio,
    EstadoVencimiento,
    condicion_de_estado,
    conteos_por_estado,
    estado_de_sitio,
    estados_por_vencimiento,
)
from .models import Plano, PuntoControl, Sitio
from .panel_forms import (
    PlanoForm,
    PosicionForm,
    ProgramacionForm,
    PuntoAltaForm,
    PuntoForm,
    SitioForm,
)

PESTANAS = ("turnos", "planos", "datos")
TURNOS_REALIZADOS_MAXIMO = 10
ATENCION_MAXIMO = 10
CLASE_VENCIMIENTO = {
    EstadoVencimiento.AL_DIA: "ok",
    EstadoVencimiento.PROXIMA: "warn",
    EstadoVencimiento.VENCIDA: "danger",
    EstadoVencimiento.SIN_PROGRAMAR: "neutral",
}


def _marcar_vencimiento(puntos):
    """Agrega a cada punto su estado por vencimiento, con etiqueta y clase."""
    estados = estados_por_vencimiento(puntos, timezone.localdate())
    for punto in puntos:
        estado = punto.estado = estados[punto.pk]
        punto.vencimiento_etiqueta = EstadoVencimiento(estado).label
        punto.vencimiento_clase = CLASE_VENCIMIENTO[estado]


class SitioListado(AdministradorRequeridoMixin, ListadoPanelMixin):
    """Inicio del panel: turnos de hoy, qué requiere atención y todos los sitios.

    El estado de cada sitio sale del mínimo ``proximo_vencimiento`` de sus puntos
    activos; la cantidad de consultas no depende de la cantidad de sitios.
    """

    model = Sitio
    template_name = "sitios/panel/listado.html"
    template_parcial = "sitios/panel/_listado.html"
    orden_permitido = (
        "nombre",
        "cliente__razon_social",
        "localidad",
        "proximo_vencimiento",
    )
    campos_busqueda = ("nombre", "direccion", "localidad", "cliente__razon_social")
    # Turnos que cuentan para "tiene turno": los que todavía no se hicieron.
    ESTADOS_EN_CURSO = (Visita.Estado.PENDIENTE, Visita.Estado.ABIERTA)

    @cached_property
    def hoy(self):
        return timezone.localdate()

    @staticmethod
    def _con_vencimiento(queryset):
        """Agrega el mínimo vencimiento de los puntos activos y el próximo turno."""
        pendientes = Visita.objects.filter(
            sitio=OuterRef("pk"), estado=Visita.Estado.PENDIENTE
        ).order_by("programada_para", "pk")
        return queryset.annotate(
            proximo_vencimiento=Min(
                "puntos__proximo_vencimiento", filter=Q(puntos__activo=True)
            ),
            proximo_turno=Subquery(pendientes.values("programada_para")[:1]),
            proximo_turno_pk=Subquery(pendientes.values("pk")[:1]),
        )

    def _parametro_estado(self):
        estado = self.request.GET.get("estado", "")
        return estado if estado in EstadoSitio.values else ""

    def _base(self):
        """Sitios del alcance pedido (búsqueda, cliente, activo), sin el estado."""
        self.queryset = self._con_vencimiento(Sitio.objects.select_related("cliente"))
        queryset = super().get_queryset()
        cliente = self.request.GET.get("cliente", "")
        # Solo un id válido de BigAutoField; otro valor se ignora, sin dar 500.
        if (
            cliente.isascii()
            and cliente.isdigit()
            and len(cliente) <= 19
            and int(cliente) <= 2**63 - 1
        ):
            queryset = queryset.filter(cliente_id=cliente)
        return queryset.filter(activo=self.request.GET.get("activo") != "0")

    def get_queryset(self):
        base = self._base()
        self.conteos = conteos_por_estado(base, self.hoy)
        estado = self._parametro_estado()
        if estado:
            base = base.filter(condicion_de_estado(estado, self.hoy))
        orden = self.get_orden()
        if orden.lstrip("-") == "proximo_vencimiento" or not orden:
            campo = F("proximo_vencimiento")
            campo = campo.desc(nulls_last=True) if orden else campo.asc(nulls_last=True)
            return base.order_by(campo, "nombre", "pk")
        return base.order_by(orden, "pk")

    def _turnos_de_hoy(self):
        hoy = self.hoy
        visitas = (
            Visita.objects.filter(
                Q(estado=Visita.Estado.PENDIENTE, programada_para__lte=hoy)
                | Q(estado=Visita.Estado.ABIERTA)
                | Q(estado=Visita.Estado.REALIZADA, cerrada_en__date=hoy)
            )
            .select_related("sitio", "empleado")
            .annotate(
                total=Count("items", distinct=True),
                revisados=Count("revisiones__punto", distinct=True),
                atrasado=Case(
                    When(
                        estado=Visita.Estado.PENDIENTE,
                        programada_para__lt=hoy,
                        then=Value(True),
                    ),
                    default=Value(False),
                    output_field=BooleanField(),
                ),
            )
            .order_by("-atrasado", "sitio__nombre", "pk")
        )
        return list(visitas)

    def _requieren_atencion(self):
        vencidos = (
            self._con_vencimiento(Sitio.objects.select_related("cliente"))
            .filter(activo=True)
            .filter(condicion_de_estado(EstadoSitio.VENCIDOS, self.hoy))
            .exclude(
                Exists(
                    Visita.objects.filter(
                        sitio=OuterRef("pk"), estado__in=self.ESTADOS_EN_CURSO
                    )
                )
            )
            .order_by("proximo_vencimiento", "nombre", "pk")
        )
        return list(vencidos[:ATENCION_MAXIMO])

    def _incidencias(self):
        return list(
            Visita.objects.filter(incidencia=True, incidencia_revisada_en__isnull=True)
            .select_related("sitio", "empleado")
            .order_by("-cerrada_en", "-pk")[:ATENCION_MAXIMO]
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        for sitio in contexto["object_list"]:
            estado = estado_de_sitio(sitio.proximo_vencimiento, self.hoy)
            sitio.estado_clave = estado.value
            sitio.chip_tono, sitio.chip_texto = CHIP_ESTADO_SITIO[estado]
        activo = self.request.GET.get("activo", "")
        estado = self._parametro_estado()
        cliente = self.request.GET.get("cliente", "")
        conservar = {"estado": estado, "cliente": cliente, "activo": activo}
        conservar = {k: v for k, v in conservar.items() if v}
        contexto.update(
            conteos=self.conteos,
            estado=estado,
            filtros=[(e.value, e.label, self.conteos[e]) for e in EstadoSitio],
            clientes=Cliente.objects.order_by("razon_social"),
            cliente=cliente,
            activo=activo,
            conservar=conservar,
            conservar_qs=urlencode(conservar),
        )
        parametros = {"q": self.get_busqueda(), "orden": self.get_orden(), **conservar}
        contexto["querystring"] = urlencode({k: v for k, v in parametros.items() if v})
        if not self.request.headers.get("HX-Request"):
            contexto.update(
                turnos_hoy=self._turnos_de_hoy(),
                requieren_atencion=self._requieren_atencion(),
                incidencias=self._incidencias(),
            )
        return contexto


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioAlta(AdministradorRequeridoMixin, CreateView):
    model = Sitio
    form_class = SitioForm
    template_name = "sitios/panel/formulario.html"
    extra_context = {"titulo": "Nuevo sitio"}

    def get_success_url(self):
        return reverse("panel:sitios:ficha", args=[self.object.pk])


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioEdicion(AdministradorRequeridoMixin, UpdateView):
    model = Sitio
    form_class = SitioForm
    template_name = "sitios/panel/formulario.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Editar {self.object.nombre}"
        return contexto

    def get_success_url(self):
        return reverse("panel:sitios:ficha", args=[self.object.pk])


def _numero(valor):
    """Decimal de la base a número de JSON; vacío queda en ``None``."""
    return None if valor is None else float(valor)


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioFicha(AdministradorRequeridoMixin, DetailView):
    """Ficha con pestañas ``?pestana=turnos|planos|datos`` (por defecto, turnos)."""

    model = Sitio
    template_name = "sitios/panel/ficha.html"

    def get_queryset(self):
        return Sitio.objects.select_related("cliente", "responsable")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        sitio = self.object
        hoy = timezone.localdate()
        pestana = self.request.GET.get("pestana", "turnos")
        if pestana not in PESTANAS:
            pestana = "turnos"
        puntos = list(sitio.puntos.select_related("plano", "servicio"))
        _marcar_vencimiento(puntos)
        activos = [p for p in puntos if p.activo]
        for numero, punto in enumerate(activos, start=1):
            punto.numero = numero
        planos = list(sitio.planos.filter(activo=True))
        pk_plano = self.request.GET.get("plano", "")
        plano = next((p for p in planos if str(p.pk) == pk_plano), None)
        plano = plano or (planos[0] if planos else None)
        fechas = [p.proximo_vencimiento for p in activos if p.proximo_vencimiento]
        estado_general = estado_de_sitio(min(fechas, default=None), hoy)
        turnos_pendientes = list(self._turnos(sitio, Visita.Estado.PENDIENTE))
        contexto.update(
            pestana=pestana,
            pestanas=(("turnos", "Turnos"), ("planos", "Planos"), ("datos", "Datos")),
            estado_general=estado_general.value,
            chip_general=CHIP_ESTADO_SITIO[estado_general],
            puntos=puntos,
            puntos_activos=activos,
            datos_ficha_plano=self._datos_ficha_plano(planos, activos),
            planos=planos,
            plano=plano,
            turnos_pendientes=turnos_pendientes,
            turnos_realizados=self._turnos(sitio, Visita.Estado.REALIZADA)[
                :TURNOS_REALIZADOS_MAXIMO
            ],
            aviso_sin_turnos=not turnos_pendientes
            and any(p.estado == EstadoVencimiento.VENCIDA for p in activos),
        )
        if pestana == "datos":
            contexto["datos_mapa"] = self._datos_mapa(sitio)
            contexto["servicios"] = TipoServicio.objects.filter(activo=True).order_by(
                "nombre"
            )
        if pestana == "planos" and plano:
            contexto["datos_plano"] = self._datos_plano(plano, activos)
        return contexto

    @staticmethod
    def _datos_ficha_plano(planos, activos):
        """Planos con sus puntos ubicados y numerados, para el plano de solo lectura."""
        return [
            {
                "id": plano.pk,
                "nombre": plano.nombre,
                "imagen": reverse("panel:sitios:plano_imagen", args=[plano.pk]),
                "ancho": plano.ancho_px,
                "alto": plano.alto_px,
                "puntos": [
                    {
                        "id": p.pk,
                        "numero": p.numero,
                        "nombre": p.nombre,
                        "x": _numero(p.x),
                        "y": _numero(p.y),
                        "estado": p.estado,
                        "estado_texto": p.vencimiento_etiqueta,
                    }
                    for p in activos
                    if p.plano_id == plano.pk and p.x is not None and p.y is not None
                ],
            }
            for plano in planos
        ]

    @staticmethod
    def _turnos(sitio, estado):
        """Turnos del sitio en un estado: pendientes por fecha, el resto recientes."""
        orden = (
            ("programada_para", "pk")
            if estado == Visita.Estado.PENDIENTE
            else ("-cerrada_en", "-pk")
        )
        return (
            sitio.visitas.filter(estado=estado)
            .select_related("empleado")
            .prefetch_related("items")
            .order_by(*orden)
        )

    @staticmethod
    def _datos_mapa(sitio):
        return {
            "sitio": {
                "nombre": sitio.nombre,
                "lat": _numero(sitio.latitud),
                "lng": _numero(sitio.longitud),
            }
        }

    @staticmethod
    def _datos_plano(plano, puntos):
        return {
            "imagen": reverse("panel:sitios:plano_imagen", args=[plano.pk]),
            "ancho": plano.ancho_px,
            "alto": plano.alto_px,
            "plano": plano.pk,
            "puntos": [
                {
                    "id": p.pk,
                    "nombre": p.nombre,
                    "x": _numero(p.x),
                    "y": _numero(p.y),
                    "estado": p.estado,
                    "url": reverse("panel:sitios:punto_posicion", args=[p.pk]),
                }
                for p in puntos
                if p.plano_id == plano.pk
            ],
            "sin_ubicar": [
                {
                    "id": p.pk,
                    "nombre": p.nombre,
                    "url": reverse("panel:sitios:punto_posicion", args=[p.pk]),
                }
                for p in puntos
                if not p.plano_id
                or (p.plano_id == plano.pk and (p.x is None or p.y is None))
            ],
        }


def _url_ficha(sitio_pk, pestana, plano_pk=None):
    url = f"{reverse('panel:sitios:ficha', args=[sitio_pk])}?pestana={pestana}"
    return f"{url}&plano={plano_pk}" if plano_pk else url


class _PuntoMixin(AdministradorRequeridoMixin):
    """Obtiene el punto de la URL, con su sitio."""

    model = PuntoControl

    def get_queryset(self):
        return PuntoControl.objects.select_related("sitio", "plano")


class PuntoAlta(AdministradorRequeridoMixin, CreateView):
    """Alta de un punto; con ``plano``, ``x`` e ``y`` es el clic sobre el plano."""

    form_class = PuntoAltaForm
    template_name = "sitios/panel/punto_formulario.html"

    @cached_property
    def sitio(self):
        """Se busca recién tras la autorización: el anónimo no distingue ids."""
        return get_object_or_404(Sitio, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "sitio": self.sitio}

    def get_initial(self):
        return {"activo": True, "orden": self.sitio.puntos.count()}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo="Nuevo punto", sitio=self.sitio, es_alta=True)
        return contexto

    def get_success_url(self):
        punto = self.object
        if punto.plano_id:
            return _url_ficha(self.sitio.pk, "planos", punto.plano_id)
        return _url_ficha(self.sitio.pk, "datos")


class PuntoEdicion(_PuntoMixin, UpdateView):
    form_class = PuntoForm
    template_name = "sitios/panel/punto_formulario.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "sitio": self.object.sitio}

    def form_valid(self, form):
        """Coordenadas corregidas limpian la marca de escaneo; baja por el servicio."""
        if {"latitud", "longitud"} & set(form.changed_data):
            form.instance.ubicacion_fijada_por = None
            form.instance.ubicacion_fijada_en = None
            form.instance.precision_m = None
        if "activo" not in form.changed_data or form.cleaned_data["activo"]:
            return super().form_valid(form)
        # El servicio bloquea las filas de los puntos activos y rechaza el último;
        # si lo rechaza, no se guarda nada.
        with transaction.atomic():
            try:
                services.desactivar_punto(form.instance)
            except ValidationError as error:
                form.add_error("activo", error)
                return self.form_invalid(form)
            return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo=f"Editar {self.object.nombre}", sitio=self.object.sitio)
        return contexto

    def get_success_url(self):
        return _url_ficha(self.object.sitio_id, "datos")


class PuntoDesactivar(_PuntoMixin, DetailView):
    """GET pide confirmación; POST desactiva el punto."""

    template_name = "sitios/panel/punto_desactivar.html"

    def post(self, request, pk):
        punto = self.get_object()
        try:
            services.desactivar_punto(punto)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, f"Se desactivó el punto {punto.nombre}.")
        return redirect(_url_ficha(punto.sitio_id, "datos"))


class PuntoQRPng(_PuntoMixin, DetailView):
    """PNG del QR del punto: descarga, o inline con ``?inline=1``."""

    def render_to_response(self, context, **kwargs):
        punto = self.object
        respuesta = HttpResponse(qr.png_qr(punto), content_type="image/png")
        nombre = slugify(f"{punto.sitio.nombre} {punto.nombre}") or "punto"
        modo = "inline" if self.request.GET.get("inline") else "attachment"
        respuesta["Content-Disposition"] = f'{modo}; filename="qr-{nombre}.png"'
        respuesta["Cache-Control"] = "private, no-store"
        return respuesta


class PuntoRegenerarQR(_PuntoMixin, DetailView):
    """GET pide confirmación; POST regenera el código e invalida la etiqueta."""

    template_name = "sitios/panel/regenerar_qr.html"

    def post(self, request, pk):
        punto = self.get_object()
        services.regenerar_qr(punto)
        messages.success(
            request, "Se generó un nuevo QR; la etiqueta anterior ya no sirve."
        )
        return redirect(_url_ficha(punto.sitio_id, "datos"))


class _AccionPunto(_PuntoMixin, SingleObjectMixin, View):
    """Acción POST sobre un punto, para HTMX o para un botón de la ficha."""

    http_method_names = ["post"]


class PuntoProgramacion(_PuntoMixin, SingleObjectMixin, View):
    """Edición en línea de servicio, frecuencia y vencimiento; devuelve la fila."""

    http_method_names = ["get", "post"]
    template_name = "sitios/panel/_fila_punto.html"

    def _fila(self, request, punto, form=None, estado=200):
        _marcar_vencimiento([punto])
        contexto = {
            "punto": punto,
            "form": form,
            "servicios": TipoServicio.objects.filter(activo=True).order_by("nombre"),
        }
        return render(request, self.template_name, contexto, status=estado)

    def get(self, request, pk):
        return self._fila(request, self.get_object())

    def post(self, request, pk):
        punto = self.get_object()
        form = ProgramacionForm(request.POST)
        if not form.is_valid():
            return self._fila(request, punto, form, estado=422)
        datos = form.cleaned_data
        services.actualizar_programacion(
            punto,
            datos["servicio"],
            datos["frecuencia_dias"],
            datos["proximo_vencimiento"],
            request.user,
        )
        return self._fila(request, punto)


class PuntoPosicion(_AccionPunto):
    """Guarda la posición (x, y en fracción 0 a 1) del marcador en el plano.

    Con ``plano`` en el POST ubica en él un punto que no lo tenía.
    """

    def post(self, request, pk):
        punto = self.get_object()
        form = PosicionForm(request.POST)
        if not form.is_valid():
            error = (
                "Plano inválido." if "plano" in form.errors else "Posición inválida."
            )
            return JsonResponse({"error": error}, status=400)
        x, y = form.cleaned_data["x"], form.cleaned_data["y"]
        if "plano" in request.POST:
            plano = form.cleaned_data["plano"]
            try:
                if plano is None:
                    raise ValidationError("Plano inexistente.")
                services.ubicar_en_plano(punto, plano, x, y)
            except ValidationError:
                return JsonResponse({"error": "Plano inválido."}, status=400)
        elif not punto.plano_id:
            return JsonResponse({"error": "Posición inválida."}, status=400)
        else:
            services.mover_en_plano(punto, x, y)
        return JsonResponse({"x": _numero(punto.x), "y": _numero(punto.y)})


class PlanoAlta(AdministradorRequeridoMixin, CreateView):
    """Sube un plano (JPG, PNG o PDF); ``Plano`` lo valida y lo guarda como PNG."""

    form_class = PlanoForm
    template_name = "sitios/panel/plano_formulario.html"

    @cached_property
    def sitio(self):
        """Se busca recién tras la autorización: el anónimo no distingue ids."""
        return get_object_or_404(Sitio, pk=self.kwargs["pk"])

    def form_valid(self, form):
        form.instance.sitio = self.sitio
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo="Subir plano", sitio=self.sitio)
        return contexto

    def get_success_url(self):
        return _url_ficha(self.sitio.pk, "planos", self.object.pk)


class PlanoImagen(AdministradorRequeridoMixin, View):
    """Imagen del plano para el editor: autenticada, nunca desde MEDIA público."""

    def get(self, request, pk):
        plano = get_object_or_404(Plano, pk=pk)
        try:
            archivo = plano.imagen.open("rb")
        except FileNotFoundError:
            raise Http404 from None
        respuesta = FileResponse(archivo, content_type="image/png")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta


class Geocodificar(AdministradorRequeridoMixin, View):
    """Candidatos de Nominatim; solo POST (con CSRF) y el texto va en el cuerpo."""

    http_method_names = ["post", "options"]

    def post(self, request):
        try:
            candidatos = geocodificacion.buscar(request.POST.get("q", ""))
        except geocodificacion.TextoInvalido:
            return JsonResponse(
                {"error": "Escriba una dirección de hasta 200 caracteres."}, status=400
            )
        except geocodificacion.GeocodificacionError:
            return JsonResponse(
                {"error": geocodificacion.MENSAJE_CARGA_MANUAL}, status=503
            )
        return JsonResponse({"resultados": candidatos})
