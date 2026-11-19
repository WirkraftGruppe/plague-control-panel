# Estado de Detach
<!-- Se reescribe: 25 líneas y 3000 bytes como máximo. Lo histórico, en git y en el registro de sesiones. -->
Actualizado: 2026-11-18
Plan activo: ninguno. trabajo-sin-conexion cerrado en `plan/trabajo-sin-conexion` (recibo `todo` en PASA); PR contra `main` abierto, espera la fusión (usuario).
Mergeado: ficha-sitio-trabajo-hecho (PR #12), ajustes-api-app-base (PR #10), soporte-app-operario (PR #8 y #9), recibo-tras-cierre (PR #7), guardia-cd-worktrees (PR #6), acelerar-tests (PR #4), robustez-listados (PR #1), PR #2 y #3. Desplegado: nada todavía (lo confirma el usuario).

## Carriles
| Plan | Rama | Worktree | Sesión |
|---|---|---|---|
| trabajo-sin-conexion | plan/trabajo-sin-conexion | raíz | corrigiendo el PR #13 (T8 a T11) |
| trabajo-sin-conexion-T9 | trabajo-sin-conexion-T9 | worktrees/trabajo-sin-conexion-T9 | implementador |
| trabajo-sin-conexion-T10 | trabajo-sin-conexion-T10 | worktrees/trabajo-sin-conexion-T10 | implementador |

## Pendiente inmediato
- Decidir P-trabajo-sin-conexion-1 a -4 (abajo) antes de que la app use el contrato nuevo; los que se acepten van a un plan nuevo.
- Avisar a `detach-app`: P-app-base-1 a -5 resueltos; `usuario` de la raíz pasó a objeto; "proxima" depende de la frecuencia; contrato de trabajo-sin-conexion (P-trabajo-sin-conexion-14, con la corrección de P-5).
- Probar en el navegador, tras `manage.py migrate` (entra `visitas.0003`): ficha del turno con "Servicio distinto del asignado" y "Llegó …", ficha con turno abierto (P-ficha-sitio-trabajo-hecho-7), hoja de QR, alta múltiple y "Cerrado sin revisiones" (usuario).
- Después: preparación del despliegue en Railway (pendientes `despliegue`) → app móvil (`expo`).
- Antes del despliegue: `showmigrations` contra producción (P-flujo-sitio-15), lo corre el usuario.
- GitHub: único remoto `origin` (`WirkraftGruppe/plague-control-panel`); cuenta `WirkraftGruppe` en `gh`; Claude abre los PR con `gh pr create`.
- Suite de Django: ~1140 tests (`verificar.py todo` en ~260 s).

## Esperan tu decisión
- P-trabajo-sin-conexion-1: reenvío de `abrir` con `abierta_en` de más de 72 h da 400 aunque haya una abierta.
- P-trabajo-sin-conexion-2 (seguridad): `ultima_revision` con hora en `datos-sin-conexion` muestra cuándo otros empleados estuvieron en cada sitio.
- P-trabajo-sin-conexion-3 (seguridad): apertura y cierre con la hora del teléfono, sin la hora de llegada en la ficha.
- P-trabajo-sin-conexion-4 (seguridad): el cierre nocturno no tiene tope absoluto.
