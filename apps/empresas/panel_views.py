"""Vistas del panel de la empresa: edición y logo."""

from django.contrib import messages
from django.http import FileResponse, Http404
from django.urls import reverse
from django.views import View
from django.views.generic import UpdateView

from apps.accounts.mixins import AdministradorRequeridoMixin

from .panel_forms import EmpresaForm


class EmpresaEditarView(AdministradorRequeridoMixin, UpdateView):
    """Edita la empresa del administrador (`request.empresa`)."""

    form_class = EmpresaForm
    template_name = "empresas/panel/formulario.html"

    def get_object(self, queryset=None):
        empresa = self.request.empresa
        # La validación del formulario ya modifica la instancia: se anota antes.
        self.logo_anterior = empresa.logo.name
        return empresa

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        if self.logo_anterior and self.logo_anterior != (self.object.logo.name or ""):
            try:
                self.object.logo.storage.delete(self.logo_anterior)
            except OSError:
                # El archivo huérfano no debe impedir guardar la empresa.
                pass
        return respuesta

    def get_success_url(self):
        messages.success(self.request, "Empresa actualizada.")
        return reverse("panel:empresas:editar")


class EmpresaLogoView(AdministradorRequeridoMixin, View):
    """Logo de la empresa del administrador: autenticado, nunca desde MEDIA."""

    def get(self, request):
        logo = request.empresa.logo if request.empresa else None
        if not logo:
            raise Http404
        try:
            archivo = logo.open("rb")
        except FileNotFoundError:
            raise Http404 from None
        respuesta = FileResponse(archivo, content_type="image/png")
        respuesta["Cache-Control"] = "private, no-store"
        respuesta["X-Content-Type-Options"] = "nosniff"
        return respuesta
