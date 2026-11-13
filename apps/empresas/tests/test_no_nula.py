from decimal import Decimal

from django.apps import apps
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.clientes.models import Cliente
from apps.empresas.models import ModeloDeEmpresa
from apps.empresas.pruebas import crear_empresa
from apps.sitios.models import PuntoControl, Sitio
from apps.visitas.models import Visita

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


class EmpresaInmutableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = crear_empresa("Empresa A")
        cls.b = crear_empresa("Empresa B")
        cls.cliente = Cliente.objects.create(empresa=cls.a, razon_social="ACME")
        cls.sitio = Sitio.objects.create(cliente=cls.cliente, nombre="Planta")

    def test_update_fields_sin_empresa_no_blanquea_el_cambio_pendiente(self):
        c = Cliente.todos.get(pk=self.cliente.pk)
        c.empresa = self.b
        c.save(update_fields=["razon_social"])
        with self.assertRaises(ValueError):
            c.save()
        self.assertEqual(Cliente.todos.get(pk=c.pk).empresa_id, self.a.pk)

    def test_cambio_de_empresa_en_full_clean_da_solo_error_general(self):
        c = Cliente.todos.get(pk=self.cliente.pk)
        c.empresa = self.b
        with self.assertRaises(ValidationError) as contexto:
            c.full_clean()
        self.assertEqual(set(contexto.exception.error_dict), {NON_FIELD_ERRORS})

    def test_un_alta_no_cuenta_como_cambio_de_empresa(self):
        c = Cliente.todos.get(pk=self.cliente.pk)
        c._state.adding = True
        c.empresa = self.b
        self.assertFalse(c._empresa_cambiada())

    def test_update_fields_sin_empresa_no_compara_la_empresa(self):
        c = Cliente.todos.get(pk=self.cliente.pk)
        c.empresa = self.b
        c.razon_social = "Nueva"
        c.save(update_fields=["razon_social"])
        self.assertEqual(Cliente.todos.get(pk=c.pk).razon_social, "Nueva")

    def test_clean_con_padre_inexistente_da_validation_error(self):
        visita = Visita(empresa=self.a, sitio_id=999999, empleado_id=999999)
        with self.assertRaises(ValidationError):
            visita.full_clean()

    def test_clean_con_referencia_inexistente_da_validation_error(self):
        visita = Visita(empresa=self.a, sitio=self.sitio, empleado_id=999999)
        with self.assertRaises(ValidationError):
            visita.full_clean()

    def test_punto_con_sitio_inexistente_da_validation_error(self):
        with self.assertRaises(ValidationError):
            PuntoControl(sitio_id=999999, nombre="P").full_clean()

    def test_referencia_a_plataforma_cuenta_como_de_otra_empresa(self):
        plataforma = User.objects.create_user(
            "plat", password="x", rol=User.Rol.PLATAFORMA
        )
        visita = Visita(
            sitio=self.sitio,
            empleado=User.objects.create_user(
                "emp", password="x", rol=User.Rol.EMPLEADO, empresa=self.a
            ),
            asignada_por=plataforma,
            origen=Visita.Origen.APP,
        )
        with self.assertRaises(ValidationError) as contexto:
            visita.full_clean()
        self.assertIn("asignada_por", contexto.exception.error_dict)
