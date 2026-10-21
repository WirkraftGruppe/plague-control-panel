# Plan: protocolo de decisiones

<!-- Nivel Chico (solo documentación, sin código, scripts ni dependencias): sin juez-plan. Debe fusionarse antes de `multiempresa`. -->

- **slug**: `protocolo-decisiones`
- **fecha**: 2026-10-21
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): protocolo-decisiones`; el hash se anota en `## Registro de verificación`.
- **objetivo**: ante una disyuntiva de diseño o implementación, el principal decide y registra sin preguntar, escala al usuario solo lo crítico y tiene una conducta por defecto cuando el usuario no responde.
- **fuera de alcance**: código Django, hooks y scripts (`pendientes.py` no cambia), dependencias, `docs/decisiones.md` (se actualiza al fusionar), otros repositorios.
- **áreas**: infraestructura (marco de trabajo: `CLAUDE.md`, `docs/`, `.claude/agents/implementador.md`)
- **seguridad**: no
- **informe previo**: `docs/planes/2026-10-21-protocolo-decisiones-informe-previo.md`

## Contexto mínimo

El informe previo lista cada regla vigente y dice qué hace el protocolo con ella. Respuestas del usuario del 2026-10-21:

- El kit de arranque es `docs/ARRANQUE.md`, porque no existe otro.
- La regla 1 «Preguntar antes de romper» se absorbe en el protocolo: su lugar pasa a ser la referencia y la regla 8 se borra, sin renumerar las reglas 2 a 7.
- La clase Escalable suma la decisión de producto o de negocio, el cambio de arquitectura general, borrar apps o pantallas enteras y el merge a `main`.

## Olas

- Ola 1: T1.
- Ola 2: T2, que depende de T1.
- Ola 3: T3, que depende de T1 y T2 porque copia el protocolo y la referencia ya escritos.
- Sin worktrees: son solo documentos y se escriben sobre la rama `plan/protocolo-decisiones`. No hay subtarea de integración.

## Subtareas

### T1 — Escribir `docs/protocolo-decisiones.md`

- **Ola**: 1
- **Depende de**: nada
- **Puede tocar**: `docs/protocolo-decisiones.md`
- **No puede tocar**: `docs/planes/`, todo otro archivo
- **Skill a leer antes**: `writing-for-agents` (skill del usuario)
- **Worktree**: no (un único archivo de documentación)
- **Ruta**: implementador · Commit: `T1: …`
- **Presupuesto**: 200 líneas agregadas
- **Qué hacer**: un documento autocontenido que no repite `CLAUDE.md`. Escrito en español neutro, sin bloques de código cercados con tres o más backticks (T3 lo embebe dentro de un cerco de cuatro). Secciones:
  1. **Clasificación**.
     - **Autónoma**: es reversible, cae dentro del «Puede tocar» de la subtarea y no toca datos existentes, contratos de `/api/v1/` ni costos. Agregar campos, modelos, índices o migraciones aditivas dentro del alcance es autónomo, y esto se escribe explícitamente.
     - **Escalable**:
       - es irreversible;
       - borra, renombra o cambia el tipo de un campo o de una tabla con datos;
       - toca producción o los settings de producción;
       - cambia `/api/v1/`;
       - agrega una dependencia con costo o licencia;
       - toca un modelo fuera del «Puede tocar»;
       - contradice `docs/decisiones.md`;
       - es una decisión de producto o de negocio;
       - cambia la arquitectura general;
       - borra apps o pantallas enteras;
       - es el merge a `main`.
     - Alterar el alcance del plan no es una decisión: es contrato modificado (§ 4 de `CLAUDE.md`).
     - Ante la duda, escalable.
  2. **Criterios de elección**, en este orden: cumple los criterios congelados del plan; es consistente con el código y con `convenciones-proyecto`; es reversible; es simple.
  3. **Registro**.
     - Cada decisión autónoma va en `### Decisiones del plan`, bajo `## Registro de verificación`, con el formato `- T<n> — disyuntiva — opciones — elección — motivo (una línea) — autónoma — cómo revertir — decidida por Claude, revisable`.
     - Se presentan juntas al cierre de cada ola.
     - Más de cinco decisiones en una subtarea se reporta al cierre de la ola como señal de un plan mal especificado.
     - Una decisión autónoma nunca modifica criterios ni el «no incluye».
     - Al fusionar, las decisiones que el usuario acepta se copian a `docs/decisiones.md` con el formato fechado de esa sección.
  4. **Escalamiento**.
     - El mensaje al usuario lleva la disyuntiva, la opción recomendada ya evaluada, el motivo de la escalada (qué criterio de la clasificación la hace escalable) y la conducta por defecto.
     - Conducta por defecto:
       - la subtarea bloqueada pasa a «pendiente de decisión» en `### Estado de subtareas`, con la pregunta copiada en el plan;
       - el principal sigue con las subtareas que no dependen de ella;
       - la pregunta se repite al cierre de la ola.
     - Nunca se asume la respuesta.
  5. **Dos ejemplos resueltos**, cada uno con un encabezado `## Ejemplo: …`.
     - Uno autónomo: la limpieza de `precision_m` en el formulario sin llamar a `services`, de `robustez-panel` ola 1 (`docs/planes/2026-10-08-robustez-panel.md:446`), con su línea de registro.
     - Uno escalado: la regresión del admin en T1 de `robustez-panel` (`:324`). La disyuntiva es corregir antes de integrar o registrar un pendiente. Se escribe el mensaje al usuario como debería haber sido, incluida la conducta por defecto.
- **Criterios**:
  - `[existe]` `docs/protocolo-decisiones.md`
  - `[cmd]` `test "$(grep -c '^## Ejemplo' docs/protocolo-decisiones.md)" -eq 2`
  - `[grep-1]` `grep -n "pendiente de decisión" docs/protocolo-decisiones.md`
  - `[grep-1]` `grep -n "migraciones aditivas" docs/protocolo-decisiones.md`
  - `[grep-1]` `grep -n "cómo revertir" docs/protocolo-decisiones.md`
  - `[grep-1]` `grep -n "precision_m" docs/protocolo-decisiones.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 200 --subtarea T1`

### T2 — Integrar el protocolo en `CLAUDE.md`, la plantilla y el implementador

- **Ola**: 2
- **Depende de**: T1
- **Puede tocar**: `CLAUDE.md`, `docs/plantilla-plan.md`, `.claude/agents/implementador.md`
- **No puede tocar**: `docs/planes/`, `docs/protocolo-decisiones.md`, `docs/ARRANQUE.md`, `.claude/hooks/`, todo otro archivo
- **Skill a leer antes**: `writing-for-agents` (skill del usuario)
- **Worktree**: no (solo documentación)
- **Ruta**: implementador · Commit: `T2: …`
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - En `CLAUDE.md`:
    - La regla 1 se reemplaza por una referencia a `docs/protocolo-decisiones.md` de 3 líneas como máximo, sin copiar contenido del protocolo.
    - La regla 8 se borra.
    - Se quita toda otra mención de «decidida por Claude, revisable» que quede duplicada.
    - «Navegación de contextos» puede sumar una línea, pero en todo el archivo hay a lo sumo 3 líneas con `protocolo-decisiones`.
  - En `docs/plantilla-plan.md`:
    - El comentario de la subsección `### Decisiones` deja de copiar la regla 8 y remite al protocolo.
    - Se agrega `### Decisiones del plan` bajo `## Registro de verificación`, después de `### Corridas` y antes de `## Pendientes que deja este plan`, con el formato del punto 3 de T1 (incluye «cómo revertir»).
    - El comentario de `### Estado de subtareas` admite el estado «pendiente de decisión».
  - En `.claude/agents/implementador.md`: una línea que remite al protocolo cuando aparece una disyuntiva.
- **Criterios**:
  - `[cmd]` `test "$(grep -c 'protocolo-decisiones' CLAUDE.md)" -ge 1 -a "$(grep -c 'protocolo-decisiones' CLAUDE.md)" -le 3`
  - `[grep-0]` `grep -n "Cuándo preguntar" CLAUDE.md`
  - `[grep-0]` `grep -n "Preguntar antes de romper" CLAUDE.md`
  - `[grep-0]` `grep -n "decidida por Claude, revisable" CLAUDE.md`
  - `[grep-1]` `grep -n "pendiente de decisión" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "cómo revertir" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "^### Decisiones del plan" docs/plantilla-plan.md`
  - `[grep-0]` `grep -n "Claude pregunta al usuario solo cuando" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "protocolo-decisiones" .claude/agents/implementador.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T2`

### T3 — Embeber el protocolo en el kit (`docs/ARRANQUE.md`)

- **Ola**: 3
- **Depende de**: T1, T2
- **Puede tocar**: `docs/ARRANQUE.md`
- **No puede tocar**: `docs/planes/`, todo otro archivo
- **Skill a leer antes**: `writing-for-agents` (skill del usuario)
- **Worktree**: no (un único archivo de documentación)
- **Ruta**: implementador · Commit: `T3: …`
- **Presupuesto**: 230 líneas agregadas (el protocolo íntegro, de 200 líneas como máximo, más el paso que lo explica)
- **Qué hacer**:
  - Agregar un paso a `docs/ARRANQUE.md` con dos indicaciones:
    - el `CLAUDE.md` del repositorio nuevo lleva la referencia de la regla 1, copiada literal de `CLAUDE.md`;
    - `docs/protocolo-decisiones.md` se crea con el bloque embebido.
  - El bloque va entre una línea `<!-- protocolo-decisiones: inicio -->` y una línea `<!-- protocolo-decisiones: fin -->`.
  - Inmediatamente adentro de esos marcadores va un cerco de cuatro backticks: una línea de apertura con cuatro backticks seguidos de `markdown`, el protocolo idéntico y una línea de cierre con cuatro backticks.
- **Criterios**:
  - `[grep-1]` `grep -n "protocolo-decisiones" docs/ARRANQUE.md`
  - `[cmd]` `sed -n '/^<!-- protocolo-decisiones: inicio -->/,/^<!-- protocolo-decisiones: fin -->/p' docs/ARRANQUE.md | sed '1,2d' | sed '$d' | sed '$d' | diff --strip-trailing-cr - docs/protocolo-decisiones.md`
  - `[cmd]` `grep -m1 'docs/protocolo-decisiones.md' CLAUDE.md | tr -d '\r' | grep -qFf - docs/ARRANQUE.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 230 --subtarea T3`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-21-protocolo-decisiones.md protocolo-decisiones`
- `[existe]` `docs/planes/2026-10-21-protocolo-decisiones-informe-previo.md`

## Registro de verificación

commit_base: (se anota tras el commit `docs(plan): protocolo-decisiones`)

### Estado de subtareas

<!-- Valores: pendiente | en curso | pendiente de decisión | hecha. Una tarea pasa a `hecha` solo después de ver pasar sus criterios. -->

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |
| T3 | pendiente |

### Corridas

| fecha | alcance | HEAD | resultado | notas |
|---|---|---|---|---|

### Decisiones del plan

- plan — T3 junto con T2 o separada — una subtarea de 120 líneas o dos — separada, con 230 líneas — el protocolo embebido (≤200 líneas) no entra en las 120 de T2 — autónoma — fundir T3 en T2 como contrato modificado — decidida por Claude, revisable
- plan — dónde va `### Decisiones del plan` — dentro de `## Pendientes que deja este plan` o bajo el Registro — bajo el Registro — `pendientes.py:28` rechaza en `### Decisiones` toda línea sin fecha, y el plan no toca scripts — autónoma — mover la sección y ampliar `RE_DECISION` en otro plan — decidida por Claude, revisable
- plan — worktree por subtarea o rama del plan — worktree o rama — rama del plan, en serie — solo documentos, sin migraciones ni código — autónoma — rehacer cada subtarea en su worktree — decidida por Claude, revisable
- plan — dónde va la referencia en `CLAUDE.md` — lugar de la regla 1 o de la 8 — lugar de la regla 1, y la 8 se borra — evita renumerar las reglas citadas como § 4 a § 6 — autónoma — mover la línea — decidida por Claude, revisable
- plan — `[test]` por subtarea — con o sin `[test]` — sin `[test]` — no se agrega comportamiento de código; los criterios son `grep` y `diff` — autónoma — agregar tests de hooks en otro plan — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-protocolo-decisiones-1 [observación] No existe un kit de arranque real (`instalar_base.py` y el zip de `docs/ARRANQUE.md` no están en ningún repositorio); por decisión del usuario, `docs/ARRANQUE.md` hace de kit.

### Decisiones

- 2026-10-21 — el kit de arranque es `docs/ARRANQUE.md` y embebe el protocolo íntegro — no existe otro archivo de arranque — reemplaza a: (nada)
- 2026-10-21 — la regla 1 de `CLAUDE.md` se absorbe en `docs/protocolo-decisiones.md` junto con la regla 8; Escalable suma producto o negocio, arquitectura general, borrar apps o pantallas y el merge a `main` — una sola regla sobre cuándo preguntar — reemplaza a: 2026-10-07

### Cierra
