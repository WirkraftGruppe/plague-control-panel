from django.urls import path

from . import api_views

app_name = "empresas"

urlpatterns = [
    path("me/empresa/", api_views.MiEmpresaView.as_view(), name="me"),
    path("empresas/<int:pk>/logo/", api_views.LogoView.as_view(), name="logo"),
]
