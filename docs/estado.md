# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-14
Plan activo: acelerar-tests (cerrado en `plan/acelerar-tests`, espera PR y fusión)
Mergeado: robustez-listados (PR #1) y el ancho ajustable del panel de nuevo turno (PR #2) en `main` (2026-11-14). Antes: multiempresa, metodo-v2, protocolo-decisiones, diseno-panel y ajustes-flujo. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| acelerar-tests | plan/acelerar-tests | raíz | cerrado; PR pendiente |

## Pendiente inmediato
- Abrir el PR de `plan/acelerar-tests` desde la web y fusionarlo (suite: 551 s → 101 s; `verificar.py todo`: 2788 s → 531 s).
- Siguiente: despliegue en Railway (pendientes con etiqueta `despliegue`) → app móvil (`expo`). Con la medición nueva, evaluar `--parallel`.
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- `gh pr create` falla en `WirkraftGruppe` ("must be a collaborator"): los PR se abren desde la web hasta que el usuario habilite GitHub CLI en la organización.
- `cd` a un worktree movió el cwd del principal por tercera vez (`docs/metodo/incidentes.md`): conviene que `guardia_bash.py` lo frene; lo decide y aplica el usuario.
- La base de desarrollo de la raíz es anterior a la demo actual: `manage.py cargar_demo` antes de probar.

## Esperan tu decisión
- Ninguna.
