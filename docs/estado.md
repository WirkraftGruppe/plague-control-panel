# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-14
Plan activo: (ninguno)
Mergeado: acelerar-tests (PR #4), robustez-listados (PR #1), el ancho del panel de nuevo turno (PR #2) y el estado (PR #3) en `main` (2026-11-14). Antes: multiempresa, metodo-v2, protocolo-decisiones, diseno-panel y ajustes-flujo. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| guarda del `cd` (directo) | guardia-cd-worktrees | raíz | PR pendiente |

## Pendiente inmediato
- Siguiente: preparación del despliegue en Railway (pendientes con etiqueta `despliegue`) → app móvil (`expo`).
- Aplicar `docs/metodo/guarda-cd-worktrees.patch` (instrucciones en `docs/metodo/parche-settings.md`): la lista `deny` impide que Claude edite `guardia_bash.py`; lo aplica el usuario.
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- `gh pr create` falla en `WirkraftGruppe` ("must be a collaborator"): los PR se abren desde la web hasta que el usuario habilite GitHub CLI en la organización.
- La base de desarrollo de la raíz es anterior a la demo actual: `manage.py cargar_demo` antes de probar.
- Suite de Django: 981 tests en ~101 s (MD5 solo en tests); `--parallel` descartado.

## Esperan tu decisión
- `recibo_pendiente.py` pide `verificar.py todo` después del commit `cierre:` aunque solo cambien docs (`docs/metodo/incidentes.md`, 2026-11-14): ¿se ajusta el hook?
