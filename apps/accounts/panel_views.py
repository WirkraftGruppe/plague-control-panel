"""Vistas del panel de usuarios (solo administradores)."""

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import CreateView, FormView, TemplateView, UpdateView, View

from apps.panel.listados import ListadoPanelMixin

from .mixins import AdministradorRequeridoMixin
from .panel_forms import UsuarioAltaForm, UsuarioEdicionForm

User = get_user_model()
URL_LISTADO = reverse_lazy("panel:usuarios:listado")


def usuarios_de_empresa(request):
    """Cuentas de la empresa del pedido; sin empresa no hay ninguna."""
    empresa = getattr(request, "empresa", None)
    if empresa is None:
        return User.objects.none()
    return User.objects.filter(empresa=empresa)


class EmpresaEnFormularioMixin:
    """Pasa la empresa del pedido al formulario para fijarla antes de validar."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.empresa
        return kwargs


def usuarios_gestionables(request):
    """Cuentas que el solicitante puede editar: solo un superusuario ve a los demás."""
    usuarios = usuarios_de_empresa(request)
    if request.user.is_superuser:
        return usuarios
    return usuarios.filter(is_superuser=False)


class UsuarioListadoView(AdministradorRequeridoMixin, ListadoPanelMixin):
    model = User
    template_name = "accounts/panel/listado.html"
    template_parcial = "accounts/panel/listado_parcial.html"
    campos_busqueda = ("username", "first_name", "last_name", "email")
    orden_permitido = ("username", "last_name", "rol", "is_active")
    ordering = ("username",)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.queryset = usuarios_de_empresa(request)

    def get_queryset(self):
        queryset = super().get_queryset()
        rol = self.request.GET.get("rol", "")
        if rol in User.Rol.values:
            queryset = queryset.filter(rol=rol)
        activo = self.request.GET.get("activo", "")
        if activo in ("1", "0"):
            queryset = queryset.filter(is_active=activo == "1")
        return queryset

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["roles"] = User.Rol.choices
        contexto["rol"] = self.request.GET.get("rol", "")
        contexto["activo"] = self.request.GET.get("activo", "")
        propio_superusuario = self.request.user.is_superuser
        for usuario in contexto["object_list"]:
            usuario.gestionable = propio_superusuario or not usuario.is_superuser
        return contexto


class UsuarioAltaView(
    AdministradorRequeridoMixin, EmpresaEnFormularioMixin, CreateView
):
    model = User
    form_class = UsuarioAltaForm
    template_name = "accounts/panel/formulario.html"
    success_url = URL_LISTADO
    extra_context = {"titulo": "Nuevo usuario", "enviar": "Crear usuario"}

    def form_valid(self, form):
        messages.success(self.request, "Usuario creado.")
        return super().form_valid(form)


class UsuarioEditarView(
    AdministradorRequeridoMixin, EmpresaEnFormularioMixin, UpdateView
):
    form_class = UsuarioEdicionForm
    template_name = "accounts/panel/formulario.html"
    success_url = URL_LISTADO
    extra_context = {"titulo": "Editar usuario"}

    def get_queryset(self):
        return usuarios_gestionables(self.request)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.object == self.request.user:
            # Evita que el administrador se quite su propio rol.
            form.fields["rol"].disabled = True
        return form

    def form_valid(self, form):
        messages.success(self.request, "Usuario actualizado.")
        return super().form_valid(form)


class UsuarioDesactivarView(AdministradorRequeridoMixin, TemplateView):
    """GET muestra la confirmación; POST desactiva (no borra)."""

    template_name = "accounts/panel/desactivar.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["usuario"] = get_object_or_404(
            usuarios_gestionables(self.request), pk=self.kwargs["pk"]
        )
        return contexto

    def post(self, request, *args, **kwargs):
        usuario = get_object_or_404(usuarios_gestionables(request), pk=kwargs["pk"])
        if usuario.pk == request.user.pk:
            messages.error(request, "No es posible desactivar la propia cuenta.")
        else:
            usuario.is_active = False
            usuario.save(update_fields=["is_active"])
            messages.success(request, "Usuario desactivado.")
        return redirect(URL_LISTADO)


class UsuarioReactivarView(AdministradorRequeridoMixin, View):
    """Solo POST: vuelve a activar una cuenta desactivada."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        usuario = get_object_or_404(usuarios_gestionables(request), pk=kwargs["pk"])
        usuario.is_active = True
        usuario.save(update_fields=["is_active"])
        messages.success(request, "Usuario reactivado.")
        return redirect(URL_LISTADO)


class UsuarioContrasenaView(AdministradorRequeridoMixin, FormView):
    form_class = SetPasswordForm
    template_name = "accounts/panel/formulario.html"
    success_url = URL_LISTADO

    @cached_property
    def usuario(self):
        return get_object_or_404(
            usuarios_gestionables(self.request), pk=self.kwargs["pk"]
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.usuario
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = f"Cambiar contraseña de {self.usuario.username}"
        return contexto

    def form_valid(self, form):
        form.save()
        if self.usuario.pk == self.request.user.pk:
            update_session_auth_hash(self.request, self.usuario)
        messages.success(self.request, "Contraseña actualizada.")
        return super().form_valid(form)
