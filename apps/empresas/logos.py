"""Proceso del logo de una empresa: PNG sin metadatos de hasta 512 px de lado."""

import warnings
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 2 * 1024 * 1024
LADO_MAXIMO_PX = 512
MAX_PIXELES = 25_000_000
ERROR_IMAGEN = "El archivo no es una imagen JPG o PNG válida."
ERROR_TAMANO = "El logo pesa más de 2 MB."


def procesar_logo(archivo):
    """Devuelve el logo como `ContentFile` PNG sin metadatos, a lo sumo de 512 px.

    Acepta solo JPEG y PNG; lanza `ValidationError` con otro formato, un archivo
    ilegible o más de 2 MB. Conserva la transparencia.
    """
    if getattr(archivo, "size", 0) > MAX_BYTES:
        raise ValidationError(ERROR_TAMANO)
    datos = archivo.read(MAX_BYTES + 1)
    if len(datos) > MAX_BYTES:
        raise ValidationError(ERROR_TAMANO)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(datos), formats=("JPEG", "PNG")) as original:
                if original.width * original.height > MAX_PIXELES:
                    raise Image.DecompressionBombError("Demasiados píxeles.")
                original.load()
                try:
                    ImageOps.exif_transpose(original, in_place=True)
                except Exception:  # noqa: BLE001
                    # La rotación es cosmética: un EXIF corrupto no debe dar un 500.
                    pass
                con_alfa = original.mode in ("RGBA", "LA", "PA", "P")
                imagen = original.convert("RGBA" if con_alfa else "RGB")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValidationError(
            "La imagen tiene una resolución demasiado alta; use una más chica."
        ) from error
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError(ERROR_IMAGEN) from error
    imagen.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX))
    # Imagen nueva desde los píxeles: no hereda EXIF, texto ni perfiles.
    limpia = Image.frombytes(imagen.mode, imagen.size, imagen.tobytes())
    salida = BytesIO()
    limpia.save(salida, format="PNG", optimize=True)
    return ContentFile(salida.getvalue(), name="logo.png")
