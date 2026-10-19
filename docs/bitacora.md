# Bitácora de MAControl

## Estado actual
Plan activo: (ninguno)

Planes activos (los hooks derivan el plan de la rama; la línea `Plan activo:` de arriba es el respaldo para la raíz):

| plan | rama | ola actual | pendiente inmediato | sesión |
|---|---|---|---|---|
| (ninguno) | main | — | plan chico: `NOMBRE_EMPRESA` obligatoria en producción + P-separacion-web-10 | sesión 2026-10-18 |

Siguiente: 72 abiertos según `pendientes.py` tras el cierre de separacion-web (19 cerrados en su `### Cierra`). Regla de cuándo preguntar: CLAUDE.md § Reglas globales, regla 8.

Problemas abiertos: ver `py -3 .claude/hooks/pendientes.py` (cada plan los declara en `## Pendientes que deja este plan`; los anteriores están en `docs/planes/2026-10-03-pendientes-heredados.md`).

## Entradas (la más reciente arriba)

### 2026-10-18 — Fusión de `separacion-web` en `main`
Hecho:
- Verificación `TODO` en 1c81459: `verificador` y `verificador-b` 117/118 PASA; único FALLA `congelado.sh` (contrato modificado 9d8aef7, a60430e). `auditor-seguridad` sin bloqueantes (P-separacion-web-10 y -11).
- El usuario aceptó el FALLA formal y aprobó el merge: `plan/separacion-web` fusionada en `main`; sus 28 decisiones copiadas a `docs/decisiones.md`.
Pendiente: plan chico para exigir `NOMBRE_EMPRESA` en producción (como `SITE_URL`) y sumar a la skill la regla de no tener formularios públicos (P-separacion-web-10); lo aprobó el usuario.

### 2026-10-18 — Plan `separacion-web` ejecutado (T1 a T12)
Hecho:
- Las cuatro olas integradas en `plan/separacion-web` (e8894ba): el producto se llama Detach y el nombre de la empresa sale de `NOMBRE_EMPRESA`; `apps/web` borrada; `/` redirige al login del panel; `/q/<uuid>/` vive en `apps.sitios` con `X-Robots-Tag: noindex, nofollow`; `TipoServicio.descripcion` fuera (migración `servicios` 0004); `SITE_URL` obligatoria en producción; `docs/contrato-api.md` y `README.md` nuevos.
- `docs/00-contenido-fuente.md` y la parte web de `docs/02-diseno.md` se movieron al repositorio del sitio público (`../macontrol-web`).
- Aviso para bases anteriores: las tablas `web_*` quedan huérfanas; quien quiera limpiarlas corre `manage.py migrate web zero` con el código anterior, antes de actualizar.
- Demo portátil borrada por decisión del usuario (`herramientas/`, `demo.bat`, `docs/demo-cliente.md`); `cargar_demo` queda como datos de desarrollo. `dist/` y `demo.sqlite3` siguen en el disco local.
- Contrato modificado dos veces con aprobación del usuario (9d8aef7: T12; a60430e: demo y corrección de T8); `congelado.sh` da FALLA formal, aceptado por el usuario en cada ola.
- La integración de T8 falló una vez (test de migraciones de sitios) y `worktree-integrar.sh` la deshizo; se corrigió con contrato ampliado.
Pendiente: (ver la entrada de fusión, arriba).

### 2026-10-18 — Fusión de `demo-portatil` en `main`
Hecho:
- `plan/demo-portatil` fusionada en `main` (4c2bcda) por pedido del usuario; sus decisiones copiadas a `docs/decisiones.md`.
- `../macontrol-web` existe (clone de este repositorio) y lo trabaja otra sesión en `plan/web-independiente`; contiene `docs/00-contenido-fuente.md` y `docs/02-diseno.md`.
- Plan Completo `separacion-web` (Detach: quitar `apps/web`, marca por `NOMBRE_EMPRESA`, `/` → login, `/q/` a `apps/sitios`, `docs/contrato-api.md`), commit_base b7dfb6a. Aprobado por el usuario; juez-plan: dos rondas RECHAZADO, bloqueantes corregidos (el último, el criterio de T2, sin rejuzgar).
Pendiente: arrancar T1 en una sesión nueva sobre la rama `plan/separacion-web` (en la raíz: T1 la hace el principal, sin worktree).

### 2026-10-13 — Plan `demo-portatil`: demo autocontenida con Python embebido
Hecho:
- Plan Chico `demo-portatil` (commit_base 74f544d), dos olas, cada subtarea con verificador.
  - T1: `herramientas/empaquetar_demo.py` arma `dist/macontrol-demo/` con Python 3.13.15 embebido (tamaño y SHA-256 fijos, tomado del `.sigstore`), wheels `--only-binary` con el pip del venv, código por `git ls-files`, `demo.bat` portátil con IP detectada y `LEEME.txt`; zip de 65,4 MB. Test `test_sin_weasyprint` (WeasyPrint no se importa en ningún lado).
  - T3: `herramientas/humo_demo.py` arranca el `demo.bat` portátil, comprueba `/`, la redirección de `/panel/` y el login de demo-admin, y apaga; sección "Llevar la demo a otra PC" en `docs/demo-cliente.md`.
- Verificación TODO: una FALLA por choque con el hook de cierre en `dist/prueba/` y luego PASA 26/26 sobre e8d79fa.
Pendiente: el merge a `main` lo decide el usuario; P-demo-portatil-1 a -5 en el plan.

### 2026-10-12 — Plan `robustez-panel`: puntos, geocodificación, filtros, incidencias y diseño del panel, fusión en `main`
Hecho:
- Plan Completo `robustez-panel` (`seguridad: sí`) en cinco olas, commit_base 21b20be; cada subtarea con verificador, verificador-b y auditor-seguridad:
  - T1: corregir coordenadas desde panel o admin limpia `ubicacion_fijada_por/en` y `precision_m`; `estado.py` ignora visitas de administradores; destildar "activo" pasa por `desactivar_punto` (dos rondas por una regresión propia en el admin).
  - T3 y T12: geocodificación con User-Agent con contacto, 503 ante JSON anidado, redirecciones y errores HTTP, y cota total de 5 s con `HTTPSConnection` y un vigilante que corta el socket (deja de honrar `HTTPS_PROXY`).
  - T4: `clean_redes` rechaza URLs con usuario/contraseña; la 404 bajo `/panel/` y `/admin/` enlaza a su inicio.
  - T6, T13, T14, T8 y T10: filtros numéricos con `isascii()`, a lo sumo 19 dígitos y `<= 2**63 - 1` en proyectos, sitios, visitas y mapa.
  - T8: filtro de incidencias de ubicación revisadas, historial de visita en una consulta (últimos 50), ficha con incidencia de asignación.
  - T10: `.enlace` y estilos de fichas en `panel.css`, CSS de tablero y mapa fuera de `<style nonce>`, contadores del tablero solo con visitas realizadas, sin CSP de teselas en el JSON del mapa, `AccesoTests` con objetos reales por modelo (dos rondas por defectos del propio test).
- Dos contratos modificados por decisión del usuario: T12 (fa3397f) y P-robustez-panel-8 con T13/T14 (43cc3af).
- Verificación TODO: 70/71 PASA en ambos verificadores (FALLA solo `congelado.sh`); auditor-seguridad sin hallazgos. Se trajo `main` (demo-cliente) sin conflictos: 669 tests OK. Fusión autorizada por el usuario.

Queda:
- P-robustez-panel-9 y -10 [menor]: `?orden=--x` y `?q=%00` (Postgres) dan 500 en los listados del panel (`apps/panel/listados.py`).
- P-robustez-panel-3 [menor]: `worktree-integrar.sh` falla siempre en el `branch -d` final cuando el destino es `plan/<slug>`.
- Resto de P-robustez-panel-1 a -14 en el plan.
- El worktree `worktrees/robustez-panel` y la rama `plan/robustez-panel` siguen existiendo; se quitan cuando el usuario lo indique.

### 2026-10-12 — Plan `demo-cliente`: datos de demostración, `demo.bat` y preparación para alojar, fusión en `main`
Hecho:
- Plan Chico `demo-cliente` (T3 con `auditor-seguridad`) en dos olas, desde `main` aba788e (commit_base d8caed8):
  - T1 y T6: `cargar_demo` reescrito en `apps/panel` (4 clientes de la Carta, 6 sitios, plano con Pillow, 90 días de historia por ORM, datos marcados y recreables; carga `contenido_inicial` si falta, cierra P-sitio-publico-3). T1 excedió su presupuesto (789/700) y se partió en T1 + T6 (`demo_historia.py`).
  - T2: `demo.bat` (base `demo.sqlite3` aparte, IP privada detectada, `runserver 0.0.0.0:8000`) y `docs/demo-cliente.md`.
  - T3: whitenoise y gunicorn, `railway.json`, `.python-version`, `CSRF_TRUSTED_ORIGINS`, abortos por `ALLOWED_HOSTS` vacío y por Railway en dev, `docs/despliegue.md`. Sin desplegar.
- Dos contratos modificados aprobados por el usuario: criterios grep como comando completo (055dd91) y T6 (dffcb24).
- Verificación TODO en 4098d88: 41/42 PASA; único FALLA `congelado.sh` (CONTRATO MODIFICADO), aceptado por el usuario. Suite 623 OK, ruff OK. `auditor-seguridad` sobre T3: sin bloqueantes; hallazgos en P-demo-cliente-4 a -9.
- Fusionado en `main` en fb14739 con `--no-ff`. Sin push.
- `worktree-integrar.sh` falla en `git branch -d` cuando la raíz no está en la rama destino (P-demo-cliente-10); las ramas se borraron con `-D` tras comprobar `merge-base --is-ancestor`.
Sigue: demo del cliente con `demo.bat` desde la raíz; antes de alojar en público, P-demo-cliente-4, -5 y -8.

### 2026-10-08 — merge de robustez-datos y sitio-publico en main
Hecho:
- `robustez-datos` (55ec1db) y `sitio-publico` (25e188a) ya estaban fusionados con sus decisiones copiadas; la rama `plan/robustez-datos` ya no existía.
- Se fusionaron en `main` con `--no-ff` los ajustes visuales del usuario posteriores al cierre de `sitio-publico` (80f8ed7, 6bd79a2) en bb788ca, sin conflictos. No había decisiones nuevas que copiar.
- En `main` (bb788ca): check, makemigrations --check, ruff y 613 tests OK. Sin push. `pruebanueva.json` queda sin versionar en la raíz y no se tocó.
Sigue: arrancar `robustez-panel`.

### 2026-10-08 — Plan `sitio-publico`: sitio público, fusión en `main`
Hecho:
- Plan Completo `sitio-publico` (seguridad: sí) en dos olas:
  - T1 (modelos `Configuracion`, `PaginaServicio`, `ClienteDestacado`, `Sector`) y T7 (fixture `contenido_inicial`: 9 servicios, 13 clientes).
  - T2 (`web.css`, `base_web.html`, 5 WebP).
  - T4 (edición del contenido desde el panel).
  - T5 (home, servicio, empresa, contacto, `/q/<uuid>/`, sitemap, robots, Open Graph, 404/500).
  - T8 y T9 (imágenes subidas sin EXIF, formato real, nombres uuid, redes solo https).
  - T10 (contraste de los sectores y dimensiones del logo).
- Contrato modificado cuatro veces y aprobado por escrito en el Registro:
  - 9ac7c9d y 56ea85f: T1 y T8 partidas por presupuesto.
  - 5c01419: T8 por la auditoría.
  - a9f80a5: T10 por la prueba en el navegador.
- `auditor-seguridad`: H1-H4 cerrados. Los hallazgos de severidad baja quedan como P-sitio-publico-12 a -14.
- Verificación TODO: 99/100 con los dos verificadores; única FALLA `congelado.sh` por el contrato modificado.
- Lighthouse móvil sobre la home, hecho por el usuario: 93/100/100/100.
- Fusión de `plan/sitio-publico` en `main` con `--no-ff` (25e188a), sin conflictos con `robustez-datos`. En `main`: check, makemigrations, ruff y 613 tests en PASA. 23 decisiones copiadas a `docs/decisiones.md`. Sin push.
- Decisiones del usuario al cierre:
  - El fixture no debe incluir `TipoServicio` (P-6 es defecto).
  - `media/publico/` se sirve en abierto solo para logos y portadas.
  - P-7 y los textos fijos de las plantillas se resuelven juntos.
  - Etiqueta `sitio-cierre` para P-1, -2, -6, -7, -12.
Sigue: el usuario trae objeciones y cambios visuales del sitio en otra sesión (P-sitio-publico-17); elegir entre `robustez-panel` y `sitio-cierre`.

### 2026-10-08 — Plan `robustez-datos`: fusión en `main`
Hecho:
- P-robustez-datos-8 y -9 pasan a `robustez-panel` por decisión del usuario: se corrigen en el próximo plan, no antes del merge.
- Fusión de `plan/robustez-datos` en `main` con `--no-ff` (55ec1db); 10 decisiones copiadas a `docs/decisiones.md` (f031b4c).
- Criterios de cierre global en `main`: check, makemigrations, 578 tests, ruff y árbol limpio en PASA; `congelado.sh` exit 1 solo por CONTRATO MODIFICADO (ampliación 01d5d1f aprobada por el usuario). Rama `plan/robustez-datos` borrada. Sin push.
Sigue: elegir el próximo plan (candidato `robustez-panel`); etiquetar los 10 pendientes nuevos sin etiqueta.

### 2026-10-08 — Plan `robustez-datos`: 28 pendientes cerrados, sin fusionar
Hecho:
- Plan Completo `robustez-datos` (07191c7) en `plan/robustez-datos`: T1 y T10 en línea (config), ola 1 con T2 (visitas) y T3 (sitios), ola 2 con T5 (panel), T6→T8 (visitas) y T9 (sitios). Contrato ampliado por el usuario el 2026-10-08 (01d5d1f) con T8, T9 y T10 para los 7 hallazgos de la auditoría de la ola 1.
- Cierra los 28 `robustez-datos` y P-cierre-puntos-2. Migraciones nuevas: `visitas.0009` (`cuenta_como_servicio`, `precision_m`) y `sitios.0008` (`precision_m`, `ubicacion_fijada_por/en`, con backfill).
- Verificación TODO en 923f396: 83/84 PASA en los dos verificadores; la única FALLA es `congelado.sh` por el contrato modificado. Suite 578 OK. Auditoría final: 0 bloqueantes; quedan P-robustez-datos-1 a -12 (dos importantes nuevos: -8 corrección de ubicación desde el panel no limpia `ubicacion_fijada_*`, -9 `sitios/estado.py` cuenta revisiones de administradores).
Sigue: decisión del usuario sobre -8/-9 y sobre el merge a `main` (sin push).

### 2026-10-07 — Plan `triage-2026-10-07`: triage de pendientes, fusión en `main`
Hecho:
- Plan sin código `triage-2026-10-07` (Chico): T1 comprobó con 8 tests existentes y un grep los 9 cierres condicionales (todos resueltos); T2 anotó en `convenciones-proyecto` que `Visita.datos` pasa por `validar_datos` y la sección nueva § Panel (`id="listado"`, decidida por Claude, revisable); T3 aplicó el triage del usuario: 29 cierres, 51 etiquetas nuevas, 12 decisiones.
- 108 → 79 abiertos, todos con destino; `panel-cierre` sin abiertos. Verificación TODO 16/16 PASA (9c877c6).
- Fusión en `main` con `--no-ff` (4cb06d2); 12 decisiones copiadas (e3525b9); en `main`: check, makemigrations, ruff y 527 tests OK. Sin push. `docs/pendientes-snapshot.txt` queda sin versionar (es la foto previa al triage).
Sigue: elegir el próximo plan (candidato `robustez-datos`).

### 2026-10-07 — Plan `auditoria-p31`: correcciones de la auditoría, fusión en `main`
Hecho:
- Plan `auditoria-p31` (commit_base 701e6b2): T1 (una revisión con incidencia de ubicación no fija coordenadas) y T2 (la `sitios/0007` deja fila histórica y solo aplica propuestas respaldadas; `PosicionForm.plano` con planos activos; la fuente del QR cae a la de Pillow), en paralelo.
- T2 rompió 4 tests de migración de visitas por la dependencia nueva `sitios.0007 → visitas.0008` → T4 (helper `_destino`), por decisión del usuario (ce638ac). La auditoría de T3 encontró que las revisiones previas a `visitas.0008` tienen `incidencia_ubicacion=False` por defecto → T5 (la `0007` filtra la revisión por punto, toma sus coordenadas y mide la distancia al sitio), por decisión del usuario (0d8b058). Re-auditoría: cerrado, nada nuevo.
- Verificación TODO: 35/36 y 40/41, único FALLA formal `congelado.sh` por las dos modificaciones, aceptado por escrito por el usuario. Cierra P-correcciones-p31-1 a 6; deja P-auditoria-p31-1 y -2 (observaciones).
- Fusión en `main` con `--no-ff` (a9a0058); decisiones copiadas (fc6e4d9); en `main`: check, makemigrations, ruff y 527 tests OK. Sin push.
- Commit pasivo: regla de cuándo preguntar al usuario en CLAUDE.md (regla 8), `docs/plantilla-plan.md` § Decisiones y `docs/decisiones.md` (d1b430b).
- `docs/pendientes-snapshot.txt` generado sin versionar para el triage: 108 abiertos (13 importantes, 40 menores, 55 observaciones; 68 sin etiqueta).
Sigue: triage `triage-2026-10-07` con el usuario; después `panel-cierre`.

### 2026-10-07 — Planes `cierre-puntos` y `correcciones-p31`: integrados y verificados
Hecho:
- `cierre-puntos` (sesiones del 2026-10-06, sin entrada propia hasta hoy): T1–T8, T10, T11 y la corrección T8b integradas; contrato openapi regenerado (dd86327); auditoría final con pendientes P-cierre-puntos-13 a 15.
- La prueba en navegador de `cierre-puntos` (P-puntos-control-31) dio seis problemas → plan `correcciones-p31` (rama desde 9728a27). juez-plan: 1 bloqueante y 5 observaciones, corregidos antes de congelar (6510a35).
- Ola 1: T1 (visitas: el primer escaneo de cualquier rol fija las coordenadas; hora futura en la visita manual) y T2 (sitios: modos del plano, arrastre que guarda, ubicar puntos existentes, QR con Barlow), verificadas e integradas. Ola 2: T3 (migración `sitios/0007` aplica las propuestas pendientes y quita el campo; la pestaña Mapa muestra solo el sitio), verificada e integrada; T4: docs de arquitectura, contrato openapi sin cambios.
- Auditoría de T4: 0 bloqueantes; 2 importantes, 1 menor y 3 observaciones → P-correcciones-p31-1 a 6, por decisión del usuario (sin corregir en este plan).
- OK del usuario en navegador (2026-10-07), que vale también para el paso 4 de T9 de `cierre-puntos`.
- Verificación TODO: `correcciones-p31` 38/38 PASA (verificador y verificador-b); `cierre-puntos` 79/80 en ambos, con el único FALLA formal de congelado.sh aceptado.
- Incidente: el 2026-10-07 la raíz amaneció en `plan/cierre-puntos` (checkout manual); se volvió a `plan/correcciones-p31` sin pérdidas.
- Fusión en `main` (1f85911) por decisión del usuario: decisiones de los tres planes copiadas a `docs/decisiones.md` (23 líneas); en `main`, check, makemigrations, ruff y suite completa (516 tests) OK.
Sigue: elegir el próximo plan; P-correcciones-p31-1 y -2 antes de desplegar.

### 2026-10-06 — Plan `puntos-control`: olas 2 a 4 integradas, verificación final
Hecho:
- Ola 2: T9 verificada e integrada; auditoría ola 2 → T9b (decisión del usuario: `visitas/abrir/` exige `qr_codigo`, cambia `/api/v1/`; `me/puntos?sitio=` validado; plano filtra sitio y cliente activos); T10: openapi regenerado (e03c8db, 654a6f4).
- Ola 3: T11, T12 (con P-17) y T13 en paralelo, integradas T13 → T12 → T11; auditoría ola 3 → T11b (PDF en subproceso con 15 s; tooltips con textContent). T14 hecha; la prueba en navegador queda diferida (P-31).
- Ola 4: T16 (docs/01 y convenciones) y T15 (`cargar_demo` y recorrido); auditoría T15 → T15b en dos rondas (decisión del usuario: `cargar_demo` solo con DEBUG, `DJANGO_ENV=development` y SQLite).
- Verificación TODO con `verificador` y `verificador-b`: 104/105 PASA en d781f25; única FALLA formal congelado.sh por 50822be. Suite 473 OK.
- Decisiones del plan escritas en `### Decisiones` (9 líneas); pendientes nuevos P-puntos-control-24 a -35.
Sigue: prueba en navegador (P-31) y merge a `main` por decisión del usuario.

### 2026-10-05 — Plan `puntos-control`: ola 1 integrada, T8 integrada, T9 implementada
Hecho:
- Plan congelado (`4e2c496`) tras `juez-plan` (10 bloqueantes, corregidos o aprobados por el usuario como excepciones de propiedad). Contrato modificado una vez (`50822be`, decisión del usuario): el criterio del punto General pasa de T3 a T6; desde ahí `congelado.sh` da CONTRATO MODIFICADO y los veredictos salen FALLA formal.
- Ola 1: T1 (pypdfium2, `VISITA_ABIERTA_MAXIMO_HORAS`), T2 (ámbito de planilla), T3 (PuntoControl, Plano, QR por punto), T5 (visita como jornada, Revision, migración de datos), T6 (sin QR en Sitio, estado por punto). auditor-seguridad: sin bloqueantes; dos importantes corregidos en T5b (cierre por `recibida_en`, coordenadas obligatorias) y cerrados en la re-auditoría.
- Ola 2: T8 (resolver por punto, imagen del plano, `me/puntos/`) verificada e integrada. T9 (abrir, revisiones, cerrar; sin `POST visitas/`) implementada en su worktree (`f678582`, suite 442 OK según el informe; control del principal OK), sin verificador.
- Pendientes nuevos: P-puntos-control-1 a -23.
- Incidente: el principal hizo `cd` a un worktree (T2) para un control; corregido con `git status` en raíz y worktrees, sin daños.
Pendiente: verificador sobre T9, integrarla, T10 (openapi + auditoría ola 2), olas 3 y 4.

### 2026-10-05 — Fusión en `main` de `panel`
Hecho:
- El usuario aprobó `plan/panel` con la verificación TODO en FALLA 1/115: la única FALLA es `congelado.sh` por el contrato modificado `2cebc16`, que él mismo autorizó. Verificador y verificador-b coincidieron (HEAD `f21d709`).
- `main` recibió `plan/panel` con `merge --no-ff`. Las 7 decisiones del plan se copiaron al final de `docs/decisiones.md`.
- Etiquetas: P-panel-4, -5, -6 y -17 → `panel-cierre` (P-panel-17 se corrige pasando `geocodificar` a POST; el usuario no lo acepta como decisión). P-panel-8, -16 y -23 → `despliegue`.
Pendiente: plan `panel-cierre`.

### 2026-10-05 — Plan `panel`: las cuatro olas integradas, verificación TODO 114/115
Hecho:
- Plan congelado (`5155082`) con los ajustes del usuario; contrato modificado una vez (`2cebc16`, decisión del usuario): `test_acceso` pasó de T5 (677/650 líneas) a la integración T11.
- Ola 1 (T1 vendor HTMX 2.0.11 y Leaflet 1.9.4, T2 diseño, T3 revisión de incidencias), ola 2 (T5 tablero y mapa, T6 clientes, T7 sitios y QR, T8 proyectos, T9 productos y planillas, T10 usuarios), ola 3 (T12 visitas, T13 geocodificación con Nominatim) y ola 4 (T15 carga manual, T16 recorrido), todas en worktrees e integradas en `plan/panel`.
- auditor-seguridad por ola: un bloqueante en T10 (un administrador gestionaba superusuarios y podía entrar a `/admin/`), corregido en `8a96aa6` y cerrado en la re-auditoría; el resto, menores y observaciones (P-panel-15 a -27).
- Verificación TODO en `f21d709`: verificador y verificador-b, 114/115 PASA; la única FALLA es `congelado.sh` por el contrato modificado. Suite 374 OK.
- Cierra P-pendientes-heredados-10, P-api-movil-10, P-contrato-app-1, P-contrato-app-8 y P-panel-1. Pendientes nuevos: P-panel-2 a -27.
- Incidentes: un `cd` del principal a un worktree (corregido, sin daños) y el renombre `form.html` → `formulario.html` quedó en el commit de T4 (P-panel-13).
Pendiente: aprobación del usuario de la FALLA de `congelado.sh`, decisión de P-panel-17 y fusión en `main`.

### 2026-10-04 — Fusión en `main` de `saneamiento`
Hecho:
- `main` recibió `plan/saneamiento` con `merge --no-ff`, con la verificación TODO en PASA 0/44 (verificador y verificador-b, HEAD `a5d1a74`) y `auditor-seguridad` sin bloqueantes.
- Las 3 decisiones del plan se copiaron al final de `docs/decisiones.md` (CUIT resto 10; `noqa` quitado; SameSite y tope de archivos explícitos).
- Rama `plan/saneamiento` borrada. Pendientes abiertos: 35.
Pendiente: plan `panel`.

### 2026-10-04 — Plan `saneamiento`: 16 de los 17 pendientes etiquetados, cerrados
Hecho:
- Regla nueva en `main` (`aab6553`): el principal no hace `cd` a los worktrees (CLAUDE.md § 5 e `implementador.md`).
- Plan congelado (`cb7b8e3`) tras `juez-plan` (0 bloqueantes, 3 observaciones incorporadas). Ola 1 en paralelo: T1 visitas (230/400), T2 sitios/clientes/accounts/logs (65/250), T3 herramientas (17/80); verificador y verificador-b PASA 27/27. T4: settings (`SESSION_COOKIE_SAMESITE`, `DATA_UPLOAD_MAX_NUMBER_FILES = 12`), 16/40.
- TODO en PASA 0/44 (verificador y verificador-b, HEAD `a5d1a74`); `auditor-seguridad`: 1 menor PLAUSIBLE y 5 observaciones, registrados como P-saneamiento-3 a -5 (plan aparte, decisión 2026-10-04).
- `--etiqueta saneamiento` deja solo P-api-movil-21 (su parte de despliegue). Abiertos totales: 35.
- Incidente: `docs/planes/2026-10-04-panel.md` (sin rastrear, de otra sesión) bloqueaba `worktree-integrar.sh`; con permiso del usuario se apartó al scratchpad y se restauró idéntico (SHA-256).
Pendiente: merge de `plan/saneamiento` en `main` (decisión del usuario); después, plan `panel`.

### 2026-10-04 — Plan `triage`: 68 → 46 pendientes abiertos, todos con destino
Hecho:
- Plan congelado (`7eac70e`) tras `juez-plan` con 2 bloqueantes corregidos (dos `grep "T2: "`/`"T3: "` en T4 que pasaban siempre por el historial).
- 22 pendientes cerrados sin código (`cierra:` en el plan); los 46 restantes etiquetados: despliegue 16, saneamiento 17, expo 5, panel 4, empresa 5 (P-api-movil-21 en dos).
- T1: `pendientes.py` reconoce `### Etiquetas`, muestra `[destino]` y filtra con `--etiqueta`; avisa id inexistente, forma inválida y destino repetido.
- T2: `convenciones-proyecto` § Worktrees (limpieza de la junction) y § Stack (`SitioAdministracion.login` al actualizar Django). T3: `docs/01` § 4.1, la app redimensiona a 1600 px antes de subir.
- Verificación TODO en PASA 0/25 (verificador y verificador-b, HEAD `7b896c4`); `main` recibió `plan/triage` con `merge --no-ff` (`db801d9`). Las 2 decisiones se copiaron a `docs/decisiones.md`.
- Incidente: `worktree-integrar.sh` mergeó pero no pudo quitar `worktrees/triage-T1` (cwd del shell del principal adentro, caso de P-herramientas-plan-2); se quitó la carpeta vacía con `rmdir` y la rama con `git branch -d`; venv intacto.
Pendiente: plan `panel`.

### 2026-10-04 — Fusión en `main` de `herramientas-plan`
Hecho:
- `main` recibió `plan/herramientas-plan` con `merge --no-ff` (`bb8b5bb`), con la verificación TODO en PASA 0/46 (verificador y verificador-b, HEAD `7b62861`).
- Las 3 decisiones del plan se copiaron al final de `docs/decisiones.md` (integración numerada, reemplaza a 2026-10-03; presupuesto `--subtarea`; exit 3 de `worktree-integrar.sh`).
- `docs/pendientes-snapshot.json` (`pendientes.py --json`) generado para el triage desde Claude Desktop; sin versionar (excluido en `.git/info/exclude`).
Pendiente: triage de pendientes; después, plan de despliegue.

### 2026-10-04 — Plan `herramientas-plan`: presupuesto por subtarea, integración segura, plantilla y agentes registrados
Hecho:
- Plan congelado (`605202d`) tras `juez-plan` con 2 bloqueantes corregidos: un grep con backticks dentro del código en línea y un presupuesto `--subtarea T5` que pasaba siempre.
- T1: `presupuesto.sh … --subtarea T<n>` mide los commits no-merge `T<n>:`/`T<n>b:`; el modo por rutas sigue.
- T2: `worktree-integrar.sh` busca el worktree en `git worktree list` y aborta con exit 3 si el cwd está dentro.
- T3: `juez-plan` y `verificador-b` no se registraban porque su `description` sin comillas tenía `: ` (YAML inválido); entrecomillado y `test_agentes.py`. Tras integrar, la sesión los listó como tipos. El veredicto del verificador se cuenta sobre la lista.
- T4: la plantilla usa `### T<n> — Integración (principal)` por ola y `--subtarea T<n>`; CLAUDE.md § 4 y § 5 actualizados.
- Verificación TODO (HEAD `7b62861`): PASA 0/46 en `verificador` y `verificador-b`.
- Cierra P-contrato-app-3, -4, -5, -12 y P-limites-ingreso-17; deja P-herramientas-plan-1 a -3 (observaciones).
Pendiente: merge a `main` (lo decide el usuario); al fusionar, copiar las 3 decisiones a `docs/decisiones.md`.

### 2026-10-04 — Fusión en `main` de `contrato-app`
Hecho:
- `main` recibió `plan/contrato-app` con `merge --no-ff` (`811d19c`), con la verificación TODO en PASA (verificador y verificador-b, HEAD `52fc995`).
- Antes del merge, por decisión del usuario:
  - cierra P-contrato-app-7 (no aplica: no hay datos previos ni producción; la consulta queda en el pendiente);
  - cierra P-contrato-app-10 (aceptado; la regla de "Puede tocar" no cambia);
  - etiqueta P-contrato-app-2 y -6 como "Diferido a despliegue" y P-contrato-app-9 como "Antes de la etapa Expo";
  - registra P-contrato-app-12 (el total del veredicto del verificador debe calcularse sobre la lista).
- Las 4 decisiones del plan se copiaron al final de `docs/decisiones.md`; la primera reemplaza el 409 de P-api-movil-15 por un 201 con visita nueva marcada.
Pendiente: plan de despliegue.

### 2026-10-04 — Plan `contrato-app`: evidencia de pendientes, atraso máximo, token JSON y contrato OpenAPI
Hecho:
- Plan congelado (`51e92b0`) tras `juez-plan` con 2 bloqueantes corregidos: presupuestos con rutas disjuntas (T3 lleva sus tests a `test_atraso.py`) y la integración del principal como subtarea T4.
- T1 (token y renovación solo JSON, 415), T2 (una pendiente no lleva evidencia; la app crea una visita nueva con incidencia y responde 201) y T3 (`realizada_en` con más de `ATRASO_MAXIMO_HORAS` da 400), cada una en su worktree, verificadas por `verificador` y `verificador-b` y auditadas.
- Por decisión del usuario sobre la auditoría de T3: un reintento tardío con el mismo `cliente_uuid` responde 409 (chequeo en `validate()`) y `ATRASO_MAXIMO_HORAS` queda acotado a 1..8760.
- `docs/api/openapi-v1.yaml` versionado (`cb31993`) y bullet "Contrato de la app" en `docs/01-modelo-y-arquitectura.md` §6.
- Verificación TODO (HEAD `52fc995`): PASA en los dos verificadores; auditor final sin hallazgos de seguridad nuevos.
- Pendientes nuevos: P-contrato-app-1 a -11 (los importantes: -2 y -6, límite de cuerpo en despliegue; -4, `presupuesto.sh` por subtarea; -9, documentación de 400/415 en el contrato).
- Incidente: `worktree-integrar.sh` no pudo borrar el worktree de T1 porque el shell del principal estaba dentro; se limpió a mano (carpeta vacía y `branch -d`) tras `git status` en raíz y worktrees.
Pendiente: merge a `main` (lo decide el usuario).

### 2026-10-04 — Fusión en `main` de `api-movil`
Hecho:
- El usuario aceptó la corrida TODO con FALLA 1/84 (presupuesto de T6, 712/650), aprobada por escrito. `main` recibió `plan/api-movil` con `merge --no-ff` (`a77bbe9`).
- Las 4 decisiones del plan se copiaron al final de `docs/decisiones.md`, más 4 decisiones nuevas del usuario:
  - un exceso de presupuesto se parte en T<n> y T<n>b, y la aprobación escrita queda solo para contrato modificado o criterio defectuoso;
  - P-api-movil-15: una pendiente no puede tener evidencia;
  - P-api-movil-16: `ATRASO_MAXIMO_HORAS = 168`;
  - P-api-movil-20: token solo JSON.
- A precisar al planificar P-api-movil-15: la decisión dice "409 y crea una nueva con `incidencia_asignacion`". Un 409 no crea nada, así que hay que elegir entre 409 sin crear y 201 con la visita nueva marcada.
- Pendientes abiertos: 63 (`py -3 .claude/hooks/pendientes.py`).
Pendiente: plan corto antes de producción (P-api-movil-15, -16 y -20).

### 2026-10-04 — Plan `api-movil`: API `/api/v1/` para la app de empleados
Hecho:
- Plan `docs/planes/2026-10-03-api-movil.md` (rama `plan/api-movil`), 7 subtareas en 5 olas, todas integradas:
  - T1: drf-spectacular con sidecar, errores `{detalle, campos}`, paginación, throttles y token normalizado.
  - T2: catálogo con ETag.
  - T3: resolver QR.
  - T4: `cliente_uuid`, `recibida_en`, `incidencia_asignacion`, `Foto.codigo`, validador de planilla y memoria de imágenes.
  - T5: servicio `registrar_visita_desde_app`.
  - T6: endpoints de visitas, historial y fotos.
  - T7: flujo de punta a punta y esquema.
- Verificación TODO (verificador y verificador-b coinciden, HEAD `f0aa3e9`): FALLA 1/84. La única FALLA es el presupuesto de T6 (712/650), aprobada por escrito por el usuario: los topes y cortes de subida se agregaron después de congelar el plan.
- Correcciones fuera de la regla de severidad, por decisión del usuario: el formato de error (T1), NaN, textos largos y tipos desconocidos en la planilla (T4), y el corte por `Content-Length` y los topes de texto (T6).
- Cierra P-pendientes-heredados-3, P-limites-ingreso-4 y -7. Deja P-api-movil-1 a -22: tres importantes (15, 16 y 20) para un plan corto antes de producción.
- Incidentes:
  - el cwd de la sesión quedó un rato dentro del worktree de T1 (sin daño, `git status` limpio);
  - la sesión se cortó con T4 a medio informar (recuperado del worktree);
  - un test viejo de rutas (`productos/tests/test_rutas.py`) lo ajustó el principal por decisión del usuario.
Pendiente: decisión del usuario sobre el merge a `main`; al fusionar, copiar las decisiones del plan a `docs/decisiones.md`.

### 2026-10-04 — Fusión en `main` de `limites-ingreso`
Hecho:
- El usuario aprobó la corrida TODO con FALLA 2/78, con el mismo criterio que `menores-abiertos`. La primera FALLA es el contrato modificado (`387c9a7`), que él aprobó. La segunda es el criterio de la ola 2 con un recuento que el propio plan cambia (33 → 27): un defecto del plan, no del código. El cierre global con 27 pasa. Queda escrito en el Registro.
- Se agregaron P-limites-ingreso-16 (regla (b) del juez: recuentos relativos o en el cierre global) y -17 (`worktree-integrar.sh` tiene que abortar si el cwd está dentro del worktree). Los tres importantes de red quedan como "Diferido a despliegue".
- `main` recibió `plan/limites-ingreso` con `merge --no-ff` (`3583a00`). Las 5 decisiones del plan se copiaron al final de `docs/decisiones.md`, que es la primera aplicación de la regla nueva de cierre.
- Pendientes abiertos: 44 (`py -3 .claude/hooks/pendientes.py`).
Pendiente: plan de API.

### 2026-10-03 — Plan `limites-ingreso`: límites por fallos, `'<commit_base>'` desde el Registro y pendientes por plan
Hecho:
- Plan `docs/planes/2026-10-03-limites-ingreso.md` (rama `plan/limites-ingreso`), 5 subtareas en 3 olas, todas integradas.
  - T1: settings `NUM_PROXIES` y cupos.
  - T2: `apps/accounts/limites.py` con tres baldes que cuentan solo fallos, en el panel, `/admin/login/` y el token; `ip_del_cliente`; `crear_usuario` normaliza; test del nonce.
  - T3: `'<commit_base>'` resuelto del Registro.
  - T4: `pendientes.py` y `contexto.sh`.
  - T5: plantilla, `CLAUDE.md` y agentes.
- Contrato modificado (`387c9a7`) por decisión del usuario: el token entra en los baldes de usuario, tras un hallazgo del auditor sobre T1. Los presupuestos pasaron a `'<commit_base>'`. Desde ahí `congelado.sh` sale con 1 y los verificadores dan FALLA formal con todos los criterios en PASA (T2 24/24 y 26/26, T5 10/10).
- La lista de problemas de la bitácora pasó a `docs/planes/2026-10-03-pendientes-heredados.md` (33). Este plan cierra 6 y deja 15 propios (3 importantes: throttles DRF sin /64, IPv4 mapeadas en `::/64`, `NUM_PROXIES` obligatorio en producción).
- Incidente: la integración de T1 no pudo borrar la carpeta del worktree porque la sesión tenía su cwd adentro. Quedó vacía y sin junction, y se limpió con `rmdir` y `git branch -d`.
Pendiente: verificación TODO, decisión del usuario sobre el merge y copiar las decisiones del plan a `decisiones.md` al fusionar.

### 2026-10-03 — Fusión en `main` de `menores-abiertos` y `autenticacion`
Hecho:
- `main` avanzó por fast-forward hasta `plan/menores-abiertos` y recibió `plan/autenticacion` con `merge --no-ff` (sin rebase, para conservar los hashes verificados). Los conflictos fueron solo de `docs/bitacora.md` y `docs/decisiones.md`.
- `menores-abiertos` entró con TODO en FALLA 5/49 (los 4 presupuestos y `congelado.sh`, todos por el contrato modificado `3478391`), aprobado por el usuario por escrito en el Registro del plan. Queda como decisión nueva en `docs/decisiones.md`.
- Los problemas de `paralelismo` que cerró `menores-abiertos` T3 (alcance por prefijo, merge que quedaba con tests en rojo, `rama_base` sin validar) se quitaron de la lista de `autenticacion` en vez de duplicarse.
- Se quitó la junction `venv` de `worktrees/autenticacion` con `cmd /c rmdir` y después el worktree.
Pendiente: plan `limites-ingreso`, en una sesión nueva sobre `main`.

### 2026-10-03 — Plan `autenticacion`: panel con rol administrador, API con JWT, admin solo superusuarios, CSP y LOGGING
Hecho:
- Plan `docs/planes/2026-10-03-autenticacion.md` (rama `plan/autenticacion`, worktree `worktrees/autenticacion`), 4 subtareas en 3 olas, todas integradas; verificación TODO en 6787a16: `verificador` 68/68 PASA, `verificador-b` sin FALLA. `auditor-seguridad` en cada subtarea.
- T1 (config): DRF solo JWT + `IsAuthenticated` + JSON; SimpleJWT 15 min / 7 días con rotación, blacklist y `CHECK_REVOKE_TOKEN`; django-csp 4 (`self` + nonce); `min_length` 12; `AdminSite` solo superusuarios (`config/admin.py`, `config/apps.py`); filtro `config/registro.py` recursivo por subcadena (incluye `telefono` y `contacto`), aplicado también a los loggers `django` y `django.server`; test de `check --deploy` que exige exactamente {W005, W021}.
- T2 (accounts): historial de `User` sin `password` ni `last_login` (y sin registro por login), `AdministradorRequeridoMixin`, `EsAdministrador`/`EsEmpleado`, comando `crear_usuario`.
- T4 (diseño/web): nonce en el `<style>` de `base.html`.
- T3 (panel/api): `/panel/ingresar/` y `/panel/salir/` (empleados rechazados en el formulario, límite por IP y por usuario), `/api/v1/auth/token/` y `/refresh/` con cupos propios, refresh rechazado tras cambio de contraseña, raíz de la API con rol; `test_rutas` invertido.
Incidentes:
- Otra sesión (`menores-abiertos`) cambió la raíz a su rama un segundo después de crear `plan/autenticacion`: los commits del plan cayeron en `plan/menores-abiertos`. Se pasaron por cherry-pick a `plan/autenticacion` (nuevo `commit_base` 6d22ff1) y `plan/menores-abiertos` volvió a cae1152 (con autorización del usuario). Desde ahí la sesión trabajó solo en `worktrees/autenticacion`.
- Integrar T2 falló al borrar el worktree ("Permission denied") porque el shell del principal estaba dentro: el merge sí quedó; se borró la carpeta vacía y la rama a mano (el caso de la decisión del 2026-10-02).
- La sesión se cortó con T2 a medias; se retomó el implementador sobre su worktree.
Pendiente: merge a `main` (decisión del usuario), plan `limites-ingreso`.

### 2026-10-03 — Cierre de los menores de fotos, worktree y plantilla (`menores-abiertos`)
Hecho:
- Plan `docs/planes/2026-10-03-menores-abiertos.md`: una ola, 4 subtareas en paralelo, integradas en `plan/menores-abiertos` (`88a449c`). El juez del plan marcó 3 bloqueantes, corregidos antes de congelar.
  - T1: `imagenes.py` acepta solo JPEG, PNG, WebP y MPO, con tope por formato (16 MP para JPEG progresivo o CMYK), `load()` fuera del `try` y `exif_transpose(in_place=True)`.
  - T2: `clean_imagen` en el inline y en `FotoAdmin` (error de formulario en vez de 500), y `programada_para` y `asignada_por` de solo lectura en una visita cerrada (N5).
  - T3: `worktree-integrar.sh` rechaza prefijos vacíos, compara por segmento, exige un worktree registrado y deshace el merge si fallan los tests o las migraciones; `worktree-crear.sh` valida `rama_base`.
  - T4: la plantilla lleva la integración en `### Trabajo del principal (integración de la ola N)` y aclara que el hook solo ejecuta `### T<n>` y el cierre global.
- El auditor de seguridad encontró en T1:
  - 1 bloqueante: un MPO daba `KeyError` y un 500;
  - 2 importantes: un `ValueError` de un `zTXt` enorme daba un 500, y la memoria seguía sin acotarse.
- El usuario decidió corregir los tres con el contrato ampliado (commit `3478391`, `docs(plan): … — modificado`). Re-auditoría: MPO y `ValueError` cerrados; la memoria sigue abierta como importante (ver Problemas abiertos).
- Verificación final TODO en `88a449c`: `verificador` y `verificador-b` dan FALLA en 5 criterios:
  - todos por el contrato modificado: los 4 de presupuesto y el `congelado.sh` del cierre global;
  - el resto pasa, con 105 tests de Django y 90 de hooks;
  - los presupuestos medidos a mano contra `b437ec1` entran todos: T1 133/160, T2 96/200, T3 122/220, T4 50/100.
- T1 quedó `en curso` en el Registro porque su criterio de presupuesto no pasa. T2 a T4 quedaron `hecha`.
- Incidente: el principal hizo `cd` a un worktree desde su shell persistente, y la decisión del 2026-10-02 lo prohíbe. Se corrigió en el momento, con `git status` en la raíz y en los worktrees: sin daño.
- El merge a `main` queda pendiente de la revisión manual del usuario.

### 2026-10-03 — Correcciones de la auditoría de visitas y bloqueo de la reversión desde el historial; fusión en main
Hecho:
- Plan `docs/planes/2026-10-03-visitas-auditoria.md` (una ola, 4 subtareas en paralelo; TODO PASA 48/48): `procesar_imagen` con tope de píxeles, `draft()`, comentario descartado y `ValidationError` para no imágenes; historial de `ProductoAplicado` (`visitas/0002`) y borrado del archivo al borrar o reemplazar una foto; `registrar_visita_realizada` con `select_for_update`, sin retroceder el proyecto ante visitas atrasadas y sin fechas futuras (tolerancia 10 min); admin con `CAMPOS_EVIDENCIA` de solo lectura en visitas no pendientes, sin borrado de visitas ni fotos y con fotos/productos bloqueados. T4 necesitó una ronda de corrección del principal (inline de fotos sin borrado y `visita` de solo lectura en los admins sueltos).
- La re-auditoría encontró un bloqueante nuevo (N2): revertir desde el historial de simple_history devolvía una visita realizada a pendiente y reactivaba QR regenerados. Por decisión del usuario, plan `docs/planes/2026-10-03-historial-revert.md` (3 subtareas; TODO PASA): `history_form_view` niega el POST en `VisitaAdmin` y `SitioAdmin`; un EXIF corrupto ya no da 500. Re-auditoría: N2 cerrado; un menor nuevo (ver Problemas abiertos).
- `juez-plan` corrido como agente Plan en los dos planes: 1 bloqueante en `visitas-auditoria` (test de doble registro que pasaba antes del cambio), corregido antes de congelar; 0 en `historial-revert`.
- `main` avanzó por fast-forward hasta `plan/historial-revert` (incluye `visitas`, `visitas-auditoria` e `historial-revert`; 95 tests).
Pendiente: menores de fotos y N5 (Problemas abiertos), después el plan de API/autenticación.

### 2026-10-03 — Registro de visitas (Visita, Foto, ProductoAplicado) y correcciones de Proyecto
Hecho (plan `docs/planes/2026-10-03-visitas.md`, rama `plan/visitas`, primer plan con olas y worktrees):
- Ola 1 en paralelo: T1 `Proyecto.__str__` tolera un sitio inexistente; T2 `suprimir_sitio` borra `Proyecto.history` del sitio; T3 modelos `Visita` (historial sin coordenadas ni `datos`, `esquema_planilla`, `clean()` de estado), `Foto` (uuid4, 1600 px, JPEG sin EXIF en `apps/visitas/imagenes.py`) y `ProductoAplicado`, con `visitas/0001_initial`.
- Ola 2 en paralelo: T4 `apps/visitas/services.py::registrar_visita_realizada` (valida origen, coordenadas, foto y motivo; copia el esquema; actualiza encargado y próxima visita en un `atomic`); T5 admin técnico con inlines y `estado`/`realizada_en`/`esquema_planilla` de solo lectura.
- Cada subtarea: PASA de `verificador` y `verificador-b`; TODO PASA 60/60 en `05b8cef` (77 tests). `juez-plan` (corrido como agente Plan, no está registrado como tipo) marcó 2 bloqueantes antes de congelar: presupuesto de T3 compartido con T5 y bloques `### Ola` que nadie ejecuta; se corrigieron moviendo el procesamiento de fotos a T3, el admin a T5 y los criterios de integración al cierre global.
- `auditor-seguridad`: 0 bloqueantes, 6 importantes, 8 menores (en Problemas abiertos).
- Incidente: un `cd` del principal al worktree de T3 desde el shell persistente (contra la decisión del 2026-10-02); se volvió a la raíz y `git status` de todos los árboles estaba limpio.
Pendiente: decidir el merge de `plan/visitas` a `main` y si los hallazgos importantes del auditor se corrigen antes, en un plan propio.

### 2026-10-02 — Paralelismo con multiagentes (worktrees, plan por rama, rutas por app)
Hecho:
- Plan `docs/planes/2026-10-02-paralelismo.md`, congelado en 2823e82 sobre la rama `plan/paralelismo`. El juez-plan encontró 4 bloqueantes y 1 observación; se corrigieron antes de congelar.
- Ola 1: T2, scripts `worktree-crear.sh` y `worktree-integrar.sh` (junction de `venv`, control de alcance, merge `--no-ff`). Se hizo inline porque era el bootstrap.
- Ola 2: T1 (el plan se deriva de la rama), T3 (`api_urls.py`/`panel_urls.py` por app, routers de una línea, `templates/panel/base.html`) y T4 (documentación). Las tres en paralelo, cada una en su worktree, integradas con los scripts.
- Ola 3: T5, prueba de fuego. Dos worktrees (clientes y productos), dos implementadores en paralelo, integración con exit 0 y salida literal en el Registro.
- pytest instalado en `py -3` por decisión del usuario.
- Cada subtarea dio PASA con verificador y verificador-b.
- auditor-seguridad: T1 sin hallazgos. En T2, 1 bloqueante (un renombre esquivaba el control de alcance), corregido en 1bf9878 con un test que se vio fallar antes del cambio. Los hallazgos menores quedan en Problemas abiertos.
- Incidente: en T3, `git worktree remove` dio "Permission denied" porque el shell del principal tenía el cwd dentro del worktree. Quedó anotado en el Registro y como decisión.
- Verificación final: TODO PASA 69/69 (verificador y verificador-b) en de25aee. El usuario aprobó el merge: `main` avanzó por fast-forward hasta 8ad718d y se borró la rama `plan/paralelismo`.

### 2026-10-02 — Acciones de Sitio por rol administrador (H1-a, H3-a)
Hecho:
- Plan `docs/planes/2026-10-02-acciones-sitio.md`, congelado en e6f47e4. El juez-plan dio 0 bloqueantes y 1 observación, que se aplicó.
- Decisiones del usuario: H1-a con la opción (b) y H3-a aprobado. Las dos quedaron en `docs/decisiones.md`.
- T1 (084e253):
  - "Suprimir datos (Ley 25.326)" es una acción separada, con confirmación, que borra el sitio y su historial e informa qué sitios tienen proyectos.
  - `regenerar_qr` exige rol administrador, pide confirmación, acepta como máximo 20 sitios y guarda el motivo en el historial con `update_fields`.
- El test de permisos se vio fallar antes del cambio. Los tests de confirmación del admin no se corrieron antes de implementar.
- verificador y verificador-b dieron PASA 18/18. Verificación final: TODO PASA 25/25 en 1d03e23, 54 tests.
- auditor-seguridad: H1-a, H3-a y H3-b CERRADOS. Hay un hallazgo nuevo menor, sobre el historial de Proyecto de un sitio suprimido (ver Problemas abiertos).

Incidente: el implementador corrió `ruff format` y tocó `apps/sitios/models.py`, que no tenía permitido. Lo restauró, y el diff del commit sobre ese archivo está vacío.

A medias: nada del plan.

### 2026-10-02 — Correcciones de la auditoría de dominio (H1–H4)
Hecho:
- Plan `docs/planes/2026-10-02-auditoria-dominio.md`, congelado en 4d8223d. El juez-plan dio 0 bloqueantes y 3 observaciones, aplicadas antes de congelar. Decisión de H1 en `docs/decisiones.md`.
- Una ola en paralelo con worktrees, integrada en 9b2115d:
  - T1: historial de Sitio sin contacto ni teléfono, `suprimir_sitio`, `regenerar_qr` y la acción del admin (1298e73).
  - T2: encargados validados en `save()` como empleados activos, solo al asignarlos (20456ae).
  - T3: dígito verificador del CUIT (07e536e).
- T1 y T2 vieron fallar sus tests antes de implementar; T3, uno de los dos.
- verificador y verificador-b dieron PASA en cada subtarea. Verificación final: TODO PASA 40/40 en 64fb555, con 47 tests.
- auditor-seguridad: H2 y H4 CERRADOS; H1 y H3 CERRADO PARCIAL, con dos hallazgos nuevos importantes (H1-a y H3-a) y varios menores (ver Problemas abiertos).

A medias: H1-a y H3-a, que esperan una decisión del usuario.

### 2026-10-02 — Modelos de dominio
Hecho:
- Commit aparte de los cambios a mano del usuario (bad5c80).
- Plan `docs/planes/2026-10-02-modelos-dominio.md`, congelado en ced3334. El juez-plan lo revisó en dos rondas: primero 3 bloqueantes, después 1. Todos se corrigieron antes de congelar.
- Ola 1, en paralelo con worktrees (junction `venv` → raíz, `venv` en `.git/info/exclude`), integrada en c4cb9cb:
  - T1: Cliente y Sitio con QR e historial; simple_history activado (d296031).
  - T2: TipoServicio, CampoPlanilla y fixture de 9 servicios (2215f95).
  - T3: Producto (a272650).
- Ola 2: T4, Proyecto con `estado_visita`, encargados empleados e historial (d126350).
- verificador y verificador-b dieron PASA en cada subtarea. Verificación final: TODO PASA 51/51 en 60d41f8, con 37 tests.
- auditor-seguridad: 0 bloqueantes, 1 importante (H1) y 3 menores, todos abiertos.

A medias:
- Los tests nuevos no se vieron fallar antes de implementar: los implementadores escribieron el test y el modelo juntos.
- El criterio literal `loaddata tipos_servicio` del pedido se reemplazó por un `[test]` que carga el fixture.

### 2026-10-01 — Espacios en ALLOWED_HOSTS
Hecho: plan `docs/planes/2026-10-01-hosts-espacios.md` (congelado en 734d06a, nivel chico, inline). `dev.py` y `prod.py` recortan espacios y descartan vacíos en `ALLOWED_HOSTS` (24e44a0); dos tests nuevos, vistos fallar antes del cambio. Verificación TODO PASA 12/12. El usuario decidió diferir la barrera por hosting y las IP privadas al plan de despliegue: hoy el proyecto es solo desarrollo. · A medias: nada.

### 2026-10-01 — Corrección de los hallazgos de la auditoría del esqueleto
Hecho: plan `docs/planes/2026-10-01-hallazgos-esqueleto.md` (congelado en 8f23dee; juez-plan en dos rondas, pasó de 7 bloqueantes a 1 y ese último se corrigió moviendo el trabajo del principal a T4). T1 barrera de hosts en `dev.py`, `.env.example` sin `DJANGO_ENV` fijo y HSTS de 3600 s sin subdominios ni preload (afdfc0e); T2 `app_name` en web, panel y api (a5f8b65); T3 fuentes Barlow en `static/fonts/` sin Google Fonts, y corrección del test de `data-tema` (a91fc9f); T4 decisiones y `docs/02-diseno.md` (338b81b, inline). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 43/43 en 1c43751. auditor-seguridad: hallazgos 2, 3 y 4 corregidos; el 1 corregido a medias (ver Problemas abiertos). · A medias: el hueco de la barrera, que depende de saber qué hosting se usa.

### 2026-10-01 — Arranque del repositorio y plan esqueleto
Hecho: pasos 2 a 5 de `docs/ARRANQUE.md`. Hooks y 16 skills copiados de TerritoryOS (tests de hooks: 70 OK), `git init`, venv con Python 3.13, `.gitattributes` (`*.sh` en LF), `images-for-content/` fuera de git. Plan `docs/planes/2026-10-01-esqueleto.md` (congelado en 37f1ec7, juez-plan en dos rondas: 4 bloqueantes corregidos antes de congelar): T1 base del proyecto y `accounts.User` con rol (fb08f0f), T2 diez apps y prefijos de URL con vistas provisorias (f9677fa), T3 `base.html` con tokens de ambos temas y logo (ced36a0). verificador y verificador-b PASA en cada subtarea; verificación final TODO PASA 50/50 en b44c4bf; `check --deploy` con settings de producción sin avisos. auditor-seguridad: 0 bloqueantes, 4 hallazgos abiertos (ver Problemas abiertos). · A medias: nada del plan; los hallazgos del auditor quedan para decidir.

### 2026-09-29 — Base del repositorio
Hecho: se crea la carpeta del proyecto con el esquema de trabajo con agentes copiado de TerritoryOS y adaptado a un solo repositorio Django: `CLAUDE.md`, `.claude/agents/` (implementador, verificador, verificador-b, juez-plan, refutador, auditor-seguridad), `.claude/hooks/`, `.claude/skills/convenciones-proyecto/`, `docs/plantilla-plan.md`, `docs/decisiones.md`. Documentos fuente: `docs/00-contenido-fuente.md` (transcripción de la Carta de Servicios), `docs/01-modelo-y-arquitectura.md` (modelo de datos, roles, flujos, estructura), `docs/02-diseno.md` (tokens del tablero elegido, dirección A "Industrial certificada"). Diseños en el lienzo de claude.ai: https://claude.ai/artifact/MtQNQtkxRLrvi4TiePksNk · A medias: no hay código; `git init` y primer commit pendientes.
