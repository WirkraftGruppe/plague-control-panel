"""Vistas del panel de Visitas: listado, ficha, fotos, nuevo turno y carga manual."""

import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import (
    BooleanField,
    Count,
    Exists,
    ExpressionWrapper,
    OuterRef,
    Q,
)
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import DetailView, FormView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.accounts.models import User
from apps.panel.listados import ListadoPanelMixin
from apps.sitios.estado import EstadoVencimiento
from apps.sitios.models import Sitio

from .models import Foto, Revision, Visita
from .panel_forms import FormSetProductos, FormularioManual, FormularioTurno
from .planillas import filas_planilla
from .services import crear_turno, marcar_incidencia_revisada, registrar_visita_manual

logger = logging.getLogger(__name__)

FILTROS = ("empleado", "sitio", "estado", "incidencia")
INCIDENCIAS = (
    ("sin_revisar", "Sin revisar"),
    ("todas", "Todas las incidencias"),
    ("ubicacion", "Ubicación sin revisar"),
    ("ubicacion_revisadas", "Ubicación revisadas"),
)
MAXIMO_ID = 2**63 - 1  # máximo de BigAutoField
MAXIMO_DIGITOS_ID = len(str(MAXIMO_ID))
HISTORIAL_MAXIMO = 50
TIPOS_IMAGEN = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
CAMPOS_OCULTOS = {"datos"}
TIPOS_CAMBIO = {"+": "Creación", "~": "Modificación", "-": "Eliminación"}
DIAS_SEMANA = 7  # "Esta semana" llega hasta hoy + 7, como el umbral de "próximo"
GRUPOS = (
    ("hoy", "Hoy"),
    ("manana", "Mañana"),
    ("semana", "Esta semana"),
    ("despues", "Más adelante"),
)


def _es_id_valido(valor):
    """Un valor del filtro numérico: dígitos ASCII y dentro del rango de un id."""
    return (
        bool(valor)
        and valor.isascii()
        and valor.isdigit()
        and len(valor) <= MAXIMO_DIGITOS_ID
        and int(valor) <= MAXIMO_ID
    )


class ListadoVisitas(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = Visita
    template_name = "visitas/panel/listado.html"
    template_parcial = "visitas/panel/_listado.html"
    context_object_name = "visitas"
    orden_permitido = ("creado", "programada_para", "cerrada_en", "estado")
    campos_busqueda = ("sitio__nombre",)
    # Solo se pagina "Realizados": lo hace `get_context_data`.
    paginate_by = None

    def get_filtros(self):
        valores = {f: self.request.GET.get(f, "").strip() for f in FILTROS}
        return {f: v for f, v in valores.items() if v}

    def get_queryset(self):
        # Subconsulta: un join con las revisiones multiplicaría las visitas.
        en_revision = Revision.objects.filter(
            visita=OuterRef("pk"), incidencia_ubicacion=True
        )
        queryset = (
            super()
            .get_queryset()
            .select_related("sitio", "empleado")
            .annotate(
                n_puntos=Count("items", distinct=True),
                con_ubicacion=ExpressionWrapper(
                    Q(incidencia_ubicacion=True) | Exists(en_revision),
                    output_field=BooleanField(),
                ),
            )
        )
        filtros = self.get_filtros()
        for parametro, campo in (
            ("empleado", "empleado_id"),
            ("sitio", "sitio_id"),
        ):
            valor = filtros.get(parametro)
            if _es_id_valido(valor):
                queryset = queryset.filter(**{campo: int(valor)})
        if filtros.get("estado") in Visita.Estado.values:
            queryset = queryset.filter(estado=filtros["estado"])
        if filtros.get("incidencia") in ("sin_revisar", "todas"):
            queryset = queryset.filter(incidencia=True)
            if filtros["incidencia"] == "sin_revisar":
                queryset = queryset.filter(incidencia_revisada_en__isnull=True)
        elif filtros.get("incidencia") in ("ubicacion", "ubicacion_revisadas"):
            # Igual que el tablero: solo visitas realizadas que cuentan como servicio.
            queryset = queryset.filter(
                con_ubicacion=True,
                cuenta_como_servicio=True,
                estado=Visita.Estado.REALIZADA,
                incidencia_revisada_en__isnull=filtros["incidencia"] == "ubicacion",
            )
        return queryset

    def agrupar(self, queryset, hoy):
        """Reparte turnos pendientes y abiertos por `programada_para`.

        Hoy lleva las abiertas y las pendientes de hoy o atrasadas (estas primero,
        marcadas con `atrasado`); las pendientes sin fecha van a "Más adelante".
        """
        grupos = {clave: [] for clave, _ in GRUPOS}
        atrasadas = []
        abiertos = queryset.filter(
            estado__in=(Visita.Estado.PENDIENTE, Visita.Estado.ABIERTA)
        ).order_by("programada_para", "pk")
        for visita in abiertos:
            fecha = visita.programada_para
            visita.atrasado = (
                visita.estado == Visita.Estado.PENDIENTE
                and fecha is not None
                and fecha < hoy
            )
            if visita.atrasado:
                atrasadas.append(visita)
            elif visita.estado == Visita.Estado.ABIERTA or fecha == hoy:
                grupos["hoy"].append(visita)
            elif fecha is None:
                grupos["despues"].append(visita)
            elif fecha == hoy + timedelta(days=1):
                grupos["manana"].append(visita)
            elif fecha <= hoy + timedelta(days=DIAS_SEMANA):
                grupos["semana"].append(visita)
            else:
                grupos["despues"].append(visita)
        grupos["hoy"] = atrasadas + grupos["hoy"]
        # Los pendientes sin fecha cierran la lista (el orden de NULL varía por base).
        grupos["despues"].sort(
            key=lambda v: (v.programada_para is None, v.programada_para or hoy, v.pk)
        )
        return grupos

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtros = self.get_filtros()
        parametros = {"q": contexto["q"], "orden": contexto["orden"], **filtros}
        contexto["querystring"] = urlencode({k: v for k, v in parametros.items() if v})
        contexto["filtros"] = filtros
        contexto["empleados"] = User.objects.filter(
            rol=User.Rol.EMPLEADO, is_active=True
        ).order_by("username")
        contexto["sitios"] = Sitio.objects.order_by("nombre")
        contexto["estados"] = Visita.Estado.choices
        contexto["incidencias"] = INCIDENCIAS

        # Las incidencias sin revisar van arriba y no se repiten en los grupos.
        queryset = self.object_list
        sin_revisar = queryset.filter(
            incidencia=True, incidencia_revisada_en__isnull=True
        )
        resto = queryset.exclude(incidencia=True, incidencia_revisada_en__isnull=True)
        grupos = self.agrupar(resto, timezone.localdate())
        realizados = resto.filter(
            estado__in=(Visita.Estado.REALIZADA, Visita.Estado.CANCELADA)
        ).order_by(Coalesce("cerrada_en", "creado").desc(), "-pk")
        pagina = Paginator(realizados, 25).get_page(self.request.GET.get("page"))
        contexto["page_obj"] = pagina
        contexto["incidencias_sin_revisar"] = list(sin_revisar.order_by("-creado"))
        contexto["grupos"] = [
            (clave, titulo, grupos[clave]) for clave, titulo in GRUPOS if grupos[clave]
        ]
        contexto["realizados"] = list(pagina)
        contexto["visitas"] = (
            contexto["incidencias_sin_revisar"]
            + [v for _, _, lista in contexto["grupos"] for v in lista]
            + contexto["realizados"]
        )
        return contexto


def _historial(visita):
    """Últimos cambios de la visita: quién, cuándo, tipo y campos modificados.

    Una sola consulta: se trae uno más del máximo para comparar el último mostrado.
    """
    registros = list(
        visita.history.select_related("history_user")[: HISTORIAL_MAXIMO + 1]
    )
    filas = []
    for registro, anterior in zip(registros[:HISTORIAL_MAXIMO], registros[1:] + [None]):
        campos = []
        if anterior:
            for cambio in registro.diff_against(anterior).changes:
                if cambio.field not in CAMPOS_OCULTOS:
                    campos.append(Visita._meta.get_field(cambio.field).verbose_name)
        filas.append(
            {
                "usuario": registro.history_user,
                "fecha": registro.history_date,
                "tipo": TIPOS_CAMBIO.get(registro.history_type, registro.history_type),
                "campos": campos,
            }
        )
    return filas


class FichaVisita(AdministradorRequeridoMixin, DetailView):
    template_name = "visitas/panel/ficha.html"
    context_object_name = "visita"
    queryset = Visita.objects.select_related(
        "sitio", "empleado", "asignada_por", "incidencia_revisada_por"
    ).prefetch_related(
        "revisiones__punto",
        "revisiones__servicio",
        "revisiones__fotos",
        "revisiones__productos__producto",
        "items__punto",
        "items__servicio",
    )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        visita = contexto["visita"]
        contexto["planillas"] = [
            (slug, filas_planilla(esquema, visita.datos.get(slug)))
            for slug, esquema in visita.esquema_planilla.items()
            if esquema
        ]
        contexto["revisiones"] = list(visita.revisiones.all())
        revisados = {r.punto_id for r in contexto["revisiones"]}
        contexto["items"] = list(visita.items.all())
        for item in contexto["items"]:
            item.revisado = item.punto_id in revisados
        contexto["con_ubicacion"] = visita.incidencia_ubicacion or any(
            r.incidencia_ubicacion for r in contexto["revisiones"]
        )
        for revision in contexto["revisiones"]:
            revision.filas = filas_planilla(revision.esquema_planilla, revision.datos)
        contexto["historial"] = _historial(visita)
        return contexto


class RevisarIncidencia(AdministradorRequeridoMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        visita = get_object_or_404(Visita, pk=pk)
        try:
            marcar_incidencia_revisada(visita, request.user)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Incidencia marcada como revisada.")
        return redirect("panel:visitas:ficha", pk=visita.pk)


class FotoVisita(AdministradorRequeridoMixin, View):
    http_method_names = ["get"]

    def get(self, request, codigo):
        foto = get_object_or_404(Foto, codigo=codigo)
        nombre = foto.imagen.name
        extension = "." + nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
        try:
            archivo = foto.imagen.storage.open(nombre, "rb")
        except (FileNotFoundError, ValueError, OSError):
            logger.warning("Falta el archivo de la foto %s.", foto.pk)
            raise Http404("La foto no está disponible.") from None
        respuesta = FileResponse(
            archivo, content_type=TIPOS_IMAGEN.get(extension, "image/jpeg")
        )
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta


class _SitioMixin:
    """Carga el sitio de la URL (con su cliente) y se lo pasa al formulario."""

    @cached_property
    def sitio(self):
        return get_object_or_404(
            Sitio.objects.select_related("cliente"), pk=self.kwargs["sitio_pk"]
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "sitio": self.sitio}

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["sitio"] = self.sitio
        return contexto


def _numero(valor):
    """Decimal de la base a número de JSON; vacío queda en ``None``."""
    return None if valor is None else float(valor)


class NuevoTurnoView(AdministradorRequeridoMixin, _SitioMixin, FormView):
    form_class = FormularioTurno
    template_name = "visitas/panel/nuevo_turno.html"
    template_parcial = "visitas/panel/_nuevo_turno_lateral.html"

    @property
    def es_htmx(self):
        return bool(self.request.headers.get("HX-Request"))

    def get_template_names(self):
        return [self.template_parcial if self.es_htmx else self.template_name]

    def datos_planos(self, form):
        """Planos activos del sitio con sus puntos ubicados, para dibujarlos."""
        estados = {f["punto"].pk: f["estado"] for f in form.filas()}
        planos = []
        for plano in self.sitio.planos.filter(activo=True):
            puntos = [
                {
                    "id": p.pk,
                    "nombre": p.nombre,
                    "x": _numero(p.x),
                    "y": _numero(p.y),
                    "estado": estados[p.pk],
                    "estado_texto": EstadoVencimiento(estados[p.pk]).label,
                }
                for p in form.puntos_activos
                if p.plano_id == plano.pk and p.x is not None and p.y is not None
            ]
            planos.append(
                {
                    "id": plano.pk,
                    "nombre": plano.nombre,
                    "imagen": reverse("panel:sitios:plano_imagen", args=[plano.pk]),
                    "ancho": plano.ancho_px,
                    "alto": plano.alto_px,
                    "puntos": puntos,
                }
            )
        return planos

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["planos"] = self.datos_planos(contexto["form"])
        contexto["lateral"] = self.es_htmx
        return contexto

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            crear_turno(
                sitio=self.sitio,
                empleado=datos["empleado"],
                programada_para=datos["programada_para"],
                items=form.items(),
                asignada_por=self.request.user,
            )
        except ValidationError as error:
            for mensaje in error.messages:
                form.add_error(None, mensaje)
            return self.form_invalid(form)
        messages.success(self.request, "Turno creado.")
        if self.es_htmx:
            # HTMX no sigue redirecciones de página: se le pide la navegación.
            respuesta = HttpResponse(status=200)
            respuesta["HX-Redirect"] = self.get_success_url()
            return respuesta
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("panel:sitios:ficha", args=[self.sitio.pk])


class CargarVisitaView(AdministradorRequeridoMixin, _SitioMixin, FormView):
    form_class = FormularioManual
    template_name = "visitas/panel/cargar.html"

    def get_productos(self):
        if self.request.method == "POST":
            return FormSetProductos(self.request.POST, prefix="productos")
        return FormSetProductos(prefix="productos")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault("productos", self.get_productos())
        return contexto

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        productos = self.get_productos()
        if form.is_valid() and productos.is_valid():
            return self.form_valid(form, productos)
        return self.render_to_response(
            self.get_context_data(form=form, productos=productos)
        )

    def form_valid(self, form, productos):
        datos = form.cleaned_data
        try:
            visita = registrar_visita_manual(
                sitio=self.sitio,
                empleado=datos["empleado"],
                administrador=self.request.user,
                motivo=datos["motivo"],
                realizada_en=datos["realizada_en"],
                items=form.items(),
                datos=form.datos_planilla(),
                datos_visita=form.datos_planilla_visita(),
                productos_aplicados=[
                    {**p.cleaned_data, "producto": p.cleaned_data["producto"].pk}
                    for p in productos
                    if p.cleaned_data
                ],
                fotos=datos["fotos"],
                pendiente=datos["pendiente"],
                confirmar_atraso=datos["confirmar_atraso"],
                observaciones=datos["observaciones"],
                incidencia=datos["incidencia"],
                incidencia_detalle=datos["incidencia_detalle"],
            )
        except ValidationError as error:
            mensajes = (
                error.message_dict
                if hasattr(error, "error_dict")
                else {None: error.messages}
            )
            # `productos_aplicados.<i>.<campo>` va al formulario de ese producto.
            filas = [p for p in productos if p.cleaned_data]
            for campo, lista in mensajes.items():
                destino, formulario = campo if campo in form.fields else None, form
                _, _, resto = (campo or "").partition("productos_aplicados.")
                posicion, _, campo_fila = resto.partition(".")
                if resto and posicion.isdigit() and int(posicion) < len(filas):
                    formulario = filas[int(posicion)]
                    destino = campo_fila if campo_fila in formulario.fields else None
                for mensaje in lista:
                    formulario.add_error(destino, mensaje)
            return self.render_to_response(
                self.get_context_data(form=form, productos=productos)
            )
        messages.success(self.request, "Visita registrada.")
        return redirect("panel:visitas:ficha", pk=visita.pk)
