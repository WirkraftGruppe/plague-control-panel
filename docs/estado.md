# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-13
Plan activo: multiempresa (rama `plan/multiempresa`, en la raíz); `metodo-v2` en `worktrees/metodo-v2`.
Mergeado: protocolo-decisiones, diseno-panel y ajustes-flujo en `main` (último: diseno-panel, 7270e4c). multiempresa y metodo-v2, sin fusionar.

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| multiempresa | plan/multiempresa | raíz | — |
| metodo-v2 | plan/metodo-v2 | worktrees/metodo-v2 | — |

## Pendiente inmediato
- multiempresa: T1 a T14 hechas; verificación TODO 180/181 en 5c7b016 (solo CONTRATO MODIFICADO). Falta la prueba manual del usuario.
- multiempresa: pasar a un plan los pendientes sin dueño y decidir el merge a `main`.
- metodo-v2: T1 a T11 integradas en `plan/metodo-v2`; falta el cierre (auditoría y verificación TODO) y aplicar `docs/metodo/parche-settings.md`.
- Después de multiempresa: despliegue en Railway; antes, `showmigrations` contra producción (P-flujo-sitio-15).
- P-diseno-panel-1 (primer clic en un marcador del panel lateral): en un plan aparte.

## Esperan tu decisión
- Merge de `plan/multiempresa` en `main` tras tu prueba manual.
- Qué pendientes de multiempresa quedan sin dueño y en qué plan se atienden.
- Merge de `plan/metodo-v2` cuando cierre su verificación.
