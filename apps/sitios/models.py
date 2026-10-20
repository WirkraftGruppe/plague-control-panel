"""Modelos de Sitios: Sitio, PuntoControl y Plano."""

import logging
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from simple_history.models import HistoricalRecords

from apps.clientes.models import Cliente
from apps.visitas import imagenes

from . import planos

logger = logging.getLogger(__name__)

MOTIVO_SITIO_DESACTIVADO = "Sitio desactivado"
MOTIVO_SITIO_REACTIVADO = "Sitio reactivado"


def _borrar_archivo_al_confirmar(almacenamiento, nombre):
    """Borra el archivo del almacenamiento cuando la transacción se confirma."""
    transaction.on_commit(lambda: almacenamiento.delete(nombre))


class Sitio(models.Model):
    """Lugar físico de un cliente donde se hacen visitas; los QR son de sus puntos."""

    class Sector(models.TextChoices):
        INDUSTRIA = "industria", "Industria"
        PUERTO = "puerto", "Puerto"
        GASTRONOMIA = "gastronomia", "Gastronomía"
        HOTELERIA = "hoteleria", "Hotelería"
        EDIFICIO = "edificio", "Edificio"
        SALUD = "salud", "Salud"
        EDUCACION = "educacion", "Educación"
        RURAL = "rural", "Rural"
        ESPACIO_VERDE = "espacio_verde", "Espacio verde"
        TRANSPORTE = "transporte", "Transporte"
        HOGAR = "hogar", "Hogar"
        OTRO = "otro", "Otro"

    cliente = models.ForeignKey(
        Cliente,
        verbose_name="cliente",
        on_delete=models.PROTECT,
        related_name="sitios",
    )
    nombre = models.CharField("nombre", max_length=200)
    direccion = models.CharField("dirección", max_length=255, blank=True)
    localidad = models.CharField("localidad", max_length=100, blank=True)
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    precision_m = models.DecimalField(
        "precisión del GPS (m)",
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sector = models.CharField(
        "sector", max_length=20, choices=Sector.choices, default=Sector.OTRO
    )
    contacto_en_sitio = models.CharField(
        "contacto en el sitio", max_length=150, blank=True
    )
    telefono_en_sitio = models.CharField(
        "teléfono en el sitio", max_length=30, blank=True
    )
    horario_acceso = models.CharField("horario de acceso", max_length=200, blank=True)
    notas = models.TextField("notas", blank=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="responsable",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="sitios_a_cargo",
        limit_choices_to={"rol": "empleado", "is_active": True},
    )
    activo = models.BooleanField("activo", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    history = HistoricalRecords(
        excluded_fields=[
            "contacto_en_sitio",
            "telefono_en_sitio",
            "notas",
            "horario_acceso",
            "precision_m",
        ]
    )

    class Meta:
        verbose_name = "sitio"
        verbose_name_plural = "sitios"
        ordering = ["cliente__razon_social", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.cliente})"

    def save(self, *args, **kwargs):
        """Al crear suma el punto General; al desactivar apaga sus puntos y al
        reactivar vuelven solo los que apagó el sitio."""
        creado = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if creado:
                PuntoControl.objects.create(sitio=self, nombre="General", orden=0)
            elif not self.activo:
                for punto in self.puntos.filter(activo=True):
                    punto.activo = False
                    punto._change_reason = MOTIVO_SITIO_DESACTIVADO
                    punto.save()
            else:
                for punto in self.puntos.filter(activo=False):
                    ultimo = (
                        punto.history.order_by("-history_date", "-history_id")
                        .values_list("history_change_reason", flat=True)
                        .first()
                    )
                    if ultimo == MOTIVO_SITIO_DESACTIVADO:
                        punto.activo = True
                        punto._change_reason = MOTIVO_SITIO_REACTIVADO
                        punto.save()


def ruta_plano(instancia, nombre):
    """Ruta de almacenamiento: UUID aleatorio, nunca el nombre original."""
    return f"sitios/planos/{uuid.uuid4().hex}.png"


class Plano(models.Model):
    """Imagen de una planta o zona del sitio donde se ubican los puntos de control."""

    sitio = models.ForeignKey(
        Sitio, verbose_name="sitio", on_delete=models.CASCADE, related_name="planos"
    )
    nombre = models.CharField("nombre", max_length=100)
    imagen = models.FileField("imagen (JPG, PNG o PDF)", upload_to=ruta_plano)
    ancho_px = models.PositiveIntegerField("ancho (px)", default=0, editable=False)
    alto_px = models.PositiveIntegerField("alto (px)", default=0, editable=False)
    orden = models.PositiveIntegerField("orden", default=0)
    activo = models.BooleanField("activo", default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "plano"
        verbose_name_plural = "planos"
        ordering = ["sitio_id", "orden", "id"]

    def __str__(self):
        return f"{self.nombre} ({self.sitio})"

    def _sin_confirmar(self):
        return bool(self.imagen) and not self.imagen._committed

    def clean(self):
        """Valida y convierte el archivo nuevo; ``save`` reutiliza el resultado."""
        if self._sin_confirmar():
            self._procesado = planos.procesar_plano(self.imagen.file)

    def save(self, *args, **kwargs):
        nuevo = self._sin_confirmar()
        anterior = None
        campos = kwargs.get("update_fields")
        if self.pk and (campos is None or "imagen" in campos):
            anterior = (
                Plano.objects.filter(pk=self.pk)
                .values_list("imagen", flat=True)
                .first()
            )
        if nuevo:
            procesado = getattr(self, "_procesado", None)
            self._procesado = None
            contenido, self.ancho_px, self.alto_px = procesado or planos.procesar_plano(
                self.imagen.file
            )
            self.imagen.save("plano.png", contenido, save=False)
        try:
            super().save(*args, **kwargs)
        except BaseException:
            # El archivo nuevo ya está escrito y el INSERT falló: no se deja huérfano.
            if nuevo:
                try:
                    self.imagen.storage.delete(self.imagen.name)
                except Exception:  # noqa: BLE001
                    logger.exception("No se pudo borrar el plano huérfano.")
            raise
        if anterior and anterior != self.imagen.name:
            _borrar_archivo_al_confirmar(self.imagen.storage, anterior)


@receiver(post_delete, sender=Plano)
def borrar_archivo_de_plano(sender, instance, **kwargs):
    """Al borrar un plano (también en cascada) no queda el archivo en disco."""
    if instance.imagen:
        almacenamiento, nombre = instance.imagen.storage, instance.imagen.name
        transaction.on_commit(lambda: almacenamiento.delete(nombre))


_FRACCION = [MinValueValidator(0), MaxValueValidator(1)]


def ruta_foto_punto(instancia, nombre):
    """Ruta de almacenamiento: UUID aleatorio, nunca el nombre original."""
    return f"sitios/puntos/{uuid.uuid4().hex}.jpg"


class PuntoControl(models.Model):
    """Lugar concreto del sitio con su propio QR donde se hace una revisión."""

    sitio = models.ForeignKey(
        Sitio, verbose_name="sitio", on_delete=models.CASCADE, related_name="puntos"
    )
    nombre = models.CharField("nombre", max_length=100)
    sector = models.CharField("sector", max_length=100, blank=True)
    orden = models.PositiveIntegerField("orden", default=0)
    activo = models.BooleanField("activo", default=True)
    qr_codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    qr_impreso_el = models.DateField("QR impreso el", null=True, blank=True)
    plano = models.ForeignKey(
        Plano,
        verbose_name="plano",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="puntos",
    )
    x = models.DecimalField(
        "x", max_digits=5, decimal_places=4, null=True, blank=True, validators=_FRACCION
    )
    y = models.DecimalField(
        "y", max_digits=5, decimal_places=4, null=True, blank=True, validators=_FRACCION
    )
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    precision_m = models.DecimalField(
        "precisión del GPS (m)",
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    servicio = models.ForeignKey(
        "servicios.TipoServicio",
        verbose_name="servicio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="puntos",
    )
    frecuencia_dias = models.PositiveIntegerField(
        "frecuencia (días)",
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
    )
    proximo_vencimiento = models.DateField("próximo vencimiento", null=True, blank=True)
    foto = models.ImageField("foto", upload_to=ruta_foto_punto, null=True, blank=True)
    ubicacion_fijada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="ubicación fijada por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    ubicacion_fijada_en = models.DateTimeField(
        "ubicación fijada en", null=True, blank=True
    )

    history = HistoricalRecords(excluded_fields=["precision_m"])

    class Meta:
        verbose_name = "punto de control"
        verbose_name_plural = "puntos de control"
        ordering = ["sitio_id", "orden", "id"]

    def __str__(self):
        return f"{self.nombre} ({self.sitio.nombre})"

    def clean(self):
        errores = {}
        if self.sitio_id and self.activo and not self.sitio.activo:
            errores["activo"] = "Un punto activo necesita un sitio activo."
        if self.plano_id and self.plano.sitio_id != self.sitio_id:
            errores["plano"] = "El plano pertenece a otro sitio."
        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        """Una foto nueva se procesa como las de visitas (JPEG sin metadatos)."""
        anterior = None
        campos = kwargs.get("update_fields")
        if self.pk and (campos is None or "foto" in campos):
            anterior = (
                PuntoControl.objects.filter(pk=self.pk)
                .values_list("foto", flat=True)
                .first()
            )
        nuevo = bool(self.foto) and not self.foto._committed
        if nuevo:
            contenido = imagenes.procesar_imagen(self.foto)
            self.foto.save("foto.jpg", contenido, save=False)
        try:
            super().save(*args, **kwargs)
        except BaseException:
            # El archivo nuevo ya está escrito y el INSERT falló: no se deja huérfano.
            if nuevo:
                try:
                    self.foto.storage.delete(self.foto.name)
                except Exception:  # noqa: BLE001
                    logger.exception("No se pudo borrar la foto huérfana.")
            raise
        if anterior and anterior != (self.foto.name or ""):
            _borrar_archivo_al_confirmar(self.foto.storage, anterior)


@receiver(post_delete, sender=PuntoControl)
def borrar_foto_de_punto(sender, instance, **kwargs):
    """Al borrar un punto (también en cascada) no queda la foto en disco."""
    if instance.foto:
        almacenamiento, nombre = instance.foto.storage, instance.foto.name
        transaction.on_commit(lambda: almacenamiento.delete(nombre))
