# Plan: NOMBRE_EMPRESA obligatoria en producción

- **slug**: `nombre-empresa-prod`
- **fecha**: 2026-10-18
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): nombre-empresa-prod`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: un despliegue de producción sin `NOMBRE_EMPRESA` no arranca, en lugar de mostrar el nombre de otra empresa; la skill vuelve a prohibir formularios públicos.
- **fuera de alcance**: `CORREO_CONTACTO` (sigue opcional, decisión del usuario); los valores por defecto de desarrollo (siguen en `base.py`); cargar la variable en Railway (lo hace el usuario antes del próximo despliegue); el resto de P-separacion-web-11 (`.claude/agents/auditor-seguridad.md`, `.gitignore`, `dist/`); multiempresa.
- **áreas**: infraestructura
- **seguridad**: sí — settings de producción (`config/settings/prod.py`); corre también `auditor-seguridad`

## Contexto mínimo

- `config/settings/base.py:87`: si `NOMBRE_EMPRESA` falta o está vacía, toma el valor "MAControl S.A.".
- `config/settings/prod.py` ya aborta con `ImproperlyConfigured` si falta `SITE_URL`. Con `NOMBRE_EMPRESA` tiene que hacer lo mismo.
- Los tests que arrancan producción en un subproceso (`config/tests/test_settings.py`, `config/tests/test_empresa.py`) tienen que pasar la variable nueva. Si no, dejan de arrancar.
- P-separacion-web-10: la prohibición de formularios públicos solo quedó en el agente auditor. Hay que sumarla a las Prohibiciones de `.claude/skills/convenciones-proyecto/SKILL.md`.
- P-separacion-web-11 (parte): `docs/despliegue.md:27` dice que `NOMBRE_EMPRESA` aparece en los PDF, y todavía no hay ningún PDF. `:36` habla de logos subidos.
- El plan toca 5 archivos, así que entra en el nivel Completo: `juez-plan`, los dos verificadores y el auditor.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | ninguna |

## Subtareas

### T1 — Exigir NOMBRE_EMPRESA en producción (principal)

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `config/settings/prod.py`, `config/tests/test_empresa.py`, `config/tests/test_settings.py`
- **No puede tocar**: `docs/planes/`, `config/settings/base.py`, `config/settings/dev.py`, `apps/`, `docs/`, `.claude/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Variables de entorno
- **Worktree**: no (los archivos de `config/` son del principal; los commits `T1:` van sobre `plan/nombre-empresa-prod`, como T1 de separacion-web)
- **Ruta**: inline
- **Presupuesto**: 60 líneas agregadas
- **Qué hacer**:
  - En `prod.py`, después del control de `SITE_URL`: si `env("NOMBRE_EMPRESA", default="").strip()` queda vacía, abortar con `ImproperlyConfigured`. El mensaje nombra la variable.
  - El docstring de `prod.py` suma `NOMBRE_EMPRESA` a las variables obligatorias.
  - En los tests, agregar `NOMBRE_EMPRESA` a cada entorno de producción que tiene que arrancar, y sumar un test nuevo a `EmpresaTests`.
  - El commit principal se titula `T1: exige NOMBRE_EMPRESA en producción`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_empresa.EmpresaTests.test_prod_sin_nombre_empresa_no_arranca --keepdb`
  - `[grep-1]` `grep -n 'env("NOMBRE_EMPRESA"' config/settings/prod.py`
  - `[grep-0]` `grep -n "CORREO_CONTACTO" config/settings/prod.py`
  - `[grep-0]` `grep -n "NOMBRE_EMPRESA" config/settings/dev.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T1`

### T2 — Skill y despliegue: NOMBRE_EMPRESA obligatoria y sin formularios públicos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/skills/convenciones-proyecto/SKILL.md`, `docs/despliegue.md`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/`, `CLAUDE.md`, `.claude/agents/`, los demás `docs/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` (completa, porque es el archivo que se edita)
- **Worktree**: sí
- **Presupuesto**: 40 líneas agregadas
- **Qué hacer**:
  - Skill, § Variables de entorno: `NOMBRE_EMPRESA` sale de "Opcionales" y pasa a la línea de obligatorias en producción, junto a `SITE_URL`. `CORREO_CONTACTO` sigue en "Opcionales".
  - Skill, § Prohibiciones de código: agregar la viñeta "Ninguna ruta pública (`/`, `/q/<uuid>/`) tiene formularios que escriban en la base ni envíen correo".
  - `docs/despliegue.md`: la fila de `NOMBRE_EMPRESA` dice **Obligatoria** y no menciona los PDF; la de `CORREO_CONTACTO` no cambia.
  - `docs/despliegue.md`: el párrafo sobre definir `SITE_URL` antes del build nombra también `NOMBRE_EMPRESA`, y la sección del volumen deja de hablar de logos.
- **Criterios**:
  - `[grep-1]` `grep -n "Obligatoria.* en producción.*SITE_URL.*NOMBRE_EMPRESA" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-0]` `grep -n "Opcionales:.*NOMBRE_EMPRESA" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "Opcionales:.*CORREO_CONTACTO" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "Ninguna ruta pública.*formularios" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "NOMBRE_EMPRESA.*\*\*Obligatoria\*\*" docs/despliegue.md`
  - `[grep-0]` `grep -n "NOMBRE_EMPRESA.*opcional" docs/despliegue.md`
  - `[grep-0]` `grep -n "los PDF\|logos" docs/despliegue.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 40 --subtarea T2`

### T3 — Integración y cierre (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/nombre-empresa-prod` de T2, no el informe.
  2. Desde la raíz, correr `bash .claude/hooks/worktree-integrar.sh nombre-empresa-prod T2 plan/nombre-empresa-prod .claude/skills/convenciones-proyecto/SKILL.md docs/despliegue.md`.
  3. Con todo integrado, correr el cierre global y la verificación `TODO` (verificador, verificador-b, auditor-seguridad).
  4. En `### Cierra`, cerrar P-separacion-web-10 y la parte de P-separacion-web-11 que corresponde a `NOMBRE_EMPRESA` y a `docs/despliegue.md`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/nombre-empresa-prod | grep -q " T1: exige NOMBRE_EMPRESA en producción"`
  - `[cmd]` `git log --oneline plan/nombre-empresa-prod | grep -q "T2: integra nombre-empresa-prod-T2"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-18-nombre-empresa-prod.md nombre-empresa-prod`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): nombre-empresa-prod — modificado: <motivo>`. -->

commit_base: 2e92f78

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha (c9ec157; verificador y verificador-b 6/6 PASA) |
| T2 | hecha (14b45c5, integrada en 120757e; verificador y verificador-b 8/8 PASA) |
| T3 | en curso (integración hecha; falta la verificación TODO) |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-18 | juez-plan ronda 1 | (sin commit) | RECHAZADO | 3 bloqueantes (backticks en dos grep de T2; el criterio de T3 pasaba por commits ` T1: ` anteriores) y 1 observación (los grep de prod.py se cumplían con el docstring), corregidos |
| 2026-10-18 | juez-plan ronda 2 | (sin commit) | APROBADO | sin hallazgos |
| 2026-10-19 | usuario | (sin commit) | — | aprueba el plan y deja `CORREO_CONTACTO` opcional: se quita del alcance antes del commit `docs(plan)` |
| 2026-10-19 | T1, T2 (verificador) | c9ec157 / 14b45c5 | PASA 14/14 | contrato intacto |
| 2026-10-19 | T1, T2 (verificador-b) | c9ec157 / 14b45c5 | PASA 14/14 | observación: los criterios de T2 no cubren el párrafo previo al build ni la sección del volumen (revisados a mano en el diff) |
| 2026-10-19 | T3 pasos 1-2 | 120757e | — | `cambios.sh` de T2 solo en sus dos archivos; spot check `grep "Ninguna ruta pública"` OK; `worktree-integrar.sh` T2 exit 0, 657 tests OK |

## Pendientes que deja este plan

### Problemas

- P-nombre-empresa-prod-1 [observación] Resto de P-separacion-web-11: `.claude/agents/auditor-seguridad.md:20,84` todavía nombra el sitio público; `.gitignore:33` nombra el empaquetador borrado; `dist/` local guarda el paquete viejo.
- P-nombre-empresa-prod-2 [observación] `pendientes.py` avisa formas inválidas: `2026-10-12-demo-portatil.md:157-163` declara P-demo-portatil-1 a 5 y una decisión fuera de una subsección (nunca contaron como abiertos), y `2026-10-18-separacion-web.md:449` junta cinco ids en una sola línea `cierra:`. Hoy no cambia el conteo; se corrige al tocar esos planes o con una regla del hook.

### Decisiones

- 2026-10-18 — `NOMBRE_EMPRESA` es obligatoria en producción, como `SITE_URL` — un despliegue sin ella mostraría el nombre de otra empresa — decisión del usuario — reemplaza a: 2026-10-18 (`NOMBRE_EMPRESA` con valor por defecto `MAControl S.A.`), solo en producción
- 2026-10-19 — `CORREO_CONTACTO` sigue opcional en producción, con su valor por defecto — decisión del usuario — reemplaza a: (nada)

### Cierra

- cierra: P-separacion-web-10 — la prohibición de formularios públicos vuelve a las Prohibiciones de la skill (T2)
- cierra: P-separacion-web-11 — parcial: `NOMBRE_EMPRESA` obligatoria en producción (T1) y `docs/despliegue.md` sin PDF ni logos (T2); lo que queda (`auditor-seguridad.md:20,84`, `.gitignore:33`, `dist/`) pasa a P-nombre-empresa-prod-1
- cierra: P-demo-portatil-1 — la demo portátil se borró en separacion-web T9; su línea `cierra:` con cinco ids no la reconoce `pendientes.py`
- cierra: P-demo-portatil-2 — la demo portátil se borró en separacion-web T9; su línea `cierra:` con cinco ids no la reconoce `pendientes.py`
- cierra: P-demo-portatil-3 — la demo portátil se borró en separacion-web T9; su línea `cierra:` con cinco ids no la reconoce `pendientes.py`
- cierra: P-demo-portatil-4 — la demo portátil se borró en separacion-web T9; su línea `cierra:` con cinco ids no la reconoce `pendientes.py`
- cierra: P-demo-portatil-5 — la demo portátil se borró en separacion-web T9; su línea `cierra:` con cinco ids no la reconoce `pendientes.py`
