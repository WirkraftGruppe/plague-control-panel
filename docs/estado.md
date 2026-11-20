# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-20
Plan activo: coordinacion-operarios (`docs/planes/2026-11-20-coordinacion-operarios.md`), congelado en 794af57 (commit_base); ruta completo, seguridad sí, 4 olas (T1 a T9). Sin empezar: la implementación arranca en otra sesión por T1.
Mergeado: trabajo-sin-conexion (PR #13), ficha-sitio-trabajo-hecho (PR #12), ajustes-api-app-base (PR #10), soporte-app-operario (PR #8 y #9), recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| coordinacion-operarios | plan/coordinacion-operarios | worktrees/coordinacion-operarios-T<n> (aún ninguno) | libre: la toma la sesión de implementación |

## Pendiente inmediato
- Implementar coordinacion-operarios desde T1 (ola 1: productos y `cargar_demo`).
- En cada entorno, `manage.py migrate` tras fusionar #13 (`visitas.0003` y `0004`) y, al cerrar este plan, `productos.0002` y `visitas.0005`.
- Avisar a `detach-app` del contrato nuevo (P-trabajo-sin-conexion-14) y, al cerrar este plan, de `revisado_hoy_por`, `revisado_por_otro`, `duplicada_hoy`, dosis opcional, coordenadas opcionales y `visitas/<pk>/abrir/`.
- Probar en el navegador lo de trabajo-sin-conexion (usuario).
- Después: plan de despliegue en Railway (cron de `cerrar_visitas_abiertas` cada hora, P-trabajo-sin-conexion-17) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- GitHub: único remoto `origin`; Claude abre los PR con `gh pr create`. Suite de Django: ~1170 tests (`todo` en ~270 s).
