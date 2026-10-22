# Informe previo: protocolo-decisiones

<!-- Solo lectura, 2026-10-21, sobre main a8d2232. Insumo del plan docs/planes/2026-10-21-protocolo-decisiones.md; no es parte del contrato. -->

Archivos leídos: `CLAUDE.md`, `docs/plantilla-plan.md`, `.claude/skills/convenciones-proyecto/SKILL.md`, `.claude/agents/*.md`, además de `.claude/hooks/pendientes.py` y `.claude/hooks/verificar_plan.py` para ver cómo se leen las secciones.

## Reglas sobre cuándo preguntar, cómo registrar decisiones y qué hacer sin respuesta

| Regla | Ubicación | Qué hace el protocolo |
|---|---|---|
| Regla 8 «Cuándo preguntar» | `CLAUDE.md:29` | **Reemplaza**: la regla se borra. |
| Regla 1 «Preguntar antes de romper» (arquitectura, `/api/v1/`, borrar apps o pantallas) | `CLAUDE.md:22` | **Reemplaza**: pasa a ser la referencia al protocolo, de 3 líneas como máximo, y su contenido se suma a la clase Escalable. Decisión del usuario del 2026-10-21. |
| Marca «decidida por Claude, revisable» | `CLAUDE.md:29`, `docs/plantilla-plan.md:228`; 98 líneas en `docs/decisiones.md` | **Amplía**: formato de línea nuevo, que agrega disyuntiva, opciones y cómo revertir. |
| `### Decisiones del plan` | Solo aparece nombrada (`CLAUDE.md:29`, `plantilla-plan.md:227`, `decisiones.md:114`); no existe como encabezado. | **Amplía**: sección nueva bajo `## Registro de verificación`. `pendientes.py:28` (`RE_DECISION`) rechaza en `### Decisiones` toda línea sin fecha. |
| `## Pendientes que deja este plan`, con `### Decisiones` fechadas | `CLAUDE.md:119-120`, `plantilla-plan.md:208-242`, `pendientes.py:20,28` | **Sin cambios**: sigue recibiendo las decisiones del usuario y las que se copian a `docs/decisiones.md` al fusionar. |
| Contrato modificado (cambiar un criterio o el alcance) | `CLAUDE.md:68`, `:71`, `:123`; `plantilla-plan.md:24-27` | **Sin cambios**: el protocolo la cita, porque alterar el alcance no es una decisión. |
| Pedido que contradice `docs/decisiones.md` | `CLAUDE.md:18` | **Sin cambios**: en el protocolo es escalable. |
| Regla 0: intención ambigua, entonces preguntar | `CLAUDE.md:21` | **Sin cambios**: trata de la autorización para escribir, no de disyuntivas de diseño. |
| Esperar confirmación del resumen de entrada antes de escribir | `CLAUDE.md:17` | **Sin cambios**. |
| El merge a `main` lo decide el usuario | `CLAUDE.md:81` | **Sin cambios**: en el protocolo es escalable. |
| Implementador: cambiar un criterio o partir la subtarea es decisión de otro; pendientes propuestos | `implementador.md:41`, `:61`, `:100-114` | **Amplía**: una línea que remite al protocolo. |
| Auditor: «Cuándo parás y preguntás» | `auditor-seguridad.md:151-158` | **Sin cambios**: es un subconjunto de Escalable, propio del auditor. |
| Verificador, refutador y juez: corregir un criterio o lo inconcluso lo decide el usuario | `verificador.md:52`, `verificador-b.md:52`, `refutador.md:47-48`, `juez-plan.md:56-57` | **Sin cambios**. |
| Preguntar antes de crear markdown nuevo | `convenciones-proyecto/SKILL.md:173` | **Sin cambios**: es una prohibición de código. |
| Qué hacer si el usuario no responde | No hay regla. | **Nuevo**: conducta por defecto con el estado «pendiente de decisión». |

## Archivo de arranque del kit

No existe ningún archivo que embeba los archivos del esquema para copiarlos a repositorios nuevos. Se buscó «kit», «arranque», «bootstrap», «starter», «instalar» y «plantilla-repo» en este repo, en los repos hermanos de `Desktop/WEB`, en `Documents`, en `Downloads` y en `~/.claude`.

- `docs/ARRANQUE.md` tiene los pasos para arrancar un repo. Remite a un `instalar_base.py` y a un zip que no están en ningún repo, y copia los hooks y las skills desde TerritoryOS.
- `macontrol-web/docs/ARRANQUE.md` sigue el mismo patrón.

Decisión del usuario (2026-10-21): el kit es **`docs/ARRANQUE.md`**, que va a embeber el protocolo y la referencia de `CLAUDE.md`.

No existe un archivo de agente para el principal: su rol está en `CLAUDE.md` § «El principal coordina, no ejecuta».

## Casos de ejemplo (robustez-panel, ola 1)

- **Autónomo**: `docs/planes/2026-10-08-robustez-panel.md:446`. El panel y el admin limpian `ubicacion_fijada_por/en` y `precision_m` en el formulario, sin llamar a `services.fijar_ubicacion`.
- **Escalado**: la regresión del admin en T1, `robustez-panel.md:324`. El auditor encontró que se rechazaba el alta en el admin, y el usuario decidió corregirla en T1 antes de integrar (ronda 2, `:325`).
