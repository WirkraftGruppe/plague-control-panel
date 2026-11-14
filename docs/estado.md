# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-14
Plan activo: ninguno. soporte-app-operario cerrado de nuevo tras el contrato modificado (c9bc222): T8 a T10 en `plan/soporte-app-operario`, PR nuevo a `main` (el #8 ya estaba fusionado), lo fusiona el usuario.
Mergeado: soporte-app-operario hasta T7 (PR #8), recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3 en `main` (2026-11-14). Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| soporte-app-operario | plan/soporte-app-operario | raíz (sin worktrees de subtareas) | libre: espera la fusión del PR |

## Pendiente inmediato
- Fusionar el PR de T8 a T10 de soporte-app-operario (usuario); después, `git fetch` y `git merge --ff-only` de `main`.
- Probar en el navegador, tras `manage.py migrate`: hoja de QR con el botón Imprimir, alta múltiple, ficha del turno con reportes y una visita "Cerrado sin revisiones" (usuario).
- Después: preparación del despliegue en Railway (pendientes `despliegue`) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- GitHub: cuenta `WirkraftGruppe` en `gh` y en `.git/config`; Claude abre los PR con `gh pr create`.
- La base de desarrollo de la raíz es anterior a la demo actual: `manage.py cargar_demo` antes de probar.
- Suite de Django: 1032 tests (`verificar.py todo` completo en ~295 s); `--parallel` descartado.

## Esperan tu decisión
- Ninguna.
