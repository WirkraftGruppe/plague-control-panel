from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect, resolve_url


class AdministradorRequeridoMixin(UserPassesTestMixin):
    """Solo administradores activos de una empresa activa.

    Anónimo al login, otros roles 403. Un `plataforma` autenticado va a `/admin/`.
    Un administrador cuya empresa falta o está inactiva pierde la sesión.
    """

    def dispatch(self, request, *args, **kwargs):
        usuario = request.user
        if usuario.is_authenticated and usuario.is_active:
            if usuario.es_plataforma:
                return redirect("admin:index")
            if usuario.es_administrador and not self._empresa_activa():
                logout(request)
                return redirect(resolve_url(settings.LOGIN_URL))
        return super().dispatch(request, *args, **kwargs)

    def _empresa_activa(self):
        empresa = getattr(self.request, "empresa", None)
        return empresa is not None and empresa.activo

    def test_func(self):
        usuario = self.request.user
        return bool(
            usuario.is_authenticated and usuario.is_active and usuario.es_administrador
        )
