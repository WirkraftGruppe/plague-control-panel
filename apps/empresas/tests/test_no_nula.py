from decimal import Decimal

from django.apps import apps
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.empresas.models import ModeloDeEmpresa

from .ayudas import una_empresa


def _modelos_de_empresa():
    return [
        modelo
        for modelo in apps.get_models()
        if issubclass(modelo, ModeloDeEmpresa) and not modelo._meta.abstract
    ]


def _valor(campo, contador):
    """Un valor válido para un campo obligatorio, según su tipo."""
    if campo.choices:
        return campo.choices[0][0]
    if isinstance(campo, models.ForeignKey):
        return _crear(campo.related_model, contador)
    if isinstance(campo, models.DateTimeField):
        return timezone.now()
    if isinstance(campo, models.DecimalField):
        return Decimal("1")
    if isinstance(campo, models.FileField):
        return "prueba.png"
    if isinstance(campo, models.IntegerField):
        return 1
    if isinstance(campo, models.SlugField):
        return f"valor-{contador}"
    return f"valor {contador}"


def _campos_obligatorios(modelo):
    return [
        campo
        for campo in modelo._meta.concrete_fields
        if not campo.primary_key
        and campo.name != "empresa"
        and not campo.null
        and not campo.blank
        and not campo.has_default()
        and not getattr(campo, "auto_now", False)
        and not getattr(campo, "auto_now_add", False)
    ]


def _crear(modelo, contador, **extra):
    """Crea y guarda un objeto válido (con empresa) de `modelo`."""
    contador[0] += 1
    empresa = una_empresa()
    if modelo is User:
        return User.objects.create_user(
            f"usuario{contador[0]}", rol=User.Rol.EMPLEADO, empresa=empresa
        )
    datos = {c.name: _valor(c, contador) for c in _campos_obligatorios(modelo)}
    return modelo.todos.create(empresa=empresa, **datos, **extra)


class EmpresaObligatoriaTests(TestCase):
    def test_hay_trece_modelos_de_empresa(self):
        self.assertEqual(len(_modelos_de_empresa()), 13)

    def test_guardar_sin_empresa_falla_en_cada_modelo(self):
        contador = [0]
        for modelo in _modelos_de_empresa():
            with self.subTest(modelo=modelo.__name__):
                datos = {
                    c.name: _valor(c, contador) for c in _campos_obligatorios(modelo)
                }
                objeto = modelo(**datos)
                self.assertIsNone(objeto.empresa_id)
                # `bulk_create` no pasa por `save()`: no copia la empresa del padre.
                with self.assertRaises(IntegrityError) as contexto:
                    with transaction.atomic():
                        modelo.todos.bulk_create([objeto])
                self.assertIn("empresa_id", str(contexto.exception))
