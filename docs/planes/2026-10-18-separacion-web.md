# Plan: separacion-web — el panel, la API y la app pasan a ser Detach; el sitio público sale del repositorio

- **slug**: `separacion-web`
- **fecha**: 2026-10-18
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): separacion-web`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: que el proyecto deje de servir el sitio público de MAControl: `/` lleva al login del panel, el producto se llama Detach en títulos, login y API, el nombre de la empresa sale de `NOMBRE_EMPRESA`, y `/q/<uuid>/`, la 404 y la 500 siguen funcionando sin marca fija.
- **fuera de alcance**: multiempresa (modelo `Empresa`, datos por empresa; `NOMBRE_EMPRESA` es provisoria); borrar las tablas `web_*` de bases existentes (ver Decisiones); el repositorio `../macontrol-web`; `docs/ARRANQUE.md`, `docs/prompts/**`, `docs/propuestas/**` y los planes anteriores (históricos); `static/img/logo.png` y `static/fonts/**` (los usa el panel); las rutas de `/api/v1/` (ninguna cambia; `apps.web.api_urls` estaba vacío).
- **áreas**: web (se elimina) | panel | api (título del esquema y documento del contrato) | dominio (servicios) | infraestructura
- **seguridad**: sí — toca settings de producción (`SITE_URL` obligatoria en `prod.py`), `INSTALLED_APPS` y un context processor nuevo, las URL raíz (redirección de `/`), la página pública del QR (cambia de app), la 404 y la 500 de todo el proyecto, la mudanza de los tests de CSP y Referer, la desaparición de `robots.txt` (`noindex` en `base.html`), el User-Agent de la consulta saliente a Nominatim y el admin de usuarios. Corren `verificador`, `verificador-b` y `auditor-seguridad`.

## Contexto mínimo

- `apps.web` está en `config/settings/base.py:118`, `config/urls.py:10`, `apps/panel/urls.py:25` y `apps/api/urls.py:27` (vacío). `cargar_demo.py:39,68-69` importa `PaginaServicio` y carga `apps/web/fixtures/contenido_inicial.json`, que trae los 9 `servicios.tiposervicio` con `descripcion`; `test_cargar_demo.test_clientes_salen_de_la_carta` lee `docs/00-contenido-fuente.md`.
- De `apps/web` es de todo el proyecto: la página `/q/<uuid>/` de los QR impresos (`apps/sitios/qr.py:19` usa `reverse("web:qr")`; test `apps/sitios/tests/test_panel.py:157-162`), `apps/web/templates/404.html` y `500.html` (enlazan `css/web.css`), y los tests `test_base`, `test_cabeceras`, `test_csp` y `test_rutas` de `apps/web/tests`. `apps/panel/tests/test_routers.py:16`, `apps/api/tests/test_routers.py:16` y `apps/panel/tests/test_acceso.py:22,45-46,199-203` nombran a web.
- `TipoServicio` (`apps/servicios/models.py:6-13`): `slug` lo usan el admin y la demo (se queda); `descripcion` solo aparece en fixtures (se elimina). Barlow (`templates/base.html:9-56`, `apps/sitios/qr.py:14`) y `logo.png` los usa el panel.
- "MAControl" en código: ~25 plantillas `· MAControl`, `templates/base.html:6,126`, `templates/panel/base.html:4,14`, `templates/panel/ingresar.html:3,6`, `config/settings/base.py:96,188,226-227`, `config/apps.py:6`, `apps/sitios/geocodificacion.py:24`, `apps/accounts/admin.py:13,15`, `apps/clientes/models.py:10` y prefijos de `tempfile` en seis tests. No existe setting ni context processor con el nombre.
- `worktree-integrar.sh` corre la suite completa tras cada merge y lo deshace si falla: el corte de web es un solo cambio (T6 más el commit `T7:` del principal en la rama de T6). `server_error` renderiza la 500 sin context processors. `herramientas/humo_demo.py:70` sigue redirecciones. `/api/v1/` resuelve 18 rutas; `docs/api/openapi-v1.yaml` ya existe y no se reemplaza.
- `docs/01-modelo-y-arquitectura.md` §3.3 (TipoServicio), §3.10 (certificado), §3.12 (web) y el árbol de apps.

## Decisiones

- 2026-10-18 — `plan/separacion-web` sale de `main` después de fusionar `plan/demo-portatil` (4c2bcda) — T9 modifica `humo_demo.py` y `empaquetar_demo.py`, que vienen de ese plan — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — El panel, la API y la app son el producto "Detach"; el sitio público de MAControl vive en otro repositorio y este proyecto deja de tener `apps/web` (se borra la app entera, regla 1) — decisión del usuario — reemplaza a: 2026-09-28 (un único proyecto Django con sitio público, panel y API)
- 2026-10-18 — "Detach" va en `<title>`, login y `TITLE` de la API; `NOMBRE_EMPRESA` (entorno, por defecto `MAControl S.A.`, provisoria hasta multiempresa) va donde se nombra a la empresa: `DESCRIPTION` de la API, admin de usuarios, `alt` del logo y página del QR — decisión del usuario — reemplaza a: 2026-09-28 (razón social en textos), en lo que toca a textos fijos del código
- 2026-10-18 — `/q/<uuid>/` se muda a `apps/sitios` con la misma URL y una página neutra con `NOMBRE_EMPRESA` — los QR ya impresos siguen abriendo — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — `docs/02-diseno.md` se recorta al panel y `docs/00-contenido-fuente.md` se quita (ambos están en `../macontrol-web`) — decisión del usuario — reemplaza a: (nada)
- 2026-10-18 — La demo es solo del panel — consecuencia de quitar el sitio — decisión del usuario — reemplaza a: 2026-10-12 (la demo es solo del sitio público y del panel)
- 2026-10-18 — No hay servido público de `media/` — sin sitio público no hay logos ni portadas que publicar — decisión del usuario — reemplaza a: 2026-10-08 (`media/publico/` en abierto)
- 2026-10-18 — Se elimina `TipoServicio.descripcion` (migración en `servicios`, se quita de `tipos_servicio.json`) — solo la usaban los fixtures — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — Las tablas `web_*` no se borran con migración: quien quiera limpiarlas corre `manage.py migrate web zero` con el código anterior, antes de actualizar; la integración no lo corre sobre `demo.sqlite3` (`demo.bat` no la borra y las tablas huérfanas no molestan) — no hay producción — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `/` responde 302 a `panel:ingresar` (`RedirectView` con `pattern_name`, `permanent=False`) — destino fijo, sin redirección abierta — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — La página del QR vive en `apps/sitios/publico_views.py`, `publico_urls.py` (`app_name = "publico"`) y `templates/sitios/publico/qr.html`; `contenido_qr` resuelve con `reverse("qr", urlconf="apps.sitios.publico_urls")` y un test de T6 ata el contenido del QR a la ruta montada — T3 es verificable en su worktree sin tocar `config/urls.py` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — T1 toca solo archivos del principal (`config/`, `.env.example`, `docs/api/openapi-v1.yaml`) y la hace el principal, inline, en commits `T1:` sobre `plan/separacion-web` — la tabla de propiedad reserva esos archivos al principal (juez-plan, bloqueante) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — El commit que desconecta `apps.web` (`T7:`, archivos del principal) se hace en la rama de T6 al crearla, no en `plan/separacion-web` — la suite completa no puede quedar en rojo en ninguna integración — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — T6 es a la vez la subtarea transversal, la de diseño y la de web de este plan — el corte toca los tres dueños a la vez — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — La 404 y la 500 pasan a `templates/` raíz, autónomas, sin logo ni nombre de empresa, con `css/panel.css`; la 404 conserva el enlace según `request_path` (P-sitio-publico-9) y dice "Volver al panel" o "Volver al admin" — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `templates/base.html` queda con un solo tema (claro) y `<meta name="robots" content="noindex, nofollow">` — sin sitio público no hay `robots.txt` ni tema oscuro — decidida por Claude, revisable — reemplaza a: 2026-09-28 (dirección visual A para el sitio público), en este repositorio
- 2026-10-18 — Los tests de `apps/web` que cuidan comportamiento del proyecto se mudan a `apps/panel/tests/` (`test_rutas`, `test_errores`, `test_plantilla_base`, `test_cabeceras`, `test_csp`); los que solo prueban la web se borran — `config/tests` es del principal y `apps/panel/**` de la transversal — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `cargar_demo` carga `tipos_servicio` solo si no hay ningún `TipoServicio` — reemplaza la carga de `contenido_inicial`, que pisaba los pk 1-9 — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `SITE_URL` toma por defecto `http://localhost:8000` y `prod.py` la exige — un QR de producción con un dominio ajeno o local no lo abre nadie — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `CORREO_CONTACTO` (entorno, por defecto `administracion@macontrol.com.ar`, provisorio como `NOMBRE_EMPRESA`) va en el User-Agent `Detach/1.0 (+<SITE_URL>; <CORREO_CONTACTO>)` — Nominatim exige contacto — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — `config/tests/test_settings.py` conserva `macontrol.com.ar` como dato de hosts (`config/` queda fuera del grep de marca) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — Cada criterio de humo usa su propia carpeta `dist/prueba-separacion-<id>/`; el puerto 8000 sigue compartido (P-demo-portatil-5 mitigado, no cerrado) — decidida por Claude, revisable — reemplaza a: (nada)

## Olas

<!-- Única migración: `servicios` en T8. Las olas siguen el corte de web: la 1 prepara config, la 2 agrega lo nuevo sin quitar web, la 3 corta en un solo cambio, la 4 hace lo que necesita a web ya quitada. -->

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 (integración) | config (ninguna) |
| 2 | T3, T4, T5 (integración) | sitios; accounts, clientes, productos, visitas (ninguna) |
| 3 | T6, T7 (integración) | web (se borra), panel, api, diseño (ninguna) |
| 4 | T8, T9, T10, T11 (integración y cierre) | servicios (0004); herramientas; documentación |

## Subtareas

<!-- Común a las subtareas delegadas, salvo que se diga otra cosa:
No puede tocar: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `config/`, `.env.example`, `apps/*/urls.py`, migraciones existentes, archivos de otro dueño.
Skill a leer antes: `.claude/skills/convenciones-proyecto/SKILL.md`.
Worktree: sí (`worktrees/separacion-web-T<n>`, base `plan/separacion-web`). Ruta: delegada (`implementador`). -->

### T1 — Configuración de empresa y producto (principal)

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `config/settings/base.py`, `config/settings/prod.py`, `config/apps.py`, `config/contexto.py` (nuevo), `config/tests/test_empresa.py` (nuevo), `config/tests/test_settings.py`, `.env.example`, `docs/api/openapi-v1.yaml`
- **No puede tocar**: `docs/planes/`, `apps/`, `templates/`, `static/`, `config/urls.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; `.agents/skills/django-conventions/SKILL.md` § Settings
- **Worktree**: no; commits `T1:` en `plan/separacion-web` (archivos del principal según la tabla de propiedad)
- **Ruta**: inline (principal); el asunto del primer commit `T1:` nombra `NOMBRE_EMPRESA` (lo comprueba T2)
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `base.py`: `NOMBRE_EMPRESA = env("NOMBRE_EMPRESA", default="") or "MAControl S.A."` y `CORREO_CONTACTO` igual con `administracion@macontrol.com.ar`, ambos con comentario "provisoria hasta multiempresa"; agregarlos a `.env.example`.
  - `config/contexto.py::empresa(request)` devuelve `{"NOMBRE_EMPRESA": settings.NOMBRE_EMPRESA}`; agregarlo a `TEMPLATES[0]["OPTIONS"]["context_processors"]`.
  - `SPECTACULAR_SETTINGS["TITLE"] = "API de Detach"`; `DESCRIPTION` con `NOMBRE_EMPRESA`. `AdminMAControlConfig` → `AdminDetachConfig` (`config/apps.py` y `base.py:96`).
  - `SITE_URL` por defecto `http://localhost:8000`; `prod.py` levanta `ImproperlyConfigured` si falta o está vacía; `test_settings.py` pasa `SITE_URL=https://ejemplo.test` donde arranca producción.
  - Regenerar `docs/api/openapi-v1.yaml` con `manage.py spectacular --validate --file docs/api/openapi-v1.yaml` (arrastra también la descripción de la foto de `visitas/abrir`, que hoy falta en el yaml commiteado).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_empresa.EmpresaTests.test_contexto_expone_nombre_empresa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_empresa.EmpresaTests.test_nombre_empresa_y_correo_salen_del_entorno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_empresa.EmpresaTests.test_site_url_por_defecto_es_local --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_empresa.EmpresaTests.test_prod_sin_site_url_no_arranca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_empresa.EmpresaTests.test_admin_y_api_se_llaman_detach --keepdb`
  - `[grep-1]` `grep -n '"config.contexto.empresa"' config/settings/base.py`
  - `[grep-1]` `grep -n '"config.apps.AdminDetachConfig"' config/settings/base.py`
  - `[grep-0]` `grep -n "https://macontrol.com.ar" config/settings/base.py config/settings/prod.py`
  - `[grep-1]` `grep -n "^NOMBRE_EMPRESA=" .env.example`
  - `[grep-1]` `grep -n "^CORREO_CONTACTO=" .env.example`
  - `[grep-1]` `grep -n "title: API de Detach" docs/api/openapi-v1.yaml`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T1`

### T2 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. `verificador`, `verificador-b` y `auditor-seguridad` sobre T1 (commits `T1:` en `plan/separacion-web`).
  2. `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb` en verde sobre la rama.
  3. Crear T3 y T4 con `bash .claude/hooks/worktree-crear.sh separacion-web T<n> plan/separacion-web`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q " T1: .*NOMBRE_EMPRESA"`

### T3 — Sitios: página pública del QR, contenido del QR y User-Agent

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `apps/sitios/publico_views.py` (nuevo), `apps/sitios/publico_urls.py` (nuevo), `apps/sitios/templates/sitios/publico/qr.html` (nuevo), `apps/sitios/qr.py`, `apps/sitios/geocodificacion.py`, `apps/sitios/templates/sitios/panel/*.html`, `apps/sitios/tests/test_publico.py` (nuevo), `apps/sitios/tests/test_geocodificacion.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/urls.py`, `apps/sitios/panel_urls.py`, `apps/sitios/api_urls.py`, `apps/sitios/migrations/`, otras apps, `templates/`, `static/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; `.agents/skills/django-conventions/SKILL.md` § Views/URLs
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `publico_urls.py`: `app_name = "publico"`, `path("q/<uuid:codigo>/", publico_views.qr, name="qr")`. La vista no consulta la base ni muestra el código.
  - `qr.html` extiende `base.html`, `{% block tema %}claro{% endblock %}`, `<meta name="robots" content="noindex">` y `css/panel.css` en `extra_head`, logo con `alt="{{ NOMBRE_EMPRESA }}"` y el texto exacto `Punto de control de {{ NOMBRE_EMPRESA }} — use la app` (con el valor por defecto coincide con lo que esperan los tests actuales de `apps/web`).
  - `contenido_qr`: `settings.SITE_URL + reverse("qr", urlconf="apps.sitios.publico_urls", args=[...])`.
  - `geocodificacion.py`: User-Agent calculado al consultar, `Detach/1.0 (+<SITE_URL>; <CORREO_CONTACTO>)`; adaptar el test existente.
  - `· MAControl` → `· Detach` en los títulos de las plantillas de panel de sitios. `test_publico.py` monta `publico_urls` con `override_settings(ROOT_URLCONF=__name__)`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_publico.PaginaQRTests.test_q_uuid_muestra_nombre_empresa_sin_consultar_la_base --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_publico.PaginaQRTests.test_q_no_uuid_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_publico.PaginaQRTests.test_pagina_qr_es_noindex_y_no_expone_el_codigo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_publico.ContenidoQRTests.test_contenido_no_depende_de_la_urlconf_raiz --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_geocodificacion.GeocodificacionTests.test_user_agent_usa_producto_y_correo_de_settings --keepdb`
  - `[grep-1]` `grep -n 'app_name = "publico"' apps/sitios/publico_urls.py`
  - `[grep-0]` `grep -n "web:" apps/sitios/qr.py`
  - `[grep-0]` `grep -rIli macontrol apps/sitios --exclude-dir=__pycache__`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T3`

### T4 — Marca en accounts, clientes, productos y visitas

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `apps/accounts/admin.py`, `apps/accounts/tests/test_admin_marca.py` (nuevo), `apps/clientes/models.py` (solo el docstring), `apps/clientes/templates/clientes/panel/*.html`, `apps/productos/templates/productos/panel/*.html`, `apps/visitas/tests/test_admin.py`, `apps/visitas/tests/test_fotos.py`, `apps/visitas/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `config/`, migraciones, `apps/*/urls.py`, `apps/sitios/`, `apps/panel/`, `apps/api/`, `templates/`, `static/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**:
  - Los fieldsets propios de `CuentaAdmin` se titulan con `settings.NOMBRE_EMPRESA`.
  - Docstring de `Cliente`: "a la que la empresa presta servicios".
  - `· MAControl` → `· Detach` en los títulos de clientes y productos; prefijos de `tempfile` `macontrol-` → `detach-` en los tests de visitas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_admin_marca.CuentaAdminMarcaTests.test_seccion_propia_lleva_nombre_de_la_empresa --keepdb`
  - `[grep-0]` `grep -rIli macontrol apps/accounts apps/clientes apps/productos apps/visitas --exclude-dir=__pycache__`
  - `[grep-1]` `grep -rln "· Detach" apps/clientes/templates`
  - `[grep-1]` `grep -rln "· Detach" apps/productos/templates`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts apps.clientes apps.productos apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T4`

### T5 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T3 y T4)
- **Depende de**: T3, T4
- **Pasos**:
  1. Revisar `cambios.sh` de T3 y T4.
  2. Desde la raíz: `bash .claude/hooks/worktree-integrar.sh separacion-web T3 plan/separacion-web apps/sitios` y `bash .claude/hooks/worktree-integrar.sh separacion-web T4 plan/separacion-web apps/accounts apps/clientes apps/productos apps/visitas`.
  3. Commit `T5: monta /q/ de apps.sitios`: en `config/urls.py`, `path("", include("apps.sitios.publico_urls"))` **antes** de `apps.web.urls`; `manage.py test --keepdb` en verde (los tests de QR de `apps/web` pasan con la página nueva).
  4. `verificador`, `verificador-b` y `auditor-seguridad` sobre T3, T4 y T5; presentar las decisiones de la ola.
  5. Crear T6 (`worktree-crear.sh separacion-web T6 plan/separacion-web`) y commitear **en su rama**, con `git -C worktrees/separacion-web-T6`, `T7: desconecta apps.web de config y routers`: quita `"apps.web"` de `INSTALLED_APPS`, reemplaza en `config/urls.py` `include("apps.web.urls")` por `path("", RedirectView.as_view(pattern_name="panel:ingresar", permanent=False))`, y quita las líneas `web/` de `apps/panel/urls.py` y `apps/api/urls.py`. T6 arranca con la suite en rojo a propósito.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 20 --subtarea T5`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q "T3: integra separacion-web-T3"`
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q "T4: integra separacion-web-T4"`
  - `[grep-1]` `grep -n 'include("apps.sitios.publico_urls")' config/urls.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 20 --subtarea T5`

### T6 — Quitar el sitio público (transversal, diseño y web)

- **Ola**: 3
- **Depende de**: T5 y el commit `T7:` del principal, que es la base de su rama (los criterios de raíz → login, `/panel/web/` → 404 y los `test_routers` necesitan ese commit; `config/` y `apps/*/urls.py` siguen fuera de lo que T6 puede tocar)
- **Puede tocar**: se borran `apps/web/**`, `templates/web/**`, `static/css/web.css`, `static/img/hero-pulverizacion-quincho.webp`, `static/img/empresa-oficina-equipo.webp`, `static/img/mantenimiento-fachada-andamio.webp`, `static/img/fumigacion-termonebulizacion-cocina.webp`, `static/img/flota-vehiculos-industria.webp`; diseño: `templates/base.html`, `templates/panel/base.html`, `templates/panel/ingresar.html`, `templates/404.html` (nuevo), `templates/500.html` (nuevo), `static/css/panel.css`; transversal: `apps/panel/**` salvo `urls.py`, `apps/api/**` salvo `urls.py`; `docs/contrato-api.md` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/panel/urls.py`, `apps/api/urls.py`, `apps/servicios/**`, `apps/sitios/**`, las demás apps, `static/img/logo.png`, `static/fonts/**`, `herramientas/`, `demo.bat`, los demás `docs/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; `.agents/skills/django-conventions/SKILL.md` § Templates y Testing
- **Presupuesto**: 550 líneas agregadas
- **Qué hacer**:
  - Borrar lo listado. `cargar_demo` no importa `apps.web` y reemplaza `loaddata contenido_inicial` por `loaddata tipos_servicio` solo si `not TipoServicio.objects.exists()`; `demo_datos.py` deja de citar `docs/00-contenido-fuente.md`; en `test_cargar_demo` se quitan `PaginaServicio` y `test_carga_contenido_inicial_solo_si_faltan_paginas`, `test_clientes_salen_de_la_carta` deja de leer `docs/00`, y se agregan los dos tests nuevos de abajo. Quitar `"web"` de los dos `test_routers` y lo de web en `test_acceso`.
  - Tests que se mudan a `apps/panel/tests/` (archivos nuevos): `test_rutas.py` (panel anónimo → login, `/api/v1/` anónimo 401, más los nuevos: raíz 302 a `/panel/ingresar/`; `/q/<uuid>/` resuelve a `publico:qr` y responde 200 con `NOMBRE_EMPRESA`; `urlparse(contenido_qr(punto)).path` resuelve a `publico:qr`; `/empresa/`, `/contacto/`, `/servicio/x/`, `/sitemap.xml`, `/robots.txt` y `/panel/web/` dan 404), `test_errores.py`, `test_plantilla_base.py`, `test_cabeceras.py` y `test_csp.py` (contra `/panel/ingresar/` en lugar de `/`; la clase nueva `CspPanelTests` prueba la CSP con nonce en el login del panel). Los tests mudados conservan su nombre y los cubre el `[cmd]` de `apps.panel`; solo los de comportamiento nuevo son `[test]`.
  - `templates/404.html` y `500.html` autónomas, `noindex`, con `css/panel.css` y la clase `.pagina-error` (colores en `panel.css`); la 500 sin variables de contexto. `base.html`: solo tema claro (sin bloque oscuro ni comentario "sitio público"), `<title>` por defecto "Detach", `alt="{{ NOMBRE_EMPRESA }}"`, `<meta name="robots" content="noindex, nofollow">`. `panel/base.html` e `ingresar.html`: "Panel · Detach", "Ingresar · Detach", `<h1>` "Ingresar a Detach", `alt` con `NOMBRE_EMPRESA`. Títulos de `tablero.html`, `mapa.html`; prefijos `tempfile` de `test_recorrido.py` y `test_cargar_demo.py`.
  - `docs/contrato-api.md` (resumen legible para la app que remite a `docs/api/openapi-v1.yaml` como fuente completa; agrega throttle y rol por ruta): línea `Actualizado: AAAA-MM-DD`, tabla `| Método | Ruta | Auth | Throttle | Respuesta |` con una fila por cada una de las 18 rutas (ruta entre comillas invertidas, parámetros como `<pk>` o `<codigo>`). `apps/api/tests/test_contrato_doc.py` compara ese conjunto con las rutas resueltas bajo `/api/v1/` (normalizando `<int:pk>` a `<pk>`) y exige que ninguna celda esté vacía.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_rutas.RutasTests.test_raiz_redirige_al_login --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_rutas.RutasTests.test_q_uuid_lo_sirve_sitios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_rutas.RutasTests.test_contenido_del_qr_abre_la_pagina_de_sitios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_rutas.RutasTests.test_rutas_del_sitio_publico_dan_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_errores.ErroresTests.test_404_y_500_sin_marca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_plantilla_base.BaseTemplateTests.test_titulo_es_detach_y_logo_lleva_nombre_empresa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_plantilla_base.BaseTemplateTests.test_base_es_noindex_y_de_un_solo_tema --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_csp.CspPanelTests.test_ingresar_del_panel_lleva_csp_con_nonce --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTests.test_no_carga_contenido_del_sitio_publico --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTests.test_carga_tipos_de_servicio_si_no_hay --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_contrato_doc.ContratoDocTests.test_rutas_del_contrato_coinciden_con_las_de_la_api --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_contrato_doc.ContratoDocTests.test_cada_ruta_declara_metodo_auth_throttle_y_respuesta --keepdb`
  - `[cmd]` `test -z "$(git ls-files apps/web templates/web static/css/web.css 'static/img/*.webp')"`
  - `[existe]` `templates/404.html`
  - `[existe]` `templates/500.html`
  - `[existe]` `docs/contrato-api.md`
  - `[existe]` `static/img/logo.png`
  - `[existe]` `static/fonts/barlow-latin-600-normal.woff2`
  - `[grep-1]` `grep -nE "^Actualizado: [0-9]{4}-[0-9]{2}-[0-9]{2}" docs/contrato-api.md`
  - `[grep-0]` `grep -rIn "apps\.web\|apps/web\|00-contenido-fuente" apps templates --exclude-dir=__pycache__`
  - `[grep-0]` `grep -n '"web"' apps/panel/tests/test_routers.py apps/api/tests/test_routers.py`
  - `[grep-0]` `grep -n "oscuro" templates/base.html`
  - `[grep-0]` `grep -rIli macontrol apps/panel apps/api templates static --exclude='demo*' --exclude-dir=__pycache__`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel apps.api --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 550 --subtarea T6`

### T7 — Integración ola 3 (principal)

- **Ola**: 3 (después de verificar T6)
- **Depende de**: T6 (el commit `T7:` ya está en la rama de T6, ver T5 paso 5)
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh` de T6 contra el commit `T7:` (no contra `plan/separacion-web`): lo de `config/` y `apps/*/urls.py` es del principal y queda fuera de lo atribuible a T6.
  2. Desde la raíz: `bash .claude/hooks/worktree-integrar.sh separacion-web T6 plan/separacion-web apps/web apps/panel apps/api templates static/css static/img docs/contrato-api.md config/urls.py config/settings/base.py`.
  3. `verificador`, `verificador-b` y `auditor-seguridad` sobre T6 y T7; presentar las decisiones de la ola.
  4. Crear T8, T9 y T10.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 30 --subtarea T7`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q "T6: integra separacion-web-T6"`
  - `[grep-0]` `grep -rIn "apps\.web" config --exclude-dir=__pycache__`
  - `[grep-0]` `grep -n "apps.web" apps/panel/urls.py apps/api/urls.py`
  - `[grep-1]` `grep -n 'RedirectView.as_view(pattern_name="panel:ingresar", permanent=False)' config/urls.py`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 30 --subtarea T7`

### T8 — Servicios: quitar `TipoServicio.descripcion`

- **Ola**: 4
- **Depende de**: T7
- **Puede tocar**: `apps/servicios/models.py`, `apps/servicios/migrations/0004_*.py` (generada con `makemigrations`), `apps/servicios/fixtures/tipos_servicio.json`, `apps/servicios/templates/servicios/panel/*.html`, `apps/servicios/tests/test_sin_descripcion.py` (nuevo)
- **No puede tocar**: `docs/planes/`, `config/`, migraciones existentes, `apps/servicios/urls.py`, otras apps
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; `.agents/skills/django-conventions/SKILL.md` § Models
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**: quitar el campo y generar la migración; quitar `descripcion` de los 9 objetos del fixture; `· MAControl` → `· Detach` en los títulos; tests nuevos en `SinDescripcionTests`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_sin_descripcion.SinDescripcionTests.test_tipo_servicio_no_tiene_descripcion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_sin_descripcion.SinDescripcionTests.test_fixture_tipos_servicio_carga_los_nueve --keepdb`
  - `[grep-1]` `grep -l "RemoveField" apps/servicios/migrations/0004_*.py`
  - `[grep-0]` `grep -n "descripcion" apps/servicios/models.py apps/servicios/fixtures/tipos_servicio.json`
  - `[grep-0]` `grep -rIli macontrol apps/servicios --exclude-dir=__pycache__`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T8`

### T9 — Demo: nombre del paquete, textos y humo con `/` → login

- **Ola**: 4
- **Depende de**: T7
- **Puede tocar**: `herramientas/empaquetar_demo.py`, `herramientas/humo_demo.py`, `demo.bat`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/`, `templates/`, `static/`, `docs/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; `.agents/skills/python-best-practices/SKILL.md` (subprocess)
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**: `NOMBRE_PAQUETE = "detach-demo"` y textos (docstring, `LEEME`, `demo.bat` portátil) con Detach; en `demo.bat` de la raíz, comentario con Detach y sin la línea "Sitio publico"; `humo_demo.py`: el primer chequeo pasa a `GET / -> 302 al login` con el abridor sin redirección y `Location` con `/panel/ingresar/`.
- **Criterios**:
  - `[cmd]` `./venv/Scripts/python.exe herramientas/empaquetar_demo.py --sin-descarga --destino dist/prueba-separacion-T9 && ./venv/Scripts/python.exe herramientas/humo_demo.py dist/prueba-separacion-T9/detach-demo`
  - `[grep-1]` `grep -n 'NOMBRE_PAQUETE = "detach-demo"' herramientas/empaquetar_demo.py`
  - `[grep-1]` `grep -n "GET / -> 302 al login" herramientas/humo_demo.py`
  - `[grep-0]` `grep -ni "macontrol\|sitio publico" herramientas/empaquetar_demo.py herramientas/humo_demo.py demo.bat`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T9`

### T10 — Documentación: Detach, sin sitio público

- **Ola**: 4
- **Depende de**: T7
- **Puede tocar**: `CLAUDE.md`, `README.md` (nuevo), `.claude/skills/convenciones-proyecto/SKILL.md`, `.claude/agents/verificador.md`, `.claude/agents/verificador-b.md`, `.claude/agents/refutador.md`, `.claude/agents/juez-plan.md`, `.claude/agents/implementador.md`, `.claude/agents/auditor-seguridad.md`, `docs/01-modelo-y-arquitectura.md`, `docs/02-diseno.md`, `docs/demo-cliente.md`, `docs/despliegue.md`, `docs/00-contenido-fuente.md` (se borra)
- **No puede tocar**: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `docs/contrato-api.md`, `docs/api/`, código
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - `CLAUDE.md`: "Detach" en lugar de MAControl; navegación sin `00` y con `docs/contrato-api.md`; `02` acotado al panel; la regla 7 pasa a "Datos de la empresa: el nombre sale de `NOMBRE_EMPRESA`; ninguna plantilla ni código escribe el nombre de una empresa"; el sitio público vive en otro repositorio.
  - Skill: qué es, estructura (sin `web/`; `publico_views.py` y `publico_urls.py` en sitios), mapa de rutas (`/` → login; `/q/<uuid>/` en `apps.sitios`), variables (`NOMBRE_EMPRESA`, `CORREO_CONTACTO`, `SITE_URL` obligatoria en producción), prohibiciones y tabla de propiedad sin el sitio público. Agentes: nombre del proyecto y referencias a `docs/00` y `apps.web`.
  - `README.md`: qué es Detach, arranque con los comandos canónicos, la demo, el contrato de la API y el aviso de `migrate web zero` para bases anteriores.
  - `docs/01`: §3.3 sin `descripcion`, §3.10 con los datos legales del certificado sin modelo, se quitan §3.12, la fila de la web, `web/` del árbol y las menciones del sitio. `docs/02`: tokens claros, tipografía y componentes del panel, sin páginas web ni tema oscuro. `docs/demo-cliente.md`: sin el recorrido del sitio. `docs/despliegue.md`: `NOMBRE_EMPRESA`, `CORREO_CONTACTO`, `SITE_URL` obligatoria.
- **Criterios**:
  - `[no-existe]` `docs/00-contenido-fuente.md`
  - `[grep-1]` `grep -n "^# Detach" README.md`
  - `[grep-1]` `grep -n "docs/contrato-api.md" CLAUDE.md`
  - `[grep-1]` `grep -n "NOMBRE_EMPRESA" CLAUDE.md`
  - `[grep-1]` `grep -n "NOMBRE_EMPRESA" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-0]` `grep -rIli macontrol CLAUDE.md README.md .claude/agents .claude/skills/convenciones-proyecto docs/02-diseno.md docs/demo-cliente.md`
  - `[grep-0]` `grep -rIn "00-contenido-fuente\|apps/web\|apps\.web" CLAUDE.md README.md .claude/agents .claude/skills/convenciones-proyecto docs/01-modelo-y-arquitectura.md docs/02-diseno.md docs/demo-cliente.md`
  - `[grep-0]` `grep -n "Contenido real\|Tema oscuro" CLAUDE.md docs/02-diseno.md`
  - `[grep-0]` `grep -n "Sitio público\|/empresa/\|/contacto/" docs/demo-cliente.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T10`

### T11 — Integración ola 4 y cierre (principal)

- **Ola**: 4 (después de verificar T8, T9 y T10)
- **Depende de**: T8, T9, T10
- **Pasos**:
  1. Revisar `cambios.sh` de T8, T9 y T10.
  2. Desde la raíz: `worktree-integrar.sh separacion-web T8 plan/separacion-web apps/servicios`; `… T9 … herramientas demo.bat`; `… T10 … CLAUDE.md README.md .claude/agents .claude/skills/convenciones-proyecto docs/00-contenido-fuente.md docs/01-modelo-y-arquitectura.md docs/02-diseno.md docs/demo-cliente.md docs/despliegue.md`.
  3. En la raíz, si `find apps/web -type f -not -name '*.pyc'` no devuelve nada, borrar los `__pycache__` residuales de `apps/web` (el `[no-existe]` del cierre lo exige).
  4. Al cierre, `docs/bitacora.md`: `00-contenido-fuente.md` y la parte web de `02-diseno.md` se movieron a `../macontrol-web`; aviso de `migrate web zero` antes de actualizar. Completar `### Cierra` con: P-sitio-publico-1, -2, -4, -5, -6, -7 (sigue como P-separacion-web-1), -8, -10, -11, -12, -14, -15; P-demo-cliente-8; P-robustez-panel-4, -5; P-pendientes-heredados-31.
  5. `verificador`, `verificador-b` y `auditor-seguridad` sobre `TODO`. El merge a `main` lo decide el usuario.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q "T8: integra separacion-web-T8"`
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q "T9: integra separacion-web-T9"`
  - `[cmd]` `git log --oneline plan/separacion-web | grep -q "T10: integra separacion-web-T10"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-18-separacion-web.md separacion-web`
- `[no-existe]` `apps/web`
- `[no-existe]` `docs/00-contenido-fuente.md`
- `[cmd]` `test -z "$(git ls-files templates/web static/css/web.css 'static/img/*.webp')"`
- `[existe]` `static/img/logo.png`
- `[existe]` `docs/contrato-api.md`
- `[grep-0]` `grep -rIn "apps\.web" config --exclude-dir=__pycache__`
- `[grep-0]` `grep -rIli macontrol apps templates static --exclude='demo*' --exclude-dir=__pycache__`
- `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
- `[cmd]` `./venv/Scripts/python.exe herramientas/empaquetar_demo.py --sin-descarga --destino dist/prueba-separacion-cierre && ./venv/Scripts/python.exe herramientas/humo_demo.py dist/prueba-separacion-cierre/detach-demo`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): separacion-web — modificado: <motivo>`. -->

commit_base: b7dfb6a

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | en curso (pasos 1-4 hechos; falta el 5: crear T6 y su commit `T7:`) |
| T6 | pendiente |
| T7 | pendiente |
| T8 | pendiente |
| T9 | pendiente |
| T10 | pendiente |
| T11 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-18 | juez-plan ronda 1 | (sin commit) | RECHAZADO | 2 bloqueantes (T3 con apps.web; T1 delegada con config/), corregidos |
| 2026-10-18 | juez-plan ronda 2 | (sin commit) | RECHAZADO | 1 bloqueante (criterio de T2 pasaba siempre), corregido a `" T1: .*NOMBRE_EMPRESA"` sin tercera ronda; observación menor abierta: `--exclude='demo*'` |
| 2026-10-18 | T1, T2 (verificador) | 4a01cd8 | PASA 15/15 | suite completa (paso 2 de T2): 675 tests OK |
| 2026-10-18 | T1, T2 (verificador-b) | 4a01cd8 | PASA 15/15 | |
| 2026-10-18 | T1 (auditor-seguridad) | 4a01cd8 | sin bloqueantes | 1 menor (P-separacion-web-2), 3 observaciones (P-separacion-web-3) |
| 2026-10-18 | T2 paso 3 | 4a01cd8 | — | `worktree-crear.sh` T3 y T4: exit 0, `manage.py check` sin problemas |
| 2026-10-18 | T3, T4 (integración) | fa310e2 | — | `worktree-integrar.sh` T3 exit 0 (679 tests OK) y T4 exit 0 (681 tests OK); revisión previa con `cambios.sh` y spot check de un `[test]` de cada una |
| 2026-10-18 | T3, T4, T5 (verificador) | dc31bc4 | PASA 20/20 | suite completa (paso 3 de T5): 681 tests OK |
| 2026-10-18 | T3, T4, T5 (verificador-b) | dc31bc4 | PASA 20/20 | |
| 2026-10-18 | T3, T4, T5 (auditor-seguridad) | dc31bc4 | sin hallazgos | 2 observaciones (P-separacion-web-5) |

## Pendientes que deja este plan

### Problemas

- P-separacion-web-1 [importante] Los datos legales, habilitaciones y director técnico del certificado (`docs/01-modelo-y-arquitectura.md` §3.10) no tienen modelo desde que se quita `web.Configuracion`; van al plan multiempresa.
- P-separacion-web-2 [menor] `prod.py` solo rechaza `SITE_URL` vacía: con `http://…`, sin esquema o `localhost` producción arranca y los QR impresos quedarían en texto plano o sin abrir; exigir origen `https` sin ruta (auditor-seguridad T1, PLAUSIBLE).
- P-separacion-web-3 [observación] Sin `SITE_URL`, los QR de la demo pasan de `https://macontrol.com.ar/q/…` a `http://localhost:8000/q/…`, que un teléfono de la red tampoco abre; se podría fijar `SITE_URL=http://<IP>:8000` en `demo.bat` y `empaquetar_demo.py` (T9, decisión de producto). `docs/despliegue.md` (T10) debe avisar que sin `SITE_URL` falla también el build de Railway. T3, T4 y T6 no deben envolver `NOMBRE_EMPRESA` con `|safe`/`mark_safe`.
- P-separacion-web-5 [observación] Al quitar `apps.web` (T6) desaparece `robots.txt` y con él `Disallow: /q/`; solo queda el `<meta name="robots" content="noindex">` de `sitios/publico/qr.html`. El auditor sugiere `X-Robots-Tag: noindex` en `apps/sitios/publico_views.py::qr` (fuera de lo que T6 puede tocar). `web:qr` y su vista quedan sin uso hasta T6.
- P-separacion-web-6 [observación] `/q/` muestra dos logos (el de la cabecera de `templates/base.html` y el de `qr.html`); T6 cambia el `alt` de la cabecera a `NOMBRE_EMPRESA`, pero el logo duplicado sigue (implementador T3).
- P-separacion-web-4 [observación] `docs/bitacora.md` mezcla finales CRLF y CR desde 8325925 y su línea `Plan activo:` apunta a `2026-10-17-separacion-web.md`, que no existe.

### Decisiones

- 2026-10-18 — `NOMBRE_EMPRESA`, `CORREO_CONTACTO` y `SITE_URL` se recortan (`.strip()`) y con solo espacios caen al valor por defecto; `DESCRIPTION` de la API quita el punto final del nombre para no dejar `S.A..` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-18 — El User-Agent de Nominatim es la función `geocodificacion.user_agent()` (se evalúa en cada consulta) en lugar de la constante `USER_AGENT` — así toma `SITE_URL` y `CORREO_CONTACTO` vigentes y se prueba con `override_settings` — decidida por Claude (implementador T3), revisable — reemplaza a: (nada)
- 2026-10-18 — `CuentaAdmin` deja `""` como título estático de la sección propia y `get_fieldsets` le pone `settings.NOMBRE_EMPRESA` en cada llamada — un título calculado al importar no seguiría a `override_settings` ni a un cambio de entorno sin reinicio — decidida por Claude (implementador T4), revisable — reemplaza a: (nada)

### Cierra
