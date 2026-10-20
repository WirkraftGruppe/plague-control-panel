"""Vistas del panel de Visitas: listado, ficha, fotos, asignación y carga manual."""

import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.views import View
from django.views.generic import DetailView, FormView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.accounts.models import User
from apps.panel.listados import ListadoPanelMixin
from apps.proyectos.models import Proyecto

from .models import Foto, Revision, Visita
from .panel_forms import FormSetProductos, FormularioAsignar, FormularioManual
from .planillas import filas_planilla
from .services import marcar_incidencia_revisada, registrar_visita_manual

logger = logging.getLogger(__name__)

FILTROS = ("empleado", "proyecto", "estado", "incidencia")
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
    campos_busqueda = ("proyecto__titulo", "proyecto__sitio__nombre")

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
            .select_related("proyecto__sitio", "empleado")
            .annotate(
                con_ubicacion=ExpressionWrapper(
                    Q(incidencia_ubicacion=True) | Exists(en_revision),
                    output_field=BooleanField(),
                )
            )
        )
        filtros = self.get_filtros()
        for parametro, campo in (
            ("empleado", "empleado_id"),
            ("proyecto", "proyecto_id"),
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

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtros = self.get_filtros()
        parametros = {"q": contexto["q"], "orden": contexto["orden"], **filtros}
        contexto["querystring"] = urlencode({k: v for k, v in parametros.items() if v})
        contexto["filtros"] = filtros
        contexto["empleados"] = User.objects.filter(
            rol=User.Rol.EMPLEADO, is_active=True
        ).order_by("username")
        contexto["proyectos"] = Proyecto.objects.order_by("titulo")
        contexto["estados"] = Visita.Estado.choices
        contexto["incidencias"] = INCIDENCIAS
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
        "proyecto__sitio", "empleado", "asignada_por", "incidencia_revisada_por"
    ).prefetch_related(
        "revisiones__punto", "revisiones__fotos", "revisiones__productos__producto"
    )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        visita = contexto["visita"]
        contexto["filas"] = filas_planilla(visita.esquema_planilla, visita.datos)
        contexto["revisiones"] = list(visita.revisiones.all())
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


class AsignarVisita(AdministradorRequeridoMixin, FormView):
    form_class = FormularioAsignar
    template_name = "visitas/panel/asignar.html"

    @cached_property
    def proyecto(self):
        return get_object_or_404(
            Proyecto.objects.select_related("sitio__cliente"),
            pk=self.kwargs["proyecto_pk"],
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["proyecto"] = self.proyecto
        return contexto

    def form_valid(self, form):
        if self.proyecto.estado != Proyecto.Estado.ACTIVO:
            form.add_error(None, "Solo se asignan visitas a proyectos activos.")
            return self.form_invalid(form)
        if not (self.proyecto.sitio.activo and self.proyecto.sitio.cliente.activo):
            form.add_error(None, "El sitio o el cliente del proyecto están de baja.")
            return self.form_invalid(form)
        Visita.objects.create(
            proyecto=self.proyecto,
            empleado=form.cleaned_data["empleado"],
            origen=Visita.Origen.APP,
            estado=Visita.Estado.PENDIENTE,
            programada_para=form.cleaned_data["programada_para"],
            asignada_por=self.request.user,
        )
        messages.success(self.request, "Visita asignada.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("panel:proyectos:ficha", args=[self.proyecto.pk])


class RegistrarVisitaManual(AdministradorRequeridoMixin, FormView):
    form_class = FormularioManual
    template_name = "visitas/panel/manual.html"

    @cached_property
    def proyecto(self):
        return get_object_or_404(
            Proyecto.objects.select_related(
                "sitio__cliente", "tipo_servicio"
            ).prefetch_related("tipo_servicio__campos"),
            pk=self.kwargs["proyecto_pk"],
        )

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "proyecto": self.proyecto}

    def get_productos(self):
        if self.request.method == "POST":
            return FormSetProductos(self.request.POST, prefix="productos")
        return FormSetProductos(prefix="productos")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["proyecto"] = self.proyecto
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
                proyecto=self.proyecto,
                empleado=datos["empleado"],
                administrador=self.request.user,
                motivo=datos["motivo"],
                realizada_en=datos["realizada_en"],
                puntos=datos["puntos"],
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
