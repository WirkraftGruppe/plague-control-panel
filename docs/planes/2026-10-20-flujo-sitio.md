# Plan: flujo-sitio — sin Proyecto, vencimiento por punto y turnos por punto

- **slug**: `flujo-sitio`
- **fecha**: 2026-10-20
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): flujo-sitio`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: el administrador trabaja desde el sitio: cada punto tiene servicio, frecuencia y vencimiento propios; arma turnos tildando puntos (con su servicio) para un operario, y el operario revisa por QR con el servicio que le toca; `Proyecto` y el Tablero desaparecen.
- **fuera de alcance**: rediseño visual (plan `diseno-panel`); generación automática de turnos, calendario, notificaciones; indicaciones para el operario; multiempresa; `apps/informes` (no existe código ni referencias a proyecto: nada que adaptar); bloqueo de `modo_unidad` (resto de P-catalogo-stock-3).
- **áreas**: panel | api | dominio (sitios, visitas, productos, servicios; se borra proyectos) | infraestructura (hook de cierre) | docs
- **seguridad**: sí — cambia la resolución de QR, la apertura de visitas y `POST /api/v1/revisiones/` (fotos 0 a 2), el acceso a planos pasa de proyecto a sitio, rutas nuevas del panel que escriben; corren `verificador`, `verificador-b` y `auditor-seguridad`.

## Contexto mínimo

- `Proyecto` (`apps/proyectos/models.py:27`) junta sitio, `tipo_servicio`, `frecuencia_dias`, `proxima_visita` y encargados. `Visita` toma la planilla de `proyecto.tipo_servicio`; `cerrar_visita` (`apps/visitas/services.py:628-668`) actualiza el proyecto; `abrir_visita` (`:259`) recibe `proyecto` + `qr_codigo` y bloquea Proyecto → Visita → Punto.
- `apps/sitios/estado.py` calcula el estado por (punto, proyecto) con la última revisión; lo usan `sitios/api_views.py:56,242`, `sitios/panel_views.py:122`, `panel/estado.py:24` y `panel/mapa.py:62`.
- Migraciones: `visitas/0001` depende de `proyectos/0002` y la `0006` usa `visita.proyecto`; `sitios/0007` depende de `visitas/0008`. **Decisión del usuario: se rehacen las migraciones de todas las apps** (un `0001_initial` por app).
- Tablero: `apps/panel/views.py:23` + `tablero.py` + `templates/panel/tablero.html`. Menú en `templates/panel/base.html:15-25`. El test de acceso (`apps/panel/tests/test_acceso.py:33`, `MODELO_POR_RUTA`) falla ante una ruta con parámetro sin mapeo.
- Fotos: `MAX_FOTOS = 10` y mínimo 1 en `apps/visitas/services.py:23,416` y `serializers.py:116`.
- P-catalogo-stock-1: `cantidad_base` `Decimal(14,4)` se desborda (`apps/visitas/services.py:126` `_errores_de_cantidad`, `apps/productos/services.py:34` `registrar_ingreso`, `panel_forms.py:45` `MovimientoForm.clean`). P-catalogo-stock-10: `TIMEOUT_CRITERIO = 300` y `PRESUPUESTO_TOTAL = 780` (`.claude/hooks/verificar_plan.py:71-72`), Stop con `timeout: 900` (`.claude/settings.json:19`); la suite completa supera los 300 s.
- docs/01 completo; `docs/contrato-api.md` (`test_contrato_doc` exige 18 filas); OpenAPI regenerado con `spectacular` (docs/01:201).

## Decisiones

- 2026-10-20 — Se rehacen las migraciones de todas las apps (un `0001_initial` por app, sin `RunPython` heredados); se borran `apps/visitas/tests/test_migraciones.py` y `apps/sitios/tests/test_migraciones.py`; las bases locales se recrean con `migrate` + `cargar_demo` — nada está en producción — decisión del usuario — reemplaza a: (nada)
- 2026-10-20 — Una revisión de un punto fuera del turno cuyo punto no tiene servicio da 400 ("El punto no tiene servicio asignado.") — decisión del usuario — reemplaza a: (nada)
- 2026-10-20 — El servicio de una revisión lo decide el servidor: el `ItemTurno` de la visita para ese punto o, si no hay, `PuntoControl.servicio`; `Revision.servicio` no es nulo; `fuera_de_turno` = la visita no tiene ítem para ese punto — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — `POST /api/v1/visitas/abrir/` recibe solo `qr_codigo` (más ubicación): abre el turno pendiente más antiguo del empleado en ese sitio, devuelve el abierto si ya hay uno, o crea una visita `origen=app` sin ítems — conserva la regla actual de abrir sin asignación previa — decidida por Claude, revisable — reemplaza a: 2026-10-05 (`abrir_visita(*, empleado, proyecto, qr_codigo)`)
- 2026-10-20 — Una revisión con `origen=app` lleva de 0 a 2 fotos (`MAX_FOTOS = 2`, sin mínimo) — decisión del usuario — reemplaza a: 2026-10-03 (al menos una foto para `origen=app`)
- 2026-10-20 — El orden de bloqueo único es Sitio → Visita → PuntoControl — el sitio ocupa el lugar del proyecto — decidida por Claude, revisable — reemplaza a: 2026-10-07 (Proyecto → Visita → PuntoControl)
- 2026-10-20 — La frecuencia y el vencimiento son por punto (`PuntoControl.frecuencia_dias`, `proximo_vencimiento`) — decisión del usuario — reemplaza a: 2026-09-29 (frecuencia por proyecto)
- 2026-10-20 — La carga manual rechaza una `realizada_en` anterior a `sitio.creado` — decidida por Claude, revisable — reemplaza a: 2026-10-07 (anterior a `proyecto.creado`, P-panel-24)
- 2026-10-20 — `Visita.datos` y `Visita.esquema_planilla` pasan a `{slug_servicio: …}` con la planilla de ámbito visita de cada servicio presente (ítems ∪ revisiones); `cerrar_visita` valida cada una con `validar_datos` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — Estados del punto: `vencida` (< hoy), `proxima` (≤ 7 días), `al_dia`, `sin_programar` (nulo); gravedad para el sitio: vencida > próxima > sin programar > al día — un punto sin programar pide atención antes que uno al día; `EstadoPunto`, `GRAVEDAD_PUNTO`, `peor_estado_punto` y `EstadoVisita`/`UMBRAL_PROXIMA_DIAS` de proyectos se unifican en `apps/sitios/estado.py` (T3 agrega, T5 borra lo viejo) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — Editar `frecuencia_dias` en el panel no recalcula `proximo_vencimiento`; el administrador ajusta la fecha a mano y la próxima revisión que cuenta la recalcula — `sitios` no depende de `visitas` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — El recálculo del vencimiento vive en `apps/visitas/services.py` (`actualizar_vencimiento(punto)`): toma la revisión más reciente de visitas abiertas o realizadas con `cuenta_como_servicio`, y lo llaman `registrar_revision` y `registrar_visita_manual` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — Propiedad: las líneas de `config/settings/base.py` (`INSTALLED_APPS`), `apps/api/urls.py` y `apps/panel/urls.py` que nombran proyectos las quita el principal, inline, en un commit `T5: quita proyectos de INSTALLED_APPS y de los routers` en el worktree de T5 antes de delegar (antecedente 2026-10-18); T5 es la única transversal de `apps/panel/**` del plan; T8 es la de diseño (`templates/panel/base.html`, `static/css/panel.css`; antecedente 2026-10-08); en la ola 3, T7 (capa API) y T8 (capa panel) se reparten `apps/sitios` y `apps/visitas` con archivos disjuntos listados en cada `Puede tocar` — juez-plan, ronda 1 — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — El criterio "sin referencias a Proyecto" excluye, además de `docs/planes/` y `docs/bitacora.md`, `docs/decisiones.md`, `docs/propuestas/` y `docs/prompts/` (registro histórico), y `.claude/hooks/` (`ProyectoTemporal` = proyecto de prueba del hook, no del dominio) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-20 — Hook de cierre: los criterios con el mismo comando se ejecutan una sola vez por corrida; un `manage.py test` sin etiquetas o solo con etiquetas de app (`apps.<app>`) recibe `TIMEOUT_SUITE = 700` s (`VERIFICAR_PLAN_TIMEOUT_SUITE`), recortado por el presupuesto; `PRESUPUESTO_TOTAL` (780 s) y el Stop de 900 s no cambian, porque Claude Code toma la configuración de hooks al iniciar la sesión; las subtareas de este plan usan la suite completa como criterio de regresión, así la corrida final la ejecuta una sola vez — cierra P-catalogo-stock-10 — juez-plan, ronda 1 — decidida por Claude, revisable — reemplaza a: (nada)

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3, T4 (integración) | sitios (T3) |
| 2 | T5, T6 (integración) | todas (reinicio de migraciones, solo T5) |
| 3 | T7, T8, T9 (integración) | — |
| 4 | T10, T11 (integración y cierre) | — |

## Subtareas

<!-- Común a las subtareas delegadas, salvo que se diga otra cosa:
No puede tocar: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `config/`, `apps/api/urls.py`, `apps/panel/urls.py`, migraciones existentes, `templates/panel/base.html`, archivos de otro dueño (excepciones de T5 y T8 en Decisiones).
Skill a leer antes: `.claude/skills/convenciones-proyecto/SKILL.md`.
Worktree: sí (`worktrees/flujo-sitio-T<n>`, base `plan/flujo-sitio`). Ruta: delegada (`implementador`). -->

### T1 — Productos: tope de `cantidad_base` y `unidad_base` fija con movimientos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/productos/unidades.py`, `apps/productos/services.py`, `apps/productos/panel_forms.py`, `apps/productos/tests/test_tope.py` (nuevo), `apps/productos/tests/test_panel_unidad_base.py` (nuevo)
- **No puede tocar**: lo común, `apps/productos/models.py`, `apps/productos/migrations/`, `apps/visitas/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 5 (Forms)
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**: `unidades.py` expone `MAXIMO_CANTIDAD_BASE = Decimal("9999999999.9999")` y `validar_cantidad_base(valor)` (lanza `ValidationError` con mensaje en español). `registrar_ingreso` y `registrar_ajuste` la aplican después de convertir; `MovimientoForm.clean` devuelve el error en `cantidad`. `ProductoForm.clean_unidad_base` rechaza el cambio si el producto tiene movimientos ("No se puede cambiar la unidad base de un producto con movimientos de stock.").
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_tope.TopeCantidadTests.test_ingreso_en_envases_desbordado_da_error_sin_movimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_tope.TopeCantidadTests.test_formulario_de_movimiento_desbordado_da_error_en_cantidad --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_tope.TopeCantidadTests.test_tope_exacto_se_acepta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_unidad_base.UnidadBaseTests.test_cambiar_unidad_base_con_movimientos_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_unidad_base.UnidadBaseTests.test_sin_movimientos_se_puede_cambiar --keepdb`
  - `[grep-1]` `grep -n "MAXIMO_CANTIDAD_BASE" apps/productos/unidades.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T1`

### T2 — Hook de cierre: timeout propio para la suite completa y criterios sin repetir

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `.claude/hooks/verificar_plan.py`, `.claude/hooks/test_verificar_plan.py`
- **No puede tocar**: lo común, `apps/`, los demás hooks, `.claude/settings.json`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Comandos canónicos
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: `es_suite(cmd)` reconoce `manage.py test` sin etiquetas o con etiquetas que son todas de app (`apps.<app>`, sin módulo ni clase), con o sin `--keepdb`; ese criterio recibe `TIMEOUT_SUITE = 700` (`VERIFICAR_PLAN_TIMEOUT_SUITE`, misma validación que `leer_timeout`), siempre recortado por el presupuesto. Los criterios con comando idéntico se ejecutan una vez por corrida y el resultado se reutiliza en el informe de cada subtarea. `PRESUPUESTO_TOTAL` sigue en 780 y `.claude/settings.json` no se toca; un test comprueba que `PRESUPUESTO_TOTAL` < el `timeout` del Stop leído de `.claude/settings.json`. Docstring del módulo actualizado (punto 8).
- **Criterios**:
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::TestTimeoutSuite::test_suite_sin_etiquetas_usa_timeout_de_suite -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::TestTimeoutSuite::test_suite_por_app_usa_timeout_de_suite -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::TestTimeoutSuite::test_test_nombrado_usa_timeout_comun -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::TestTimeoutSuite::test_criterio_repetido_se_ejecuta_una_vez -q`
  - `[test]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py::TestTimeoutSuite::test_presupuesto_total_queda_bajo_el_timeout_del_stop -q`
  - `[grep-1]` `grep -n "TIMEOUT_SUITE" .claude/hooks/verificar_plan.py`
  - `[cmd]` `py -3 -m pytest .claude/hooks/test_verificar_plan.py -q`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T2`

### T3 — Sitios: servicio, frecuencia y vencimiento por punto, responsable, estado y edición en línea

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/sitios/models.py`, `apps/sitios/migrations/0009_*.py` (generada; T5 la absorbe al reiniciar), `apps/sitios/estado.py`, `apps/sitios/services.py`, `apps/sitios/panel_views.py`, `apps/sitios/panel_forms.py`, `apps/sitios/panel_urls.py`, `apps/sitios/admin.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/tests/test_estado_vencimiento.py`, `apps/sitios/tests/test_panel_programacion.py` (nuevos)
- **No puede tocar**: lo común, `apps/visitas/`, `apps/proyectos/`, `apps/panel/`, `apps/sitios/api_views.py`, `apps/sitios/serializers.py`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2 (Models)
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**: `PuntoControl` suma `servicio` (FK `servicios.TipoServicio`, nulo, `PROTECT`, `related_name="puntos"`), `frecuencia_dias` (positivo, nulo) y `proximo_vencimiento` (fecha, nula), en el historial existente. `Sitio.responsable` (FK al usuario, nulo, `PROTECT`, limitado a empleados activos) en el formulario del sitio. En `estado.py`, **sin borrar lo existente** (sus llamadores los cambia T5): `EstadoVencimiento` (`vencida`, `proxima`, `al_dia`, `sin_programar`), `estado_por_vencimiento(fecha, hoy)`, `estados_por_vencimiento(puntos, hoy)` y `resumen_de_sitios(sitios, hoy)` (peor estado y vencimiento más cercano de los puntos activos), con un número fijo de consultas; usa el `UMBRAL_PROXIMA_DIAS` que hoy importa `estado.py` (no define otro). `services.actualizar_programacion(punto, servicio, frecuencia_dias, proximo_vencimiento, usuario)` con motivo en el historial. Ruta `puntos/<int:pk>/programacion/` (GET y POST con HTMX, devuelve la fila parcial) y la lista de puntos de la ficha con servicio, frecuencia y vencimiento editables en línea.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_estado_vencimiento.EstadoVencimientoTests.test_vencido_ayer_es_vencida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_estado_vencimiento.EstadoVencimientoTests.test_en_7_dias_es_proxima --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_estado_vencimiento.EstadoVencimientoTests.test_en_8_dias_es_al_dia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_estado_vencimiento.EstadoVencimientoTests.test_sin_fecha_es_sin_programar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_estado_vencimiento.EstadoVencimientoTests.test_sitio_toma_el_peor_estado_y_el_vencimiento_mas_cercano --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_estado_vencimiento.EstadoVencimientoTests.test_consultas_fijas_con_uno_o_cinco_sitios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ProgramacionPuntoTests.test_htmx_guarda_servicio_frecuencia_y_vencimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ProgramacionPuntoTests.test_devuelve_la_fila_parcial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ProgramacionPuntoTests.test_frecuencia_cero_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ProgramacionPuntoTests.test_cambio_queda_en_el_historial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ProgramacionPuntoTests.test_empleado_no_accede --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ResponsableSitioTests.test_formulario_guarda_responsable_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_programacion.ResponsableSitioTests.test_administrador_no_puede_ser_responsable --keepdb`
  - `[grep-1]` `grep -n "proximo_vencimiento = models.DateField" apps/sitios/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T3`

### T4 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1, T2 y T3)
- **Depende de**: T1, T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/flujo-sitio` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh flujo-sitio T<n> plan/flujo-sitio <rutas de Puede tocar>` para T1, T2 y T3.
  3. Crear el worktree de T5: `bash .claude/hooks/worktree-crear.sh flujo-sitio T5 plan/flujo-sitio`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T1: integra flujo-sitio-T1"`
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T2: integra flujo-sitio-T2"`
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T3: integra flujo-sitio-T3"`

### T5 — Dominio: borrar Proyecto, visita por sitio, ItemTurno, servicio por revisión, vencimiento y migraciones nuevas

- **Ola**: 2
- **Depende de**: T4
- **Propiedad**: única subtarea de la ola 2 y única transversal de `apps/panel/**` del plan (ver Decisiones). Antes de delegar, el principal hace inline en `worktrees/flujo-sitio-T5` el commit `T5: quita proyectos de INSTALLED_APPS y de los routers` (`config/settings/base.py`, `apps/api/urls.py`, `apps/panel/urls.py`); el implementador no toca esos tres archivos.
- **Puede tocar**: `apps/proyectos/**` (la borra), `apps/visitas/**`, `apps/sitios/**`, `apps/servicios/panel_forms.py`, `apps/servicios/tests/test_panel.py`, `apps/api/**` (salvo `urls.py`), `apps/panel/**` (salvo `urls.py`), `apps/*/migrations/**`. Incluye borrar `apps/visitas/tests/test_migraciones.py`, `apps/sitios/tests/test_migraciones.py` y `apps/panel/tests/test_tablero.py`, y los nuevos `apps/visitas/tests/test_turnos.py`, `apps/visitas/tests/test_vencimiento.py`, `apps/visitas/tests/test_turnos_api.py`, `apps/sitios/tests/test_acceso_por_sitio.py`, `apps/panel/tests/test_inicio.py`
- **No puede tocar**: lo común, `apps/productos/` (usa `validar_cantidad_base`, no la cambia), `templates/panel/base.html` y `static/` (sus restos de proyecto los quita T8), `docs/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2 (Models); `.agents/skills/django-rest-framework/SKILL.md` § Serializers
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 3000 líneas agregadas (incluye ≈700 de migraciones generadas y la adaptación mecánica de ≈450 líneas de tests)
- **Qué hacer**:
  - Modelo: `Visita.proyecto` → `Visita.sitio` (FK `Sitio`, `PROTECT`, `related_name="visitas"`); `ItemTurno` (visita `CASCADE` `related_name="items"`, punto `PROTECT`, servicio `PROTECT`; `UniqueConstraint` visita+punto); `Revision.servicio` (FK no nula, `PROTECT`) y `Revision.fuera_de_turno` (bool). `Visita.datos`/`esquema_planilla` por servicio (Decisiones). Borrar `apps/proyectos` entera y quitarla de `INSTALLED_APPS` y de los routers.
  - Migraciones: borrar todas las de todas las apps y generar un `0001_initial` por app con `makemigrations`; ningún `RunPython`.
  - Servicios (`apps/visitas/services.py`): `crear_turno(sitio, empleado, programada_para, items, asignada_por)` (≥ 1 ítem, puntos activos del sitio, servicio activo en cada uno; reemplaza a la asignación por proyecto); `abrir_visita(empleado, qr_codigo, …)` por sitio (Decisiones), bloqueo Sitio → Visita → Punto; `registrar_revision` resuelve servicio y `fuera_de_turno`, 400 si no hay servicio, esquema del servicio, `MAX_FOTOS = 2` sin mínimo (también en el serializer), tope de `cantidad_base` con `validar_cantidad_base` en `_errores_de_cantidad` (error en `productos_aplicados.<i>.cantidad`); `actualizar_vencimiento(punto)` (Decisiones) desde `registrar_revision` y `registrar_visita_manual`; `cerrar_visita` sin tocar proyecto y con datos por servicio; `registrar_visita_manual` por sitio con servicio por punto. Se mantienen atraso máximo, incidencias de ubicación, consumo de stock y `cuenta_como_servicio`.
  - Sitios: `ResolverQRView`, `PlanoImagenView` y `MisPuntosView` filtran por `visita.sitio` (el acceso al plano exige una visita abierta o pendiente del empleado en el sitio); callers de `estado.py` pasan a `estados_por_vencimiento`/`resumen_de_sitios` y se borra la lógica vieja por proyecto; `services.py` y `admin.py` sin proyecto. `servicios/panel_forms.py` `clave_en_uso` por `Revision.servicio` e `ItemTurno.servicio`. En `estado.py`, `UMBRAL_PROXIMA_DIAS` pasa a vivir ahí y se borran `EstadoPunto`, `GRAVEDAD_PUNTO`, `peor_estado_punto`, `estados_de_puntos` y `estado_revision`.
  - API mínima para que la suite pase: `AbrirVisitaSerializer` sin `proyecto`; los serializers de visita exponen `sitio` directo. (Las salidas nuevas son de T7.)
  - Panel: borrar el tablero (`InicioView`, `tablero.py`, `tablero.html`, `test_tablero.py`); `/panel/` redirige a `/panel/sitios/`; `mapa.py` con estado y vencimiento más cercano por sitio; las rutas de asignación y carga manual por proyecto pasan a `visitas/sitios/<int:sitio_pk>/turnos/nuevo/` (`NuevoTurnoView`, formulario básico con operario, fecha y puntos con servicio, sobre `crear_turno`) y `visitas/sitios/<int:sitio_pk>/cargar/` (`CargarVisitaView`, sobre `registrar_visita_manual`), sin plano ni atajos (los suma T8); `MODELO_POR_RUTA` con `visitas/sitios/@PK@/` → sitio; el popup del mapa (`mapa.py`, `static/panel/mapa.js`) muestra el vencimiento más cercano y enlaza a "Nuevo turno".
  - Demo: `cargar_demo` sin proyectos: puntos con servicios, frecuencias y vencimientos distintos (vencidos, próximos, al día, sin programar), turnos pendientes, abiertos y realizados con `crear_turno`; `registrar_revision_demo` por sitio.
  - Tests existentes: adaptar de proyecto a sitio sin dejar de probar lo que prueban.
- **Criterios**:
  - `[cmd]` `test -z "$(git ls-files apps/proyectos)"`
  - `[grep-0]` `grep -rniE "proyecto" apps config --include=*.py --include=*.html --include=*.js --include=*.css | grep -vE "RAIZ_PROYECTO|^config/(apps|asgi|contexto|urls|wsgi)\.py:1:|^config/settings/base\.py:[0-9]+:# Origen público del proyecto"`
  - `[grep-0]` `grep -rnE "EstadoPunto|GRAVEDAD_PUNTO|peor_estado_punto|estados_de_puntos|estado_revision|EstadoVisita" apps --include=*.py`
  - `[cmd]` `test "$(ls apps/*/migrations/0*.py | grep -v '/0001_initial.py$' | wc -l)" -eq 0`
  - `[grep-0]` `grep -rln "RunPython" apps --include=*.py --exclude-dir=tests`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.CrearTurnoTests.test_tres_puntos_uno_con_servicio_cambiado_guarda_tres_items --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.CrearTurnoTests.test_sin_puntos_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.CrearTurnoTests.test_punto_de_otro_sitio_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.RevisionTurnoTests.test_punto_del_turno_usa_el_servicio_del_item --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.RevisionTurnoTests.test_punto_fuera_del_turno_queda_fuera_de_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.RevisionTurnoTests.test_punto_sin_servicio_fuera_del_turno_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.CerrarTurnoTests.test_datos_de_visita_por_servicio_presente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_vencimiento.VencimientoTests.test_revision_con_frecuencia_30_fija_fecha_mas_30 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_vencimiento.VencimientoTests.test_revision_anterior_no_pisa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_vencimiento.VencimientoTests.test_visita_de_administrador_no_cambia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_vencimiento.VencimientoTests.test_carga_manual_actualiza_el_vencimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos_api.AbrirVisitaSitioApiTests.test_abre_el_turno_pendiente_del_sitio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos_api.AbrirVisitaSitioApiTests.test_sin_turno_crea_visita_sin_items --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos_api.RevisionFotosApiTests.test_cero_fotos_da_201 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos_api.RevisionFotosApiTests.test_tres_fotos_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos_api.RevisionCantidadApiTests.test_9999999_gal_en_base_ml_da_400_sin_movimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.CargaManualTests.test_cantidad_desbordada_da_error_sin_movimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_inicio.InicioTests.test_panel_redirige_a_sitios --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_inicio.InicioTests.test_rutas_del_tablero_y_de_proyectos_dan_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_inicio.MapaVencimientoTests.test_punto_vencido_ayer_pinta_el_sitio_vencido --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_inicio.MapaVencimientoTests.test_popup_trae_vencimiento_y_enlace_a_nuevo_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_acceso_por_sitio.AccesoPorSitioTests.test_plano_exige_visita_del_empleado_en_el_sitio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_acceso_por_sitio.AccesoPorSitioTests.test_plano_con_visita_en_otro_sitio_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_acceso_por_sitio.AccesoPorSitioTests.test_mis_puntos_solo_de_sitios_con_visita_propia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_turnos.CargaManualTests.test_fecha_anterior_al_alta_del_sitio_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTurnosTests.test_turnos_en_los_tres_estados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoTurnosTests.test_puntos_con_servicios_y_vencimientos_distintos --keepdb`
  - `[cmd]` `D=$(mktemp -d) && export DATABASE_URL="sqlite:///$(cygpath -m "$D")/vacia.sqlite3" MEDIA_ROOT="$(cygpath -m "$D")/media" && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py migrate --noinput && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py cargar_demo; r=$?; rm -rf "$D"; exit $r`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 3000 --subtarea T5`

### T6 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T5)
- **Depende de**: T5
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/flujo-sitio` de T5.
  2. Desde la raíz, `worktree-integrar.sh flujo-sitio T5 plan/flujo-sitio <rutas de Puede tocar más los tres archivos del commit inline>`.
  3. Con `git ls-files apps/proyectos` vacío, borrar en la raíz lo ignorado que queda (`rm -rf apps/proyectos`, solo `__pycache__`).
  4. Base local: renombrar `db.sqlite3` a `db.sqlite3.antes-flujo-sitio` (no se borra) y correr `migrate` + `cargar_demo`; avisar al usuario.
  5. Crear los worktrees de T7 y T8.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T5: integra flujo-sitio-T5"`
  - `[no-existe]` `apps/proyectos`

### T7 — API: servicio del punto en el QR, ítems de cada turno, respuesta de la revisión y contrato

- **Ola**: 3
- **Depende de**: T6
- **Puede tocar**: `apps/sitios/api_views.py`, `apps/sitios/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/serializers.py`, `apps/sitios/tests/test_api_resolver_servicio.py`, `apps/visitas/tests/test_api_mis_turnos.py` (nuevos), `apps/sitios/tests/test_api.py`, `apps/visitas/tests/test_api.py`, `docs/contrato-api.md`, `docs/api/openapi-v1.yaml` (regenerado con `spectacular`, nunca a mano)
- **No puede tocar**: lo común, `apps/*/services.py`, `apps/*/models.py`, `apps/*/panel_*.py`, `apps/panel/`, `apps/api/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Serializers
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**: el resolver de QR devuelve el punto con `estado`, `proximo_vencimiento`, `servicio` (`{id, nombre, slug, esquema_punto, esquema_visita}` o `null`) según el ítem del turno pendiente o abierto del empleado en el sitio o el servicio del punto, `en_turno`, y los ids de visita pendiente/abierta propias; sin `proyectos[]`. `GET /api/v1/me/visitas/` devuelve en cada turno `sitio{id,…}` e `items[]` (`punto{id,nombre,sector}`, `servicio{id,nombre}`, `revisado`). La respuesta de `POST /revisiones/` incluye `servicio` y `fuera_de_turno`. `docs/contrato-api.md` (abrir por `qr_codigo`, fotos 0 a 2, 400 sin servicio, `Actualizado:`) y OpenAPI regenerado.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverServicioTests.test_punto_del_turno_devuelve_el_servicio_del_item --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverServicioTests.test_punto_fuera_del_turno_devuelve_el_servicio_del_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverServicioTests.test_devuelve_el_esquema_del_servicio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverServicioTests.test_punto_vencido_ayer_figura_vencida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_api_resolver_servicio.ResolverServicioTests.test_punto_sin_servicio_devuelve_servicio_nulo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_mis_turnos.MisTurnosApiTests.test_devuelve_los_items_de_cada_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_mis_turnos.MisTurnosApiTests.test_no_devuelve_turnos_de_otro_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_mis_turnos.RevisionRespuestaTests.test_incluye_servicio_y_fuera_de_turno --keepdb`
  - `[grep-1]` `grep -n "fuera_de_turno" docs/api/openapi-v1.yaml`
  - `[grep-0]` `grep -niE "proyecto" docs/api/openapi-v1.yaml docs/contrato-api.md`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T7`

### T8 — Panel: menú, ficha del sitio, nuevo turno, cargar visita, turnos y popup del mapa

- **Ola**: 3
- **Depende de**: T6
- **Propiedad**: subtarea de diseño del plan (`templates/panel/base.html`, `static/css/panel.css`); no toca `apps/panel/**` (ver Decisiones).
- **Puede tocar**: `apps/sitios/panel_views.py`, `apps/sitios/panel_forms.py`, `apps/sitios/panel_urls.py`, `apps/sitios/templates/sitios/panel/**`, `apps/sitios/static/sitios/**`, `apps/visitas/panel_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/panel_urls.py`, `apps/visitas/templates/visitas/panel/**`, `apps/visitas/static/visitas/**`, `apps/visitas/templatetags/**` (nuevo), `templates/panel/base.html`, `static/css/panel.css`, `apps/sitios/tests/test_panel_ficha_turnos.py`, `apps/visitas/tests/test_panel_turnos.py`, `apps/visitas/tests/test_panel_menu.py` (nuevos), `apps/sitios/tests/test_panel.py`, `apps/visitas/tests/test_panel.py`
- **No puede tocar**: lo común salvo lo de Propiedad, `apps/*/services.py`, `apps/*/models.py`, `apps/*/api_views.py`, `apps/*/serializers.py`, `apps/panel/`, `static/src/**`, `static/css/app.css`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 3 (Views and URLs); `docs/02-diseno.md` (componentes existentes, sin rediseño)
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 1300 líneas agregadas
- **Qué hacer**: sobre las vistas `NuevoTurnoView` y `CargarVisitaView` de T5. Menú: Sitios, Mapa, Turnos (con contador de incidencias sin revisar, template tag en `apps/visitas/templatetags/`), Clientes, Catálogo (Servicios, Productos), Usuarios. Listado de visitas titulado "Turnos"; la ficha muestra ítems, servicio de cada revisión y "fuera de turno". Ficha del sitio: plano con puntos coloreados por estado, turnos pendientes y realizados, acciones "Nuevo turno" y "Cargar visita". `visitas/sitios/<int:sitio_pk>/turnos/nuevo/`: operario, fecha, plano y lista de puntos con casilla y servicio precargado (cambiable), atributos `data-punto`, `data-estado`, `data-servicio`; atajos "Todos", "Solo vencidos" (vencida o próxima) y "Ninguno"; tildar en la lista resalta en el plano y viceversa (JS estático, sin `<script>` en línea por la CSP); sin plano, solo la lista; usa `crear_turno`. `visitas/sitios/<int:sitio_pk>/cargar/` ("Cargar visita") con servicio por punto, usa `registrar_visita_manual`. Quitar el comentario de proyecto de `static/css/panel.css`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.NuevoTurnoPanelTests.test_tres_puntos_uno_con_servicio_cambiado_guarda_tres_items --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.NuevoTurnoPanelTests.test_cero_puntos_da_error_de_formulario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.NuevoTurnoPanelTests.test_punto_tildado_sin_servicio_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.NuevoTurnoPanelTests.test_html_expone_estado_y_servicio_de_cada_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.NuevoTurnoPanelTests.test_sin_plano_muestra_solo_la_lista --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.CargarVisitaPanelTests.test_carga_con_servicio_por_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_turnos.CargarVisitaPanelTests.test_cantidad_desbordada_da_error_en_el_producto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_turnos.FichaSitioTurnosTests.test_punto_vencido_ayer_figura_vencida_en_la_ficha --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_turnos.FichaSitioTurnosTests.test_lista_turnos_pendientes_y_realizados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_turnos.FichaSitioTurnosTests.test_acciones_nuevo_turno_y_cargar_visita --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_menu.MenuTests.test_menu_tiene_las_secciones_nuevas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_menu.MenuTests.test_contador_de_incidencias_sin_revisar --keepdb`
  - `[grep-0]` `grep -rniE "proyecto|tablero|visita manual" templates apps/*/templates`
  - `[grep-0]` `grep -rni "proyecto" static --include=*.css --include=*.js`
  - `[grep-0]` `grep -rn "<script>" apps/visitas/templates/visitas/panel apps/sitios/templates/sitios/panel`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 1300 --subtarea T8`

### T9 — Integración ola 3 (principal)

- **Ola**: 3 (después de verificar T7 y T8)
- **Depende de**: T7, T8
- **Pasos**:
  1. Revisar `cambios.sh` de T7 y T8.
  2. Desde la raíz, `worktree-integrar.sh` de T7 y de T8 en `plan/flujo-sitio`.
  3. Crear el worktree de T10.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T7: integra flujo-sitio-T7"`
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T8: integra flujo-sitio-T8"`

### T10 — Documentación del modelo y convenciones

- **Ola**: 4
- **Depende de**: T9
- **Puede tocar**: `docs/01-modelo-y-arquitectura.md`, `.claude/skills/convenciones-proyecto/SKILL.md`, `README.md`, `docs/ARRANQUE.md`, `docs/despliegue.md`
- **No puede tocar**: lo común, `apps/`, `docs/contrato-api.md`, `docs/api/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**: docs/01: modelo sin Proyecto (sitio con responsable, punto con servicio/frecuencia/vencimiento, `ItemTurno`, `Revision.servicio` y `fuera_de_turno`, datos por servicio), flujos (turno, QR, vencimiento, estados), panel sin tablero. Skill: lista de apps, olas por FK sin proyectos, reglas de dominio (abrir por QR del sitio, fotos 0 a 2, vencimiento por punto, planos por visita del sitio), `simple_history` sin Proyecto. README, ARRANQUE y despliegue sin proyectos. Fotos de 0 a 2 por revisión (docs/01 hoy dice "de 1 a 10").
- **Criterios**:
  - `[grep-0]` `grep -niE "proyecto" docs/01-modelo-y-arquitectura.md .claude/skills/convenciones-proyecto/SKILL.md README.md docs/ARRANQUE.md docs/despliegue.md | grep -viE "ra[ií]z del proyecto"`
  - `[grep-0]` `grep -nE "1 a 10 fotos|al menos una foto|m[ií]nimo una foto" docs/01-modelo-y-arquitectura.md .claude/skills/convenciones-proyecto/SKILL.md`
  - `[grep-1]` `grep -n "ItemTurno" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "proximo_vencimiento" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "fuera_de_turno" .claude/skills/convenciones-proyecto/SKILL.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T10`

### T11 — Integración ola 4 y cierre (principal)

- **Ola**: 4 (después de verificar T10)
- **Depende de**: T10
- **Pasos**:
  1. Revisar `cambios.sh` de T10; desde la raíz, `worktree-integrar.sh` de T10 en `plan/flujo-sitio`.
  2. `verificador` y `verificador-b` sobre `TODO`; `refutador` si discrepan; `auditor-seguridad` sobre resolver QR, abrir visita, revisiones, acceso a planos y rutas nuevas del panel.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/flujo-sitio | grep -q "T10: integra flujo-sitio-T10"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-20-flujo-sitio.md flujo-sitio`
- `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
- `[no-existe]` `apps/proyectos`
- `[grep-0]` `grep -rniE "proyecto" apps config templates static --include=*.py --include=*.html --include=*.js --include=*.css | grep -vE "RAIZ_PROYECTO|^config/(apps|asgi|contexto|urls|wsgi)\.py:1:|^config/settings/base\.py:[0-9]+:# Origen público del proyecto"`

## Registro de verificación

commit_base: fefbf2d

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | hecha |
| T3 | hecha |
| T4 | hecha |
| T5 | hecha |
| T6 | hecha |
| T7 | hecha |
| T8 | hecha |
| T9 | hecha |
| T10 | en curso |
| T11 | hecha |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-20 | T1 (verificador) | b8f17ee | PASA 8/8 | contraprueba del principal: `test_tope` 3 OK |
| 2026-10-20 | T2 (verificador) | f6608bb | PASA 8/8 | contraprueba: `TestTimeoutSuite` 5 passed |
| 2026-10-20 | T3 (verificador) | 4648291 | PASA 17/17 | suite 711 tests en 401 s; contraprueba: `test_estado_vencimiento` 6 OK |
| 2026-10-20 | T4 (principal) | fb3337d | PASA 3/3 | T1, T2 y T3 integrados con `worktree-integrar.sh` (exit 0) |
| 2026-10-20 | T5 (verificador) | d255b2f | PASA 36/36 | suite 697 tests en 382 s; nombre de `test_rutas_del_tablero_y_de_proyectos_dan_404` armado con `setattr` (ver P-flujo-sitio-3) |
| 2026-10-20 | T5 (verificador-b) | d255b2f | PASA 35/35 | coincide con verificador; `abrir_visita` sin sitio del cliente y plano por visita del sitio, con archivo:línea |
| 2026-10-20 | T6 (principal) | 382b863 | PASA 2/2 | T5 integrado; `apps/proyectos` (solo `__pycache__`) borrado; `db.sqlite3` → `db.sqlite3.antes-flujo-sitio`, `migrate` + `cargar_demo` OK |
| 2026-10-20 | T7 (verificador) | d954ee2 | PASA 13/13 | suite 705 tests en 390 s; commit `T7:` hecho por el principal con los archivos del implementador; contraprueba: 8 tests nuevos OK |
| 2026-10-20 | T8 (verificador) | 8241879 | PASA 17/17 | suite 709 tests en 391 s; sin `apps/panel/`, sin `<script>` ni `style=` en línea; contraprueba: 9 tests OK |
| 2026-10-20 | T9 (principal) | d7d9e5b | PASA 2/2 | T7 y T8 integrados; el primer intento de T7 lo rechazó un archivo sin seguimiento en la raíz (respaldo de la base, movido fuera del repo) |
| 2026-10-20 | T10 (verificador) | aa363f4 | FALLA 1/6 | único FALLA: el `grep-0` encuentra `.claude/skills/convenciones-proyecto/SKILL.md:2:name: convenciones-proyecto` (P-flujo-sitio-10); muestreo de docs/01 contra el código coincide; integrado igual en `plan/flujo-sitio`, T10 queda `en curso` |
| 2026-10-20 | TODO (verificador) | 2993dda | FALLA 3/122 | P-flujo-sitio-10 y dos `[grep-0]` de referencias a proyecto (T5 y cierre) por tests de T7 y T8 que nombraban lo quitado; corregidos en 0c6b32a (T7:) y 8d84bb2 (T8:) |
| 2026-10-20 | TODO (auditor-seguridad) | 2993dda | sin bloqueantes | 1 importante (P-flujo-sitio-11), 1 menor (P-flujo-sitio-12), 3 observaciones (P-flujo-sitio-13 a -15); migraciones sin restricciones perdidas |
| 2026-10-20 | TODO (verificador-b) | 8d84bb2 | FALLA 1/122 | único FALLA: P-flujo-sitio-10; suite 717 tests en 391 s; contrato intacto (una corrida previa la detuvo el usuario) |
| 2026-10-20 | TODO (verificador) | 8d84bb2 | FALLA 1/122 | coincide con verificador-b; los dos tests corregidos siguen probando lo mismo (el del menú delega la ausencia de la sección quitada al `[grep-0]` de T8) |
| 2026-10-20 | merge (usuario) | cf27f54 | aprobado | el usuario aprueba fusionar con el FALLA de P-flujo-sitio-10 a la vista y lo cierra como aceptado sin cambios; T10 queda `en curso` porque su primer `[grep-0]` sigue en FALLA |

## Pendientes que deja este plan

### Problemas

- P-flujo-sitio-1 [importante] `MovimientoAltaView` (`apps/productos/panel_views.py:80`) no pasa `producto` a `MovimientoForm`: un ingreso "en envases" desbordado desde el panel llega a `registrar_ingreso`, que lanza `ValidationError` sin capturar, y da 500. Corrección: `get_form_kwargs` con `producto=self.producto` y un test. Va a un plan aparte (decisión 2026-10-04; usuario, 2026-10-20) (implementador T1).
- P-flujo-sitio-2 [menor] `ProgramacionForm` (`apps/sitios/panel_forms.py`) ofrece solo servicios activos: si un punto tiene un servicio desactivado, el select de la fila no lo muestra y cualquier cambio en la fila lo pisa con otro valor o vacío (implementador T3).
- P-flujo-sitio-3 [menor] Defecto del contrato: el `[test]` `test_rutas_del_tablero_y_de_proyectos_dan_404` lleva "proyecto" en el nombre y el `[grep-0]` de T5 prohíbe esa palabra en `apps/`; `apps/panel/tests/test_inicio.py:16,60-66` arma el nombre con `"proy" + "ecto"` y `setattr`. Además `/panel/tablero/` nunca fue ruta (el tablero vivía en `/panel/`); que `/panel/` ya no es el tablero lo prueba `test_panel_redirige_a_sitios` (verificador T5).
- P-flujo-sitio-4 [observación] Redacción del plan: T5 "No puede tocar `apps/productos/`" choca con rehacer las migraciones de todas las apps (decisión del usuario); T5 tocó solo `apps/productos/migrations/` (verificador T5).
- P-flujo-sitio-5 [menor] `incidencia_asignacion` se marca si hay cualquier turno pendiente de otro empleado en el sitio; con varios operarios en un sitio puede ser ruido; quizá solo si el turno ajeno incluye ese punto (implementador T5).
- P-flujo-sitio-6 [menor] Un punto dado de alta en campo por la API no tiene servicio: su primera revisión fuera de turno da 400 hasta que el administrador le asigne uno; el contrato y la app deben explicarlo (implementador T5).
- P-flujo-sitio-7 [menor] `apps/visitas/static/visitas/nuevo_turno.js` (atajos "Todos", "Solo vencidos", "Ninguno" y la sincronización plano ↔ lista) no tiene test de JS ni se probó en un navegador; los tests cubren solo el HTML y los `data-*` (implementador T8).
- P-flujo-sitio-8 [observación] El plano coloreado por estado de la ficha del sitio está en la pestaña "Planos"; la pestaña por defecto muestra la tabla de puntos con su etiqueta de estado (implementador T8).
- P-flujo-sitio-9 [observación] Los marcadores del plano en "Nuevo turno" responden solo a clic (`keyboard: false`); la vía accesible es la lista con casillas (implementador T8).
- P-flujo-sitio-10 [importante] Defecto del contrato: el primer `[grep-0]` de T10 incluye `.claude/skills/convenciones-proyecto/SKILL.md`, cuyo frontmatter es `name: convenciones-proyecto`; no puede pasar sin renombrar la skill. El usuario decidió renombrarla en un plan aparte (cambia `.claude/skills/`, CLAUDE.md, agentes y planes); hasta entonces T10 no se marca `hecha` y el plan no llega a TODO PASA (verificador T10).
- P-flujo-sitio-11 [importante] El resolver de QR (`apps/sitios/api_views.py:77-101`, `_servicio_del_punto`) busca el ítem en cualquier turno propio abierto o pendiente, pero la revisión va a la visita que devuelve `abrir_visita` (la abierta): con una abierta sin ítems y una pendiente con ítem en el punto, el teléfono muestra `en_turno=true` y el esquema del ítem y el servidor registra con el servicio del punto (o 400 sin servicio). Corrección: buscar el ítem solo en la visita destino (abierta propia del sitio, o la pendiente que tomaría `abrir_visita`), con un test que falle antes (auditor-seguridad, TODO).
- P-flujo-sitio-12 [menor] `/admin/` permite cambiar el `sitio` de un turno pendiente con ítems (`apps/visitas/admin.py:36-56,153-164`) y crear pendientes sin ítems; `Visita.clean` no lo valida. Corrección: `sitio` de solo lectura si hay ítems (o validar en `clean` que los ítems sean del sitio) y considerar `has_add_permission = False` (auditor-seguridad, TODO).
- P-flujo-sitio-13 [observación] La definición de `auditor-seguridad` (`.claude/agents/auditor-seguridad.md`) todavía trata "visita `origen=app` sin foto" como hallazgo; contradice la decisión de fotos 0 a 2 (auditor-seguridad, TODO).
- P-flujo-sitio-14 [menor] `_servicio_de_la_revision` y el resolver no miran `TipoServicio.activo`: una revisión se registra con un servicio dado de baja; `PuntoProgramacion` acepta POST sobre un punto inactivo (`apps/sitios/panel_views.py:343-374`). Decisión de producto; relacionado con P-flujo-sitio-2 (auditor-seguridad, TODO).
- P-flujo-sitio-15 [observación] [despliegue] Las migraciones rehechas exigen que producción no tenga el esquema viejo: antes de desplegar, `manage.py showmigrations sitios visitas` contra la base de producción no debe mostrar `0008_ubicacion_fijada_y_precision`; quitar `proyecto` de `POST /visitas/abrir/` solo vale si no hay binarios de la app publicados (auditor-seguridad, TODO).

### Decisiones

- 2026-10-20 — La skill `convenciones-proyecto` se renombra en un plan aparte para que el criterio de T10 pueda pasar; este plan no modifica su contrato — decisión del usuario — reemplaza a: (nada)
- 2026-10-20 — La skill `convenciones-proyecto` no se renombra: en su nombre "proyecto" es el repositorio, no la entidad borrada; el FALLA del primer `[grep-0]` de T10 es un error del criterio y P-flujo-sitio-10 se cierra como aceptado sin cambios — decisión del usuario — reemplaza a: 2026-10-20 (renombrar la skill en un plan aparte)
- 2026-10-20 — El usuario acepta las decisiones del plan marcadas 'decidida por Claude, revisable' y fusiona `plan/flujo-sitio` en `main` (cf27f54) con el FALLA de P-flujo-sitio-10 a la vista — decisión del usuario — reemplaza a: (nada)
- 2026-10-20 — El resolver de QR elige, entre varios turnos propios con ese punto, el abierto antes que el pendiente y después el de `programada_para` más antigua; `SitioResumenSerializer` suma `id` en todas las respuestas — decidida por Claude (implementador T7), revisable — reemplaza a: (nada)
- 2026-10-20 — En el menú, "Catálogo" es un encabezado no clicable con "Servicios" y "Productos"; el contador de incidencias devuelve 0 sin consultar la base si no hay un administrador autenticado — decidida por Claude (implementador T8), revisable — reemplaza a: (nada)
- 2026-10-20 — El 400 "El punto no tiene servicio asignado." va bajo la clave `qr_codigo` — es el campo que identifica al punto — decidida por Claude (implementador T5), revisable — reemplaza a: (nada)
- 2026-10-20 — Una carga manual nueva crea un `ItemTurno` por cada (punto, servicio); al completar una pendiente, los puntos sin ítem quedan `fuera_de_turno` — decidida por Claude (implementador T5), revisable — reemplaza a: (nada)
- 2026-10-20 — `crear_turno(*, sitio, empleado, programada_para, items=[(punto, servicio)], asignada_por)`; rutas `panel:visitas:nuevo_turno` y `panel:visitas:cargar`; `Visita.datos = {slug: {clave: valor}}` con errores `"slug: clave: mensaje"` bajo `datos` — decidida por Claude (implementador T5), revisable — reemplaza a: (nada)

### Cierra

- cierra: P-catalogo-stock-1 — tope `MAXIMO_CANTIDAD_BASE` tras convertir en la API, la carga manual y el servicio de ingresos (T1, T5, T8); el 500 que queda en el ingreso en envases desde el panel sigue como P-flujo-sitio-1
- cierra: P-catalogo-stock-10 — timeout propio de la suite completa y criterios sin repetir en el hook de cierre (T2)
- cierra: P-catalogo-stock-8 — el menú lateral deja "Planillas" por "Catálogo › Servicios" (T8)
- cierra: P-flujo-sitio-10 — aceptado sin cambios: el criterio era el error, la skill no se renombra (decisión del usuario 2026-10-20)

## Verificación de punta a punta (para el usuario)

Con el plan integrado: `migrate` + `cargar_demo` en una base vacía, `runserver`, ingresar como `demo-admin`: `/panel/` cae en Sitios; en un sitio se edita el vencimiento de un punto en línea, se arma un turno con "Solo vencidos" y se ve en Turnos; desde la API (o `registrar_revision_demo`) una revisión de un punto del turno corre el vencimiento y una de un punto fuera del turno queda "fuera de turno".
