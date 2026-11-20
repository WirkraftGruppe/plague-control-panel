"""Modelos de Visitas: Visita (jornada), Revision (escaneo), Foto y ProductoAplicado."""

import logging
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.accounts.models import User
from apps.empresas.models import ModeloDeEmpresa
from apps.productos import unidades

from . import imagenes

logger = logging.getLogger(__name__)


class Visita(ModeloDeEmpresa):
    padre_de_empresa = "sitio"
    referencias_de_empresa = ("empleado", "asignada_por", "incidencia_revisada_por")

    class Origen(models.TextChoices):
        APP = "app", "App móvil"
        MANUAL = "manual", "Manual"

    class Cierre(models.TextChoices):
        EMPLEADO = "empleado", "Empleado"
        SISTEMA = "sistema", "Sistema"
        ADMINISTRADOR = "administrador", "Administrador"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ABIERTA = "abierta", "Abierta"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"

    sitio = models.ForeignKey(
        "sitios.Sitio",
        on_delete=models.PROTECT,
        related_name="visitas",
        verbose_name="sitio",
    )
    empleado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="visitas",
        limit_choices_to={"rol__in": [User.Rol.EMPLEADO, User.Rol.ADMINISTRADOR]},
        verbose_name="empleado",
    )
    origen = models.CharField("origen", max_length=10, choices=Origen.choices)
    motivo_manual = models.TextField("motivo manual", blank=True)
    programada_para = models.DateField("programada para", null=True, blank=True)
    asignada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="visitas_asignadas",
        verbose_name="asignada por",
    )
    abierta_en = models.DateTimeField("abierta en", null=True, blank=True)
    cerrada_en = models.DateTimeField("cerrada en", null=True, blank=True)
    abierta_recibida_en = models.DateTimeField(
        "apertura recibida en", null=True, blank=True, editable=False
    )
    cerrada_recibida_en = models.DateTimeField(
        "cierre recibido en", null=True, blank=True, editable=False
    )
    cierre = models.CharField(
        "cierre", max_length=15, choices=Cierre.choices, blank=True
    )
    estado = models.CharField(
        "estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    # Planilla de ámbito visita por servicio: `{slug_servicio: {clave: valor}}`.
    datos = models.JSONField("datos de la planilla", default=dict, blank=True)
    # Esquema copiado al cerrar: `{slug_servicio: [campos]}`.
    esquema_planilla = models.JSONField(
        "esquema de la planilla", default=dict, blank=True
    )
    observaciones = models.TextField("observaciones", blank=True)
    incidencia = models.BooleanField("incidencia", default=False)
    incidencia_detalle = models.TextField("detalle de la incidencia", blank=True)
    incidencia_asignacion = models.BooleanField(
        "incidencia de asignación", default=False
    )
    incidencia_revisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="incidencia revisada por",
    )
    incidencia_revisada_en = models.DateTimeField(
        "incidencia revisada en", null=True, blank=True
    )
    distancia_m = models.PositiveIntegerField(
        "distancia al punto (m)", null=True, blank=True
    )
    precision_m = models.DecimalField(
        "precisión (m)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    incidencia_ubicacion = models.BooleanField("incidencia de ubicación", default=False)
    incidencia_horas = models.BooleanField(
        "incidencia de horas",
        default=False,
        editable=False,
        help_text="La hora declarada de cierre o de reporte es anterior a la apertura.",
    )
    incidencia_apertura_sin_escaneo = models.BooleanField(
        "incidencia de apertura sin escaneo",
        default=False,
        editable=False,
        help_text="El empleado abrió el turno sin escanear el QR.",
    )
    # Rol del empleado al abrir la visita: un administrador no cuenta como servicio.
    cuenta_como_servicio = models.BooleanField("cuenta como servicio", default=True)
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    history = HistoricalRecords(excluded_fields=["datos", "distancia_m", "precision_m"])

    class Meta:
        verbose_name = "visita"
        verbose_name_plural = "visitas"
        ordering = ["-creado"]

    def __str__(self):
        return f"Visita {self.pk} - {self.sitio_id}"

    @property
    def realizada_en(self):
        """Fecha de realización: el momento en que se cerró la jornada."""
        return self.cerrada_en

    def clean(self):
        super().clean()
        if self.estado == self.Estado.REALIZADA and not self.cerrada_en:
            raise ValidationError({"cerrada_en": "Falta la fecha de cierre."})
        if self.estado == self.Estado.CANCELADA and self.cerrada_en:
            raise ValidationError(
                {"cerrada_en": "Una cancelada no lleva fecha de cierre."}
            )
        if self.estado == self.Estado.ABIERTA and not self.abierta_en:
            raise ValidationError({"abierta_en": "Falta la fecha de apertura."})
        if (
            self.pk
            and self.estado == self.Estado.PENDIENTE
            and self.revisiones.exists()
        ):
            raise ValidationError("Una visita pendiente no tiene revisiones.")
        if (
            self.estado == self.Estado.PENDIENTE
            and self.empleado_id
            # User no tiene guardia de empresa: se consulta con _default_manager.
            and User._default_manager.filter(
                pk=self.empleado_id, rol=User.Rol.ADMINISTRADOR
            ).exists()
        ):
            raise ValidationError(
                {"empleado": "Una visita pendiente no se asigna a un administrador."}
            )


class ItemTurno(ModeloDeEmpresa):
    """Punto de control de un turno con el servicio que se hará en él."""

    padre_de_empresa = "visita"
    referencias_de_empresa = ("punto", "servicio")

    visita = models.ForeignKey(
        Visita,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="visita",
    )
    punto = models.ForeignKey(
        "sitios.PuntoControl",
        on_delete=models.PROTECT,
        related_name="items_turno",
        verbose_name="punto de control",
    )
    servicio = models.ForeignKey(
        "servicios.TipoServicio",
        on_delete=models.PROTECT,
        related_name="items_turno",
        verbose_name="servicio",
    )

    class Meta:
        verbose_name = "ítem del turno"
        verbose_name_plural = "ítems del turno"
        ordering = ["visita_id", "punto__orden", "punto_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["visita", "punto"], name="item_turno_punto_unico_por_visita"
            )
        ]

    def __str__(self):
        return f"Ítem {self.pk} de visita {self.visita_id}"


class Revision(ModeloDeEmpresa):
    """Un escaneo de un punto de control dentro de una visita."""

    padre_de_empresa = "visita"
    referencias_de_empresa = ("punto", "servicio")

    visita = models.ForeignKey(
        Visita,
        on_delete=models.CASCADE,
        related_name="revisiones",
        verbose_name="visita",
    )
    punto = models.ForeignKey(
        "sitios.PuntoControl",
        on_delete=models.PROTECT,
        related_name="revisiones",
        verbose_name="punto de control",
    )
    servicio = models.ForeignKey(
        "servicios.TipoServicio",
        on_delete=models.PROTECT,
        related_name="revisiones",
        verbose_name="servicio",
    )
    fuera_de_turno = models.BooleanField("fuera de turno", default=False)
    orden = models.PositiveSmallIntegerField("orden", default=0)
    realizada_en = models.DateTimeField("realizada en")
    recibida_en = models.DateTimeField("recibida en")
    cliente_uuid = models.UUIDField("identificador del cliente", null=True, blank=True)
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    precision_m = models.DecimalField(
        "precisión (m)", max_digits=7, decimal_places=1, null=True, blank=True
    )
    distancia_m = models.PositiveIntegerField(
        "distancia al punto (m)", null=True, blank=True
    )
    incidencia_ubicacion = models.BooleanField("incidencia de ubicación", default=False)
    datos = models.JSONField("datos de la planilla", default=dict, blank=True)
    esquema_planilla = models.JSONField(
        "esquema de la planilla", default=list, blank=True
    )
    observaciones = models.TextField("observaciones", blank=True)
    incidencia = models.BooleanField("incidencia", default=False)
    incidencia_detalle = models.TextField("detalle de la incidencia", blank=True)
    incidencia_servicio = models.BooleanField(
        "incidencia de servicio",
        default=False,
        help_text="El empleado hizo la revisión con un servicio distinto del asignado.",
    )
    incidencia_duplicada = models.BooleanField(
        "incidencia de revisión duplicada",
        default=False,
        help_text="Otro empleado ya había revisado el punto ese día.",
    )
    incidencia_sin_ubicacion = models.BooleanField(
        "incidencia de revisión sin ubicación",
        default=False,
        help_text="La revisión llegó sin coordenadas.",
    )

    history = HistoricalRecords(
        excluded_fields=["latitud", "longitud", "precision_m", "distancia_m", "datos"]
    )

    class Meta:
        verbose_name = "revisión"
        verbose_name_plural = "revisiones"
        ordering = ["visita_id", "orden", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "cliente_uuid"],
                name="revision_cliente_uuid_unico_por_empresa",
            )
        ]

    def __str__(self):
        return f"Revisión {self.pk} de visita {self.visita_id}"


def ruta_foto(instancia, nombre):
    """Ruta de almacenamiento: UUID aleatorio, nunca el nombre original."""
    return f"visitas/fotos/{uuid4().hex}.jpg"


class Foto(ModeloDeEmpresa):
    padre_de_empresa = "revision"

    revision = models.ForeignKey(
        Revision,
        on_delete=models.CASCADE,
        related_name="fotos",
        verbose_name="revisión",
    )
    codigo = models.UUIDField("código", default=uuid4, unique=True, editable=False)
    imagen = models.ImageField("imagen", upload_to=ruta_foto)
    tomada_en = models.DateTimeField("tomada en", null=True, blank=True)
    orden = models.PositiveSmallIntegerField("orden", default=0)

    class Meta:
        verbose_name = "foto"
        verbose_name_plural = "fotos"
        ordering = ["orden", "id"]

    def __str__(self):
        return f"Foto {self.pk} de revisión {self.revision_id}"

    def save(self, *args, **kwargs):
        anterior = None
        if self.pk:
            anterior = (
                Foto.todos.filter(pk=self.pk).values_list("imagen", flat=True).first()
            )
        nuevo = bool(self.imagen) and not self.imagen._committed
        if nuevo:
            contenido = imagenes.procesar_imagen(self.imagen)
            self.imagen.save("foto.jpg", contenido, save=False)
        try:
            super().save(*args, **kwargs)
        except BaseException:
            # El archivo nuevo ya está escrito y el INSERT falló: no se deja huérfano.
            if nuevo:
                try:
                    self.imagen.storage.delete(self.imagen.name)
                except Exception:  # noqa: BLE001
                    logger.exception("No se pudo borrar la foto huérfana.")
            raise
        if anterior and anterior != self.imagen.name:
            _borrar_archivo_al_confirmar(self.imagen.storage, anterior)


def _borrar_archivo_al_confirmar(almacenamiento, nombre):
    """Borra el archivo del almacenamiento cuando la transacción se confirma."""
    transaction.on_commit(lambda: almacenamiento.delete(nombre))


@receiver(post_delete, sender=Foto)
def borrar_archivo_de_foto(sender, instance, **kwargs):
    """Al borrar una foto (también en cascada) no queda el archivo en disco."""
    if instance.imagen:
        _borrar_archivo_al_confirmar(instance.imagen.storage, instance.imagen.name)


class PuntoNoRevisado(ModeloDeEmpresa):
    """Reporte de un punto que el empleado no pudo revisar en una visita.

    No es una revisión: no cuenta para el vencimiento ni para cerrar la visita.
    """

    padre_de_empresa = "visita"
    referencias_de_empresa = ("punto",)

    class Motivo(models.TextChoices):
        FALTA_ESTACION = "falta_estacion", "Falta la estación"
        CODIGO_ILEGIBLE = "codigo_ilegible", "Código ilegible"
        SIN_ACCESO = "sin_acceso", "Sin acceso"
        OTRO = "otro", "Otro"

    visita = models.ForeignKey(
        Visita,
        on_delete=models.CASCADE,
        related_name="no_revisados",
        verbose_name="visita",
    )
    punto = models.ForeignKey(
        "sitios.PuntoControl",
        on_delete=models.PROTECT,
        related_name="no_revisados",
        verbose_name="punto de control",
    )
    motivo = models.CharField("motivo", max_length=20, choices=Motivo.choices)
    detalle = models.TextField("detalle", blank=True)
    latitud = models.DecimalField(
        "latitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitud = models.DecimalField(
        "longitud", max_digits=9, decimal_places=6, null=True, blank=True
    )
    precision_m = models.DecimalField(
        "precisión (m)", max_digits=7, decimal_places=1, null=True, blank=True
    )
    distancia_m = models.PositiveIntegerField(
        "distancia al punto (m)", null=True, blank=True
    )
    foto = models.ImageField("foto", upload_to=ruta_foto, blank=True)
    foto_codigo = models.UUIDField(
        "código de la foto", default=uuid4, unique=True, editable=False
    )
    cliente_uuid = models.UUIDField("identificador del cliente", null=True, blank=True)
    reportado_en = models.DateTimeField("reportado en", default=timezone.now)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "punto no revisado"
        verbose_name_plural = "puntos no revisados"
        ordering = ["visita_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "cliente_uuid"],
                name="no_revisado_cliente_uuid_unico_por_empresa",
            ),
            models.UniqueConstraint(
                fields=["visita", "punto"], name="no_revisado_punto_unico_por_visita"
            ),
        ]

    def __str__(self):
        return f"Punto {self.punto_id} no revisado en visita {self.visita_id}"


@receiver(post_delete, sender=PuntoNoRevisado)
def borrar_archivo_de_no_revisado(sender, instance, **kwargs):
    """Al borrar un reporte (también en cascada) no queda la foto en disco."""
    if instance.foto:
        _borrar_archivo_al_confirmar(instance.foto.storage, instance.foto.name)


class ProductoAplicado(ModeloDeEmpresa):
    padre_de_empresa = "revision"
    referencias_de_empresa = ("producto", "movimiento")

    revision = models.ForeignKey(
        Revision,
        on_delete=models.CASCADE,
        related_name="productos",
        verbose_name="revisión",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        verbose_name="producto",
    )
    lote = models.CharField("lote", max_length=60)
    dosis = models.DecimalField(
        "dosis", max_digits=10, decimal_places=3, null=True, blank=True
    )
    unidad_dosis = models.CharField("unidad de la dosis", max_length=20, blank=True)
    unidad = models.CharField(
        "unidad de la cantidad", max_length=10, choices=unidades.CHOICES
    )
    cantidad = models.DecimalField("cantidad", max_digits=10, decimal_places=3)
    cantidad_base = models.DecimalField(
        "cantidad en unidad base",
        max_digits=14,
        decimal_places=4,
        help_text="Calculada por el servidor a partir de la cantidad y su unidad.",
    )
    movimiento = models.OneToOneField(
        "productos.MovimientoStock",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="producto_aplicado",
        verbose_name="movimiento de stock",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "producto aplicado"
        verbose_name_plural = "productos aplicados"

    def __str__(self):
        return f"{self.producto_id} en revisión {self.revision_id}"
