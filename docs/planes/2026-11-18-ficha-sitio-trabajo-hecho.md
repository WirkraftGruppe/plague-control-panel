# Plan: Ficha del sitio — que se vea el trabajo hecho

- **slug**: `ficha-sitio-trabajo-hecho`
- **fecha**: 2026-11-18
- **objetivo**: el administrador ve en la ficha del sitio la última revisión de cada punto y el avance de los turnos abiertos, y un punto recién revisado deja de figurar "próxima".
- **fuera de alcance**: el cálculo de `proximo_vencimiento` (`actualizar_vencimiento`); la app móvil; el filtro "Esta semana" de turnos (`apps/visitas/panel_views.py:63`, sigue con hoy + 7); el sondeo de estado de 5 s de la ficha (`apps/panel/estado.py`, se mantiene tal cual por decisión del usuario); el orden del listado de sitios.
- **áreas**: panel | api | dominio (modelos y servicios)
- **ruta**: completo
- **seguridad**: sí — vista nueva del panel (parcial del avance) que expone datos del sitio, revisiones y nombres de empleados; tiene que filtrar por `request.empresa`. Corre `auditor-seguridad`.

## Contexto mínimo

- `apps/sitios/estado.py`: hoy "próxima" es `proximo_vencimiento <= hoy + 7` (`UMBRAL_PROXIMA_DIAS`), sin mirar `frecuencia_dias`. El estado del sitio (`estado_de_sitio`, `condicion_de_estado`, `conteos_por_estado`) sale del **mínimo** vencimiento de sus puntos activos, anotado en `SitioListado._con_vencimiento` (`apps/sitios/panel_views.py:108`). La ficha lo calcula igual (`panel_views.py:300`). El mapa usa `resumen_de_sitios` (`apps/panel/mapa.py:45`). La API usa `estado_por_vencimiento` (`apps/sitios/api_views.py:172`, `apps/visitas/serializers.py:269`) y `estados_por_vencimiento` (`apps/sitios/api_views.py:60` y `:280`).
- Regla nueva: días de aviso = `ceil(frecuencia_dias / 4)` acotado a [1, 7]; sin frecuencia (nula o 0), 7; si el aviso cubre la frecuencia entera, se usa `frecuencia_dias - 1` (frecuencia 1: "próxima" solo el día que vence). Con un aviso variable, el mínimo vencimiento ya no decide: el sitio es "próxima" si **algún** punto activo lo es. El estado del sitio pasa a calcularse sobre los puntos, y `EstadoSitio.SEMANA` pasa a decir "Próxima" (su valor `semana` en la URL no cambia). Se conserva el orden actual del listado ("sin fechas" solo si ningún punto tiene fecha) y el del mapa (`GRAVEDAD_VENCIMIENTO`); la diferencia entre los dos ya existe y queda como pendiente.
- Ficha (`SitioFicha`, `apps/sitios/panel_views.py:274`, `sitios/panel/ficha.html:49-64`): la lista `ul#ficha-puntos` muestra el vencimiento, pero no la última revisión. `ficha_plano.js:7` se engancha a `#ficha-puntos`.
- Última revisión que cuenta: la misma regla que `actualizar_vencimiento` (`apps/visitas/services.py:548-556`), o sea `Revision` con `visita__estado` abierta o realizada y `visita__cuenta_como_servicio=True`; la más reciente por `realizada_en`.
- Turno abierto: `Visita` del sitio con `estado=abierta`. Sus puntos son los `ItemTurno` (`apps/visitas/models.py:152`); una visita abierta por QR sin turno previo no tiene ítems. Una visita abierta por un administrador (`cuenta_como_servicio=False`) no cuenta como turno en la ficha: ni bloque, ni marca, ni actualización.
- HTMX ya está cargado (`templates/panel/base.html:7`); `sondeo.js` pausa todo elemento `data-sondeo` mientras la pestaña está oculta.
- Docs: `docs/01-modelo-y-arquitectura.md:71` (estados), `docs/contrato-api.md:44` y `:76`, `docs/02-diseno.md` (ficha del sitio).

## Olas

No hay migraciones. T1 cambia `estado.py`, que usan T3 y T4, así que va sola en la ola 1. `panel_views.py` y las plantillas son todos de T4.

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 (integración) | sitios (sin migraciones) |
| 2 | T3, T4, T5, T6 (integración) | visitas, sitios, docs (sin migraciones) |

## Subtareas

### T1 — Aplicar los días de aviso por frecuencia en `estado.py` y la API de sitios

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/sitios/estado.py`, `apps/sitios/api_views.py`, `apps/sitios/tests/test_aviso_proxima.py`, `apps/sitios/tests/test_estado_vencimiento.py`
- **No puede tocar**: `docs/planes/`, `apps/sitios/panel_views.py`, `apps/sitios/templates/`, `apps/panel/`, `apps/visitas/`, `docs/`, migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 7: Performance Optimization y § Task 8: Testing Django Applications
- **Worktree**: sí
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**: `dias_aviso(frecuencia_dias)` con la regla del Contexto (`UMBRAL_PROXIMA_DIAS = 7` queda como tope y como valor sin frecuencia). `estado_por_vencimiento(fecha, hoy, frecuencia_dias=None)`; `estados_por_vencimiento(puntos, hoy)` y `resumen_de_sitios` leen la frecuencia de cada punto (la segunda, en la misma única consulta). Estado del sitio: el peor de sus puntos activos (vencidos si alguno vence antes de hoy, próxima si alguno está en aviso, sin fechas si ninguno tiene fecha, al día en otro caso). Se agrega `estado_de_sitio_por_puntos(puntos, hoy)` para Python, y `condicion_de_estado(estado, hoy)` se reescribe sobre los puntos activos del sitio (`Exists` y condiciones por rango de frecuencia, sin aritmética de fechas en SQL), conservando su firma de llamada para que `conteos_por_estado` y los filtros del listado sigan andando sin tocar `panel_views.py`. Un test comprueba que las dos versiones coinciden. `EstadoSitio.SEMANA` y su chip dicen "Próxima". `estado_de_sitio(vencimiento, hoy)` se conserva: T4 deja de usarlo y su borrado queda como pendiente. `api_views.py:172` pasa la frecuencia.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.DiasAvisoTests.test_dias_aviso_por_frecuencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_7_revisado_hoy_queda_al_dia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_7_a_dos_dias_queda_proxima --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_14_proxima_a_4_dias_o_menos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_30_y_90_proxima_a_7_dias_o_menos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_sin_frecuencia_proxima_a_7_dias_o_menos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_1_proxima_solo_el_dia_que_vence --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoSitioTests.test_condicion_sql_coincide_con_estado_en_python --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoSitioTests.test_sitio_proximo_por_un_punto_que_no_es_el_mas_cercano --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoSitioTests.test_mapa_usa_los_dias_de_aviso --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.ApiSitiosTests.test_resolver_y_me_puntos_usan_los_dias_de_aviso --keepdb`
  - `[grep-0]` `grep -n "Esta semana" apps/sitios/estado.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T1`

### T2 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/ficha-sitio-trabajo-hecho` de T1, no el informe.
  2. Desde el worktree de la rama destino, `bash .claude/hooks/worktree-integrar.sh ficha-sitio-trabajo-hecho T1 plan/ficha-sitio-trabajo-hecho <rutas>` y `verificar.py tarea`.
  3. Crear los worktrees de T3, T4 y T5 con `bash .claude/hooks/worktree-crear.sh ficha-sitio-trabajo-hecho T<n> plan/ficha-sitio-trabajo-hecho`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T2:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T2`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T1: integra ficha-sitio-trabajo-hecho-T1"`

### T3 — Usar los días de aviso en el estado del punto de los turnos de la API

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `apps/visitas/serializers.py`, `apps/visitas/tests/test_estado_aviso.py`
- **No puede tocar**: `docs/planes/`, `apps/sitios/`, `apps/panel/`, `docs/`, migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 8: Testing Django Applications
- **Worktree**: sí
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**: `PuntoItemSerializer.get_estado` (`apps/visitas/serializers.py:269`) pasa `frecuencia_dias=punto.frecuencia_dias` a `estado_por_vencimiento`. El test va por el endpoint que usa ese serializador: un punto con frecuencia 7 que vence dentro de 5 días devuelve `al_dia`, el mismo valor que `estados_por_vencimiento`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_estado_aviso.EstadoAvisoApiTests.test_estado_del_punto_del_turno_usa_la_frecuencia --keepdb`
  - `[grep-1]` `grep -n "frecuencia_dias=punto.frecuencia_dias" apps/visitas/serializers.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T3`

### T4 — Estado del sitio por sus puntos en el panel, última revisión y avance de los turnos abiertos en la ficha

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `apps/sitios/panel_views.py`, `apps/sitios/panel_urls.py`, `apps/sitios/templates/sitios/panel/`, `apps/sitios/static/sitios/ficha_plano.js`, `apps/sitios/tests/test_panel_ficha_avance.py`, `apps/sitios/tests/test_panel.py`
- **No puede tocar**: `docs/planes/`, `apps/sitios/estado.py`, `apps/visitas/`, `apps/panel/`, `templates/panel/`, `static/css/`, `docs/`, migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 3: Views and URLs Best Practices y § Task 8: Testing Django Applications; `.agents/skills/django-security/SKILL.md` § Authorization
- **Worktree**: sí
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**: (1) El chip de cada sitio del listado y el `estado_general` de la ficha salen de los puntos activos (`estado_de_sitio_por_puntos` o una anotación equivalente a `condicion_de_estado`), sin consultas por sitio; `panel_views.py` deja de usar `estado_de_sitio(`. (2) Cada punto de `#ficha-puntos` muestra la fecha, la hora local y el operario de su última revisión que cuenta (regla del Contexto), o "Sin revisiones", con anotaciones `Subquery` sobre los puntos. (3) Arriba de la lista va un bloque por **cada** visita abierta del sitio que cuenta como servicio (las de un administrador se ignoran), con el operario, la hora de apertura y "N de M puntos revisados". M son los ítems del turno; si la visita no tiene ítems, los puntos activos del sitio. N son los puntos distintos de esos M con una revisión en esa visita. Cada punto revisado en un turno abierto lleva la marca "Revisado en este turno" con el operario. "Turnos de hoy" del listado (`panel_views.py:168-169`) pasa a usar la misma definición de N y M. (4) Bloques y lista van en un parcial que sirve una vista nueva, `SitioFichaAvance` (`panel:sitios:ficha_avance`, `<int:pk>/avance/`, solo administrador, `Sitio.objects.de_empresa(request.empresa)`). El contenedor lleva `data-sondeo hx-get hx-trigger="every 30s" hx-swap="outerHTML"` solo si hay una visita abierta que cuenta; sin ella (o cuando se cierra la última) el contenedor no lleva `hx-get`, `hx-trigger` ni `data-sondeo`, y la actualización se corta. El test de consultas arma, con 5 y con 50 puntos, una revisión por punto de operarios distintos, una revisión de visita de administrador y un turno abierto con ítems, y mide la ficha y `SitioFichaAvance`. Tras el reemplazo (`htmx:afterSwap`), `ficha_plano.js` vuelve a engancharse a la lista. Solo se usan clases que ya existen en `panel.css`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.EstadoSitioPanelTests.test_listado_chip_proxima_por_un_punto_que_no_es_el_mas_cercano --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.EstadoSitioPanelTests.test_estado_de_me_puntos_coincide_con_la_ficha --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_muestra_fecha_hora_y_operario_de_la_ultima_revision --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_revision_de_visita_de_administrador_no_cuenta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_punto_sin_revisiones_dice_sin_revisiones --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_consultas_iguales_con_5_y_50_puntos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_turno_abierto_muestra_operario_apertura_y_avance --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_dos_turnos_abiertos_muestran_dos_bloques --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_punto_revisado_en_el_turno_queda_marcado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_sin_turno_abierto_no_hay_actualizacion_de_30_s --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_avance_tras_cerrar_el_turno_corta_la_actualizacion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_visita_de_administrador_no_cuenta_como_turno --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_turnos_de_hoy_usan_el_mismo_avance --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_avance_de_sitio_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_avance_pide_administrador --keepdb`
  - `[grep-0]` `grep -nw "estado_de_sitio" apps/sitios/panel_views.py`
  - `[grep-1]` `grep -rn "every 30s" apps/sitios/templates/sitios/panel/`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T4`

### T5 — Documentar la regla de aviso y la ficha nueva

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `docs/01-modelo-y-arquitectura.md`, `docs/contrato-api.md`, `docs/02-diseno.md`
- **No puede tocar**: `docs/planes/`, `docs/decisiones.md`, `docs/estado.md`, `apps/`
- **Skill a leer antes**: —
- **Worktree**: sí
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**: doc 01 (`:71`): la regla de días de aviso y que el estado del sitio es el peor de sus puntos. `contrato-api.md` (`:44` y `:76`): `proxima` depende de `frecuencia_dias` con la misma regla. `02-diseno.md`: una sección nueva de la ficha del sitio (hoy no existe) con el chip "Próxima" del listado, la última revisión en la lista de la ficha, el bloque por turno abierto y la actualización cada 30 s solo con un turno abierto que cuenta, y el sondeo de estado de 5 s que sigue.
- **Criterios**:
  - `[grep-1]` `grep -n "días de aviso" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "días de aviso" docs/contrato-api.md`
  - `[grep-1]` `grep -n "30 s" docs/02-diseno.md`
  - `[grep-0]` `grep -n "dentro de los próximos 7 días" docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T5`

### T6 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T3, T4 y T5)
- **Depende de**: T3, T4, T5
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/ficha-sitio-trabajo-hecho` de cada subtarea, no los informes.
  2. Desde el worktree de la rama destino, `worktree-integrar.sh` de T3, T4 y T5, de a una, con `verificar.py tarea` tras cada integración.
  3. Con todo integrado, el cierre: `verificar.py todo`, `revisor` en modo cierre, `auditor-seguridad` y el commit `cierre: ficha-sitio-trabajo-hecho`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T6:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T6`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T3: integra ficha-sitio-trabajo-hecho-T3"`
  - `[cmd]` `git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T4: integra ficha-sitio-trabajo-hecho-T4"`
  - `[cmd]` `git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T5: integra ficha-sitio-trabajo-hecho-T5"`

## Registro de verificación

commit_base: 3b0bb32

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | hecha | d1f40d1 | PASA 2026-11-18 |
| T2 | hecha | c0ff43a | PASA 2026-11-18 |
| T3 | pendiente | | |
| T4 | pendiente | | |
| T5 | pendiente | | |
| T6 | pendiente | | |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-18 17:05 | plan | 0 | 3 | 6 |

Auditoría: pendiente
Hallazgos: pendiente

### Decisiones del plan

- T4 — qué es M en "N de M" — ítems del turno / puntos activos del sitio — los ítems del turno; sin ítems (visita abierta por QR), los puntos activos del sitio — es lo que el operario tiene que hacer — autónoma — cambiar la cuenta en `SitioFichaAvance` — decidida por Claude, revisable
- T1 — firma de `estado_por_vencimiento` — parámetro obligatorio / `frecuencia_dias=None` — `None`, que vale "sin frecuencia" (7 días) — los llamadores de otras apps siguen andando hasta que su subtarea los ajusta; T3 cubre el único fuera de `sitios` — autónoma — volverlo obligatorio — decidida por Claude, revisable
- T1/T4 — reparto de `estado.py` y `panel_views.py` — una subtarea / dos sin archivos compartidos — dos: T1 conserva `estado_de_sitio` y la firma de `condicion_de_estado`, T4 deja de usar el primero; el borrado queda pendiente — `revisar_plan.py` no admite dos subtareas con el mismo archivo — autónoma — fusionar T1 y T4 — decidida por Claude, revisable
- T1 — gravedad de "sin fechas" en el sitio — unificar listado y mapa / conservar las dos — conservar: la diferencia es anterior y unificarla cambia el listado sin pedido — autónoma — unificar en otro plan — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-ficha-sitio-trabajo-hecho-1 [menor] `estado_de_sitio(vencimiento, hoy)` (`apps/sitios/estado.py`) queda sin uso tras T4; borrarlo en el próximo plan que toque `sitios`.
- P-ficha-sitio-trabajo-hecho-2 [observación] El listado de sitios pone "Al día" a un sitio con puntos al día y sin programar; el mapa lo pone "sin_programar" (`GRAVEDAD_VENCIMIENTO`). Diferencia anterior a este plan; la revisión de plan del 2026-11-18 la señaló.

### Decisiones

- 2026-11-18 — "próxima" depende de la frecuencia: días de aviso = `ceil(frecuencia_dias / 4)` entre 1 y 7; sin frecuencia, 7; el sitio es "próxima" si alguno de sus puntos activos lo es, y si el aviso cubre la frecuencia entera se usa `frecuencia_dias - 1`; el chip y el filtro de sitios dicen "Próxima" — un punto con frecuencia 7 figuraba "próxima" recién revisado — (usuario) — reemplaza a: 2026-10-20
- 2026-11-18 — la ficha muestra un bloque de avance por cada turno abierto del sitio que cuenta como servicio (las visitas de un administrador se ignoran), actualizado cada 30 s solo mientras haya uno abierto — elección del usuario — (usuario) — reemplaza a: (nada)
- 2026-11-18 — el sondeo de estado de 5 s de la ficha (`apps/panel/estado.py`) se mantiene aunque no haya turno abierto; el criterio "sin turno abierto no hay pedidos periódicos" vale para la actualización nueva de 30 s — elección del usuario — (usuario) — reemplaza a: (nada)

### Cierra
