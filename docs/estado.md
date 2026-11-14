# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-14
Plan activo: (ninguno)
Mergeado: acelerar-tests (PR #4), robustez-listados (PR #1), el ancho del panel de nuevo turno (PR #2) y el estado (PR #3) en `main` (2026-11-14). Antes: multiempresa, metodo-v2, protocolo-decisiones, diseno-panel y ajustes-flujo. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| recibo tras el cierre (directo) | recibo-tras-cierre | raíz | PR pendiente |

## Pendiente inmediato
- Siguiente: preparación del despliegue en Railway (pendientes con etiqueta `despliegue`) → app móvil (`expo`).
- Fusionar `recibo-tras-cierre` (PR #7: `recibo_pendiente.py` no pide verificar tras un cierre que solo toca docs de proceso). La guarda del `cd` ya está en `main` (PR #6).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- Prueba en navegador del primer clic en un marcador y de los filtros de turnos (P-robustez-listados-7), la hace el usuario.
- GitHub: `gh` usa la cuenta activa `WirkraftGruppe` (admin del repo) y Claude abre los PR con `gh pr create`; git fija la misma cuenta con `credential.https://github.com.username` en `.git/config` (sin selector de cuentas).
- La base de desarrollo de la raíz es anterior a la demo actual: `manage.py cargar_demo` antes de probar.
- Suite de Django: 981 tests en ~101 s (MD5 solo en tests); `--parallel` descartado.

## Esperan tu decisión
- Ninguna.
