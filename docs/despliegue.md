# Despliegue en Railway (a mano)

Guía para alojar una instancia de Detach. Nada de esto se ejecuta solo: lo hace el usuario desde su cuenta. La configuración ya está en el repositorio (`railway.json`, `.python-version`, `config/settings/prod.py`).

## 1. Cuenta y proyecto
1. Crear la cuenta en railway.com y conectar el repositorio de GitHub.
2. `New Project` -> `Deploy from GitHub repo` -> elegir el repositorio y la rama a alojar.
3. Railway lee `railway.json`:
   - Build: `python manage.py collectstatic --noinput`.
   - Antes de cada despliegue: `python manage.py migrate --noinput`.
   - Inicio: `gunicorn config.wsgi --bind 0.0.0.0:$PORT --timeout 60`.
4. Python 3.13 sale de `.python-version`.

## 2. Base de datos
1. En el proyecto: `New` -> `Database` -> `Add PostgreSQL`.
2. En el servicio web, variable `DATABASE_URL` como referencia a la base: `${{Postgres.DATABASE_URL}}`.

## 3. Variables del servicio web
| Variable | Valor |
|---|---|
| `DJANGO_ENV` | `production` (obligatoria; con `development` el arranque aborta en Railway) |
| `SECRET_KEY` | una clave larga y aleatoria, propia de esta instancia |
| `DATABASE_URL` | referencia a Postgres (punto 2) |
| `ALLOWED_HOSTS` | el dominio público, p. ej. `demo.up.railway.app` (si queda vacío, el arranque aborta) |
| `CSRF_TRUSTED_ORIGINS` | el mismo dominio con esquema, p. ej. `https://demo.up.railway.app` (varios, separados por comas) |
| `SITE_URL` | `https://demo.up.railway.app` (base del contenido de los QR). **Obligatoria**: sin ella el arranque aborta |
| `NOMBRE_EMPRESA` | nombre de la empresa que aparece en el panel y en la página `/q/<uuid>/`. **Obligatoria**: sin ella el arranque aborta |
| `CORREO_CONTACTO` | correo de contacto de la empresa (opcional; vacío usa el valor por defecto de `base.py`) |
| `MEDIA_ROOT` | `/data/media` (ruta del volumen, punto 4) |

`SITE_URL` y `NOMBRE_EMPRESA` también deben estar definidas **antes del build**: `prod.py` aborta con `ImproperlyConfigured` al importar los settings con `DJANGO_ENV=production`, y el build de Railway corre `collectstatic` (y el despliegue, `migrate`) con esas variables; sin ellas fallan el build y el despliegue, no solo el arranque.

El dominio público se genera en `Settings` -> `Networking` -> `Generate Domain`. Las variables no se versionan: `.env.example` solo lista los nombres.

## 4. Volumen para `media/`
Fotos y planos se guardan en disco (`MEDIA_ROOT`). El disco del contenedor se pierde en cada despliegue, así que hace falta un volumen:
1. En el servicio web: `Settings` -> `Volumes` -> `Add Volume`, punto de montaje `/data`.
2. `MEDIA_ROOT=/data/media`.

Sin volumen, las imágenes subidas desaparecen en el siguiente despliegue (P-demo-cliente-1). Los respaldos del volumen y de Postgres son responsabilidad del usuario.

## 5. Primer ingreso
Con la base vacía no hay usuarios. Crear el primer administrador desde la consola del servicio (`railway ssh` o la pestaña de comandos):
`python manage.py createsuperuser`.
Después, desde el panel, crear las cuentas que hagan falta.

## 6. Por qué `cargar_demo` no corre sobre Postgres
`cargar_demo` solo corre con `DEBUG`, `DJANGO_ENV=development` y SQLite (decisión 2026-10-06 en `docs/decisiones.md`): con una `DATABASE_URL` de producción sembraría un administrador con clave pública, y una base "local" por HOST no se puede asegurar. En Railway, `DJANGO_ENV=production` y `DEBUG=False`, por lo que el comando se niega. Una instancia alojada queda sin datos de demo; mostrarlos ahí requiere una decisión nueva del usuario (P-demo-cliente-3).

## 7. Pendientes de `despliegue` que siguen abiertos
Esta configuración no los cierra. Listarlos con:

```bash
py -3 .claude/hooks/pendientes.py
```

Los de más peso antes de abrir la instancia al público:
- `NUM_PROXIES` obligatorio y `CACHES` compartida (P-pendientes-heredados-21, P-limites-ingreso-3): detrás del proxy de Railway todas las peticiones comparten IP.
- Tope de bytes de las subidas en el proxy o con un middleware (P-panel-23, P-contrato-app-2, P-contrato-app-6).
- Programar `cerrar_visitas_abiertas` (P-puntos-control-10): no hay cron configurado.
- Timeout del worker mayor que `TIEMPO_MAXIMO_PDF` (P-puntos-control-30): `--timeout 60` ya lo cumple.
- Prueba contra PostgreSQL de los bloqueos (P-robustez-datos-7).
