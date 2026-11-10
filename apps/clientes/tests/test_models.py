from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.clientes.models import Cliente
from apps.clientes.validators import validar_cuit
from apps.empresas.tests.ayudas import una_empresa


class ClienteTests(TestCase):
    def test_cuit_invalido_no_valida(self):
        for cuit in ("2012345678", "20-1234567-9", "2012345678a"):
            with self.subTest(cuit=cuit):
                with self.assertRaises(ValidationError) as ctx:
                    Cliente(
                        razon_social="ACME", cuit=cuit, empresa=una_empresa()
                    ).full_clean()
                self.assertIn("cuit", ctx.exception.message_dict)

    def test_cuit_valido_pasa(self):
        Cliente(
            razon_social="ACME", cuit="20123456786", empresa=una_empresa()
        ).full_clean()

    def test_cuit_con_digito_verificador_invalido_no_valida(self):
        with self.assertRaises(ValidationError) as ctx:
            Cliente(
                razon_social="ACME", cuit="20123456789", empresa=una_empresa()
            ).full_clean()
        self.assertIn("cuit", ctx.exception.message_dict)

    def test_validar_cuit_solo_acepta_el_digito_correcto(self):
        for x in range(10):
            with self.subTest(digito=x):
                if x == 6:
                    validar_cuit(f"2012345678{x}")
                else:
                    with self.assertRaises(ValidationError):
                        validar_cuit(f"2012345678{x}")

    def test_cuit_resto_10_solo_prefijos_afip(self):
        # Con resto 10 el dígito es 9 y solo es válido con prefijo 23 o 33.
        for cuit in ("23000000069", "33000000099"):
            with self.subTest(cuit=cuit):
                validar_cuit(cuit)
        for cuit in ("20000000019", "27000000099"):
            with self.subTest(cuit=cuit):
                with self.assertRaises(ValidationError):
                    validar_cuit(cuit)
                with self.assertRaises(ValidationError):
                    Cliente(
                        razon_social="ACME", cuit=cuit, empresa=una_empresa()
                    ).full_clean()

    def test_cuit_es_opcional(self):
        cliente = Cliente(razon_social="ACME", empresa=una_empresa())
        cliente.full_clean()
        cliente.save()
        self.assertEqual(cliente.cuit, "")
