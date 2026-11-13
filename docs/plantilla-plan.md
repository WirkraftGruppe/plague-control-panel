# Plan: <título corto>

<!--
Copiar a docs/planes/AAAA-MM-DD-<slug>.md. Ciclo completo: CLAUDE.md § Rutas de trabajo y
convenciones-proyecto § Método.
  1. Se escribe, se corre `py -3 .claude/hooks/revisar_plan.py <plan>` y el `revisor` en modo plan;
     el usuario aprueba. Cada veredicto va a `### Revisiones`.
  2. Se commitea solo, ANTES de lanzar el primer subagente:  git commit -m "docs(plan): <slug>"
  3. El hash de ese commit se anota como `commit_base:` en `## Registro de verificación`
     (debajo del corte), nunca en el encabezado. Desde ahí los criterios están congelados.
  4. Cada subtarea se delega con su bloque Criterios literal, se commitea `T<n>: …` y se corre
     `py -3 .claude/hooks/verificar.py tarea <plan> T<n>`. Un FALLA vuelve al implementador 2 veces
     como máximo.
  5. Al final: `verificar.py todo <plan>`, `revisor` en modo cierre, `auditor-seguridad` si
     `seguridad: sí`, `py -3 .claude/hooks/medir_metodo.py --registrar docs/metodo/metricas.md` y un
     solo commit `cierre: <slug>` (el hook `commit-msg` exige el recibo en PASA).
Lo que está entre <> se reemplaza; los comentarios se borran. Excepción: en los criterios de
presupuesto, `'<commit_base>'` queda literal y entre comillas simples; `presupuesto.sh` lo resuelve
con la línea `commit_base:` del Registro.

Corte del congelado: todo lo anterior a `## Registro de verificación` queda congelado con el commit
`docs(plan): <slug>` y lo comprueba `bash .claude/hooks/congelado.sh <plan> <slug>`. De ahí hacia abajo
(commit_base, tabla, revisiones) lo actualiza el principal durante la ejecución. Un cambio de contrato
es un commit nuevo `docs(plan): <slug> — modificado: <motivo>`, decidido por el usuario, con su línea
`(usuario)` y el hash en `docs/decisiones.md`.

El cierre global no va en el plan: `verificar.py` lo toma de `.claude/hooks/cierre_global.json`.
-->

- **slug**: `<slug>`
- **fecha**: AAAA-MM-DD
- **objetivo**: <una oración: qué cambia para el usuario final cuando esto está hecho>
- **fuera de alcance**: <qué NO se toca, explícito>
- **áreas**: web | panel | api | dominio (modelos y servicios) | infraestructura
- **ruta**: completo | ligero <!-- ligero: hasta 10 archivos, sin seguridad: sí, migraciones, carpetas ni comodines en Puede tocar -->
- **seguridad**: sí/no — <si sí: qué toca (auth, roles, get_queryset de la API, fotos, QR, geolocalización, certificados, settings de producción, datos personales) y por lo tanto corre también `auditor-seguridad`>

## Contexto mínimo

<3 a 8 líneas. Qué existe hoy, qué está roto o falta, y la decisión de diseño tomada.
Enlaces a archivos concretos con ruta, y a la sección de `docs/01-modelo-y-arquitectura.md`
que aplica. Sin narrativa.>

## Olas

<!-- Las olas siguen el grafo de FK entre apps (convenciones-proyecto § Olas por grafo de FK). Dentro de
una ola todas las subtareas corren en paralelo, cada una en su worktree; la ola siguiente ramifica desde
la integración de la anterior (subtarea `Integración (principal)`). Si el plan no necesita paralelismo,
una sola ola. -->

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | <apps sin FK entre sí> |
| 2 | T4, T5 (integración) | <apps que dependen de la ola 1> |

## Subtareas

<!--
Reglas para escribir criterios (las hacen cumplir `revisar_plan.py` y `verificar.py`, no el implementador):
- Solo tipos permitidos: [cmd] [cmd-falla] [existe] [no-existe] [grep-1] [grep-0] [test]
- Comandos completos y literales. Los de Django llevan siempre el prefijo canónico:
  PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py …
- Toda subtarea que agrega comportamiento lleva al menos un [test]; toda subtarea que corrige un
  defecto, un [test] que reproduce el defecto y fallaba antes.
- Un [test] se escribe como comando completo y tiene que ser NUEVO respecto de commit_base:
  PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test <ruta.punteada.Clase.test_nombre> --keepdb
  Los tests de hooks usan pytest: py -3 -m pytest .claude/hooks/<archivo>::<función> -q
- Prohibido: "funciona", "tests pasando", "revisado", "sin regresiones", "quedó implementado".
- Dos subtareas no escriben el mismo archivo ni crean migraciones en la misma app en paralelo.
- `Puede tocar` respeta la tabla de propiedad de `convenciones-proyecto`: nada de otro dueño.
- Presupuesto: `presupuesto.sh . '<commit_base>' <N> --subtarea T<n>` mide los commits `T<n>:` (sin
  merges; también suma `T<n>b:`, por eso ese sufijo no se usa). Se fija antes y nunca se sube: si el
  trabajo no entra, lo que falta va en una subtarea nueva `T<m>` con presupuesto y criterios propios,
  como contrato modificado. No es golf: no se recortan comentarios, docs ni tests para entrar.
- Las subtareas se llaman siempre T<n>: solo se reconocen `### T<n>` y las filas `| T<n> |`.
-->

### T1 — <título imperativo, p. ej. "Crear el modelo Sitio con qr_codigo único">

- **Ola**: <n>
- **Depende de**: — | T<n>
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0001_initial.py`, `apps/sitios/tests/test_models.py`
- **No puede tocar**: `docs/planes/`, `config/settings/`, migraciones existentes de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models
- **Worktree**: sí (por defecto; `no` solo si es pasivo o un único archivo de documentación)
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

### T3 — Integración ola 1 (principal)

<!-- Integración por ola: cada ola termina con una subtarea `### T<n> — Integración ola <k> (principal)`
(la de la última ola es la última subtarea numerada). Es una `### T<n>` como las demás: tiene fila en la
tabla del Registro y `verificar.py tarea` ejecuta sus criterios. Presupuesto: si solo hace merges y
commits `registro:`, `--subtarea T<n>` mediría 0 y pasaría siempre; entonces "no aplica", salvo que el
principal haga commits `T<n>:` de ajuste. -->

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . <rama_base>` de cada subtarea, no los informes.
  2. Desde el worktree de la rama destino (no desde el de la subtarea: exit 3), `bash .claude/hooks/worktree-integrar.sh <slug> T<n> plan/<slug> <ruta>...` por cada subtarea de la ola, de a una, con `verificar.py tarea` tras cada integración.
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

### T5 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T4)
- **Depende de**: T4
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . <rama_base>` de cada subtarea, no los informes.
  2. Desde el worktree de la rama destino, `bash .claude/hooks/worktree-integrar.sh <slug> T4 plan/<slug> <ruta>...`.
  3. Cablear `apps/api/urls.py` y `apps/panel/urls.py`, migrar y ajustar imports si hace falta.
  4. Con todo integrado, el cierre: `verificar.py todo`, `revisor` en modo cierre y el commit `cierre: <slug>`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T5:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T5`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/<slug> | grep -q "T4: integra <slug>-T4"`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): <slug> — modificado: <motivo>`. -->

commit_base: <hash del commit docs(plan): <slug>>

<!-- Estado: pendiente | en curso | pendiente de decisión | hecha (solo después de ver pasar sus
criterios). Commit: hash corto del último commit `T<n>:`. Recibo: `PASA AAAA-MM-DD` del recibo
de `verificar.py`; un veredicto vale solo para el HEAD verificado. -->

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | pendiente | | |
| T2 | pendiente | | |
| T3 | pendiente | | |
| T4 | pendiente | | |
| T5 | pendiente | | |

### Revisiones

<!-- Una fila por veredicto del `revisor`, con sus números literales; Fecha como AAAA-MM-DD HH:MM
(hora local); Modo: plan o cierre. `SIN HALLAZGOS` se anota con ceros. Un contrato modificado exige una
fila posterior al commit `modificado`. -->

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|

Auditoría: <veredicto de `auditor-seguridad` o "no aplica">
Hallazgos: <cada uno con su disposición: corregido | pendiente P-<slug>-<n> | espera decisión>

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

- AAAA-MM-DD — decisión — motivo — (usuario|agente) — reemplaza a: (nada|fecha)

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
