"""Registra una revisión de demostración en un punto, para probar el modo campo."""

import uuid
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image

from apps.accounts.models import User
from apps.panel.demo import exigir_entorno_demo
from apps.sitios.models import PuntoControl
from apps.visitas import services

# ~1 km hacia el norte (un grado de latitud son ~111 km).
DESPLAZAMIENTO_LEJOS = Decimal("0.009")


def _foto():
    salida = BytesIO()
    Image.new("RGB", (320, 240), "#7a9e7e").save(salida, format="JPEG")
    return SimpleUploadedFile("demo.jpg", salida.getvalue(), "image/jpeg")


class Command(BaseCommand):
    help = (
        "Registra una revisión de demostración con foto en el punto indicado, dentro "
        "de la visita del empleado en el sitio del punto. Con --lejos usa "
        "coordenadas a ~1 km del punto. Solo corre con DEBUG, "
        "DJANGO_ENV=development y SQLite."
    )

    def add_arguments(self, parser):
        parser.add_argument("punto", help="Nombre del punto de control.")
        parser.add_argument(
            "--empleado", help="Usuario del empleado (por defecto el primero activo)."
        )
        parser.add_argument(
            "--lejos", action="store_true", help="Coordenadas a ~1 km del punto."
        )

    def handle(self, *args, **opciones):
        exigir_entorno_demo("registrar_revision_demo")
        punto = self._punto(opciones["punto"])
        empleado = self._empleado(opciones["empleado"])
        latitud = punto.latitud if punto.latitud is not None else punto.sitio.latitud
        longitud = (
            punto.longitud if punto.longitud is not None else punto.sitio.longitud
        )
        if latitud is None or longitud is None:
            raise CommandError("El punto y su sitio no tienen coordenadas.")
        if opciones["lejos"]:
            latitud += DESPLAZAMIENTO_LEJOS
        visita, _ = services.abrir_visita(empleado=empleado, qr_codigo=punto.qr_codigo)
        revision = services.registrar_revision(
            visita=visita,
            empleado=empleado,
            qr_codigo=punto.qr_codigo,
            cliente_uuid=uuid.uuid4(),
            realizada_en=timezone.now(),
            latitud=latitud,
            longitud=longitud,
            precision_m=Decimal("8.0"),
            datos={},
            productos_aplicados=[],
            fotos=[_foto()],
            observaciones="Revisión de demostración.",
        )
        self.stdout.write(
            f"Revisión {revision.pk} registrada en {punto.nombre} "
            f"(visita {visita.pk}, distancia {revision.distancia_m} m)."
        )

    def _punto(self, nombre):
        puntos = list(PuntoControl.objects.filter(nombre=nombre, activo=True))
        if len(puntos) != 1:
            raise CommandError(
                f"Hay {len(puntos)} puntos activos llamados {nombre!r}: se esperaba 1."
            )
        return puntos[0]

    def _empleado(self, username):
        empleados = User.objects.filter(rol=User.Rol.EMPLEADO, is_active=True)
        empleado = (
            empleados.filter(username=username).first()
            if username
            else empleados.order_by("pk").first()
        )
        if empleado is None:
            raise CommandError("No hay un empleado activo que coincida.")
        return empleado
