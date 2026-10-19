# Detach

Detach es un sistema de gestión para empresas de control de plagas: un único proyecto Django con el panel de gestión (`/panel/`, administradores) y la API (`/api/v1/`, app móvil de los empleados). Clientes, sitios con puntos de control y QR, proyectos, visitas, mapa, productos y certificados.

`/` redirige al login del panel. El nombre de la empresa sale de la variable `NOMBRE_EMPRESA` (`config/settings/base.py`). El sitio público de cada empresa vive en otro repositorio.

## Arranque (Windows, desde la raíz)

```bash
python -m venv venv && source venv/Scripts/activate
pip install -r requirements.txt
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py migrate
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py runserver
```

Variables de entorno: plantilla en `.env.example`. En producción son obligatorias `SECRET_KEY`, `DJANGO_ENV`, `DATABASE_URL`, `ALLOWED_HOSTS`, `SITE_URL` y `NOMBRE_EMPRESA`; opcional `CORREO_CONTACTO`. Despliegue: `docs/despliegue.md`.

## Tests y calidad

```bash
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb
./venv/Scripts/python.exe -m ruff check .
```

## Datos de demostración

```bash
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py cargar_demo
```

Siembra clientes, sitios, proyectos y visitas de ejemplo, con un administrador de clave pública. Solo corre con `DEBUG`, `DJANGO_ENV=development` y SQLite; se niega en cualquier otro caso. No hay paquete portátil de la demostración.

## Contrato de la API

`docs/contrato-api.md` describe `/api/v1/` para la app móvil; el esquema OpenAPI está en `docs/api/openapi-v1.yaml`.

## Bases anteriores a la separación del sitio público

Antes se incluía una app `web` con el sitio público. Sus tablas (`web_*`) no se borran con una migración. Quien tenga una base anterior y quiera limpiarlas debe correr, **con el código anterior y antes de actualizar**:

```bash
PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py migrate web zero
```

Si no se corre, las tablas quedan huérfanas y no molestan.

## Más documentación

`CLAUDE.md` (flujo de trabajo), `docs/01-modelo-y-arquitectura.md` (dominio), `docs/02-diseno.md` (sistema visual del panel).
