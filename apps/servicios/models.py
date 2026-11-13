"""Modelos de Servicios: tipos de servicio y su planilla dinámica."""

from django.db import IntegrityError, models, transaction
from django.utils.text import slugify

from apps.empresas.models import ModeloDeEmpresa


class TipoServicio(ModeloDeEmpresa):
    """Servicio que ofrece la empresa; define la planilla de cada visita."""

    nombre = models.CharField("nombre", max_length=150)
    slug = models.SlugField("slug", max_length=150)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "slug"], name="tipo_servicio_slug_unico_por_empresa"
            )
        ]

    def __str__(self):
        return self.nombre

    INTENTOS_SLUG = 5

    def save(self, *args, **kwargs):
        """Genera el slug solo si viene vacío; nunca lo cambia después.

        Si el slug se generó acá y el INSERT choca por una carrera con otro alta,
        reintenta con el siguiente sufijo libre; un slug explícito repetido falla.
        """
        if self.slug:
            return super().save(*args, **kwargs)
        campos = kwargs.get("update_fields")
        if campos is not None:
            kwargs["update_fields"] = {*campos, "slug"}
        for intento in range(self.INTENTOS_SLUG):
            self.slug = self._slug_libre()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if intento == self.INTENTOS_SLUG - 1:
                    raise
                self.slug = ""

    def _slug_libre(self) -> str:
        """`slugify(nombre)` con sufijo `-2`, `-3`… si ya existe en la empresa."""
        base = slugify(self.nombre)[:140] or "servicio"
        slug, numero = base, 2
        while TipoServicio.todos.filter(empresa_id=self.empresa_id, slug=slug).exists():
            slug = f"{base}-{numero}"
            numero += 1
        return slug

    def esquema_planilla(self, ambito: str = "punto") -> list[dict]:
        """Esquema de los campos activos de un ámbito ordenado por `orden`.

        Lo consume la API. `ambito` es `punto` o `visita`.

        Usa `self.campos.all()` para aprovechar un `prefetch_related("campos")`.
        """
        activos = sorted(
            (
                campo
                for campo in self.campos.all()
                if campo.activo and campo.ambito == ambito
            ),
            key=lambda campo: campo.orden,
        )
        return [
            {
                "clave": campo.clave,
                "etiqueta": campo.etiqueta,
                "tipo": campo.tipo,
                "opciones": campo.opciones,
                "obligatorio": campo.obligatorio,
                "ayuda": campo.ayuda,
                "orden": campo.orden,
            }
            for campo in activos
        ]


class CampoPlanilla(ModeloDeEmpresa):
    """Campo de la planilla de un tipo de servicio."""

    class Tipo(models.TextChoices):
        TEXTO = "texto", "Texto"
        NUMERO = "numero", "Número"
        BOOLEANO = "booleano", "Sí/No"
        OPCION = "opcion", "Opción"
        OPCION_MULTIPLE = "opcion_multiple", "Opción múltiple"
        FECHA = "fecha", "Fecha"

    class Ambito(models.TextChoices):
        PUNTO = "punto", "Punto de control"
        VISITA = "visita", "Visita"

    padre_de_empresa = "tipo_servicio"

    tipo_servicio = models.ForeignKey(
        TipoServicio,
        on_delete=models.CASCADE,
        related_name="campos",
        verbose_name="tipo de servicio",
    )
    orden = models.PositiveIntegerField("orden")
    etiqueta = models.CharField("etiqueta", max_length=150)
    clave = models.SlugField("clave", max_length=100)
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    ambito = models.CharField(
        "ámbito", max_length=10, choices=Ambito.choices, default=Ambito.PUNTO
    )
    opciones = models.JSONField("opciones", default=list, blank=True)
    obligatorio = models.BooleanField("obligatorio", default=False)
    ayuda = models.CharField("ayuda", max_length=255, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "campo de planilla"
        verbose_name_plural = "campos de planilla"
        ordering = ["orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_servicio", "clave"],
                name="campo_planilla_clave_unica_por_tipo",
            )
        ]

    def __str__(self):
        return f"{self.tipo_servicio} · {self.etiqueta}"
