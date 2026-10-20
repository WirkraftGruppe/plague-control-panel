"""Estado de los puntos de un sitio: parcial HTML que sondea el panel.

Es el único punto de transporte del estado; si más adelante se pasa a SSE,
solo cambia esta vista.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.mixins import AdministradorRequeridoMixin
from apps.sitios.estado import estados_por_vencimiento
from apps.sitios.models import PuntoControl, Sitio


class EstadoSitioView(AdministradorRequeridoMixin, TemplateView):
    """`<ul id="estado-puntos">` con un `<li>` por punto activo del sitio."""

    template_name = "panel/estado_puntos.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        sitio = get_object_or_404(Sitio, pk=self.kwargs["pk"])
        puntos = list(PuntoControl.objects.filter(sitio=sitio, activo=True))
        estados = estados_por_vencimiento(puntos, timezone.localdate())
        contexto["puntos"] = [(p, estados[p.pk]) for p in puntos]
        return contexto
