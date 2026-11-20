# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-20
Plan activo: ninguno. coordinacion-operarios cerrado (cierre en PASA); rama `plan/coordinacion-operarios` subida y PR abierto contra `main`, a fusionar por el usuario.
Mergeado: trabajo-sin-conexion (PR #13), ficha-sitio-trabajo-hecho (PR #12), ajustes-api-app-base (PR #10), soporte-app-operario (PR #8 y #9), recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| — | — | sin worktrees activos | libre |

## Pendiente inmediato
- Fusionar el PR de coordinacion-operarios (usuario) y sincronizar `main` (fetch + merge --ff-only).
- En cada entorno, `manage.py migrate`: `visitas.0003` y `0004` (#13) y `productos.0002` y `visitas.0005` (este plan). En desarrollo ya están aplicadas.
- Probar en el navegador: Nuevo turno (asignado a otro), ficha del turno (incidencias nuevas), Cargar visita (dosis y lote), ficha del sitio (duplicadas), formulario de producto, y lo de trabajo-sin-conexion (usuario).
- Avisar a `detach-app` (P-trabajo-sin-conexion-14 y este plan): `revisado_hoy_por`, `revisado_por_otro`, `duplicada_hoy`, dosis opcional según `dosis_variable`, `ultimo_lote` del catálogo, coordenadas opcionales en revisiones, 429 de `datos-sin-conexion` y `visitas/<pk>/abrir/` (solo `abierta_en`, sin ubicación).
- Plan del método: ids de subtarea con letra (P-coordinacion-operarios-8).
- Después: plan de despliegue en Railway (cron de `cerrar_visitas_abiertas` cada hora, P-trabajo-sin-conexion-17) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- GitHub: único remoto `origin`; Claude abre los PR con `gh pr create`. Suite de Django: ~1230 tests.

## Esperan tu decisión
- Nada abierto.
