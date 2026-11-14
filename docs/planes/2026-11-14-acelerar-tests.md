# Plan: acelerar la suite de tests y la verificación de planes

- **slug**: `acelerar-tests`
- **fecha**: 2026-11-14
- **objetivo**: la suite de Django y `verificar.py todo` tardan bastante menos, sin ningún cambio de comportamiento en producción.
- **fuera de alcance**: `--parallel` (se evalúa después, con la medición nueva); reescribir tests o fixtures; `config/settings/prod.py`; `verificar.py cierre` sin plan (sigue corriendo todo el cierre global); `recibo.py`.
- **áreas**: infraestructura
- **ruta**: completo
- **seguridad**: sí — toca `PASSWORD_HASHERS` (solo para los tests, en `config/settings/dev.py`); el auditor confirma que con `DJANGO_ENV=production` nunca queda MD5.

## Contexto mínimo

- No hay `PASSWORD_HASHERS` en `config/settings/`: cada usuario de prueba se crea con PBKDF2. La suite tarda entre 550 y 740 s; la medición de esta sesión (977 tests) va en `### Decisiones del plan`.
- `config/settings/__init__.py` elige `dev` o `prod` por `DJANGO_ENV`; ningún settings detecta que corren los tests. Diseño: `dev.py` usa `MD5PasswordHasher` solo si `sys.argv[1:2] == ["test"]` (`manage.py:16` pasa `sys.argv` sin tocarlo; no hay pytest-django); `prod.py` no se toca. `config/settings/*.py` es del principal y no va en paralelo: lo hace T3, la integración.
- El único test que depende del formato del hash es `apps/accounts/tests/test_panel.py:28` (`test_no_expone_hash` busca `"pbkdf2"` en el HTML). Los usuarios salen de `setUpTestData` (líneas 12-23), así que el `override_settings` va en la clase `UsuarioPanelTests`, no en el método.
- `config/tests/test_settings.py` prueba settings en un subproceso (`_correr`, línea 23).
- `verificar.py todo` de `robustez-listados` tardó 2788 s: los criterios de subtarea repetían la suite entera y el cierre corre `pytest .claude/hooks` aunque el plan no toque el método. `pytest .claude/hooks` valida también `.claude/settings.json`, `.claude/agents/` y `docs/plantilla-plan.md`. `cierre_global.json` es una lista de cadenas; `criterios_de_texto` (`.claude/hooks/verificar.py:268`) la convierte en criterios `[cmd]`; `recibo.py` solo conoce PASA y FALLA, y `emitir_recibo` (`verificar.py:474`) ya agrega líneas informativas propias.
- `revisar_plan.py` emite los avisos desde `revisar_criterio` (`.claude/hooks/revisar_plan.py:333`) e importa `verificar_plan`, que ya tiene `es_suite` (`.claude/hooks/verificar_plan.py:505`).

## Olas

Ninguna subtarea crea migraciones ni comparte archivos.

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración, hasher y cierre) | config, accounts (ninguna) |

## Subtareas

### T1 — Avisar cuando un criterio de subtarea corre la suite completa

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/revisar_plan.py`, `.claude/hooks/test_revisar_plan.py`, `docs/plantilla-plan.md`, `.claude/skills/convenciones-proyecto/SKILL.md`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/verificar.py`, `.claude/hooks/verificar_plan.py`, `.claude/hooks/permisos.py`, `.claude/hooks/guardia_bash.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Método
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**: en `revisar_criterio`, un criterio de una `T<n>` cuyo comando cumple `verificar_plan.es_suite(cmd)` y no lleva ninguna etiqueta después de `test` (solo flags, o nada) da `AVISO: T<n>: corre la suite completa; usa sus tests nombrados o las apps que toca` (aviso, no error: el exit sigue en 0). Cuenta como "sin etiquetas" cualquier combinación de flags (`--keepdb`, `--parallel`, `-v 2`, `--noinput`): se reutiliza el recorrido de tokens de `es_suite` (prefijo de entorno y `python`, `manage.py`, `test`), sin tocar `verificar_plan.py`; si hace falta, una función auxiliar en `revisar_plan.py`. `manage.py test apps.x --keepdb` no avisa. En `docs/plantilla-plan.md` (comentario de reglas de criterios) y en `SKILL.md` § Método › Criterios: los criterios de una subtarea corren sus tests nombrados y, como mucho, los de las apps que toca; la suite completa corre una sola vez, en el cierre global.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_revisar_plan.py::test_avisa_criterio_que_corre_la_suite_completa -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_revisar_plan.py::test_no_avisa_criterio_con_apps_nombradas -q`
  - `[grep-1]` `grep -n "suite completa" docs/plantilla-plan.md`
  - `[grep-1]` `grep -n "suite completa" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_revisar_plan.py .claude/hooks/test_verificar_plan.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`

### T2 — Correr `pytest .claude/hooks` en el cierre solo si el plan toca el método

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/verificar.py`, `.claude/hooks/test_verificar.py`, `.claude/hooks/cierre_global.json`
- **No puede tocar**: `docs/planes/`, `.claude/hooks/revisar_plan.py`, `.claude/hooks/recibo.py`, `.claude/hooks/permisos.py`, `.claude/hooks/guardia_bash.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Método
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**: un elemento de `comandos` en `cierre_global.json` puede ser una cadena (como hoy) o un objeto `{"cmd": "...", "si_toca": ["<prefijo>", ...]}`; solo `py -3 -m pytest .claude/hooks -q` pasa a objeto, con `"si_toca": [".claude/", "docs/plantilla-plan.md"]`. `si_toca` viaja aparte del `Criterio` (que no cambia), dentro de `verificar.py`. En `verificar.py todo <plan>`, un comando con `si_toca` se omite solo si hay base del plan resoluble y ningún archivo cambiado desde ella (commits `base..HEAD` y archivos versionados modificados) empieza con alguno de los prefijos; sin base, se corre. Lo omitido no entra en los criterios del recibo (ni PASA ni FALLA): `verificar.py` agrega una línea propia `- Omitido (no toca <prefijos>): \`<cmd>\`` en la salida y en el recibo, como hace con "Fuera de alcance". `verificar.py cierre` (sin plan) corre todos los comandos. Se actualiza `test_cierre_global_json_del_repo_trae_los_cinco_comandos_de_detach`.
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar.py::test_todo_omite_pytest_de_hooks_si_el_plan_no_toca_el_metodo -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar.py::test_todo_corre_pytest_de_hooks_si_el_plan_toca_settings_json -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar.py::test_cierre_sin_plan_corre_los_comandos_con_si_toca -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar.py::test_todo_corre_pytest_de_hooks_sin_base_resoluble -q`
  - `[grep-1]` `grep -n "si_toca" .claude/hooks/cierre_global.json`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_verificar.py .claude/hooks/test_verificar_plan.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T2`

### T3 — Integración, hasher rápido en los tests y tiempos (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Puede tocar**: `config/settings/dev.py`, `config/tests/test_settings.py`, `apps/accounts/tests/test_panel.py`, `docs/metodo/metricas.md`
- **No puede tocar**: `docs/planes/` (salvo el Registro de este plan), `config/settings/prod.py`, `config/settings/base.py`
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/acelerar-tests` de cada subtarea, no los informes.
  2. Desde la raíz (rama `plan/acelerar-tests`), `bash .claude/hooks/worktree-integrar.sh acelerar-tests T<n> plan/acelerar-tests <rutas>` de a una, con `verificar.py tarea` tras cada integración.
  3. Commit `T3:` con el hasher: en `config/settings/dev.py`, si `sys.argv[1:2] == ["test"]`, `PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]`, con un comentario en español. En `SettingsTests` (`config/tests/test_settings.py`): `test_prod_primer_hasher_no_es_md5` (subproceso con `DJANGO_ENV=production` y el entorno de `test_prod_hsts_reversible`, que fija `sys.argv = ["manage.py", "test"]` antes de cargar los settings e imprime `settings.PASSWORD_HASHERS[0]`; es una guarda: ya pasa hoy y falla si alguien mueve el bloque a `base.py`), `test_dev_fuera_de_tests_no_usa_md5` (`_correr(["shell", "-c", …], DJANGO_ENV="development")`) y `test_dev_en_tests_usa_md5` (en proceso). En `apps/accounts/tests/test_panel.py`: `@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])` sobre la clase `UsuarioPanelTests` (cubre `setUpTestData`) y `test_hash_del_empleado_es_pbkdf2`, que comprueba `self.empleado.password.startswith("pbkdf2_sha256$")`.
  4. Medir la suite completa con `manage.py test --keepdb` y anotar en `docs/metodo/metricas.md`, en una sección `## Tiempos de la suite` encima de la tabla (que pasa a llevar el encabezado `## Por plan`, porque `medir_metodo.py --registrar` agrega filas al final del archivo), el tiempo y el `Ran N` de antes y de después, y el tiempo de `verificar.py todo`. N después = N antes + 4.
- **Presupuesto**: `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T3` (hasher, sus tests y `metricas.md`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/acelerar-tests | grep -q "T1: integra acelerar-tests-T1"`
  - `[cmd]` `git log --oneline plan/acelerar-tests | grep -q "T2: integra acelerar-tests-T2"`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_prod_primer_hasher_no_es_md5 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_dev_fuera_de_tests_no_usa_md5 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_settings.SettingsTests.test_dev_en_tests_usa_md5 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_panel.UsuarioPanelTests.test_hash_del_empleado_es_pbkdf2 --keepdb`
  - `[grep-0]` `grep -n "PASSWORD_HASHERS" config/settings/prod.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts config --keepdb`
  - `[grep-1]` `grep -n "## Tiempos de la suite" docs/metodo/metricas.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T3`

## Registro de verificación

commit_base: 49cfb0b

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | hecha | 79226e3 | PASA 2026-11-14 |
| T2 | hecha | bf7dea7 | PASA 2026-11-14 |
| T3 | hecha | d558741 | PASA 2026-11-14 |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-14 09:46 | plan | 3 | 0 | 3 |
| 2026-11-14 09:46 | plan | 0 | 0 | 3 |
| 2026-11-14 10:13 | cierre | 0 | 0 | 4 |

<!-- Primera pasada: override de método que no cubre setUpTestData, dev.py en una subtarea paralela, si_toca demasiado estrecho; menores: línea Omitido, reutilizar es_suite, caso dev fuera de tests. Segunda pasada: Puede tocar de T3, flags además de --keepdb, test sin base. Todo corregido en el texto antes de congelar. Hora: la de registro. -->

Auditoría: `auditor-seguridad`, sin hallazgos explotables; (a) a (d) confirmados; una observación [BAJA]: la guarda de producción miraba solo el primer hasher.
Hallazgos:
- Auditoría [BAJA], la guarda miraba solo `PASSWORD_HASHERS[0]` — corregido (4eb038b): `test_prod_primer_hasher_no_es_md5` y `test_dev_fuera_de_tests_no_usa_md5` revisan la lista entera.
- Revisor de cierre, menor: `git diff --name-only` sin `--no-renames` ni `-z` en `archivos_cambiados` — pendiente P-acelerar-tests-1.
- Revisor de cierre, menor: tests de `si_toca` sin los caminos sin commitear, `docs/plantilla-plan.md` y renombres — pendiente P-acelerar-tests-2.
- Revisor de cierre, menor: `FLAGS_CON_VALOR` sin `--durations`, `--shuffle`, `--settings`, `--testrunner`, `--pythonpath`, `-t` — pendiente P-acelerar-tests-3.
- Revisor de cierre, menor: faltaba el tiempo de `verificar.py todo` en `metricas.md` — corregido (4eb038b).

### Decisiones del plan

Medición previa (2026-11-14, `main` @ 667ce36, `manage.py test --keepdb`): `Ran 977 tests in 551.388s`, OK; 554 s de reloj.

- T3 — cómo detectar que corren los tests — `sys.argv` en `dev.py` / variable de entorno / settings de tests aparte — `sys.argv[1:2] == ["test"]` en `dev.py` — producción nunca importa `dev.py` y no cambia el comando canónico — autónoma — revertir el bloque en `dev.py` — decidida por Claude, revisable
- T2 — cuándo omitir `pytest .claude/hooks` — también en `cierre` sin plan / solo en `todo` con plan y base resoluble — solo en `todo` con base — sin base no hay forma fiable de saber qué se tocó — autónoma — quitar `si_toca` del JSON — decidida por Claude, revisable
- T3 — quién cambia `config/settings/dev.py` — subtarea en paralelo / integración del principal — integración — la tabla de propiedad lo asigna al principal, nunca en paralelo (revisión de plan) — autónoma — — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-acelerar-tests-1 [menor] [despues] `.claude/hooks/verificar.py` `archivos_cambiados`: `git diff --name-only base..HEAD` va sin `--no-renames` ni `-z`; mover un archivo fuera de `.claude/` o una ruta no ASCII dentro de `.claude/` (entre comillas por `core.quotePath`) haría omitir `pytest .claude/hooks` aunque el plan toque el método.
- P-acelerar-tests-2 [menor] [despues] `.claude/hooks/test_verificar.py`: los tests de `si_toca` solo cubren cambios commiteados bajo `.claude/`; faltan un cambio sin commitear o sin seguimiento, el prefijo `docs/plantilla-plan.md` y un renombre.
- P-acelerar-tests-3 [observación] [despues] `.claude/hooks/revisar_plan.py` `FLAGS_CON_VALOR` no incluye `--durations`, `--shuffle`, `--settings`, `--testrunner`, `--pythonpath` ni `-t`: `manage.py test --keepdb --durations 10` corre la suite completa sin aviso (nunca da un aviso falso).

### Decisiones

- 2026-11-14 — los tests usan `MD5PasswordHasher` solo con `manage.py test` (`sys.argv` en `config/settings/dev.py`); producción no cambia — la suite pasa de 551 s a 101 s — (agente) — reemplaza a: (nada)
- 2026-11-14 — `verificar.py todo` omite `pytest .claude/hooks` si el plan no toca `.claude/` ni `docs/plantilla-plan.md` (`si_toca` en `cierre_global.json`); `verificar.py cierre` sin plan lo corre siempre — sin base no hay forma fiable de saber qué se tocó — (agente) — reemplaza a: (nada)
- 2026-11-14 — los criterios de una subtarea corren sus tests nombrados y, como mucho, los de sus apps; la suite completa, solo en el cierre global (`revisar_plan.py` avisa) — `verificar.py todo` de robustez-listados tardó 2788 s — (agente) — reemplaza a: (nada)

### Cierra
