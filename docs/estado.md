# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-14
Plan activo: soporte-app-operario (`docs/planes/2026-11-14-soporte-app-operario.md`, congelado, commit_base 2229493; ninguna T empezada)
Mergeado: recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3 en `main` (2026-11-14). Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| soporte-app-operario | plan/soporte-app-operario | raíz (las T en `worktrees/soporte-app-operario-T<n>`) | libre: la retoma la sesión siguiente |

## Pendiente inmediato
- Ejecutar soporte-app-operario: ola 1 = T1 (visitas) y T2 (empresas) en paralelo, luego T3 (integración, rutas y contrato, del principal); ola 2 = T4, T5, T6 en paralelo y T7 (cierre con revisor y auditor-seguridad).
- Después: preparación del despliegue en Railway (pendientes `despliegue`) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- GitHub: cuenta `WirkraftGruppe` en `gh` y en `.git/config`; Claude abre los PR con `gh pr create`.
- La base de desarrollo de la raíz es anterior a la demo actual: `manage.py cargar_demo` antes de probar.
- Suite de Django: 981 tests en ~101 s; `--parallel` descartado.

## Esperan tu decisión
- Ninguna.
