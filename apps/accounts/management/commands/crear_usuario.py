from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from apps.accounts.limites import normalizar_usuario
from apps.empresas.models import Empresa


class Command(BaseCommand):
    help = "Crea un usuario del sistema con rol administrador o empleado."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--rol", required=True, choices=["administrador", "empleado"]
        )
        parser.add_argument("--nombre", default="")
        parser.add_argument("--apellido", default="")
        parser.add_argument("--email", default="")
        parser.add_argument("--empresa", type=int, help="Id de la empresa.")

    def handle(self, *args, **opciones):
        User = get_user_model()
        username = normalizar_usuario(opciones["username"])
        existentes = User.objects.values_list("username", flat=True)
        if any(normalizar_usuario(existente) == username for existente in existentes):
            raise CommandError(f"El usuario «{username}» ya existe.")

        empresa = None
        if opciones["empresa"] is not None:
            empresa = Empresa.objects.filter(pk=opciones["empresa"]).first()
            if empresa is None:
                raise CommandError(f"No existe la empresa {opciones['empresa']}.")

        contrasena = getpass("Contraseña: ")
        if contrasena != getpass("Repita la contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")

        usuario = User(
            username=username,
            rol=opciones["rol"],
            empresa=empresa,
            first_name=opciones["nombre"],
            last_name=opciones["apellido"],
            email=opciones["email"],
            is_staff=False,
            is_superuser=False,
        )
        try:
            usuario.full_clean(exclude=["password"])
            validate_password(contrasena, usuario)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages)) from error

        usuario.set_password(contrasena)
        try:
            usuario.save()
        except IntegrityError as error:
            raise CommandError(f"El usuario «{username}» ya existe.") from error
        self.stdout.write(self.style.SUCCESS(f"Usuario «{username}» creado."))
