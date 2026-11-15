# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-15
Plan activo: ninguno.
Mergeado: ajustes-api-app-base (PR #10), soporte-app-operario (PR #8 y #9), recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3 en `main`. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| (ninguno) | — | — | libre |

## Pendiente inmediato
- Avisar a `detach-app`: P-app-base-1 a -5 resueltos; `usuario` de la raíz pasó a objeto.
- Probar en el navegador, tras `manage.py migrate`: hoja de QR con Imprimir, alta múltiple, ficha del turno con reportes y una visita "Cerrado sin revisiones" (usuario).
- Después: preparación del despliegue en Railway (pendientes `despliegue`) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- GitHub: único remoto `origin` (`WirkraftGruppe/plague-control-panel`), `main` sigue a `origin/main`; cuenta `WirkraftGruppe` en `gh` y en `.git/config`; Claude abre los PR con `gh pr create`.
- Suite de Django: ~1050 tests (`verificar.py todo` completo en ~190 s); `--parallel` descartado.

## Esperan tu decisión
- Ninguna.
