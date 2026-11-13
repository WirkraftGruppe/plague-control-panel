"""Ayudas de los tests de visitas con dos empresas."""

from io import BytesIO
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.productos.models import Producto
from apps.servicios.models import TipoServicio
from apps.sitios.models import Sitio
from apps.visitas.models import Foto, Revision, Visita


def _lado(nombre):
    """Una empresa con administrador, empleado, servicio, producto, sitio y visita."""
    empresa = Empresa.objects.create(nombre=f"Empresa {nombre}")
    minuscula = nombre.lower()
    admin = User.objects.create_user(
        f"adm-{minuscula}",
        password="clave-segura-123",
        rol=User.Rol.ADMINISTRADOR,
        empresa=empresa,
    )
    empleado = User.objects.create_user(
        f"emp-{minuscula}",
        password="clave-segura-123",
        rol=User.Rol.EMPLEADO,
        empresa=empresa,
    )
    servicio = TipoServicio.objects.create(
        nombre=f"Servicio {nombre}", slug="roedores", empresa=empresa
    )
    producto = Producto.objects.create(
        nombre_comercial=f"Producto {nombre}", empresa=empresa
    )
    cliente = Cliente.objects.create(razon_social=f"Cliente {nombre}", empresa=empresa)
    sitio = Sitio.objects.create(cliente=cliente, nombre=f"Sitio {nombre}")
    punto = sitio.puntos.get(orden=0)
    punto.servicio = servicio
    punto.save()
    visita = Visita.objects.create(
        sitio=sitio,
        empleado=empleado,
        origen=Visita.Origen.MANUAL,
        motivo_manual="Carga",
        incidencia=True,
    )
    return SimpleNamespace(
        empresa=empresa,
        admin=admin,
        empleado=empleado,
        servicio=servicio,
        producto=producto,
        sitio=sitio,
        punto=punto,
        visita=visita,
    )


def dos_empresas():
    """`(a, b)`: los datos de dos empresas completas."""
    return _lado("A"), _lado("B")


def jpeg_chico():
    """Un JPEG válido de 20 x 20 para subir como foto."""
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "red").save(buffer, "JPEG")
    return SimpleUploadedFile("f.jpg", buffer.getvalue(), content_type="image/jpeg")


def crear_foto(lado):
    """Revisión con una foto en la visita del lado (usar con `MEDIA_ROOT` temporal)."""
    ahora = timezone.now()
    revision = Revision.objects.create(
        visita=lado.visita,
        punto=lado.punto,
        servicio=lado.servicio,
        orden=1,
        realizada_en=ahora,
        recibida_en=ahora,
    )
    return Foto.objects.create(revision=revision, imagen=jpeg_chico())
