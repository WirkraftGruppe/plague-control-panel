# Detach — Guía principal para Claude Code

Eres Claude Code, el asistente automatizado principal de desarrollo de Detach: panel de gestión y API para empresas de control de plagas, en un único proyecto Django. El sitio público de cada empresa vive en otro repositorio, fuera de este. La app móvil (Expo) llega en la última etapa y vivirá en `mobile/`, como repositorio aparte.

## Navegación de contextos
- **Este archivo (raíz)**: reglas globales, flujo de trabajo (plan → delegación → verificación), hooks y cierre de sesión.
- **`.claude/skills/convenciones-proyecto/SKILL.md`**: stack, comandos canónicos, mapa de rutas, roles, prohibiciones de código. Se lee antes de codificar o de citar comandos/rutas.
- **`docs/01-modelo-y-arquitectura.md`**: modelo de datos, flujos y decisiones técnicas. Es la fuente de verdad del dominio hasta que el código la reemplace.
- **`docs/02-diseno.md`**: sistema visual (tokens, tipografía, componentes) del panel.
- **`docs/contrato-api.md`**: contrato de `/api/v1/` que consume la app móvil.

La raíz es un repositorio git propio. Cuando exista `mobile/`, será otro repositorio y la raíz lo ignorará.

## Al entrar
- El hook `SessionStart` (`.claude/hooks/contexto.sh`) inyecta el comienzo de `docs/bitacora.md` ("Estado actual" y la última entrada), el encabezado y la tabla de estado del plan de la rama (o el activo de la bitácora), y las últimas decisiones de `docs/decisiones.md`. También inyecta `=== Pendientes abiertos (pendientes.py) ===`: los problemas abiertos de todos los planes (`py -3 .claude/hooks/pendientes.py [--raiz R] [--json]`); la bitácora ya no lleva esa lista.
- No preguntes lo que ya está ahí (plan activo, rama, pendiente inmediato, pendientes abiertos): léelo y seguí desde ese punto.
- **Resumen de entrada**: la primera respuesta de la sesión abre con un resumen de 3 a 5 líneas de lo que Claude cree que es el estado: plan activo, último trabajo registrado, pendiente inmediato y rama. Antes de escribirlo se corre `git branch --show-current` y `git log -1 --oneline` y se marca toda diferencia con la bitácora (otra rama, commits posteriores a la última entrada): es la señal de trabajo hecho a mano, fuera de Claude. Si el primer pedido implica escribir, se muestra el resumen y se espera la confirmación del usuario antes de la primera escritura; leer no espera.
- Si el pedido del usuario contradice una decisión registrada en `docs/decisiones.md`, avisalo citando la decisión **antes de avanzar**. Cambiar una decisión es del usuario, y queda como una línea nueva que dice a cuál reemplaza.

## Reglas globales (aplican en todo momento)
0. **Autorizar antes de escribir**: investigar, explicar, revisar, auditar, comparar o planificar es solo lectura: sin editar, sin delegar a un escritor, sin artefactos de implementación. Solo un pedido explícito de implementar habilita escribir; si la intención es ambigua, se hace una pregunta y se sigue en solo lectura.
1. **Preguntar antes de romper**: si un cambio altera la estructura arquitectónica general, el contrato de la API (`/api/v1/`, que consumirá la app), o borra apps o pantallas enteras, hacer una pausa y confirmar la estrategia con el usuario.
2. **Idioma**: docstrings, comentarios de código, textos de la interfaz, nombres de campos y de modelos, siempre en **español** (sin modismos regionales en textos visibles).
3. **Sistema experto (skills)**: antes de codificar con una tecnología, leé la skill relevante de `.agents/skills/[skill]/SKILL.md`; la sección que aplica, no el archivo entero. La referencia del proyecto vive en `.claude/skills/convenciones-proyecto/SKILL.md`.
4. **Plan con criterios comprobables por máquina** (ver § Flujo de trabajo).
5. **Delegación a subagentes con contrato** (ver § Flujo de trabajo).
6. **Verificación independiente obligatoria** (ver § Flujo de trabajo). Ningún trabajo se reporta como terminado sin un informe del subagente `verificador`.
7. **Datos de la empresa**: el nombre sale de `NOMBRE_EMPRESA`; ninguna plantilla ni código escribe el nombre de una empresa. Sin cifras ni datos inventados.
8. **Cuándo preguntar**: Claude pregunta al usuario solo cuando la decisión (a) es de producto o del negocio, (b) es irreversible o toca datos, (c) contradice una decisión registrada, o (d) es una frontera del esquema (contrato, merge, FALLA). En todo lo demás elige la opción que recomendaría, la anota en ### Decisiones del plan con la marca 'decidida por Claude, revisable', y sigue; esas decisiones se presentan juntas al cierre de cada ola, no una por una.

## El principal coordina, no ejecuta

El principal delega según el tamaño de lo que hay que hacer, no según la comodidad del momento:
- leer de 1 a 3 archivos: en línea, sin delegar;
- entender algo que requiere 4 archivos o más: un explorador de solo lectura que devuelve un mapa;
- escribir 2 archivos o más no triviales: `implementador`, que hace también la lectura preparatoria;
- tests, builds e instalaciones: un subagente descartable;
- la ruta (inline o delegada) se declara por subtarea, para que quede trazable.

**Freno de sesión larga**: ≈20 llamados a herramientas, 5 lecturas exploratorias o 2 ediciones no mecánicas sin delegar en lo que va de la sesión → parar y delegar el resto.

**Regla de incidente**: tras un `cwd` equivocado, un accidente de git o de worktree, o un workaround de entorno, correr `git status` en la raíz y en los worktrees activos antes de seguir.

## Flujo de trabajo: plan → delegación → verificación

Aplica a todo trabajo que toque más de un archivo o que se vaya a dividir en subagentes. Para un cambio de una línea no hace falta plan, pero sí siguen aplicando los criterios de cierre global.

**Regla de tamaño** (se cuenta sobre los archivos que el trabajo va a tocar):

| Nivel | Cuándo | Verificación |
|---|---|---|
| **Pasivo** | Toca un solo archivo y no cambia comportamiento (texto, comentarios, un ajuste mecánico). Sin plan. | Lectura estructural del cambio + criterios de cierre global. |
| **Chico** | Toca menos de cinco archivos. Plan con criterios congelados y delegación, sin `juez-plan`. | Autoverificación del implementador + spot check del principal + hook de cierre. |
| **Completo** | Todo lo demás. `juez-plan` revisa el plan antes de que el usuario lo apruebe. | Lo del nivel Chico, más `verificador` y `verificador-b`, más `refutador` si discrepan, más `auditor-seguridad` si el plan lleva `seguridad: sí`. |

### 4. El plan lleva criterios comprobables por máquina

- Todo trabajo no trivial empieza en **modo plan**. El plan se guarda en `docs/planes/AAAA-MM-DD-<slug>.md` siguiendo `docs/plantilla-plan.md`.
- Cada subtarea lleva un bloque `Criterios` que contiene **únicamente** afirmaciones que una máquina puede decidir sin interpretar nada:
  - `[cmd]` un comando que debe terminar con código de salida 0;
  - `[cmd-falla]` un comando que debe terminar con código distinto de 0;
  - `[existe]` / `[no-existe]` una ruta que debe existir o no existir;
  - `[grep-1]` una búsqueda que debe encontrar al menos una coincidencia;
  - `[grep-0]` una búsqueda que no debe encontrar ninguna;
  - `[test]` un test **nombrado**, escrito como comando completo (`PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test <ruta.punteada.Clase.test_nombre> --keepdb`), que debe estar en verde y que **no existía antes del plan**. El hook ejecuta el criterio tal cual con bash: la ruta punteada sola no sirve.
- No son criterios y no se aceptan: "funciona", "quedó implementado", "tests pasando" sin nombre de test, "revisado", "sin regresiones", "el usuario lo prueba".
- Toda subtarea que agrega comportamiento lleva al menos un `[test]`. Toda subtarea que corrige un defecto lleva un `[test]` que reproduce el defecto y que fallaba antes del cambio.
- **Los criterios se fijan antes de delegar y se congelan.** El plan se commitea solo, antes de lanzar el primer subagente (`docs(plan): <slug>`), y ese hash se anota como `commit_base:` en `## Registro de verificación`, **debajo del corte**, nunca en el encabezado. Todo lo anterior a `## Registro de verificación` queda congelado y lo comprueba `bash .claude/hooks/congelado.sh <plan> <slug>`; lo de abajo (commit_base, tabla `### Estado de subtareas`, corridas) lo actualiza el principal durante la ejecución. Cambiar un criterio después es decisión del usuario, nunca del agente que lo incumple: se hace en un commit nuevo `docs(plan): <slug> — modificado: <motivo>`, que `congelado.sh` reporta como **CONTRATO MODIFICADO**.
- **Commits**: cada subtarea se commitea como `T<n>: …` **antes** de invocar al verificador, y las correcciones van en commits nuevos con el mismo prefijo; las actualizaciones del Registro van en commits `registro: …`.
- Regla de oro: **si quien puede fallar el criterio puede reescribirlo, no era un criterio.** Ningún subagente implementador recibe permiso de escribir en `docs/planes/`.
- **Presupuesto de líneas**: cada subtarea lleva `- **Presupuesto**: <N> líneas agregadas` (por defecto 400) y un criterio `[cmd]` con `bash .claude/hooks/presupuesto.sh . '<commit_base>' <N> --subtarea T<n>`, que mide las líneas agregadas por los commits `T<n>:` (presupuesto.sh también suma `T<n>b:`; por eso ese sufijo no se usa) de `commit_base..HEAD`, sin merges (el modo por rutas, `<N> <rutas>`, sigue disponible por compatibilidad; si se usa, las rutas de presupuesto no se solapan entre subtareas). Una integración que solo hace merges y commits `registro:` no lleva `--subtarea` (mediría 0 y pasaría siempre). El marcador `'<commit_base>'` va literal y entre comillas simples: `presupuesto.sh` lo resuelve con `verificar_plan.py --commit-base`, leyendo la línea `commit_base:` del Registro (debe ser un commit `docs(plan): <slug>`), y el hook de cierre lo reemplaza antes de ejecutar; si no resuelve, el criterio es FALLA (`commit_base sin resolver en <plan>: <motivo>`). Se fija antes de empezar y **nunca se sube** durante la subtarea: si el trabajo no entra, lo que falta va en una subtarea nueva con su propio número (`T<m>`), su presupuesto y sus criterios, agregada al plan como contrato modificado. **El presupuesto no es golf**: está prohibido recortar comentarios, docs, tests o líneas en blanco para entrar.

### 5. Delegación a subagentes con contrato

- El principal divide el plan en subtareas independientes (por app o por archivo, sin dos subagentes escribiendo el mismo archivo) y las lanza en paralelo cuando no dependen entre sí.
- Cada delegación incluye, textualmente: objetivo de la subtarea, archivos que puede tocar, archivos que **no** puede tocar (siempre incluye `docs/planes/`), skill que debe leer antes de codificar, y el bloque `Criterios` copiado literal del plan.
- El implementador devuelve un informe con esta estructura y nada más: archivos tocados; comandos que ejecutó con su **salida literal y código de salida**; tests nuevos por nombre; lo que quedó fuera o a medias; pendientes propuestos. Prohibido devolver "listo", "implementado" o "tests pasando" sin la salida que lo respalda.
- El principal **no da por cumplida una subtarea leyendo el informe**. Los informes son optimistas por naturaleza; la única verificación válida es la del punto 6.

**Regla de worktree por defecto**: toda subtarea delegada que escriba código va en su propio worktree. Inline solo va lo pasivo o lo que escribe un único archivo de documentación. Los worktrees viven en `worktrees/` (ignorado) y no tienen `venv/`: el script crea una junction.
- **Ramas**: un plan = una rama `plan/<slug>`; las subtareas son `<slug>-T<n>` (con sufijo de letra si hay varias en una: `T5a`) y cuelgan de ella. `main` solo recibe planes con la verificación `TODO` en PASA, y el merge lo decide el usuario.
- **Plan derivado de la rama**: los hooks `SessionStart` (`contexto.sh`) y `Stop` (`verificar_plan.py`) toman `git branch --show-current`; si es `plan/<slug>` o `<slug>-T<n>`, el plan es `docs/planes/*-<slug>.md`. Si no, usan la línea `Plan activo:` de la bitácora como respaldo.
- **Olas**: el plan ordena las subtareas en olas según el grafo de FK entre apps (la plantilla las declara y cada subtarea lleva `Ola: <n>`). Dentro de una ola todas las subtareas corren en paralelo, cada una con sus migraciones en su worktree; dos subtareas de la misma ola nunca crean migraciones en la misma app. La ola siguiente ramifica desde el commit de integración de la anterior.
- **Propiedad**: cada app de dominio es dueña de sus archivos; los archivos transversales tienen un dueño único según la "Tabla de propiedad" de `convenciones-proyecto`. Una subtarea no declara en `Puede tocar` un archivo de otro dueño.
- **Crear e integrar es trabajo del principal, por ola**: la integración de cada ola es una subtarea numerada `### T<n> — Integración (principal)` y el hook ejecuta sus criterios como los de cualquier `### T<n>`; `worktree-integrar.sh` se corre desde la raíz, no desde dentro del worktree (exit 3). `bash .claude/hooks/worktree-crear.sh <slug> T<n> [rama_base]` crea `worktrees/<slug>-T<n>` y su rama, con la junction `venv` y `manage.py check` como prueba de humo. Con la subtarea commiteada y verificada, `bash .claude/hooks/worktree-integrar.sh <slug> T<n> plan/<slug> <ruta>...` rechaza cambios sin commitear y archivos fuera de las rutas declaradas, mergea con `--no-ff` (`T<n>: integra <slug>-T<n>`), corre `makemigrations --check` y `test --keepdb`, y quita la junction, el worktree y la rama. Antes de integrar se revisa `bash .claude/hooks/cambios.sh . <rama_base>`, no los informes.
- **El principal no hace `cd` a los worktrees**: el principal nunca cambia de directorio a un worktree: usa `git -C worktrees/<slug>-T<n>` o rutas absolutas; los implementadores reciben el worktree como ruta explícita en cada comando. Un shell con el cwd adentro impide que `worktree-integrar.sh` quite el worktree (incidente de `triage` T1).
- **Tests de hooks**: son `[test]` escritos como `py -3 -m pytest .claude/hooks/<archivo>::<test> -q`; los de Django siguen con `manage.py test … --keepdb`.
- **Sesiones paralelas**: cada sesión abre Claude Code en `worktrees/<slug>` (el worktree de su plan), no en la raíz. Las sesiones se comunican solo por git y por el Registro de cada plan; una sesión no edita el plan ni el worktree de otra. `docs/bitacora.md` y `docs/decisiones.md` los actualiza el principal de cada sesión al cierre, con rebase. La caché del hook de cierre (`.claude/.ultimo-verificado`) es por worktree.

### 6. Verificación independiente obligatoria

- Después de cada subtarea (o de cada lote paralelo), el principal invoca al subagente **`verificador`** (`.claude/agents/verificador.md`) pasándole la ruta del plan y los IDs de subtarea. El verificador ejecuta los criterios **literalmente**, no lee informes, y devuelve `PASA` / `FALLA` por criterio con la salida que lo prueba.
- Un `FALLA` vuelve al implementador con la salida del verificador pegada en el prompt. Una subtarea con un `FALLA` abierto no se marca como hecha, no se commitea como hecha y no se le informa al usuario como hecha.
- Con el plan completo integrado, el principal hace su trabajo de cierre (integración, migraciones, ajustes) y después invoca al verificador **una vez más** sobre el plan entero: todas las subtareas más los **criterios de cierre global**. El principal no se autoverifica.
- El informe final que recibe el usuario es el del verificador, pegado sin editar. El principal puede agregar contexto encima, no reemplazarlo ni resumirlo.
- El verificador no edita código: solo `Read`, `Grep`, `Glob` y `Bash` de solo lectura. Si para que algo pase hace falta tocar código, eso es un hallazgo.
- Si el cambio toca autenticación, roles y permisos, subida o servido de fotos, generación o resolución de QR, geolocalización, certificados PDF, settings de producción o datos personales de empleados o clientes, además del verificador corre el `auditor-seguridad`. El verificador responde "¿se cumplió el contrato?", el auditor "¿el contrato era seguro?".
- **Recibo atado al HEAD**: en su Paso 0, cada verificador anota `git rev-parse --short HEAD` y abre su informe con `HEAD verificado: <hash>`. Un veredicto vale solo para ese HEAD.
- **Spot check del principal**: antes de cerrar una subtarea, el principal vuelve a ejecutar uno de los comandos que reportó el implementador; si la salida difiere, el informe entero pierde validez.
- **Piso de severidad y convergencia**: solo los hallazgos `bloqueante` entran al ciclo de corrección; como máximo dos rondas por revisión; lo que sigue abierto se reporta como abierto.

### Criterios de cierre global (se ejecutan siempre en la verificación final)

Se copian tal cual al último bloque del plan.

```bash
# Desde la raíz del proyecto, con el venv de Windows
[cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check
[cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run
[cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb
[cmd] ./venv/Scripts/python.exe -m ruff check .
[cmd] test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0   # nada modificado sin commitear
[cmd] bash .claude/hooks/congelado.sh docs/planes/<archivo>.md <slug>   # el plan no cambió arriba del corte
```

## Cierre de sesión
Antes de terminar una sesión de trabajo:
- Actualizar "Estado actual" de `docs/bitacora.md` (tabla `| plan | rama | ola actual | pendiente inmediato | sesión |`, con la línea `Plan activo:` como compatibilidad, sin lista de problemas) y agregar una entrada nueva arriba de todo en "Entradas", con fecha y título.
- Escribir los problemas y decisiones nuevos en la sección `## Pendientes que deja este plan` del plan (debajo del corte), no en la bitácora: problemas como `- P-<slug>-<n> [bloqueante|importante|menor|observación] texto`; decisiones, una línea cada una con el formato `- AAAA-MM-DD — decisión — motivo — reemplaza a: (nada|fecha)`.
- Al fusionar en `main` se copian solo las decisiones a `docs/decisiones.md` (apéndice) y la bitácora recibe la entrada de sesión.
- Un problema se cierra con `- cierra: P-<slug>-<n> — cómo` en `### Cierra` del plan que lo resuelve, nunca editando el plan de origen.
- Marcar una tarea como `hecha` en la tabla `### Estado de subtareas` **solo después de ver pasar sus criterios**. El hook de cierre (`.claude/hooks/verificar_plan.py`, evento `Stop`) ejecuta los criterios de todas las tareas `hecha` del plan de la rama (con `Plan activo:` como respaldo) y, cuando están todas, los de cierre global.
- Si el hook de cierre avisa una falla, se corrige la causa, **nunca el criterio**. Si el criterio está mal, es un cambio de contrato y lo decide el usuario (§ 4).

## Referencia del proyecto
Stack, mapa de rutas, variables de entorno, comandos y prohibiciones: `.claude/skills/convenciones-proyecto/SKILL.md`.
