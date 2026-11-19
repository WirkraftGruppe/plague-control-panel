# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-19
Plan activo: ninguno. trabajo-sin-conexion cerrado de nuevo con las decisiones del 2026-11-19 (T8 a T11, `todo` en PASA); PR #13 contra `main`: lo fusiona el usuario.
Mergeado: ficha-sitio-trabajo-hecho (PR #12), ajustes-api-app-base (PR #10), soporte-app-operario (PR #8 y #9), recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| trabajo-sin-conexion | plan/trabajo-sin-conexion | — | cerrado, PR #13 abierto |

## Pendiente inmediato
- Fusionar el PR #13 (usuario) y, en cada entorno, `manage.py migrate` (entran `visitas.0003` y `visitas.0004`).
- Avisar a `detach-app` del contrato nuevo (P-trabajo-sin-conexion-14): `ultima_revision_fecha`, horas del cliente, `code` nuevos y reenvío de `abrir`.
- Probar en el navegador: ficha del turno con "Llegó … · registrado sin conexión" en apertura, cierre y revisiones, y "Servicio distinto del asignado" (usuario).
- Después: plan de coordinación entre operarios (revisiones de hoy en el resolver de QR) y preparación del despliegue en Railway (incluye el cron de `cerrar_visitas_abiertas`) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- GitHub: único remoto `origin`; Claude abre los PR con `gh pr create`. Suite de Django: ~1170 tests (`todo` en ~270 s).

## Decidido (2026-11-19), espera plan
- Plan de coordinación entre operarios: incidencia de horas inconsistentes en lugar del 400 (P-trabajo-sin-conexion-15 y -16) y 30 pedidos por hora por usuario en `datos-sin-conexion` (P-18, riesgo residual aceptado).
- Plan de despliegue: cron de `cerrar_visitas_abiertas` cada hora (P-trabajo-sin-conexion-17).
