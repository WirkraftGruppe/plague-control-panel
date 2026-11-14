# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-14
Plan activo: ninguno. soporte-app-operario cerrado (`plan/soporte-app-operario`, PR abierto a `main`, lo fusiona el usuario).
Mergeado: recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3 en `main` (2026-11-14). Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| soporte-app-operario | plan/soporte-app-operario | raíz (sin worktrees de subtareas) | libre: espera la fusión del PR |

## Pendiente inmediato
- Fusionar el PR de soporte-app-operario (usuario); después, `git fetch` y `git merge --ff-only` de `main`.
- Probar en el navegador la hoja de QR (`/panel/sitios/<pk>/qr/`) e imprimirla, el alta múltiple y la ficha del turno con reportes (usuario; tras `manage.py migrate`).
- Después: preparación del despliegue en Railway (pendientes `despliegue`) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- GitHub: cuenta `WirkraftGruppe` en `gh` y en `.git/config`; Claude abre los PR con `gh pr create`.
- La base de desarrollo de la raíz es anterior a la demo actual: `manage.py cargar_demo` antes de probar.
- Suite de Django: 1024 tests (987 al integrar T2, en 105 s); `--parallel` descartado.

## Esperan tu decisión
- P-soporte-app-operario-11: una visita con solo reportes de puntos no revisados no se cierra, nunca llega al contador de incidencias y al reabrirse trae los reportes del día anterior. ¿Se permite cerrarla con solo reportes, se cuentan también las pendientes o canceladas, o se mueven los reportes al reabrir?
