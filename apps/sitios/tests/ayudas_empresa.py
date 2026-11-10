"""Dos empresas con sus datos de sitios, para los tests de aislamiento."""

import datetime
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.servicios.models import TipoServicio
from apps.sitios.models import Plano, Sitio
from apps.visitas.models import Visita


def plano_de(sitio, nombre):
    """Plano con un PNG real de 40x20 px."""
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buffer, "PNG")
    archivo = SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")
    return Plano.objects.create(sitio=sitio, nombre=nombre, imagen=archivo)


class DatosDeDosEmpresas:
    """Crea, por empresa, un administrador, un empleado, un cliente, un sitio con
    su punto, un plano, un servicio y un turno pendiente de hoy.

    Los atributos terminan en `_a` y `_b`.
    """

    def crear_empresas(self):
        for sufijo, nombre in (("a", "Empresa A"), ("b", "Empresa B")):
            empresa = Empresa.objects.create(nombre=nombre)
            empleado = User.objects.create_user(
                f"emp-{sufijo}",
                password="clave-segura-123",
                rol=User.Rol.EMPLEADO,
                empresa=empresa,
            )
            cliente = Cliente.objects.create(
                razon_social=f"Cliente {nombre}", empresa=empresa
            )
            sitio = Sitio.objects.create(cliente=cliente, nombre=f"Sitio {nombre}")
            datos = {
                "empresa": empresa,
                "admin": User.objects.create_user(
                    f"adm-{sufijo}",
                    password="clave-segura-123",
                    rol=User.Rol.ADMINISTRADOR,
                    empresa=empresa,
                ),
                "empleado": empleado,
                "cliente": cliente,
                "sitio": sitio,
                "punto": sitio.puntos.get(),
                "plano": plano_de(sitio, f"Plano {nombre}"),
                "servicio": TipoServicio.objects.create(
                    nombre=f"Servicio {nombre}", empresa=empresa
                ),
                "visita": Visita.objects.create(
                    sitio=sitio,
                    empleado=empleado,
                    origen=Visita.Origen.MANUAL,
                    programada_para=datetime.date.today(),
                ),
            }
            for clave, valor in datos.items():
                setattr(self, f"{clave}_{sufijo}", valor)
