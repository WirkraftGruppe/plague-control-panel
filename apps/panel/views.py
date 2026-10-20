"""Vistas transversales del panel: inicio, mapa, ingreso y salida."""

from csp.decorators import csp_update
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import RedirectView, TemplateView

from apps.accounts.limites import LimiteIngresoMixin
from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.servicios.models import TipoServicio
from apps.sitios.estado import EstadoVencimiento

from .forms import FormularioIngreso
from .mapa import ORIGEN_TESELAS, sitios_para_mapa

ID_MAXIMO = 2**63 - 1  # máximo de BigAutoField
LARGO_MAXIMO = len(str(ID_MAXIMO))


class InicioView(AdministradorRequeridoMixin, RedirectView):
    """El inicio del panel es el listado de sitios."""

    pattern_name = "panel:sitios:listado"


@method_decorator(csp_update({"img-src": ORIGEN_TESELAS}), name="dispatch")
class MapaView(AdministradorRequeridoMixin, TemplateView):
    """Página del mapa; los sitios se piden a `MapaDatosView`."""

    template_name = "panel/mapa.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["servicios"] = TipoServicio.objects.order_by("nombre")
        contexto["estados"] = EstadoVencimiento.choices
        return contexto


class MapaDatosView(AdministradorRequeridoMixin, View):
    """JSON con los sitios activos; filtros `cliente`, `servicio` y `estado`."""

    def get(self, request):
        estado = request.GET.get("estado")
        if estado not in EstadoVencimiento.values:
            estado = None
        sitios = sitios_para_mapa(
            cliente=_entero(request.GET.get("cliente")),
            servicio=_entero(request.GET.get("servicio")),
            estado=estado,
        )
        return JsonResponse({"sitios": sitios})


def _entero(valor):
    """Devuelve el entero o None si el parámetro falta o no es un id válido.

    El largo se mira antes de `int()` para no convertir cadenas enormes; el máximo
    es el de `BigAutoField`.
    """
    if not (
        valor and valor.isascii() and valor.isdigit() and len(valor) <= LARGO_MAXIMO
    ):
        return None
    numero = int(valor)
    return numero if numero <= ID_MAXIMO else None


class IngresarView(LimiteIngresoMixin, LoginView):
    template_name = "panel/ingresar.html"
    authentication_form = FormularioIngreso
    redirect_authenticated_user = False


class SalirView(LogoutView):
    """Cierra la sesión; solo acepta POST."""
