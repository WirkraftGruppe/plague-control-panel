from django.db import migrations, models


def marcar_dosis_variable(apps, schema_editor):
    """RunPython justificado: los productos existentes no tienen dosis habitual
    cargada, así que se marcan como de dosis variable para que sigan siendo válidos."""
    Producto = apps.get_model("productos", "Producto")
    Producto.objects.all().update(dosis_variable=True)


class Migration(migrations.Migration):
    dependencies = [
        ("productos", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="producto",
            old_name="unidad_dosis_por_defecto",
            new_name="unidad_dosis_habitual",
        ),
        migrations.AlterField(
            model_name="producto",
            name="unidad_dosis_habitual",
            field=models.CharField(
                blank=True,
                help_text="Por ejemplo: ml/l.",
                max_length=20,
                verbose_name="unidad de dosis habitual",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="dosis_habitual",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text="Concentración de la preparación (p. ej. 5 ml/l).",
                max_digits=10,
                null=True,
                verbose_name="dosis habitual",
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="dosis_variable",
            field=models.BooleanField(
                default=False,
                help_text="La dosis cambia en cada aplicación y no tiene un valor habitual.",
                verbose_name="dosis variable",
            ),
        ),
        migrations.RunPython(marcar_dosis_variable, migrations.RunPython.noop),
    ]
