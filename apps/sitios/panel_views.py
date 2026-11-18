"""Vistas del panel de Sitios (solo administradores)."""

from collections import defaultdict
from urllib.parse import urlencode

from csp.decorators import csp_update
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    BooleanField,
    Case,
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
from django.views.generic import CreateView, DetailView, FormView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.accounts.models import User
from apps.clientes.empresa import VistaDeEmpresaMixin
from apps.clientes.models import Cliente
from apps.panel.listados import ListadoPanelMixin
from apps.panel.mapa import ORIGEN_TESELAS
from apps.servicios.models import TipoServicio
from apps.visitas.models import ItemTurno, PuntoNoRevisado, Revision, Visita
from apps.visitas.services import condicion_incidencia_sin_revisar

from . import geocodificacion, qr, services
from .estado import (
    CHIP_ESTADO_SITIO,
    EstadoSitio,
    EstadoVencimiento,
    condicion_de_estado,
    conteos_por_estado,
    estado_de_sitio_por_puntos,
    estados_por_vencimiento,
)
from .models import Plano, PuntoControl, Sitio
from .panel_forms import (
    PlanoForm,
    PosicionForm,
    ProgramacionForm,
    PuntoAltaForm,
    PuntoForm,
    PuntosAltaMultipleForm,
    SitioForm,
)

PESTANAS = ("turnos", "planos", "datos")
TURNOS_REALIZADOS_MAXIMO = 10
ATENCION_MAXIMO = 10
NO_REVISADOS_MAXIMO = 20
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


def _nombre_de(usuario):
    return usuario.get_full_name() or usuario.username


def avance_de_visitas(empresa, visitas):
    """Agrega a cada visita ``total`` (M), ``revisados`` (N) y ``ids_revisados``.

    M son los ítems del turno; sin ítems (visita abierta por QR), los puntos activos
    del sitio. N son los puntos distintos de esos M con una revisión en la visita.
    Hace tres consultas, sin importar cuántas visitas ni puntos haya.
    """
    visitas = list(visitas)
    if not visitas:
        return visitas
    ids = [v.pk for v in visitas]
    items, activos, revisados = defaultdict(set), defaultdict(set), defaultdict(set)
    for visita_id, punto_id in (
        ItemTurno.objects.de_empresa(empresa)
        .filter(visita_id__in=ids)
        .values_list("visita_id", "punto_id")
    ):
        items[visita_id].add(punto_id)
    for sitio_id, punto_id in (
        PuntoControl.objects.de_empresa(empresa)
        .filter(sitio_id__in={v.sitio_id for v in visitas}, activo=True)
        .values_list("sitio_id", "pk")
    ):
        activos[sitio_id].add(punto_id)
    for visita_id, punto_id in (
        Revision.objects.de_empresa(empresa)
        .filter(visita_id__in=ids)
        .values_list("visita_id", "punto_id")
    ):
        revisados[visita_id].add(punto_id)
    for visita in visitas:
        meta = items[visita.pk] or activos[visita.sitio_id]
        visita.total = len(meta)
        visita.revisados = len(meta & revisados[visita.pk])
        visita.ids_revisados = revisados[visita.pk]
    return visitas


def contexto_de_puntos(empresa, sitio):
    """Puntos del sitio con estado, última revisión y turnos abiertos que cuentan.

    Lo comparten la ficha y su parcial de avance; la cantidad de consultas no
    depende de la cantidad de puntos.
    """
    ultima = (
        Revision.objects.de_empresa(empresa)
        .filter(
            punto=OuterRef("pk"),
            visita__estado__in=[Visita.Estado.ABIERTA, Visita.Estado.REALIZADA],
            visita__cuenta_como_servicio=True,
        )
        .order_by("-realizada_en", "-pk")
    )
    puntos = list(
        sitio.puntos.select_related("plano", "servicio").annotate(
            ultima_revision=Subquery(ultima.values("realizada_en")[:1]),
            ultimo_operario_id=Subquery(ultima.values("visita__empleado_id")[:1]),
        )
    )
    _marcar_vencimiento(puntos)
    activos = [p for p in puntos if p.activo]
    for numero, punto in enumerate(activos, start=1):
        punto.numero = numero
    abiertos = avance_de_visitas(
        empresa,
        Visita.objects.de_empresa(empresa)
        .filter(
            sitio=sitio,
            estado=Visita.Estado.ABIERTA,
            cuenta_como_servicio=True,
        )
        .select_related("empleado")
        .order_by("abierta_en", "pk"),
    )
    ids = {p.ultimo_operario_id for p in puntos if p.ultimo_operario_id}
    # User no tiene guardia de empresa: se filtra a mano.
    operarios = {
        u.pk: _nombre_de(u) for u in User.objects.filter(empresa=empresa, pk__in=ids)
    }
    for punto in puntos:
        punto.ultimo_operario = operarios.get(punto.ultimo_operario_id, "")
        punto.revisado_por = [
            _nombre_de(v.empleado) for v in abiertos if punto.pk in v.ids_revisados
        ]
    return {"puntos": puntos, "puntos_activos": activos, "turnos_abiertos": abiertos}


class SitioListado(AdministradorRequeridoMixin, ListadoPanelMixin):
    """Inicio del panel: turnos de hoy, qué requiere atención y todos los sitios.

    El estado de cada sitio sale de sus puntos activos; las consultas no
    dependen de la cantidad de sitios.
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

    def _sitios(self):
        return Sitio.objects.de_empresa(self.request.empresa).select_related("cliente")

    def _parametro_estado(self):
        estado = self.request.GET.get("estado", "")
        return estado if estado in EstadoSitio.values else ""

    def _base(self):
        """Sitios del alcance pedido (búsqueda, cliente, activo), sin el estado."""
        self.queryset = self._con_vencimiento(self._sitios())
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
            Visita.objects.de_empresa(self.request.empresa)
            .filter(
                Q(estado=Visita.Estado.PENDIENTE, programada_para__lte=hoy)
                | Q(estado=Visita.Estado.ABIERTA)
                | Q(estado=Visita.Estado.REALIZADA, cerrada_en__date=hoy)
            )
            .select_related("sitio", "empleado")
            .annotate(
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
        return avance_de_visitas(self.request.empresa, visitas)

    def _requieren_atencion(self):
        vencidos = (
            self._con_vencimiento(self._sitios())
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
            Visita.objects.de_empresa(self.request.empresa)
            .filter(condicion_incidencia_sin_revisar())
            .select_related("sitio", "empleado")
            .order_by("-cerrada_en", "-pk")[:ATENCION_MAXIMO]
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        sitios = list(contexto["object_list"])
        activos = defaultdict(list)
        for punto in PuntoControl.objects.de_empresa(self.request.empresa).filter(
            sitio__in=sitios, activo=True
        ):
            activos[punto.sitio_id].append(punto)
        for sitio in sitios:
            estado = estado_de_sitio_por_puntos(activos[sitio.pk], self.hoy)
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
            clientes=Cliente.objects.de_empresa(self.request.empresa).order_by(
                "razon_social"
            ),
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
class SitioAlta(VistaDeEmpresaMixin, AdministradorRequeridoMixin, CreateView):
    model = Sitio
    form_class = SitioForm
    template_name = "sitios/panel/formulario.html"
    extra_context = {"titulo": "Nuevo sitio"}

    def get_success_url(self):
        return reverse("panel:sitios:ficha", args=[self.object.pk])


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class SitioEdicion(VistaDeEmpresaMixin, AdministradorRequeridoMixin, UpdateView):
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
class SitioFicha(VistaDeEmpresaMixin, AdministradorRequeridoMixin, DetailView):
    """Ficha con pestañas ``?pestana=turnos|planos|datos`` (por defecto, turnos)."""

    model = Sitio
    template_name = "sitios/panel/ficha.html"

    def get_queryset(self):
        return super().get_queryset().select_related("cliente", "responsable")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        sitio = self.object
        hoy = timezone.localdate()
        pestana = self.request.GET.get("pestana", "turnos")
        if pestana not in PESTANAS:
            pestana = "turnos"
        datos = contexto_de_puntos(self.request.empresa, sitio)
        activos = datos["puntos_activos"]
        planos = list(sitio.planos.filter(activo=True))
        pk_plano = self.request.GET.get("plano", "")
        plano = next((p for p in planos if str(p.pk) == pk_plano), None)
        plano = plano or (planos[0] if planos else None)
        estado_general = estado_de_sitio_por_puntos(activos, hoy)
        turnos_pendientes = list(self._turnos(sitio, Visita.Estado.PENDIENTE))
        contexto.update(
            pestana=pestana,
            pestanas=(("turnos", "Turnos"), ("planos", "Planos"), ("datos", "Datos")),
            estado_general=estado_general.value,
            chip_general=CHIP_ESTADO_SITIO[estado_general],
            **datos,
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
            contexto["no_revisados"] = (
                PuntoNoRevisado.objects.de_empresa(self.request.empresa)
                .filter(punto__sitio=sitio)
                .select_related("punto", "visita")
                .order_by("-creado", "-pk")[:NO_REVISADOS_MAXIMO]
            )
            contexto["datos_mapa"] = self._datos_mapa(sitio)
            contexto["servicios"] = (
                TipoServicio.objects.de_empresa(self.request.empresa)
                .filter(activo=True)
                .order_by("nombre")
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


class SitioFichaAvance(VistaDeEmpresaMixin, AdministradorRequeridoMixin, DetailView):
    """Parcial de HTMX con los turnos abiertos y la lista de puntos de la ficha."""

    model = Sitio
    template_name = "sitios/panel/_ficha_avance.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(contexto_de_puntos(self.request.empresa, self.object))
        return contexto


def _url_ficha(sitio_pk, pestana, plano_pk=None):
    url = f"{reverse('panel:sitios:ficha', args=[sitio_pk])}?pestana={pestana}"
    return f"{url}&plano={plano_pk}" if plano_pk else url


class _PuntoMixin(AdministradorRequeridoMixin):
    """Obtiene el punto de la URL, con su sitio."""

    model = PuntoControl

    def get_queryset(self):
        return PuntoControl.objects.de_empresa(self.request.empresa).select_related(
            "sitio", "plano"
        )


class PuntoAlta(AdministradorRequeridoMixin, CreateView):
    """Alta de un punto; con ``plano``, ``x`` e ``y`` es el clic sobre el plano."""

    form_class = PuntoAltaForm
    template_name = "sitios/panel/punto_formulario.html"

    @cached_property
    def sitio(self):
        """Se busca recién tras la autorización: el anónimo no distingue ids."""
        return get_object_or_404(
            Sitio.objects.de_empresa(self.request.empresa), pk=self.kwargs["pk"]
        )

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


class _SitioDeEmpresaMixin(AdministradorRequeridoMixin):
    """Sitio de la URL acotado a la empresa; se busca tras la autorización."""

    @cached_property
    def sitio(self):
        return get_object_or_404(
            Sitio.objects.de_empresa(self.request.empresa), pk=self.kwargs["pk"]
        )


class PuntosAltaMultiple(_SitioDeEmpresaMixin, FormView):
    """Alta de N puntos numerados con servicio y frecuencia comunes."""

    form_class = PuntosAltaMultipleForm
    template_name = "sitios/panel/puntos_alta_multiple.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "empresa": self.request.empresa}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            sitio=self.sitio, cancelar_url=_url_ficha(self.sitio.pk, "datos")
        )
        return contexto

    def form_valid(self, form):
        try:
            puntos = services.crear_puntos_numerados(self.sitio, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, f"Se crearon {len(puntos)} puntos.")
        return redirect(_url_ficha(self.sitio.pk, "datos"))


class HojaQR(_SitioDeEmpresaMixin, View):
    """Hoja imprimible con los QR de los puntos activos; el POST los marca impresos."""

    def _activos(self, request):
        return PuntoControl.objects.de_empresa(request.empresa).filter(
            sitio=self.sitio, activo=True
        )

    def _puntos(self, request):
        puntos = self._activos(request)
        sector = request.GET.get("sector", "")
        if sector:
            puntos = puntos.filter(sector=sector)
        if request.GET.get("sin_imprimir") == "1":
            puntos = puntos.filter(qr_impreso_el__isnull=True)
        return puntos.order_by("orden", "pk")

    def get(self, request, pk):
        sectores = (
            self._activos(request)
            .exclude(sector="")
            .order_by("sector")
            .values_list("sector", flat=True)
            .distinct()
        )
        return render(
            request,
            "sitios/panel/hoja_qr.html",
            {
                "sitio": self.sitio,
                "puntos": self._puntos(request),
                "sectores": sectores,
                "sector": request.GET.get("sector", ""),
                "sin_imprimir": request.GET.get("sin_imprimir") == "1",
                "querystring": request.GET.urlencode(),
            },
        )

    def post(self, request, pk):
        hoy = timezone.localdate()
        with transaction.atomic():
            for punto in self._puntos(request):
                punto.qr_impreso_el = hoy
                punto.save(update_fields=["qr_impreso_el"])
        messages.success(request, "Se marcaron como impresos los QR de la hoja.")
        consulta = request.GET.urlencode()
        url = reverse("panel:sitios:hoja_qr", args=[self.sitio.pk])
        return redirect(f"{url}?{consulta}" if consulta else url)


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

    def get_queryset(self):
        consulta = super().get_queryset()
        return (
            consulta.filter(activo=True) if self.request.method == "POST" else consulta
        )

    def _fila(self, request, punto, form=None, estado=200):
        _marcar_vencimiento([punto])
        contexto = {
            "punto": punto,
            "form": form,
            "servicios": TipoServicio.objects.de_empresa(request.empresa)
            .filter(activo=True)
            .order_by("nombre"),
        }
        return render(request, self.template_name, contexto, status=estado)

    def get(self, request, pk):
        return self._fila(request, self.get_object())

    def post(self, request, pk):
        punto = self.get_object()
        form = ProgramacionForm(
            request.POST,
            empresa=request.empresa,
            servicio_actual_id=punto.servicio_id,
        )
        if not form.is_valid():
            return self._fila(request, punto, form, estado=422)
        datos = form.cleaned_data
        try:
            services.actualizar_programacion(
                punto,
                datos["servicio"],
                datos["frecuencia_dias"],
                datos["proximo_vencimiento"],
                request.user,
            )
        except ValidationError as error:
            form.add_error("servicio", error)
            return self._fila(request, punto, form, estado=422)
        return self._fila(request, punto)


class PuntoPosicion(_AccionPunto):
    """Guarda la posición (x, y en fracción 0 a 1) del marcador en el plano.

    Con ``plano`` en el POST ubica en él un punto que no lo tenía.
    """

    def post(self, request, pk):
        punto = self.get_object()
        form = PosicionForm(request.POST, empresa=request.empresa)
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
        return get_object_or_404(
            Sitio.objects.de_empresa(self.request.empresa), pk=self.kwargs["pk"]
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "sitio": self.sitio}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo="Subir plano", sitio=self.sitio)
        return contexto

    def get_success_url(self):
        return _url_ficha(self.sitio.pk, "planos", self.object.pk)


class PlanoImagen(AdministradorRequeridoMixin, View):
    """Imagen del plano para el editor: autenticada, nunca desde MEDIA público."""

    def get(self, request, pk):
        plano = get_object_or_404(Plano.objects.de_empresa(request.empresa), pk=pk)
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
            candidatos = geocodificacion.buscar(
                request.POST.get("q", ""), request.empresa.pk
            )
        except geocodificacion.TextoInvalido:
            return JsonResponse(
                {"error": "Escriba una dirección de hasta 200 caracteres."}, status=400
            )
        except geocodificacion.GeocodificacionError:
            return JsonResponse(
                {"error": geocodificacion.MENSAJE_CARGA_MANUAL}, status=503
            )
        return JsonResponse({"resultados": candidatos})
