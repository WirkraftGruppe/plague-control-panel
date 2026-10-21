# Plan: Ajustes de flujo-sitio (servicio coherente entre QR y revisión, desborde de envases)

- **slug**: `ajustes-flujo`
- **fecha**: 2026-10-20
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): ajustes-flujo`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: lo que la app muestra al escanear un punto (servicio, esquema, `en_turno`) es exactamente lo que se guarda en la revisión, y un ingreso de stock en envases desbordado desde el panel muestra un error de formulario en lugar de un 500.
- **fuera de alcance**: renombrar la skill `convenciones-proyecto`; P-robustez-panel-9 y -10 y los demás menores de `catalogo-stock`; P-flujo-sitio-14 (`TipoServicio.activo`); cambios visuales (`diseno-panel`); cambiar qué visita abre `POST /api/v1/visitas/abrir/` (decisión 2026-10-20, `abrir_visita`); quitar campos de la respuesta del resolver.
- **áreas**: api | panel | dominio (modelos y servicios)
- **seguridad**: sí — toca la resolución de QR y la respuesta de `/api/v1/` (elección de visita por empleado); corre también `auditor-seguridad`.

## Contexto mínimo

- P-flujo-sitio-11: el resolver (`apps/sitios/api_views.py:77-101`, `_servicio_del_punto`) busca el `ItemTurno` del punto en **cualquier** visita propia abierta o pendiente; la revisión (`apps/visitas/services.py:460-474`, `_servicio_de_la_revision`) lo busca solo en la visita a la que se guarda, que es la que devuelve `abrir_visita` (`services.py:309-382`: abierta propia del sitio, si no la pendiente más antigua sin revisiones vía `_pendiente_para`, si no una nueva sin ítems). Con una abierta sin ítems y una pendiente con el punto, el teléfono muestra el servicio del ítem y `en_turno=true` y el servidor guarda `punto.servicio` fuera de turno (o 400).
- Diseño: una sola función en `apps/visitas/services.py`, `visita_destino(*, empleado, sitio)`, devuelve la visita existente en la que se guardaría (la misma regla que hoy aplica `abrir_visita`, que pasa a usarla) o `None` si `abrir_visita` crearía una nueva; y `servicio_para_punto(*, visita, punto)` devuelve `(servicio, en_turno)` mirando solo el ítem de esa visita (con `visita=None`: `(punto.servicio, False)`). El resolver y la revisión usan las dos. La respuesta del resolver suma `visita_destino` (int o null); los campos actuales se conservan (aprobado por el usuario, 2026-10-20).
- P-flujo-sitio-1: `MovimientoAltaView` (`apps/productos/panel_views.py:80-110`) no define `get_form_kwargs`, así que `MovimientoForm.clean` (`apps/productos/panel_forms.py:64-84`) no multiplica por `contenido_por_envase` y el `ValidationError` de `registrar_ingreso` (`apps/productos/services.py:42`) sube sin capturar. Corrección: pasar `producto=self.producto`.
- `docs/api/openapi-v1.yaml` y `docs/contrato-api.md` los toca el principal (decisión 2026-10-18, tabla de propiedad); el YAML se regenera con `spectacular`, nunca a mano.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | visitas, productos (sin migraciones) |
| 2 | T4, T5 (integración) | sitios (sin migraciones) |

## Subtareas

### T1 — Unificar la elección de visita destino y de servicio en `visitas`

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/services.py`, `apps/visitas/tests/test_visita_destino.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `apps/sitios/`, `apps/productos/`, `config/`, migraciones
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones y comandos; `.agents/skills/django-conventions/SKILL.md` § Services (si existe la sección)
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: agregar `visita_destino(*, empleado, sitio)` (sin bloquear filas: devuelve la abierta propia del sitio con el mismo orden que hoy usa `abrir_visita`; si no hay y el empleado no es administrador, la de `_pendiente_para`; si no, `None`) y `servicio_para_punto(*, visita, punto)` → `(servicio | None, en_turno)`. `abrir_visita` usa `visita_destino` dentro de su transacción (después de bloquear el `Sitio`) sin cambiar su comportamiento; `_servicio_de_la_revision` usa `servicio_para_punto` y conserva el 400 `MENSAJE_SIN_SERVICIO` bajo `qr_codigo`. Docstrings en español.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.VisitaDestinoTests.test_abierta_propia_gana_sobre_pendiente_con_el_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.VisitaDestinoTests.test_sin_abierta_devuelve_la_pendiente_mas_antigua_sin_revisiones --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.VisitaDestinoTests.test_administrador_no_toma_pendientes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.VisitaDestinoTests.test_sin_visitas_devuelve_none --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.VisitaDestinoTests.test_abrir_visita_abre_la_visita_destino --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.ServicioParaPuntoTests.test_item_de_la_visita_da_su_servicio_en_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.ServicioParaPuntoTests.test_item_de_otra_visita_no_cuenta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_visita_destino.ServicioParaPuntoTests.test_sin_visita_da_el_servicio_del_punto_fuera_de_turno --keepdb`
  - `[grep-1]` `grep -n "def visita_destino(" apps/visitas/services.py`
  - `[grep-1]` `grep -n "def servicio_para_punto(" apps/visitas/services.py`
  - `[cmd]` `awk '/^def abrir_visita/{f=1;next} /^def /{f=0} f' apps/visitas/services.py | grep -v '^\s*#' | grep -q "visita_destino(empleado="`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T1`

### T2 — El ingreso en envases desde el panel aplica el tope

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/productos/panel_views.py`, `apps/productos/tests/test_panel_stock.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `apps/visitas/`, `apps/sitios/`, `apps/productos/services.py`, `apps/productos/panel_forms.py`, `config/`, migraciones
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones y comandos
- **Worktree**: sí
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**: `MovimientoAltaView.get_form_kwargs` pasa `producto=self.producto` a `MovimientoForm`. Test por el cliente del panel: con un producto de `contenido_por_envase` mayor que 1000, un POST de ingreso de 9999999 envases responde 200 con error en el formulario y no crea `MovimientoStock`; este test falla antes del cambio (500 / excepción).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_stock.FichaProductoTests.test_ingreso_en_envases_desbordado_muestra_error_sin_movimiento --keepdb`
  - `[grep-1]` `grep -n "def get_form_kwargs" apps/productos/panel_views.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T2`

### T3 — Integración (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/ajustes-flujo` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh ajustes-flujo T1 plan/ajustes-flujo apps/visitas/services.py apps/visitas/tests/test_visita_destino.py` y `bash .claude/hooks/worktree-integrar.sh ajustes-flujo T2 plan/ajustes-flujo apps/productos/panel_views.py apps/productos/tests/test_panel_stock.py`.
  3. Crear el worktree de la ola 2 con `bash .claude/hooks/worktree-crear.sh ajustes-flujo T4 plan/ajustes-flujo`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/ajustes-flujo | grep -q "T1: integra ajustes-flujo-T1"`
  - `[cmd]` `git log --oneline plan/ajustes-flujo | grep -q "T2: integra ajustes-flujo-T2"`

### T4 — El resolver usa la visita destino y la devuelve

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/sitios/api_views.py`, `apps/sitios/serializers.py`, `apps/sitios/tests/test_api_resolver_servicio.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `apps/visitas/`, `apps/productos/`, `apps/api/`, `config/`, migraciones
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § prohibiciones y comandos; `.agents/skills/django-rest-framework/SKILL.md` § Serializers (si existe la sección)
- **Worktree**: sí
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: `ResolverQRView` calcula `visita = visita_destino(empleado=request.user, sitio=sitio)` y `servicio, en_turno = servicio_para_punto(visita=visita, punto=punto)` (de `apps.visitas.services`), y quita `_servicio_del_punto`. `ResolverQRSerializer` suma `visita_destino` (entero o nulo: la visita en la que se guardaría la revisión; nulo si al abrir se crearía una nueva); `visita_pendiente_propia` y `visita_abierta_propia` se conservan sin cambios. Actualizar la `description` de `@extend_schema`. Los tests de coherencia recorren el flujo real por la API: resolver → (abrir si hace falta) → `POST /api/v1/revisiones/` con `visita` = la visita abierta resultante, y comparan `servicio` y `en_turno`/`fuera_de_turno`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverCoherenteConRevisionTests.test_abierta_sin_items_y_pendiente_con_el_punto_guarda_el_servicio_devuelto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverCoherenteConRevisionTests.test_abierto_y_pendiente_con_el_punto_devuelve_y_guarda_el_del_abierto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverCoherenteConRevisionTests.test_pendiente_mas_antigua_sin_el_punto_devuelve_y_guarda_fuera_de_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverCoherenteConRevisionTests.test_visita_destino_es_la_que_abre_abrir_visita --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverCoherenteConRevisionTests.test_sin_visitas_visita_destino_nula --keepdb`
  - `[grep-0]` `grep -n "def _servicio_del_punto" apps/sitios/api_views.py`
  - `[grep-1]` `grep -n "visita_destino" apps/sitios/serializers.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.visitas apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T4`

### T5 — Integración (principal): contrato y OpenAPI

- **Ola**: 2 (después de verificar T4)
- **Depende de**: T4
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/ajustes-flujo` de T4, no el informe.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh ajustes-flujo T4 plan/ajustes-flujo apps/sitios/api_views.py apps/sitios/serializers.py apps/sitios/tests/test_api_resolver_servicio.py`.
  3. Inline, en commits `T5:`: describir `visita_destino` en el bullet "Resolver un QR" de `docs/contrato-api.md` y regenerar `docs/api/openapi-v1.yaml` con `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file docs/api/openapi-v1.yaml`.
  4. Con todo integrado, el cierre global y la verificación `TODO`.
- **Presupuesto**: 150 líneas agregadas
- **Criterios**:
  - `[cmd]` `git log --oneline plan/ajustes-flujo | grep -q "T4: integra ajustes-flujo-T4"`
  - `[grep-1]` `grep -n "visita_destino" docs/contrato-api.md`
  - `[grep-1]` `grep -n "visita_destino" docs/api/openapi-v1.yaml`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T5`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-20-ajustes-flujo.md ajustes-flujo`

## Registro de verificación

commit_base: 377066c

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-21 | T1 | a81b59c (worktree) | PASA 13/13 (verificador y verificador-b) | |
| 2026-10-21 | T2 | 2adba9c (worktree) | PASA 4/4 (verificador y verificador-b) | |
| 2026-10-21 | T3 | 0b25de4 | integración: worktree-integrar exit 0 (T1 y T2) | sin verificador propio: criterios de log |
| 2026-10-21 | T4 | b6065a2 (worktree) | PASA 9/9 (verificador y verificador-b) | |
| 2026-10-21 | T5 | befb3c7 | PASA 6/6 (verificador, dentro de TODO) | |
| 2026-10-21 | TODO | befb3c7 | PASA 40/40 (verificador; 731 tests) | auditor-seguridad: 0 bloqueantes, 0 importantes, 4 observaciones (P-ajustes-flujo-1 a -4) |

## Pendientes que deja este plan

### Problemas

- P-ajustes-flujo-1 [observación] `abrir_visita` (`apps/visitas/services.py:384-393`): el comentario dice que se bloquean antes las visitas que pueden ser destino, pero un turno que `crear_turno` confirma entre el bloqueo y `visita_destino` se toma sin lock de fila; no es explotable porque la serialización la da el lock del Sitio. Precisar el comentario (auditor-seguridad).
- P-ajustes-flujo-2 [observación] `_pendiente_para(..., bloquear=True)` (`apps/visitas/services.py:246-256`) quedó sin llamadores con el valor por defecto: código muerto que sugiere un bloqueo que ya no ocurre (auditor-seguridad).
- P-ajustes-flujo-3 [observación] Falta un test de `visita_destino` y del campo del resolver con una visita abierta o pendiente de otro empleado o del mismo empleado en otro sitio; el código filtra bien, el test fijaría el comportamiento contra regresiones (auditor-seguridad).
- P-ajustes-flujo-4 [menor] `servicio_para_punto` no precarga `servicio__campos` como hacía `_servicio_del_punto`: el resolver hace 2-3 consultas extra por escaneo (auditor-seguridad y revisión del principal).

### Decisiones

- 2026-10-20 — El resolver de QR calcula servicio y `en_turno` sobre la visita destino (la que usaría `abrir_visita`: abierta propia del sitio; si no, la pendiente más antigua sin revisiones; si no, ninguna) y la devuelve en `visita_destino`; ya no busca el ítem en cualquier turno propio — invariante del usuario: lo que se muestra al escanear es lo que se guarda — reemplaza a: 2026-10-20 (el resolver elige el abierto antes que el pendiente y después el de `programada_para` más antigua)
- 2026-10-20 — `visita_destino(*, empleado, sitio)` y `servicio_para_punto(*, visita, punto)` viven en `apps/visitas/services.py` y las usan `abrir_visita`, la revisión y el resolver — una sola regla evita que vuelvan a divergir — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-21 — `abrir_visita` bloquea con `select_for_update` las visitas propias abiertas o pendientes del sitio antes de llamar a `visita_destino`, que no bloquea — conserva el orden de bloqueo Sitio → Visita → PuntoControl que exige `BloqueosTests.test_orden_de_bloqueo_sitio_visita` — decidida por Claude (implementador T1), revisable — reemplaza a: (nada)
- 2026-10-20 — La respuesta del resolver suma `visita_destino` y conserva `visita_pendiente_propia` y `visita_abierta_propia` — cambio aditivo del contrato, aprobado por el usuario — reemplaza a: (nada)

### Cierra

- cierra: P-flujo-sitio-1 — `MovimientoAltaView.get_form_kwargs` pasa el producto al formulario y el tope se aplica tras convertir envases (T2)
- cierra: P-flujo-sitio-11 — resolver y revisión usan `visita_destino` y `servicio_para_punto`; el resolver devuelve `visita_destino` (T1, T4, T5)
