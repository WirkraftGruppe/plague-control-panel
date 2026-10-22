# Plan: <título corto>

<!--
Copiar a docs/planes/AAAA-MM-DD-<slug>.md.
Flujo (CLAUDE.md § Flujo de trabajo):
  1. Se escribe en modo plan.
  2. Se commitea solo, ANTES de lanzar el primer subagente:  git commit -m "docs(plan): <slug>"
  3. Se anota el hash de ese commit en el Registro (línea `commit_base:`, debajo del corte), nunca
     en el encabezado. Desde ese momento los criterios están congelados.
  4. Cada subtarea se delega con su bloque Criterios copiado literal.
  5. Cada subtarea se commitea (`T<n>: …`) antes de verificarla; las actualizaciones del Registro
     van en commits `registro: …`.
  6. Después de cada subtarea:   verificador  →  <ruta del plan>  T<n>
     Recién con sus criterios en PASA se marca `hecha` en la tabla de estado.
  7. Al final:                    verificador  →  <ruta del plan>  TODO
Todo lo que está entre <> se reemplaza; los comentarios <!-- --> se borran. Excepción: en los
criterios de presupuesto, `'<commit_base>'` queda literal y entre comillas simples (sin comillas,
bash lo toma como redirección). `presupuesto.sh` lo resuelve con `verificar_plan.py --commit-base`,
que lee la línea `commit_base:` del Registro y exige que sea un commit `docs(plan): <slug>`.
Si no resuelve, el criterio es FALLA con `commit_base sin resolver en <plan>: <motivo>`.

Corte del congelado: todo lo anterior a `## Registro de verificación` queda congelado desde el
commit `docs(plan): <slug>` y lo verifica `bash .claude/hooks/congelado.sh <plan> <slug>`
(exit 1 → CONTRATO MODIFICADO; exit 2 → CONTRATO NO CONGELADO). Desde ese encabezado hacia abajo
(commit_base, estado de subtareas, corridas) el principal lo actualiza durante la ejecución.
Un cambio de contrato es un commit nuevo `docs(plan): <slug> — modificado: <motivo>`, decidido por
el usuario.

El hook de cierre (`.claude/hooks/verificar_plan.py`, evento Stop) deriva el plan de la rama
(`plan/<slug>` o `<slug>-T<n>` → `docs/planes/*-<slug>.md`), con `Plan activo:` de
`docs/bitacora.md` como respaldo, y ejecuta los criterios de las subtareas en estado `hecha`, y los
de cierre global cuando todas están `hecha`. Por eso el estado vive en la tabla del Registro, no en los encabezados.
-->

- **slug**: `<slug>`
- **fecha**: AAAA-MM-DD
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): <slug>`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: <una oración: qué cambia para el usuario final cuando esto está hecho>
- **fuera de alcance**: <qué NO se toca, explícito>
- **áreas**: web | panel | api | dominio (modelos y servicios) | infraestructura
- **seguridad**: sí/no — <si sí: qué toca (auth, roles, get_queryset de la API, fotos, QR, geolocalización, certificados, settings de producción, datos personales) y por lo tanto corre también `auditor-seguridad`>

## Contexto mínimo

<3 a 8 líneas. Qué existe hoy, qué está roto o falta, y la decisión de diseño tomada.
Enlaces a archivos concretos con ruta, y a la sección de `docs/01-modelo-y-arquitectura.md`
que aplica. Sin narrativa.>

## Olas

<!-- Las olas siguen el grafo de FK entre apps (CLAUDE.md § 5, "Olas"). Dentro de una ola todas las
subtareas corren en paralelo, cada una en su worktree; la ola siguiente ramifica desde la integración
de la anterior (subtarea `Integración (principal)`). Si el plan no necesita paralelismo, una sola ola. -->

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | <apps sin FK entre sí> |
| 2 | T4, T5 (integración) | <apps que dependen de la ola 1> |

## Subtareas

<!--
Reglas para escribir criterios (las hace cumplir el verificador, no el implementador):
- Solo tipos permitidos: [cmd] [cmd-falla] [existe] [no-existe] [grep-1] [grep-0] [test]
- Comandos completos y literales. Los de Django llevan siempre el prefijo canónico:
  PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py …
- Toda subtarea que agrega comportamiento lleva al menos un [test].
- Un [test] se escribe como comando completo:
  PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test <ruta.punteada.Clase.test_nombre> --keepdb
  (el hook lo ejecuta tal cual con bash; la ruta punteada sola falla con exit 127).
  Los tests de hooks usan pytest: py -3 -m pytest .claude/hooks/<archivo>::<función> -q
- Toda subtarea que corrige un defecto lleva un [test] que reproduzca el defecto.
- Un [test] tiene que ser NUEVO respecto de commit_base.
- Prohibido: "funciona", "tests pasando", "revisado", "sin regresiones", "quedó implementado".
- Dos subtareas no escriben el mismo archivo ni crean migraciones en la misma app en paralelo.
- Presupuesto: `presupuesto.sh . '<commit_base>' <N> --subtarea T<n>` mide los commits `T<n>:`
  (sin merges; también suma `T<n>b:`, por eso ese sufijo no se usa: si el trabajo no entra,
  lo que falta va en una subtarea nueva `T<m>` con presupuesto y criterios propios, como
  contrato modificado). Si se usan rutas en lugar de `--subtarea`, las rutas de presupuesto
  no se solapan entre subtareas: un archivo cuenta en el presupuesto de una sola.
- `Puede tocar` respeta la tabla de propiedad de `convenciones-proyecto`: nada de otro dueño.
-->

<!-- Las subtareas se llaman siempre T<n>: el hook de cierre solo reconoce `### T<n>` y las filas `| T<n> |`. -->
<!-- Integración por ola: cada ola termina con una subtarea numerada `### T<n> — Integración (principal)`
(la de la última ola es la última subtarea numerada), con Ola, Depende de, Pasos, Presupuesto y Criterios.
Es una `### T<n>` como las demás: `verificar_plan.py` y `verificador` ejecutan sus criterios cuando
la tabla de estado la marca `hecha`, y tiene fila en `### Estado de subtareas` y en `### Corridas`.
Presupuesto de la integración: si solo hace merges y commits `registro:`, `--subtarea T<n>` mediría 0
y pasaría siempre; entonces el presupuesto es "no aplica", salvo que el principal haga commits
`T<n>:` de ajuste, y en ese caso lleva `--subtarea T<n>`. -->
### T1 — <título imperativo, p. ej. "Crear el modelo Sitio con qr_codigo único">

- **Ola**: <n>
- **Depende de**: — | T<n>
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0001_initial.py`, `apps/sitios/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models
- **Worktree**: sí (por defecto; `no` solo si es pasivo o un único archivo de documentación)
- **Ruta**: inline | delegada · Evidencia: … · Commit: …
- **Presupuesto**: <N> líneas agregadas (por defecto 400)
- **Qué hacer**: <2 a 5 líneas concretas. Qué modelo, qué campo, qué comportamiento.>
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.SitioTests.test_qr_codigo_se_genera_al_crear --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_models.SitioTests.test_qr_codigo_es_unico --keepdb`
  - `[grep-1]` `grep -n "qr_codigo = models.UUIDField" apps/sitios/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T1`

### T2 — <título>

- **Ola**: <n>
- **Depende de**: T1
- **Puede tocar**: …
- **No puede tocar**: `docs/planes/`, …
- **Skill a leer antes**: …
- **Presupuesto**: <N> líneas agregadas
- **Qué hacer**: <…>
- **Criterios**:
  - `[test]` …
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T2`

### T3 — Integración (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . <rama_base>` de cada subtarea, no los informes.
  2. Desde la raíz (no desde dentro del worktree: exit 3), `bash .claude/hooks/worktree-integrar.sh <slug> T<n> plan/<slug> <ruta>...` por cada subtarea de la ola.
  3. Cablear `apps/api/urls.py` y `apps/panel/urls.py`, migrar y ajustar imports si hace falta.
  4. Crear los worktrees de la ola siguiente con `bash .claude/hooks/worktree-crear.sh <slug> T4 plan/<slug>`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T3:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T3`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/<slug> | grep -q "T1: integra <slug>-T1"`
  - `[cmd]` `git log --oneline plan/<slug> | grep -q "T2: integra <slug>-T2"`

### T4 — <título>

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: …
- **No puede tocar**: `docs/planes/`, …
- **Skill a leer antes**: …
- **Presupuesto**: <N> líneas agregadas
- **Qué hacer**: <…>
- **Criterios**:
  - `[test]` …
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T4`

### T5 — Integración (principal)

- **Ola**: 2 (después de verificar T4)
- **Depende de**: T4
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . <rama_base>` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh <slug> T<n> plan/<slug> <ruta>...` por cada subtarea de la ola.
  3. Cablear `apps/api/urls.py` y `apps/panel/urls.py`, migrar y ajustar imports si hace falta.
  4. Con todo integrado, el cierre global y la verificación `TODO`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T5:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T5`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/<slug> | grep -q "T4: integra <slug>-T4"`

## Criterios de cierre global

<!-- Copiar de CLAUDE.md § "Criterios de cierre global". Reemplazar <archivo> y <slug>. -->

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/<archivo>.md <slug>`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): <slug> — modificado: <motivo>`. -->

commit_base: <hash del commit docs(plan): <slug>>

### Estado de subtareas

<!-- Valores: pendiente | en curso | pendiente de decisión | hecha. Una tarea pasa a `hecha` solo después de ver pasar sus criterios. -->

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |
| T3 | pendiente |
| T4 | pendiente |
| T5 | pendiente |

### Corridas

<!-- Lo completa el principal pegando el veredicto del verificador, sin editar. Una línea por
corrida. Un veredicto vale solo para el HEAD verificado. -->

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| | T1 | | | |
| | T3 | | | |
| | T4 | | | |
| | T5 | | | |
| | TODO | | | |

### Decisiones del plan

<!-- Disyuntivas resueltas durante la ejecución; criterios y escalamiento en
`docs/protocolo-decisiones.md`. Una línea por decisión:
- T<n> — disyuntiva — opciones — elección — motivo (una línea) — autónoma — cómo revertir — decidida por Claude, revisable -->

## Pendientes que deja este plan

<!--
Debajo del corte, lo escribe el principal. `py -3 .claude/hooks/pendientes.py [--json]` lee solo
esta sección de cada plan (los comentarios no cuentan). Abiertos = problemas declarados menos los
cerrados con `cierra:` en cualquier plan. Si no hay nada, dejar las tres subsecciones vacías.

Ejemplo (el id lleva el slug de ESTE plan; severidad: bloqueante | importante | menor | observación;
una línea sangrada continúa la anterior):

### Problemas

- P-<slug>-1 [importante] Texto del problema, con archivo y línea si aplica.
  - detalle opcional, sangrado.

### Decisiones

- AAAA-MM-DD — decisión — motivo — reemplaza a: (nada|fecha)

Esta subsección recibe decisiones fechadas, del usuario o aceptadas al fusionar. Las disyuntivas
autónomas de Claude van en `### Decisiones del plan` (ver `docs/protocolo-decisiones.md`).

### Cierra

- cierra: P-<otro-slug>-3 — cómo lo resuelve este plan

Un problema de otro plan se cierra solo con `cierra:` acá; el plan de origen no se edita.
Al fusionar en `main` solo las Decisiones se copian a `docs/decisiones.md`.
-->

### Problemas

### Decisiones

### Cierra
