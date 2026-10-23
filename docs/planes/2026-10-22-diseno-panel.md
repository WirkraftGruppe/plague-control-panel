# Plan: Rediseño visual y de navegación del panel

- **slug**: `diseno-panel`
- **fecha**: 2026-10-22
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): diseno-panel`. No se escribe acá: el hash se anota en `## Registro de verificación`.
- **objetivo**: el panel usa el sistema visual neutro de Detach y, al entrar, el administrador ve en `/panel/sitios/` los turnos de hoy, lo que requiere atención y todos los sitios ordenados por próximo vencimiento; crea turnos desde un panel lateral sin salir de la página.
- **fuera de alcance**: subida de logo por empresa (`multiempresa`); indicaciones para el operario y pestaña de certificados; cambios de modelo, de reglas de negocio o de la API (ninguna migración); P-ajustes-flujo-1 a -4 (`robustez-listados`); modo oscuro, celular, tablet y sitio público.
- **áreas**: panel
- **seguridad**: sí — rehace la plantilla del login del panel, agrega una respuesta parcial por HTMX a una vista de administrador (nuevo turno) y muestra datos personales (responsable, contacto, operario) en pantallas nuevas. No cambia permisos ni rutas: todas siguen detrás de `AdministradorRequeridoMixin` y `AccesoTests` las recorre. `auditor-seguridad` corre sobre T1, T4 y T5 y en el cierre.

## Contexto mínimo

- Tokens y `@font-face` viven en el `<style nonce>` de `templates/base.html` (`--brand #ffc600`, Barlow Condensed en h1–h3); componentes en `static/css/panel.css` (257 líneas) y `apps/sitios/static/sitios/puntos.css`; `apps/panel/static/panel/mapa.js:7` repite el amarillo. `docs/02-diseno.md` describe la dirección "Industrial certificada".
- `templates/panel/base.html`: menú plano sin ítem activo; "Catálogo" es un encabezado con dos subítems (flujo-sitio T8); usuario y Salir en la cabecera; `{% block tema %}` muerto. El contador de incidencias es `incidencias_sin_revisar` (`apps/visitas/templatetags/visitas_ui.py:11`).
- `SitioListado` (`apps/sitios/panel_views.py:56`) lista sin estado ni vencimiento. `apps/sitios/estado.py` tiene `estado_por_vencimiento` (umbral 7 días). `SitioFicha` (línea 119) usa pestañas `mapa|planos|puntos`.
- `NuevoTurnoView` (`apps/visitas/panel_views.py:241`, `panel:visitas:nuevo_turno`) es página completa con `FormularioTurno` y `apps/visitas/static/visitas/nuevo_turno.js` (Leaflet `CRS.Simple`); llama a `crear_turno` (`apps/visitas/services.py:317`). `ListadoVisitas` (línea 55) es una tabla paginada con filtros.
- CSP (`config/settings/base.py:261`): `script-src 'self'` sin nonce, `style-src 'self' nonce`; HTMX 2.0.11 y Leaflet 1.9.4 ya vendorizados en `static/vendor/`. No hay `django-htmx`: se detecta `HX-Request` como en `apps/panel/listados.py:41`.
- Decisiones del usuario (2026-10-22): `--text-faint` pasa a `#646C76` (el `#6B737D` aprobado da 4,44:1 sobre `#F5F6F7`); los turnos pendientes atrasados van primero en "Hoy" con chip "Atrasado"; los cancelados van en "Realizados".
- Decisión de diseño: T1 conserva los nombres de clase actuales (`.boton`, `.boton-primario`, `.tabla`, `.etiqueta-estado`, `.etiqueta-ok|warn|danger|neutral`, `.formulario`, `.mensaje-*`, `.pestanas`) y los reestiliza, para que clientes, usuarios y catálogo tomen el sistema nuevo sin reescribir plantillas.

## Olas

Sin migraciones. Las olas siguen la propiedad de archivos: la ola 1 fija tokens, componentes y la base del panel; la ola 2 consume esos componentes por app.

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración: T2 antes que T1) | ninguna |
| 2 | T4, T5, T6, T7, T9, T10, T11, T8 (integración) | ninguna |

## Subtareas

### T1 — Tokens, componentes y barra lateral del panel

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `templates/**` (base, panel/base, panel/ingresar, panel/partials/**, 404, 500), `static/css/**`, `static/fonts/barlow-condensed-*`, `apps/panel/templates/**`, `apps/panel/static/**`, `apps/panel/templatetags/**`, `apps/panel/tests/**`
- **No puede tocar**: `docs/planes/`, `apps/panel/urls.py`, `apps/panel/views.py`, `apps/panel/listados.py`, `config/`, `apps/*/templates/` de otras apps, `apps/sitios/**`, `apps/visitas/**`, `static/vendor/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (prohibiciones y CSP); `.agents/skills/` de Django templates si existe
- **Worktree**: sí
- **Presupuesto**: 1200 líneas agregadas
- **Qué hacer**:
  - `templates/base.html`: tokens del Adjunto en `:root` con estos nombres: `--bg #F5F6F7`, `--surface #FFFFFF`, `--surface-2 #EEF0F2`, `--border #DFE2E6`, `--border-strong #C5CAD1`, `--text #1A1E23`, `--text-muted #545C66`, `--text-faint #646C76`, `--accion #1F5FD1`, `--accion-hover #174AA6`, `--sobre-accion #FFFFFF`, `--activo-fondo #EAF1FD`, `--activo-texto #1F5FD1`; vencido `--vencido-punto #D92D20`, `--vencido-fondo #FDECEA`, `--vencido-texto #B42318`; próximo (7 días o menos) `--proximo-punto #E0A100`, `--proximo-fondo #FFF4D6`, `--proximo-texto #7A4F00`; al día `--al-dia-punto #2E9E5B`, `--al-dia-fondo #E6F4EC`, `--al-dia-texto #1B6B3C`; sin fecha `--sin-fecha-punto #9AA1A9`, `--sin-fecha-fondo #EEF0F2`, `--sin-fecha-texto #4A525B`; `--radio-control 6px`, `--radio-bloque 8px`, `--radio-chip 999px`, `--ancho-barra 232px`. Solo Barlow 400/500/600/700; se quitan los `@font-face` y los archivos de Barlow Condensed, `data-tema` y `--brand*`.
  - `static/css/panel.css`: reescritura con los mismos nombres de clase (ver Contexto) más barra lateral con grupos, chips de estado (rojo, ámbar, verde y gris siempre con texto), pestañas (`.pestanas a[aria-current="page"]`), avisos, controles de 36 a 46 px, `.pagina-error` con tokens y el panel lateral `#panel-lateral` (fijo a la derecha, pie fijo `.panel-lateral-pie`). Ancho mínimo 1280 px; se quita el breakpoint de 900 px.
  - `templates/panel/base.html`: slot de logo (`static/img/logo.png`, `alt="{{ NOMBRE_EMPRESA }}"`); grupo "Trabajo" (Sitios con contador de sitios vencidos, Turnos con contador de incidencias, Mapa) y grupo "Administración" (Clientes, Catálogo → `panel:servicios:listado`, Usuarios) con menor peso; `aria-current="page"` según `request.resolver_match.namespaces` (Catálogo activo en `servicios` y `productos`); pie con usuario, Salir (POST) y "Detach"; contenedor `<div id="panel-lateral" role="dialog" aria-modal="true" hidden>`; se borra `{% block tema %}`.
  - Etiqueta `sitios_vencidos` en `apps/panel/templatetags/panel_ui.py`: cantidad de sitios activos con algún punto activo de `proximo_vencimiento` < hoy, en una consulta.
  - `apps/panel/static/panel/panel_lateral.js`: abre `#panel-lateral` tras un swap de HTMX iniciado por un elemento `[data-abre-panel]`, enfoca su primer control, cierra con Escape, `[data-cierra-panel]` (botón cerrar y Cancelar) vaciando el contenedor, y devuelve el foco al botón que lo abrió. Se carga desde `templates/panel/base.html`.
  - Parcial `templates/panel/partials/pestanas_catalogo.html` (pestañas Servicios y Productos con `aria-current` según el namespace), para que T5 lo incluya.
  - Login, 404, 500, `panel/mapa.html` y `mapa.js` con los tokens nuevos (colores de estado del Adjunto). La 500 sigue sin consultas.
  - Clase `.formulario-en-linea` en `panel.css` (formulario de un botón dentro de una fila de tabla), para que T6 reemplace los `style="display:inline"`.
  - La suite completa no se corre en el worktree de T1: `apps/visitas/tests/test_panel_menu.py` recién queda compatible al integrar T2 antes que T1 (T3), y `worktree-integrar.sh` corre ahí todos los tests.
  - El contador de incidencias conserva el marcado `class="contador-menu">N<` (lo afirma `apps/visitas/tests/test_panel_menu.py`).
  - Actualizar los tests de `apps/panel/tests/` que afirman el sistema viejo (`test_plantilla_base.py`, incluido el mínimo de URLs de `test_fuentes_referenciadas_existen`; `test_diseno.py`; `test_base.py`).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno_tokens.ContrasteTokensTests.test_textos_sobre_fondos_cumplen_4_5 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno_tokens.ContrasteTokensTests.test_chips_de_estado_cumplen_4_5 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno_tokens.ContrasteTokensTests.test_accion_y_menu_activo_cumplen_4_5 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno_tokens.ContrasteTokensTests.test_tokens_del_adjunto_en_base --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_menu.MenuActivoTests.test_cada_ruta_marca_solo_su_entrada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_menu.MenuActivoTests.test_servicios_y_productos_marcan_catalogo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_menu.MenuActivoTests.test_grupos_trabajo_y_administracion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_menu.MenuActivoTests.test_contador_de_sitios_vencidos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_menu.MenuActivoTests.test_logo_con_alt_nombre_empresa_y_pie_con_salir --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_menu.MenuActivoTests.test_base_trae_contenedor_y_script_del_panel_lateral --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_acceso.AccesoTests.test_rutas_del_rediseno_estan_cubiertas --keepdb`
  - `[grep-0]` `grep -rniE "#ffc600|--brand|barlow condensed" --include=*.html --include=*.css --include=*.js templates static/css apps/panel`
  - `[grep-0]` `grep -n "block tema" templates/panel/base.html`
  - `[no-existe]` `static/fonts/barlow-condensed-latin-600-normal.woff2`
  - `[no-existe]` `static/fonts/barlow-condensed-latin-700-normal.woff2`
  - `[no-existe]` `static/fonts/barlow-condensed-latin-800-normal.woff2`
  - `[existe]` `templates/panel/partials/pestanas_catalogo.html`
  - `[existe]` `apps/panel/static/panel/panel_lateral.js`
  - `[grep-1]` `grep -n "\.formulario-en-linea" static/css/panel.css`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel apps.sitios apps.servicios apps.productos apps.accounts apps.clientes --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1200 --subtarea T1`

### T2 — Test del menú de visitas compatible con la barra nueva

- **Ola**: 1 (en paralelo con T1; se integra antes que T1)
- **Depende de**: —
- **Puede tocar**: `apps/visitas/tests/test_panel_menu.py`
- **No puede tocar**: `docs/planes/`, todo lo demás
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Presupuesto**: 40 líneas agregadas
- **Qué hacer**: `MenuTests.test_menu_tiene_las_secciones_nuevas` deja de exigir el `href` de `panel:productos:listado` y los textos "Servicios" y "Productos" en la barra (la barra nueva tiene una sola entrada "Catálogo"; el menú nuevo lo prueba T1 en `apps/panel/tests/test_menu.py`). El test tiene que pasar con la barra actual y con la de T1. `test_contador_de_incidencias_sin_revisar` no cambia. No agrega comportamiento.
- **Criterios**:
  - `[grep-0]` `grep -n "panel:productos:listado" apps/visitas/tests/test_panel_menu.py`
  - `[grep-0]` `grep -nE '"(Servicios|Productos)"' apps/visitas/tests/test_panel_menu.py`
  - `[grep-1]` `grep -n "def test_contador_de_incidencias_sin_revisar" apps/visitas/tests/test_panel_menu.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_menu --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 40 --subtarea T2`

### T3 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/diseno-panel` de T1 y T2, no los informes.
  2. Desde la raíz, primero `bash .claude/hooks/worktree-integrar.sh diseno-panel T2 plan/diseno-panel apps/visitas/tests/test_panel_menu.py` y después `bash .claude/hooks/worktree-integrar.sh diseno-panel T1 plan/diseno-panel templates static apps/panel`.
  3. `auditor-seguridad` sobre T1 (login y panel lateral).
  4. Crear los worktrees de la ola 2 (T4, T5, T6, T7) desde `plan/diseno-panel`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/diseno-panel | grep -q "T2: integra diseno-panel-T2"`
  - `[cmd]` `git log --oneline plan/diseno-panel | grep -q "T1: integra diseno-panel-T1"`

### T4 — Inicio en Sitios y ficha del sitio

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/sitios/panel_views.py`, `apps/sitios/estado.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/static/sitios/**`, `apps/sitios/tests/**`
- **No puede tocar**: `docs/planes/`, `templates/`, `static/`, `apps/panel/**`, `apps/visitas/**`, `apps/sitios/models.py`, `apps/sitios/qr.py`, el sitio público `/q/` (`publico_*`, `templates/sitios/publico/`), la API de sitios, `geocodificacion.py`, cualquier `migrations/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; skill de Django ORM de `.agents/skills/` (§ anotaciones y subconsultas)
- **Worktree**: sí
- **Presupuesto**: 1000 líneas agregadas
- **Qué hacer**:
  - `/panel/sitios/` (`SitioListado`): sección "Turnos de hoy" (visitas pendientes con `programada_para` = hoy, abiertas, o realizadas con `cerrada_en` hoy; operario, puntos revisados / total del turno, chip de estado); "Requieren atención" (sitios activos cuyo mínimo `proximo_vencimiento` de puntos activos es ≤ hoy y sin visita pendiente ni abierta, con "Nuevo turno"; incidencias sin revisar con "Revisar" → ficha de la visita); "Todos los sitios" con filtros `?estado=vencidos|semana|al_dia|sin_fechas` y su conteo, búsqueda, columnas Sitio y cliente, Localidad, Próximo vencimiento, Turno (próximo pendiente o "Sin turno") y "Nuevo turno"; orden por próximo vencimiento ascendente (sin fecha al final). Solo sitios activos, con un enlace "Ver sitios inactivos" (`?activo=0`).
  - El estado del sitio sale del mínimo `proximo_vencimiento` de sus puntos activos (anotación `Min` con filtro): vencido si < hoy; esta semana si ≤ hoy + 7 (`UMBRAL_PROXIMA_DIAS`); al día si es mayor; sin fechas si es nulo. Conteos con una sola agregación. Cantidad de consultas independiente de la cantidad de sitios.
  - Ficha: cabecera (nombre, chip de estado general, cliente, dirección, responsable, contacto; "Editar sitio", "Cargar visita", "Nuevo turno" primaria); debajo dos columnas: plano con puntos numerados por `orden` y coloreados por estado, y lista de puntos (número, nombre, servicio, frecuencia, vencimiento, editar); `apps/sitios/static/sitios/ficha_plano.js` resalta el mismo punto en la otra columna al pasar el mouse (`data-punto`). Pestañas `?pestana=turnos|planos|datos` (por defecto `turnos`; `datos` lleva los datos del sitio y el mapa geográfico). Si no hay turnos pendientes y hay puntos vencidos, la pestaña Turnos muestra un aviso con enlace a nuevo turno.
  - Todo botón "Nuevo turno" (ficha, lista y "Requieren atención") es `<a href="{% url 'panel:visitas:nuevo_turno' sitio.pk %}" hx-get="…" hx-target="#panel-lateral" data-abre-panel>`; la lista y la ficha cargan Leaflet y `visitas/nuevo_turno.js` en `{% block scripts %}`.
  - `puntos.css` sin `--brand`, con los tokens nuevos. Actualizar los tests de `apps/sitios` que afirman la estructura vieja (pestañas `mapa|puntos`, columnas).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_turnos_de_hoy_lista_pendientes_abiertos_y_realizados_hoy --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_conteos_de_cada_filtro --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_contador_de_la_barra_lateral_coincide_con_vencidos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_requieren_atencion_solo_vencidos_sin_turno_pendiente_ni_abierto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_requieren_atencion_lista_incidencias_sin_revisar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_proximo_vencimiento_es_el_minimo_de_puntos_activos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_orden_por_proximo_vencimiento_ascendente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_mismas_consultas_con_5_y_50_sitios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.InicioSitiosTests.test_nuevo_turno_abre_el_panel_lateral --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_rediseno.FichaRedisenoTests.test_cabecera_con_datos_y_acciones --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_rediseno.FichaRedisenoTests.test_plano_y_lista_comparten_numero_de_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_rediseno.FichaRedisenoTests.test_pestanas_turnos_planos_y_datos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_rediseno.FichaRedisenoTests.test_aviso_sin_turnos_con_puntos_vencidos --keepdb`
  - `[grep-0]` `grep -rniE "#ffc600|--brand|barlow condensed" --include=*.html --include=*.css --include=*.js apps/sitios`
  - `[existe]` `apps/sitios/static/sitios/ficha_plano.js`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1000 --subtarea T4`

### T5 — Nuevo turno en panel lateral y Turnos agrupados

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/visitas/panel_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/templates/visitas/panel/**`, `apps/visitas/static/visitas/**`, `apps/visitas/templatetags/**`, `apps/visitas/tests/**`
- **No puede tocar**: `docs/planes/`, `templates/`, `static/`, `apps/panel/**`, `apps/sitios/**`, `apps/visitas/services.py`, `apps/visitas/models.py`, la API de visitas (`api_views.py`, `serializers.py`, `api_urls.py`), fotos, cualquier `migrations/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`; skill de Django forms/views de `.agents/skills/`
- **Worktree**: sí
- **Presupuesto**: 1000 líneas agregadas
- **Qué hacer**:
  - `NuevoTurnoView`: con `HX-Request` renderiza un parcial (`visitas/panel/_nuevo_turno_lateral.html`) para `#panel-lateral`; sin él, la página completa que lo incluye. El POST con HTMX válido responde `HX-Redirect` a la ficha del sitio; con errores devuelve el parcial con errores (status 200 para que HTMX lo inserte); sin HTMX se comporta como hoy. `crear_turno` no cambia.
  - Contenido: operario (responsable del sitio primero), fecha, plano y lista de puntos con todos los activos tildados y el servicio precargado y cambiable; atajos "Todos", "Vencidos y próximos" (reemplaza "Solo vencidos") y "Ninguno"; clic en un marcador suma o quita el punto; pie fijo con resumen en vivo (`aria-live="polite"`: puntos, vencidos, cantidad por servicio); "Crear turno" con `disabled` en el HTML cuando no hay puntos activos; botón cerrar (`aria-label="Cerrar"`) y Cancelar con `data-cierra-panel`.
  - `nuevo_turno.js` se inicializa con `htmx.onLoad` sobre el contenido insertado (y al cargar la página completa) y actualiza el resumen y el `disabled`.
  - `/panel/visitas/` (`ListadoVisitas`): incidencias sin revisar arriba; luego grupos por `programada_para`: Hoy (abiertas y pendientes de hoy, con las pendientes atrasadas primero y chip "Atrasado"), Mañana, Esta semana (de pasado mañana a hoy + 7), Más adelante (después, y pendientes sin fecha), Realizados (realizadas y canceladas, por `cerrada_en`/`creado` descendente, paginado). Cada fila: fecha, operario, sitio, puntos y chip de estado. Los filtros y la búsqueda actuales se aplican a todos los grupos.
  - Actualizar los tests de `apps/visitas` que afirman la estructura vieja.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_con_hx_request_devuelve_parcial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_sin_hx_request_devuelve_pagina_completa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_post_htmx_crea_turno_y_responde_hx_redirect --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_post_sin_htmx_crea_el_mismo_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_post_htmx_con_errores_devuelve_el_parcial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_todos_los_puntos_tildados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_responsable_es_la_primera_opcion_de_operario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_crear_deshabilitado_sin_puntos_activos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.NuevoTurnoLateralTests.test_atajos_y_resumen_presentes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.TurnosAgrupadosTests.test_agrupa_por_programada_para --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.TurnosAgrupadosTests.test_atrasados_primero_en_hoy_con_chip --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.TurnosAgrupadosTests.test_realizados_incluye_cancelados_y_pagina --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_rediseno.TurnosAgrupadosTests.test_incidencias_sin_revisar_arriba --keepdb`
  - `[grep-0]` `grep -rn "Solo vencidos" apps/visitas/templates apps/visitas/static`
  - `[grep-0]` `grep -rniE "#ffc600|--brand|barlow condensed" --include=*.html --include=*.css --include=*.js apps/visitas`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1000 --subtarea T5`

### T6 — Catálogo con pestañas y estilos de clientes y usuarios

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/servicios/templates/**`, `apps/productos/templates/**`, `apps/accounts/templates/**`, `apps/clientes/templates/**`, y en cada una de esas apps `tests/**`
- **No puede tocar**: `docs/planes/`, `templates/`, `static/`, `apps/panel/**`, `apps/sitios/**`, `apps/visitas/**`, vistas, formularios, modelos, mixins y `migrations/` de cualquier app
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - Los listados de servicios y productos incluyen `panel/partials/pestanas_catalogo.html` con el título "Catálogo"; cada pestaña lista lo mismo que hoy (servicios; productos con stock).
  - Quitar los `style="display:inline"` de `apps/accounts/templates/accounts/panel/listado_parcial.html` y `apps/servicios/templates/servicios/panel/campos.html` (P-robustez-panel-13) usando la clase `.formulario-en-linea` de T1.
  - Ajustar a los componentes de T1 (chips, botones, avisos) las plantillas de clientes, usuarios, servicios y productos que usen marcado propio.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_catalogo.CatalogoServiciosTests.test_listado_muestra_pestanas_con_servicios_activa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_catalogo.CatalogoProductosTests.test_listado_muestra_pestanas_con_productos_activa_y_stock --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_panel_estilos.EstilosPanelTests.test_listado_de_usuarios_sin_style_en_linea --keepdb`
  - `[grep-0]` `grep -rn 'style="' apps/accounts/templates apps/servicios/templates apps/productos/templates apps/clientes/templates`
  - `[grep-1]` `grep -rn "formulario-en-linea" apps/accounts/templates/accounts/panel/listado_parcial.html apps/servicios/templates/servicios/panel/campos.html`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios apps.productos apps.accounts apps.clientes --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T6`

### T7 — Reescribir `docs/02-diseno.md`

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `docs/02-diseno.md`
- **No puede tocar**: `docs/planes/`, todo lo demás
- **Skill a leer antes**: `writing-for-agents` (§ documentos de referencia)
- **Worktree**: sí
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: documentar el sistema de T1 tal como quedó integrado: tokens del Adjunto con su nombre de variable (metadato `#646C76` y el motivo), contrastes medidos, tipografía (solo Barlow 400–700), radios, alturas de control, barra lateral de 232 px con sus dos grupos, componentes por clase (botones, chips de estado, tablas, formularios, pestañas, avisos, panel lateral), reglas de uso del color (estados siempre con texto) y textos obligatorios ("Turno", "Cargar visita", "Próximo vencimiento").
- **Criterios**:
  - `[grep-1]` `grep -n "#1F5FD1" docs/02-diseno.md`
  - `[grep-1]` `grep -n "#646C76" docs/02-diseno.md`
  - `[grep-1]` `grep -n "#FDECEA" docs/02-diseno.md`
  - `[grep-1]` `grep -n "panel-lateral" docs/02-diseno.md`
  - `[grep-0]` `grep -ni "industrial certificada" docs/02-diseno.md`
  - `[grep-0]` `grep -niE "barlow condensed|#ffc600" docs/02-diseno.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T7`

### T9 — Plano interactivo de la ficha y turnos atrasados en el inicio

<!-- Agregada por contrato modificado (2026-10-22, decisión del usuario): T4 agregó 1093 líneas sobre un
presupuesto de 1000. Lo que no entra en T4 va acá; T4 no cambia sus criterios ni su presupuesto. -->

- **Ola**: 2
- **Depende de**: T4 (mismo worktree `worktrees/diseno-panel-T4`, commits `T9:` después de los `T4:`)
- **Puede tocar**: `apps/sitios/panel_views.py`, `apps/sitios/estado.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/static/sitios/**`, `apps/sitios/tests/**`
- **No puede tocar**: `docs/planes/`, `templates/`, `static/`, `apps/panel/**`, `apps/visitas/**`, `apps/sitios/models.py`, `apps/sitios/qr.py`, el sitio público `/q/`, la API de sitios, `geocodificacion.py`, cualquier `migrations/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí (el de T4)
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - `apps/sitios/static/sitios/ficha_plano.js` y `apps/sitios/static/sitios/ficha.css` (resaltado cruzado plano ↔ lista por `data-punto` y estilos de las dos columnas de la ficha) pasan del commit de T4 a un commit `T9:` sin cambiar su contenido.
  - "Turnos de hoy" del inicio incluye también los turnos pendientes atrasados (`programada_para` < hoy), primero y con chip "Atrasado", como en la pantalla Turnos (decisión del usuario, 2026-10-22). La cantidad de consultas sigue sin depender de la cantidad de sitios.
- **Criterios**:
  - `[existe]` `apps/sitios/static/sitios/ficha.css`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_rediseno.FichaPlanoTests.test_ficha_carga_script_y_estilos_del_plano --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.TurnosAtrasadosInicioTests.test_atrasados_primero_en_turnos_de_hoy_con_chip --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_inicio.TurnosAtrasadosInicioTests.test_realizados_de_dias_anteriores_no_aparecen --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T9`

### T10 — Panel lateral de nuevo turno funcionando en el navegador

<!-- Agregada por contrato modificado (2026-10-23, decisión del usuario): la prueba en navegador de T8
encontró que el JS del panel lateral no se inicializa y que la fecha llega vacía. -->

- **Ola**: 2 (después de integrar T4 y T5)
- **Depende de**: T4, T5
- **Puede tocar**: `apps/visitas/panel_forms.py`, `apps/visitas/templates/visitas/panel/**`, `apps/visitas/static/visitas/**`, `apps/visitas/tests/**`
- **No puede tocar**: `docs/planes/`, `templates/`, `static/`, `apps/panel/**`, `apps/sitios/**`, `apps/visitas/services.py`, `apps/visitas/models.py`, `apps/visitas/panel_views.py`, la API de visitas, cualquier `migrations/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `nuevo_turno.js` se inicializa sin depender del orden de carga respecto de htmx: hoy llama a `htmx.onLoad` antes de que htmx esté listo y el callback nunca se registra, así que en el panel lateral no andan atajos, marcadores, resumen ni `disabled`. Inicializar al cargar el documento y en el evento `htmx:load` (o `htmx:afterSwap` de `#panel-lateral`) con `document.addEventListener`, sin `htmx.onLoad`.
  - La fecha del turno (`programada_para`) y toda fecha de `input type="date"` de los formularios del panel de visitas se renderizan en formato `AAAA-MM-DD` (hoy salen `22/10/2026` y el navegador las descarta).
  - El listado de puntos del panel lateral no se sale de la tarjeta (selects y nombres dentro del ancho); en la página completa, un solo título "Nuevo turno" y el pie fijo no tapa las últimas filas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_navegador.PanelLateralNavegadorTests.test_nuevo_turno_js_no_usa_htmx_onload --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_navegador.PanelLateralNavegadorTests.test_fecha_del_turno_en_formato_iso --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_navegador.PanelLateralNavegadorTests.test_pagina_completa_con_un_solo_titulo --keepdb`
  - `[grep-0]` `grep -n "htmx.onLoad" apps/visitas/static/visitas/nuevo_turno.js`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T10`

### T11 — Buscador, filtros y acciones de los listados

<!-- Agregada por contrato modificado (2026-10-23, decisión del usuario): la prueba en navegador de T8
encontró el buscador de Turnos de 26 px, filtros sin estilo en Usuarios y Clientes y acciones pegadas en Servicios. -->

- **Ola**: 2 (después de integrar T4 a T7)
- **Depende de**: T4, T5, T6
- **Puede tocar**: `static/css/panel.css`, `templates/panel/partials/**`, `apps/accounts/templates/**`, `apps/clientes/templates/**`, `apps/servicios/templates/**`, y en esas tres apps `tests/**`, `apps/panel/tests/**`
- **No puede tocar**: `docs/planes/`, `templates/base.html`, `templates/panel/base.html`, `apps/visitas/**`, `apps/sitios/**`, `apps/panel/` salvo `tests/`, vistas, formularios, modelos y `migrations/` de cualquier app
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - El buscador compartido (`templates/panel/partials/buscador.html`) tiene un ancho mínimo legible en cualquier fila de filtros (en Turnos medía 26 px).
  - Filtros de Usuarios (selects Rol y Estado) y de Clientes (Todos / Activos / Inactivos) con los componentes del sistema; el filtro activo de Clientes lleva `aria-current="page"`; "Nuevo cliente" separado del buscador.
  - Las acciones de cada fila (p. ej. "Editar" y "Planilla" en Servicios) separadas con una clase común de `panel.css`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_diseno_tokens.ListadosCssTests.test_buscador_tiene_ancho_minimo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_panel_filtros.FiltrosClientesTests.test_filtro_activo_marcado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_catalogo.AccionesFilaTests.test_acciones_de_fila_agrupadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_panel_estilos.FiltrosUsuariosTests.test_filtros_usan_clase_del_sistema --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel apps.accounts apps.clientes apps.servicios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T11`

### T8 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T4, T5, T6, T7, T9, T10 y T11)
- **Depende de**: T4, T5, T6, T7, T9, T10, T11
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/diseno-panel` de cada subtarea, no los informes.
  2. Desde la raíz, `worktree-integrar.sh diseno-panel T<n> plan/diseno-panel <rutas>` para T4 (`apps/sitios`; el worktree de T4 lleva también los commits de T9), T5 (`apps/visitas`), T6 (`apps/servicios apps/productos apps/accounts apps/clientes`), T7 (`docs/02-diseno.md`), T10 (`apps/visitas`) y T11 (`static templates apps/accounts apps/clientes apps/servicios apps/panel`).
  3. Prueba manual en el navegador (1280 px): abrir y cerrar el panel lateral desde la lista y la ficha, Escape, foco de vuelta, atajos, resumen y clic en el plano; registrar lo observado en el Registro.
  4. Cierre global, verificación `TODO` (verificador y verificador-b) y `auditor-seguridad`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/diseno-panel | grep -q "T4: integra diseno-panel-T4"`
  - `[cmd]` `git log --oneline plan/diseno-panel | grep -q "T5: integra diseno-panel-T5"`
  - `[cmd]` `git log --oneline plan/diseno-panel | grep -q "T6: integra diseno-panel-T6"`
  - `[cmd]` `git log --oneline plan/diseno-panel | grep -q "T7: integra diseno-panel-T7"`
  - `[grep-0]` `grep -rniE "#ffc600|--brand|barlow condensed" --include=*.html --include=*.css --include=*.js templates static/css apps`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-22-diseno-panel.md diseno-panel`

## Registro de verificación

commit_base: 0175082

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | hecha |
| T7 | hecha |
| T9 | hecha |
| T10 | hecha |
| T11 | hecha |
| T8 | en curso |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-22 | T1 | d4488fc | PASA (verificador 21/21; verificador-b 22/22) | login, 404, 500 y mapa.html sin cambios propios: toman los tokens por panel.css |
| 2026-10-22 | T2 | 82a8da0 | PASA (verificador 5/5; verificador-b 5/5) | commit T2 hecho por el principal: el implementador dejó el cambio sin commitear |
| 2026-10-22 | T3 | 1241038 | criterios 2/2 (git log); auditor-seguridad sobre T1 sin hallazgos | observación del auditor: 404 y 500 no cargan los tokens de base.html; `.pagina-error` usa respaldos con los valores del Adjunto |
| 2026-10-22 | T4 | 04b3cc3 | criterios 17/17 PASA (verificador y verificador-b); auditor-seguridad sin hallazgos nuevos | contrato MODIFICADO por c235fc8 (T9, decisión del usuario): verificador da FALLA solo por eso, sin criterios en FALLA |
| 2026-10-22 | T5 | 485472f | PASA (verificador 17/17; verificador-b 17/17); auditor-seguridad sin hallazgos | observación del auditor: `?q=%00` en PostgreSQL (ya registrado como P-robustez-panel-10) |
| 2026-10-22 | T6 | ec34bb6 | PASA (verificador 7/7; verificador-b 7/7) | |
| 2026-10-22 | T7 | 2fcfad2 | PASA (verificador 7/7; verificador-b 7/7) | |
| 2026-10-22 | T9 | 04b3cc3 | criterios 6/6 PASA (verificador y verificador-b) | contrato MODIFICADO por c235fc8 (T9, decisión del usuario): verificador da FALLA solo por eso, sin criterios en FALLA |
| 2026-10-23 | T10 | fcea1a3 | criterios 6/6 PASA (verificador y verificador-b) | contrato MODIFICADO por c235fc8 y f386238 (decisiones del usuario): verificador da FALLA solo por eso |
| 2026-10-23 | T11 | 1600c9d | criterios 6/6 PASA (verificador y verificador-b) | contrato MODIFICADO por c235fc8 y f386238 (decisiones del usuario): los verificadores dan FALLA solo por eso |
| 2026-10-23 | T8 (prueba en navegador) | c2627ef | FALLA | panel lateral: nuevo_turno.js no se inicializa (htmx.onLoad antes de que htmx esté listo); fecha `22/10/2026` descartada por input date; visuales: desborde del panel, título duplicado, pie tapa filas, buscador de Turnos 26 px, filtros de Usuarios y Clientes, acciones de Servicios. Resto PASA (barra, inicio, ficha, Escape y foco, crear turno con fecha a mano, Turnos, Catálogo, mapa). Corrección: T10 y T11 |
| | T8 | | | |
| | TODO | | | |

### Decisiones del plan

- Plan — grep de amarillo y Barlow Condensed — solo `templates/`, `apps/*/templates/`, `static/css/` (como pide el pedido) o también `apps/*/static/` y `.js` — también `apps/*/static` y `.js` — `puntos.css` y `mapa.js` repiten `#ffc600` y quedarían con el amarillo — autónoma — volver a las tres rutas del pedido — decidida por Claude, revisable
- Plan — estado del sitio en el inicio — peor estado de los puntos (`resumen_de_sitios`) o el del mínimo `proximo_vencimiento` — el del mínimo — es la fecha que muestra la columna y "sin estados por punto"; difiere solo cuando un sitio mezcla puntos sin fecha con puntos al día — autónoma — cambiar la anotación por `resumen_de_sitios` — decidida por Claude, revisable
- Plan — "Esta semana" en Turnos — semana calendario o de pasado mañana a hoy + 7 — hoy + 7 — coincide con el umbral "Próximo (7 días o menos)" — autónoma — cambiar el límite del grupo — decidida por Claude, revisable
- Plan — sitios inactivos en "Todos los sitios" — ocultarlos o listarlos — ocultos con enlace "Ver sitios inactivos" — no se pierde el acceso que da hoy `?activo=0` — autónoma — quitar el filtro — decidida por Claude, revisable
- Plan — mapa geográfico de la ficha — pestaña propia o dentro de "Datos del sitio" — dentro de "Datos del sitio" — el pedido fija tres pestañas — autónoma — volver a la pestaña `mapa` — decidida por Claude, revisable
- Plan — Catálogo — página nueva o pestañas que enlazan los dos listados existentes — pestañas sobre los listados existentes — sin rutas nuevas ni duplicar vistas; la entrada del menú apunta a Servicios — autónoma — agregar `/panel/catalogo/` — decidida por Claude, revisable
- Plan — test del menú en `apps/visitas/tests/test_panel_menu.py`, que rompería la integración de T1 — que T1 lo edite (viola la tabla de propiedad) o una subtarea de visitas en la ola 1 que lo deje compatible con ambas barras y se integre primero — subtarea T2 — respeta la propiedad y la integración corre todos los tests — autónoma — mover el test a `apps/panel/tests/` en otro plan — decidida por Claude, revisable
- Plan — suite completa en T1 — en su worktree o recién en la integración T3 — en T3 (T1 corre las apps que no dependen de T2) — en el worktree de T1 sigue el test viejo del menú de visitas, que T2 deja compatible — autónoma — volver a correr la suite completa en T1 si T2 se integra antes de crear su worktree — decidida por Claude, revisable
- Plan — `seguridad` — no o sí — sí, con alcance acotado por subtarea (sin modelos, API, QR público, fotos ni mixins) — el juez-plan marcó login, datos personales y vistas de administrador — autónoma — no aplica — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

### Decisiones

- 2026-10-22 — `--text-faint` es `#646C76` y no el `#6B737D` del Adjunto — el aprobado da 4,44:1 sobre el fondo `#F5F6F7` y 4,2:1 sobre superficie-2 — reemplaza a: (nada)
- 2026-10-22 — En Turnos, los pendientes atrasados van primero en "Hoy" con chip "Atrasado" y los cancelados en "Realizados" — los grupos del pedido no tenían lugar para ellos — reemplaza a: (nada)
- 2026-10-22 — T4 excedió su presupuesto (1093 de 1000): lo que sobra (`ficha_plano.js`, `ficha.css`) pasa a una subtarea nueva T9, sin subir el presupuesto ni recortar código — regla de presupuesto de CLAUDE.md — reemplaza a: (nada)
- 2026-10-22 — "Turnos de hoy" del inicio incluye los pendientes atrasados, primero y con chip "Atrasado" — un sitio con un turno atrasado no aparecía ni en "Turnos de hoy" ni en "Requieren atención" — reemplaza a: (nada)

### Cierra
