"""Revision.incidencia_servicio y PuntoNoRevisado.reportado_en.

`reportado_en` se agrega nulo, se llena con `creado` (RunPython justificado: hay
que copiar una columna a otra fila por fila de la tabla) y pasa a no nulo.
"""

import django.utils.timezone
from django.db import migrations, models
from django.db.models import F


def llenar_reportado_en(apps, schema_editor):
    """Los reportes existentes se dieron por reportados cuando se crearon."""
    PuntoNoRevisado = apps.get_model("visitas", "PuntoNoRevisado")
    PuntoNoRevisado._base_manager.update(reportado_en=F("creado"))


class Migration(migrations.Migration):

    dependencies = [
        ("visitas", "0002_punto_no_revisado"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalrevision",
            name="incidencia_servicio",
            field=models.BooleanField(
                default=False,
                help_text="El empleado hizo la revisión con un servicio distinto del asignado.",
                verbose_name="incidencia de servicio",
            ),
        ),
        migrations.AddField(
            model_name="revision",
            name="incidencia_servicio",
            field=models.BooleanField(
                default=False,
                help_text="El empleado hizo la revisión con un servicio distinto del asignado.",
                verbose_name="incidencia de servicio",
            ),
        ),
        migrations.AddField(
            model_name="puntonorevisado",
            name="reportado_en",
            field=models.DateTimeField(null=True, verbose_name="reportado en"),
        ),
        migrations.RunPython(llenar_reportado_en, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="puntonorevisado",
            name="reportado_en",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="reportado en"
            ),
        ),
    ]
