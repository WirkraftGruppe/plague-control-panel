# Plan: Coordinación entre operarios y carga simple de productos

- **slug**: `coordinacion-operarios`
- **fecha**: 2026-11-20
- **objetivo**: el operario y el administrador se enteran cuando otro operario ya revisó o tiene asignado un punto ese día; el operario carga de cada producto solo cantidad y lote (la dosis la define el administrador); y lo registrado sin conexión con horas inconsistentes se acepta marcado en vez de rechazarse.
- **fuera de alcance**: bloquear una revisión duplicada o impedir que dos turnos compartan un punto; el descuento de stock; cantidad, unidades y conversión; el cron de `cerrar_visitas_abiertas` y los pendientes `despliegue`; el certificado; la app (`detach-app`).
- **áreas**: panel | api | dominio (modelos y servicios)
- **ruta**: completo
- **seguridad**: sí. Expone el nombre y la hora de revisión de otro operario (solo a usuarios de su misma empresa y solo para revisiones de hoy). Agrega un endpoint que abre un turno sin el QR, que es la prueba de presencia. Acepta revisiones sin coordenadas (geolocalización). Limita `me/datos-sin-conexion/`. Corre `auditor-seguridad`.

## Contexto mínimo

- **Revisiones y operario**: `Revision` no tiene empleado; sale de `visita.empleado`. Cuentan solo las revisiones de visitas con `cuenta_como_servicio=True` (`apps/visitas/models.py:111`) y estado distinto de `cancelada`. "Hoy" es `timezone.localdate()` del servidor.
- **Incidencias**: las de la visita están en `Visita` (`incidencia`, `incidencia_asignacion`, `incidencia_ubicacion`); las de la revisión, en `Revision` (`incidencia_servicio`). Las cuenta `condicion_incidencia_sin_revisar()` (`apps/visitas/services.py:956`) y las resuelve `marcar_incidencia_revisada()` (`services.py:1323`). Las cuatro nuevas siguen ese patrón y no tocan `proximo_vencimiento` ni el stock.
- **Horas inconsistentes** (P-trabajo-sin-conexion-15 y -16, decisión del usuario del 2026-11-19): hoy `cerrar_visita` (`services.py:1109-1118`) y `registrar_no_revisado` (`services.py:907-918`) responden 400. Pasan a guardar la hora declarada y marcar `Visita.incidencia_horas`. Los tests `test_sin_conexion_ajustes.HoraAnteriorApiTests` y `test_sin_conexion_servicios.HoraClienteTests.test_cerrada_en_anterior_a_abierta_falla` se reescriben.
- **Sin coordenadas** (decisión del usuario del 2026-11-20): hoy `_guardar_revision` (`obligatorias=True`, `services.py:684`) y `CrearRevisionSerializer` (`apps/visitas/serializers.py:139-150`) responden 400 (`test_services.py:137`, `test_api.py:382-390`). Pasan a aceptar la revisión con `Revision.incidencia_sin_ubicacion`.
- **Productos** (decisión del usuario del 2026-11-20):
  - `Producto.unidad_dosis_por_defecto` se renombra a `unidad_dosis_habitual` (RenameField). Se suman `dosis_habitual` y `dosis_variable`.
  - `ProductoAplicado.dosis` pasa a ser opcional (null) y `unidad_dosis` admite vacío (`""`, sin null).
  - Los productos que ya existen se migran con `dosis_variable=True`, para que sigan guardando la dosis enviada hasta que el administrador cargue la habitual. Un producto nuevo exige dosis habitual con unidad o `dosis_variable` (decisiones del usuario del 2026-11-20).
  - La dosis se resuelve en `_armar_productos` (`services.py:184`), que comparten la API y "Cargar visita".
  - Hay tests que esperan la dosis enviada (`test_robustez_visitas.py:52`, `test_stock_api.py:53-58`); sus productos pasan a `dosis_variable=True`.
- **Catálogo**: `CatalogoView` (`apps/productos/api_views.py:15-44`) arma un ETag con el hash del JSON, así que cambia cuando cambia `ultimo_lote`.
- **Apertura**: hoy solo está `POST visitas/abrir/`, que exige `qr_codigo` (`abrir_visita`, `services.py:425`). Se suma `POST visitas/<pk>/abrir/` sin QR. `apps/api/tests/test_contrato_doc.py:46` exige 23 rutas: la ruta, su fila en el contrato y el conteo entran juntos, en T8.
- **Límite** (P-trabajo-sin-conexion-18): `DatosSinConexionView` (`apps/sitios/api_views.py:292`) no tiene throttle. Los settings son del principal, así que la tasa va en la clase, como en `ThrottleRenovacion` (`apps/api/views.py:46-57`).
- **Panel**:
  - "Nuevo turno": `apps/visitas/panel_views.py:383`, `_puntos_servicio.html` y `apps/visitas/static/visitas/nuevo_turno.js:72-76`.
  - Ficha del turno: `panel_views.py:253` y `ficha.html`.
  - Ficha del sitio: `apps/sitios/panel_views.py:370` y `sitios/panel/ficha.html`.
  - En el modelo: `docs/01-modelo-y-arquitectura.md` §3.9 (Producto) y § Visitas.

## Olas

`revisar_plan.py` no admite que dos subtareas compartan un archivo, y `worktree-integrar.sh` corre la suite completa y revierte el merge si falla. Por eso cada archivo tiene un solo dueño en todo el plan, y cada subtarea ajusta los tests existentes que su cambio rompe.

Las olas siguen el grafo de FK: `productos` va antes que `visitas`, y `sitios` lee de `visitas` (código, no migraciones).

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2 (integración) | productos (0002); panel (demo, sin migraciones) |
| 2 | T3, T4 (integración) | visitas (0005) |
| 3 | T5, T6, T7 (integración) | sin migraciones (sitios, panel de visitas) |
| 4 | T8, T9 (integración y cierre) | sin migraciones (API de visitas y documentación) |

## Subtareas

### T1 — Dosis habitual y variable en `Producto`, `ultimo_lote` en el catálogo y `cargar_demo`

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/productos/models.py`, `apps/productos/migrations/0002_dosis_habitual.py`, `apps/productos/panel_forms.py`, `apps/productos/serializers.py`, `apps/productos/api_views.py`, `apps/productos/consultas.py`, `apps/productos/templates/productos/panel/formulario.html`, `apps/productos/tests/`, `apps/panel/demo_datos.py`, `apps/panel/demo_historia.py`, `apps/panel/demo.py`, `apps/panel/management/commands/cargar_demo.py`, `apps/panel/tests/test_cargar_demo.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/visitas/`, `apps/sitios/`, `apps/panel/urls.py`, migraciones existentes
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices y § Task 7: Performance Optimization
- **Worktree**: sí
- **Presupuesto**: 550 líneas agregadas
- **Qué hacer**:
  - **Modelo**:
    - Renombrar `unidad_dosis_por_defecto` a `unidad_dosis_habitual` con RenameField.
    - Agregar `dosis_habitual` (Decimal opcional, con los mismos dígitos que `ProductoAplicado.dosis`) y `dosis_variable` (bool, `False` por defecto).
    - `clean()`: si hay dosis, la unidad es obligatoria, y hace falta `dosis_habitual` o `dosis_variable=True`.
    - La migración 0002 incluye un RunPython que marca `dosis_variable=True` en los productos existentes; la vuelta atrás no hace nada.
    - Se ajustan los tests de `apps/productos/tests/` que crean productos por el form sin dosis.
  - **Panel**: el form lleva los tres campos y una ayuda: "Dosis: concentración de la preparación (p. ej. 5 ml/l). Cantidad: lo que se descuenta del stock en cada aplicación".
  - **Catálogo**:
    - Agrega `dosis_habitual`, `unidad_dosis_habitual`, `dosis_variable` y `ultimo_lote`.
    - `ultimo_lote` es una Subquery sobre `ProductoAplicado` de la misma empresa, ordenada por `-revision__realizada_en, -pk`, o `null`. Vive en `apps/productos/consultas.py` como `ultimo_lote_subquery()`, para que T6 la reutilice.
    - Número fijo de consultas.
  - **`cargar_demo`**:
    - Usa el nombre nuevo.
    - En la primera empresa, un segundo operario y dos turnos pendientes de operarios distintos en un mismo sitio, que comparten al menos un punto.
    - Productos con dosis habitual, sin dosis habitual y al menos uno con `dosis_variable=True`.
    - Sigue siendo idempotente.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.DosisHabitualTests.test_dosis_sin_unidad_no_valida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.DosisHabitualTests.test_sin_dosis_habitual_ni_variable_no_valida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.DosisHabitualTests.test_panel_edita_dosis_habitual_y_variable --keepdb`
  - `[grep-1]` `grep -n "update.dosis_variable=True" apps/productos/migrations/0002_dosis_habitual.py`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_catalogo_trae_dosis_y_ultimo_lote_null --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_ultimo_lote_L2291_y_etag_cambia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_ultimo_lote_no_cruza_empresas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_consultas_iguales_con_5_y_50_productos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoCoordinacionTests.test_dos_operarios_comparten_un_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoCoordinacionTests.test_productos_con_y_sin_dosis_y_uno_variable --keepdb`
  - `[grep-0]` `grep -n "unidad_dosis_por_defecto" apps/productos/models.py apps/productos/serializers.py apps/productos/panel_forms.py apps/panel/demo_historia.py apps/panel/management/commands/cargar_demo.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 550 --subtarea T1`

### T2 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1)
- **Depende de**: T1
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/coordinacion-operarios`, no el informe.
  2. Desde la raíz (worktree de `plan/coordinacion-operarios`), `bash .claude/hooks/worktree-integrar.sh coordinacion-operarios T1 plan/coordinacion-operarios <rutas>` y `verificar.py tarea`.
  3. `manage.py migrate` en desarrollo (`productos.0002`).
  4. Crear el worktree de T3.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/coordinacion-operarios | grep -q "T1: integra coordinacion-operarios-T1"`

### T3 — Dominio de `visitas`: incidencias nuevas, horas, sin coordenadas, dosis, duplicadas y apertura sin escaneo

- **Ola**: 2
- **Depende de**: T2
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/migrations/0005_incidencias_coordinacion.py`, `apps/visitas/services.py`, `apps/visitas/coordinacion.py`, `apps/visitas/tests/test_coordinacion.py`, `apps/visitas/tests/test_dosis_registro.py`, `apps/visitas/tests/test_sin_conexion_ajustes.py`, `apps/visitas/tests/test_sin_conexion_servicios.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_robustez_visitas.py`, `apps/visitas/tests/test_stock_api.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/api/`, `apps/sitios/`, `apps/panel/`, `apps/productos/`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/api_urls.py`, `apps/visitas/panel_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/templates/`, migraciones existentes
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices, § Task 7: Performance Optimization y § Task 8: Testing Django Applications
- **Worktree**: sí
- **Presupuesto**: 800 líneas agregadas
- **Qué hacer**:
  - **Migración 0005**, también en los modelos históricos:
    - `ProductoAplicado.dosis` pasa a nullable y blank; `unidad_dosis` a blank (sigue sin null, vacío es `""`).
    - `Visita.incidencia_horas` e `incidencia_apertura_sin_escaneo` (bool).
    - `Revision.incidencia_duplicada` e `incidencia_sin_ubicacion` (bool).
  - **`coordinacion.py`**:
    - `revisiones_del_dia(empresa, punto_ids, fecha)` → `{punto_id: [(empleado_id, nombre, realizada_en), …]}`, ordenado por `realizada_en`.
      - Toma solo revisiones de ese día local de visitas que cuentan como servicio y no están canceladas.
      - Una sola consulta, con `de_empresa(empresa)`.
      - `revisiones_de_hoy(empresa, punto_ids)` es `revisiones_del_dia` con `localdate()`.
      - Sigue las mismas reglas que `contexto_de_puntos` (`apps/sitios/panel_views.py:127-170`).
    - `puntos_asignados_a_otros(empresa, punto_ids, empleado_id)` → `{punto_id: nombre}`.
      - Son los puntos en `ItemTurno` de visitas `pendiente` o `abierta` de otro empleado.
      - Una sola consulta. Con `empleado_id=None`, cuenta a cualquier empleado.
    - `nombre_de_empleado(usuario)`: `get_full_name()` o, si está vacío, `username` (lo mismo que `_nombre_de`, `apps/sitios/panel_views.py:85`, que T5 pasa a importar de acá).
  - **Horas**:
    - En `cerrar_visita` y `registrar_no_revisado`, una hora anterior a `abierta_en` deja de dar 400: se guarda la hora declarada y se marca `visita.incidencia_horas = True`.
    - El resto de `validar_hora_cliente` (futura, atraso) no cambia.
  - **Sin coordenadas**:
    - `_guardar_revision` acepta que falten `latitud` o `longitud`: guarda la revisión sin coordenadas y con `incidencia_sin_ubicacion = True`.
    - Sin coordenadas no se verifica la distancia ni se fija la ubicación del sitio.
  - **Dosis**, en `_armar_productos`:
    - Producto sin `dosis_variable`: guarda `dosis_habitual` y `unidad_dosis_habitual` (o nada) e ignora lo enviado.
    - Producto con `dosis_variable`: guarda lo enviado o, si falta, la habitual.
    - `lote` sigue obligatorio, con el error en la posición del producto (`productos_aplicados.<i>.lote`).
  - **Duplicada**:
    - En `_guardar_revision`, si la visita cuenta como servicio y `revisiones_del_dia` con `localdate(realizada_en)` trae una revisión de ese punto de otro empleado, se marca `revision.incidencia_duplicada = True` (decisión del usuario del 2026-11-20: el día es el de `realizada_en`).
    - Una visita de administrador no marca nada.
  - **Apertura sin escaneo**: `abrir_turno_sin_escaneo(visita_pk, usuario, latitud=None, longitud=None, precision_m=None, abierta_en=None)`.
    - Busca con `de_empresa` una visita del empleado. Si no existe, `Visita.DoesNotExist`.
    - Bloquea en el mismo orden que `abrir_visita` (Sitio y después Visita, `services.py:468-488`).
    - Si el empleado ya tiene una visita abierta en ese sitio, la devuelve sin cambios, igual que `abrir_visita`.
    - Exige que la visita esté `pendiente`, con `programada_para` nula o ≤ el día de la apertura, y que el sitio y el cliente estén activos. Si no, una excepción propia.
    - Abre la visita con `min(abierta_en, ahora)` (validado con `validar_hora_cliente`) y marca `incidencia_apertura_sin_escaneo`. Las coordenadas se guardan si vienen, sin verificar distancia.
    - Si `_cerrar_sin_revisiones` (`services.py:974-989`) devuelve el turno a pendiente o cancelado, baja `incidencia_apertura_sin_escaneo`.
  - **Incidencias**:
    - `condicion_incidencia_sin_revisar` suma, solo con la visita `realizada` (como `incidencia_servicio` y los reportes, porque `marcar_incidencia_revisada` exige realizada), `incidencia_horas`, `incidencia_apertura_sin_escaneo` y las revisiones con `incidencia_duplicada` o `incidencia_sin_ubicacion`.
    - `marcar_incidencia_revisada` las acepta.
  - **Tests existentes**: se reescriben los que esperaban 400 por la hora o la falta de coordenadas en servicios. Los que esperaban la dosis enviada usan productos con `dosis_variable=True`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_coordinacion.RevisionesDeHoyTests.test_solo_hoy_y_que_cuentan_como_servicio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_coordinacion.RevisionesDeHoyTests.test_no_cruza_empresas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_coordinacion.RevisionesDeHoyTests.test_una_consulta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_coordinacion.AsignadosAOtrosTests.test_pendiente_o_abierta_de_otro_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_coordinacion.AsignadosAOtrosTests.test_excluye_realizadas_canceladas_y_propias --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_dosis_registro.DosisRegistroTests.test_sin_dosis_variable_y_sin_dosis_guarda_habitual --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_dosis_registro.DosisRegistroTests.test_sin_dosis_variable_ignora_dosis_enviada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_dosis_registro.DosisRegistroTests.test_con_dosis_variable_guarda_la_enviada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_dosis_registro.DosisRegistroTests.test_con_dosis_variable_sin_dosis_guarda_habitual --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 800 --subtarea T3`

### T10 — Tests de las incidencias nuevas y la apertura sin escaneo (`test_incidencias_nuevas.py`)

- **Ola**: 2
- **Depende de**: T3 (worktree propio `coordinacion-operarios-T10`, creado desde `plan/coordinacion-operarios` después de integrar T3; se integra en T4, después de T3)
- **Puede tocar**: `apps/visitas/tests/test_incidencias_nuevas.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/` salvo `apps/visitas/tests/test_incidencias_nuevas.py`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 8: Testing Django Applications
- **Worktree**: sí (propio)
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: los tests de horas inconsistentes, sin ubicación, duplicada, apertura sin escaneo y conteo de incidencias de T3, separados de T3 porque no entraban en su presupuesto (contrato modificado por el usuario el 2026-11-20).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.HorasInconsistentesTests.test_reporte_un_minuto_antes_de_abierta_201_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.HorasInconsistentesTests.test_cierre_un_minuto_antes_de_abierta_200_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.HorasInconsistentesTests.test_no_cambia_proximo_vencimiento_ni_stock --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.SinUbicacionTests.test_servicio_guarda_revision_sin_coordenadas_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.SinUbicacionTests.test_sin_coordenadas_no_fija_ubicacion_del_sitio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.DuplicadaTests.test_segunda_del_dia_por_otro_marca_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.DuplicadaTests.test_visita_de_administrador_no_marca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.DuplicadaTests.test_revision_de_ayer_no_marca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.DuplicadaTests.test_sin_conexion_compara_con_el_dia_de_realizada_en --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.AperturaSinEscaneoTests.test_abre_pendiente_propio_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.AperturaSinEscaneoTests.test_con_otra_abierta_en_el_sitio_devuelve_esa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.AperturaSinEscaneoTests.test_rechaza_programada_futura_y_sitio_inactivo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.AperturaSinEscaneoTests.test_ajena_o_de_otra_empresa_no_existe --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.AperturaSinEscaneoTests.test_vuelta_a_pendiente_baja_la_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_incidencias_nuevas.ConteoIncidenciasTests.test_cuatro_incidencias_cuentan_y_marcar_revisada_las_saca --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T10`

### T4 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T3)
- **Depende de**: T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/coordinacion-operarios`, no el informe.
  2. Desde la raíz, `worktree-integrar.sh coordinacion-operarios T3 plan/coordinacion-operarios <rutas>` y `verificar.py tarea`.
  3. `manage.py migrate` en desarrollo (`visitas.0005`).
  4. Crear los worktrees de T5 y T6.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/coordinacion-operarios | grep -q "T3: integra coordinacion-operarios-T3"`

### T5 — `sitios`: `revisado_hoy_por` en el resolver de QR, límite de `datos-sin-conexion` y señal en la ficha del sitio

- **Ola**: 3
- **Depende de**: T4
- **Puede tocar**: `apps/sitios/api_views.py`, `apps/sitios/serializers.py`, `apps/sitios/panel_views.py`, `apps/sitios/templates/sitios/panel/ficha.html`, `apps/sitios/tests/test_resolver_revisado_hoy.py`, `apps/sitios/tests/test_datos_sin_conexion_limite.py`, `apps/sitios/tests/test_panel_ficha_coordinacion.py`, `apps/sitios/tests/test_api.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/visitas/`, `apps/api/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` (serializers y throttling) y `.agents/skills/api-security-best-practices/SKILL.md` (exposición de datos)
- **Worktree**: sí
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - **Resolver de QR**: agrega `punto.revisado_hoy_por` = `{operario: {id, nombre}, realizada_en, propia}`, tomado de la revisión más reciente de hoy según `coordinacion.revisiones_de_hoy`, o `null`. `propia` indica si la revisión es del usuario que consulta.
  - **`me/datos-sin-conexion/`**:
    - No cambia su contenido.
    - Lleva `ThrottleDatosSinConexion(UserRateThrottle)`, con `scope = "datos_sin_conexion"` y `rate = "30/hour"` en la clase.
    - El throttle corre antes de la vista, así que un 304 también consume cupo. El 429 lleva `Retry-After`.
    - En los tests se limpia la caché en `setUp`.
  - `_nombre_de` (`apps/sitios/panel_views.py:85`) pasa a importar `coordinacion.nombre_de_empleado`.
  - **Ficha del sitio**: en la pestaña Turnos, un turno con revisiones `incidencia_duplicada` lleva la marca "Punto revisado por dos operarios el mismo día".
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_resolver_revisado_hoy.RevisadoHoyTests.test_revisado_hoy_por_otro_trae_nombre_y_propia_false --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_resolver_revisado_hoy.RevisadoHoyTests.test_revisado_ayer_es_null --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_resolver_revisado_hoy.RevisadoHoyTests.test_revisado_hoy_por_el_mismo_usuario_propia_true --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_resolver_revisado_hoy.RevisadoHoyTests.test_visita_de_administrador_no_cuenta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_resolver_revisado_hoy.RevisadoHoyTests.test_datos_sin_conexion_sin_nombres_ni_horas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion_limite.LimiteDatosSinConexionTests.test_pedido_31_da_429_con_retry_after --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion_limite.LimiteDatosSinConexionTests.test_304_cuenta_para_el_limite --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion_limite.LimiteDatosSinConexionTests.test_cupo_es_por_usuario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_coordinacion.FichaSitioCoordinacionTests.test_turno_con_revision_duplicada_queda_senalado --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T5`

### T6 — Panel de visitas: "Nuevo turno", ficha del turno y "Cargar visita"

- **Ola**: 3
- **Depende de**: T4
- **Puede tocar**: `apps/visitas/panel_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/templates/visitas/panel/_puntos_servicio.html`, `apps/visitas/templates/visitas/panel/ficha.html`, `apps/visitas/templates/visitas/panel/cargar.html`, `apps/visitas/static/visitas/nuevo_turno.js`, `apps/visitas/static/visitas/cargar_visita.js`, `apps/visitas/tests/test_panel_coordinacion.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/visitas/services.py`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/models.py`, `apps/visitas/coordinacion.py`, `apps/sitios/`, `apps/panel/`, `templates/`, `static/src/`, `static/css/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 5: Forms and ModelForms Best Practices y `docs/02-diseno.md`
- **Worktree**: sí
- **Presupuesto**: 500 líneas agregadas
- **Qué hacer**:
  - **"Nuevo turno"**:
    - Con `coordinacion.puntos_asignados_a_otros`, el punto asignado a otro empleado muestra "Asignado a <nombre>" y viene destildado.
    - Se puede tildar igual y el turno se crea.
    - El atajo "Todos" lo incluye; "Vencidos y próximos" no (atributo `data-asignado`).
  - **Ficha del turno**:
    - Marcas "Horas inconsistentes", "Apertura sin escaneo", "Sin ubicación" y, por revisión, "Punto revisado por otro operario el mismo día".
    - La dosis se muestra solo si existe, sin "None".
    - Las incidencias nuevas se pueden marcar como revisadas.
  - **"Cargar visita"**:
    - La dosis aparece solo en productos de dosis variable, con la habitual precargada (vía `data-*` del `<option>`).
    - El lote viene precargado con el último usado del producto (`productos.consultas.ultimo_lote_subquery()`, en un número fijo de consultas).
    - `cargar_visita.js` es nuevo y se carga con `<script src="{% static %}">` en `{% block scripts %}`, como `nuevo_turno.html`. Sin CSS ni JS en línea (CSP).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_coordinacion.NuevoTurnoAsignadoTests.test_punto_de_turno_pendiente_de_otro_destildado_con_nombre --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_coordinacion.NuevoTurnoAsignadoTests.test_turno_se_crea_incluyendo_punto_asignado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_coordinacion.FichaTurnoIncidenciasTests.test_revision_sin_coordenadas_senalada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_coordinacion.FichaTurnoIncidenciasTests.test_horas_apertura_y_duplicada_senaladas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_coordinacion.FichaTurnoIncidenciasTests.test_dosis_vacia_no_muestra_none --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_coordinacion.CargarVisitaDosisTests.test_lote_precargado_y_dosis_solo_en_variable --keepdb`
  - `[grep-1]` `grep -n "data-asignado" apps/visitas/static/visitas/nuevo_turno.js`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T6`

### T7 — Integración ola 3 (principal)

- **Ola**: 3 (después de verificar T5 y T6)
- **Depende de**: T5, T6
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/coordinacion-operarios` de cada subtarea, no los informes.
  2. Desde la raíz, `worktree-integrar.sh` para T5 y T6, de a una, con `verificar.py tarea` tras cada integración.
  3. Crear el worktree de T8.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/coordinacion-operarios | grep -q "T5: integra coordinacion-operarios-T5"`
  - `[cmd]` `git log --oneline plan/coordinacion-operarios | grep -q "T6: integra coordinacion-operarios-T6"`

### T8 — API de `visitas` (`duplicada_hoy`, coordenadas y dosis opcionales, `visitas/<pk>/abrir/`, `revisado_por_otro`) y documentación

- **Ola**: 4
- **Depende de**: T7
- **Puede tocar**: `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/api_urls.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_api_coordinacion.py`, `apps/api/tests/test_contrato_doc.py`, `docs/contrato-api.md`, `apps/visitas/tests/test_api_mis_turnos.py`, `apps/api/tests/test_aislamiento.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/`, `apps/panel/`, `apps/productos/`, `apps/api/urls.py`, `apps/visitas/models.py`, `apps/visitas/services.py`, `apps/visitas/coordinacion.py`, `apps/visitas/panel_views.py`, migraciones
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` (views y serializers) y `.agents/skills/api-security-best-practices/SKILL.md` (autorización por objeto)
- **Worktree**: sí
- **Presupuesto**: 650 líneas agregadas
- **Qué hacer**:
  - **`POST revisiones/`**:
    - `latitud` y `longitud` opcionales; sin ellas, 201 con la incidencia de T3.
    - `dosis` y `unidad_dosis` opcionales.
    - La respuesta 201 agrega `duplicada_hoy` (`revision.incidencia_duplicada`).
    - La lectura (`RevisionSerializer`, `me/historial/`) devuelve `dosis` y `unidad_dosis` o `null`.
  - **`POST visitas/<pk>/abrir/`**:
    - Llama a `abrir_turno_sin_escaneo` con `request.empresa` y `request.user`.
    - Si la visita es ajena o de otra empresa, 404; si no está pendiente, 409.
    - Coordenadas y `abierta_en`, opcionales.
    - Responde con el mismo serializer que `visitas/abrir/` y usa el throttle `crear_visita`.
    - Una revisión sin `qr_codigo` sigue en 400.
  - **`me/visitas/` y su detalle**: cada ítem agrega `revisado_por_otro` = `{operario: {nombre}, realizada_en}` o `null`, con la revisión de hoy de otro empleado. Sale de una sola llamada a `coordinacion.revisiones_de_hoy` por página.
  - **Documentación**:
    - `docs/contrato-api.md` documenta todo lo del plan: `revisado_hoy_por`, `revisado_por_otro`, `duplicada_hoy`, dosis y `ultimo_lote` del catálogo, dosis según `dosis_variable`, coordenadas opcionales, 201 con horas inconsistentes, 429 de `datos-sin-conexion` y `visitas/<pk>/abrir/` (el conteo de `test_contrato_doc` pasa a 24).
    - Regenerar `openapi-v1.yaml`.
    - Doc 01: Producto, ProductoAplicado y las cuatro incidencias.
  - **Tests existentes**: se reescribe el test de `test_api.py` que esperaba 400 sin coordenadas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisionApiTests.test_segunda_del_dia_por_otro_201_duplicada_hoy_true --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisionApiTests.test_visita_de_administrador_duplicada_hoy_false --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisionApiTests.test_sin_coordenadas_201_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisionApiTests.test_sin_dosis_variable_sin_dosis_201_guarda_habitual --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisionApiTests.test_sin_lote_400_en_productos_aplicados_i_lote --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.AbrirSinEscaneoApiTests.test_turno_pendiente_propio_se_abre_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.AbrirSinEscaneoApiTests.test_turno_ajeno_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.AbrirSinEscaneoApiTests.test_turno_de_otra_empresa_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.AbrirSinEscaneoApiTests.test_turno_no_pendiente_409 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.AbrirSinEscaneoApiTests.test_revision_sin_qr_codigo_sigue_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisadoPorOtroTests.test_item_revisado_hoy_por_otro_trae_revisado_por_otro --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisadoPorOtroTests.test_revision_propia_o_de_ayer_es_null --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisadoPorOtroTests.test_consultas_iguales_con_5_y_50_items --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_coordinacion.RevisadoPorOtroTests.test_detalle_trae_revisado_por_otro --keepdb`
  - `[grep-1]` `grep -n "revisado_hoy_por" docs/contrato-api.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T8`

### T11 — `openapi-v1.yaml` regenerado y doc 01 (Producto, ProductoAplicado e incidencias)

- **Ola**: 4
- **Depende de**: T8 (worktree propio `coordinacion-operarios-T11`, creado desde `plan/coordinacion-operarios` después de integrar T8; se integra en T9, antes del cierre)
- **Puede tocar**: `docs/api/openapi-v1.yaml`, `docs/01-modelo-y-arquitectura.md`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/`, `docs/contrato-api.md`
- **Skill a leer antes**: ninguna (documentación)
- **Worktree**: sí (propio)
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**: regenerar `openapi-v1.yaml` con todo integrado y documentar en el doc 01 Producto, ProductoAplicado y las cuatro incidencias; separado de T8 porque T8 midió 804 de 650 (contrato modificado por el usuario el 2026-11-20).
- **Criterios**:
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$TEMP/openapi-coordinacion.yaml" && diff -q --strip-trailing-cr "$TEMP/openapi-coordinacion.yaml" docs/api/openapi-v1.yaml`
  - `[grep-1]` `grep -n "dosis_variable" docs/01-modelo-y-arquitectura.md`
  - `[grep-0]` `grep -n "unidad_dosis_por_defecto" docs/contrato-api.md docs/api/openapi-v1.yaml docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T11`

### T9 — Integración ola 4 y cierre (principal)

- **Ola**: 4 (después de verificar T8)
- **Depende de**: T8
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/coordinacion-operarios`, no el informe.
  2. Desde la raíz, `worktree-integrar.sh coordinacion-operarios T8 plan/coordinacion-operarios <rutas>` y `verificar.py tarea`.
  3. El cierre: `verificar.py todo`, `revisor` en modo cierre, `auditor-seguridad`, `medir_metodo.py --registrar` y el commit `cierre: coordinacion-operarios`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/coordinacion-operarios | grep -q "T8: integra coordinacion-operarios-T8"`

## Registro de verificación

commit_base: 794af57

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | hecha | 48b6109 | PASA (tarea, HEAD 48b6109 en el worktree; b018b02 tras integrar) |
| T2 | hecha | b018b02 | PASA (tarea T1,T2, HEAD b018b02) |
| T3 | hecha | 9d142c5 | PASA (tarea, HEAD 59a152e tras integrar) |
| T10 | hecha | a5ac19b | PASA (tarea T10,T4, HEAD 834d4a4) |
| T4 | hecha | 834d4a4 | PASA (tarea T10,T4, HEAD 834d4a4) |
| T5 | hecha | dbd7820, 984cacc | PASA (tarea T5,T7, HEAD e06c285; 1 ronda de corrección) |
| T6 | hecha | 5865b5e | PASA (tarea, HEAD b6128be) |
| T7 | hecha | e06c285 | PASA (tarea T5,T7, HEAD e06c285) |
| T8 | hecha | 76b3abd | PASA (tarea, HEAD 6cf68a7; 1 ronda de corrección) |
| T11 | hecha | 57493bb | PASA (tarea T11,T9, HEAD 40c3427) |
| T9 | hecha | 40c3427 | PASA (tarea T11,T9, HEAD 40c3427) |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-20 10:37 | plan | 2 | 2 | 6 |
| 2026-11-20 12:25 | cierre | 2 | 0 | 6 |

Auditoría: 2026-11-20 12:25 — APROBADO (`auditor-seguridad`): 0 bloqueantes, 0 importantes, 2 menores (los mismos dos bloqueantes del revisor), 3 observaciones
Hallazgos (revisión de plan): los 2 bloqueantes (regresión de la dosis en productos existentes; invariantes de `abrir_turno_sin_escaneo`) y los 6 menores corregidos en el plan antes de congelar; las 2 decisiones (producto sin dosis; "mismo día" sin conexión) las tomó el usuario el 2026-11-20.
Hallazgos (revisión de cierre y auditoría): bloqueante 1, el atajo "Vencidos y próximos" de `nuevo_turno.js` tildaba los puntos próximos asignados a otro (precedencia de `&&` sobre `||`; el `[grep-1]` y el test no lo veían) — corregido en d6a1866 con el test endurecido (falla con el código viejo). Bloqueante 2, `visitas/<pk>/abrir/` aceptaba coordenadas que no guardaba, contra el contrato — el usuario decidió minimizar: el endpoint y el servicio solo admiten `abierta_en` y no guardan ubicación (69652c4, 1d5fb54, 511c902). Los menores y las observaciones, en P-coordinacion-operarios-1 a 13. Una sola ronda, en la raíz (rama del plan), con un commit por subtarea dueña para que cada línea cuente en su presupuesto.

### Decisiones del plan

- T1 — `cargar_demo` (`apps/panel/**`) va en la subtarea de `productos`, como la transversal del plan — opciones: T1 toca solo el nombre en `apps/panel/` y otra subtarea hace la demo, o T1 hace toda la demo — la segunda — `revisar_plan.py` no admite dos dueños del mismo archivo y el renombre rompería la suite al integrar — autónoma — cómo revertir: mover la demo a una subtarea propia — decidida por Claude, revisable
- T8 — la API de `visitas` y toda la documentación van juntas en la última ola — la ruta nueva y su fila en el contrato tienen que entrar juntas (`test_contrato_doc`), el contrato tiene un solo dueño y el OpenAPI se regenera con todo integrado — autónoma — decidida por Claude, revisable
- T5 — la tasa de `datos-sin-conexion` va en la clase (`rate = "30/hour"`), no en `DEFAULT_THROTTLE_RATES` — los settings son del principal y `ThrottleRenovacion` sigue ese patrón — autónoma — cómo revertir: moverla a settings en un plan del principal — decidida por Claude, revisable
- T8 — toda `AperturaNoPermitida` (no pendiente, programada para un día posterior, sitio o cliente inactivo) responde 409 `apertura_no_permitida` — opciones: 409 solo para "no pendiente" y 400 para el resto, o 409 para todo — la segunda — son conflictos con el estado del recurso y el servicio no distingue la causa; el 400 queda para `abierta_en` inválida — autónoma — cómo revertir: subclases de `AperturaNoPermitida` y mapeo por causa — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-coordinacion-operarios-1 [menor] `visitas/<pk>/abrir/` responde 409 también con el sitio o el cliente inactivos, mientras `abrir_visita` responde 400 `qr_codigo` para un sitio inactivo (`apps/visitas/services.py:483-484`); está documentado en el contrato, pero no hay test de API para el 409 por sitio o cliente inactivo (solo en el servicio, `test_incidencias_nuevas.py:206-218`).
- P-coordinacion-operarios-2 [menor] La marca "Punto revisado por dos operarios el mismo día" de la ficha del sitio va en una lista sobre la tabla de turnos (`apps/sitios/templates/sitios/panel/ficha.html:72-78`), no en la fila: `_pestana_turnos.html` estaba fuera del alcance de T5.
- P-coordinacion-operarios-3 [menor] `abrir_turno_sin_escaneo` (`apps/visitas/services.py`) no excluye las pendientes con revisiones (evidencia migrada), que `_pendiente_para` y el panel sí excluyen, ni fija `origen=APP` y `motivo_manual=""` como `abrir_visita`.
- P-coordinacion-operarios-4 [menor] En `AbrirTurnoSinEscaneoView`, `creada` se calcula con la visita leída fuera del lock: dos pedidos simultáneos sobre el mismo turno pendiente responden los dos 201 (el contrato dice 200 para el segundo); no hay doble apertura.
- P-coordinacion-operarios-5 [menor] En un producto de dosis variable, una `dosis` enviada sin `unidad_dosis` se guarda con unidad vacía en vez de la habitual (`apps/visitas/services.py:194-197`) y puede llegar al certificado sin unidad.
- P-coordinacion-operarios-6 [menor] `test_incidencias_nuevas.HorasInconsistentesTests.test_no_cambia_proximo_vencimiento_ni_stock`: la comprobación de stock no prueba nada, porque la revisión no aplica productos.
- P-coordinacion-operarios-7 [menor] Warning de `spectacular` por `UnidadEnum` (choice sets duplicados, desde T1); se resuelve con `ENUM_NAME_OVERRIDES` en `config/` (del principal).
- P-coordinacion-operarios-8 [menor] Método: `verificar.py` solo reconoce subtareas con id entero (`RE_TAREA = ^### T(\d+)\b`) y en la rama `<slug>-T<n>` cuenta todo commit como T<n>; `presupuesto.sh --subtarea T<n>` suma los commits `T<n>b:`; `worktree-crear.sh` acepta `T5a`. Al partir una subtarea hay que usar un id entero nuevo y un worktree propio (ver `docs/metodo/incidentes.md`). Para el plan del método.
- P-coordinacion-operarios-9 [observación] `revisado_hoy_por.operario` del resolver de QR incluye el `id` de usuario del otro empleado (`apps/sitios/api_views.py:92`); el plan pedía nombre y hora y `propia` ya cubre lo que necesita la app. Quitarlo minimiza.
- P-coordinacion-operarios-10 [observación] Una revisión con una sola de las dos coordenadas descarta las dos y queda con `incidencia_sin_ubicacion` (`apps/visitas/services.py:807`); no saltea el control (deja la marca), pero oculta la distancia; no hay test de ese caso y un 400 sería más estricto.
- P-coordinacion-operarios-11 [observación] `condicion_incidencia_sin_revisar` no cuenta `Revision.incidencia_ubicacion` (revisión lejos del punto) y sí la revisión sin ubicación; anterior a este plan, conviene revisarlo aparte.
- P-coordinacion-operarios-12 [observación] "Cargar visita": `cargar_visita.js` precarga lote y dosis solo en campos vacíos; si el administrador cambia de producto después, el lote anterior queda y lo corrige a mano. Sin tests de JS: los tests comprueban el HTML y los `data-*`.
- P-coordinacion-operarios-13 [observación] `ThrottleDatosSinConexion` cuenta por caché local: con varios procesos en producción cada uno lleva su cupo, igual que los demás throttles (ver P-limites-ingreso-*).

### Decisiones

- 2026-11-20 — una revisión sin coordenadas se acepta y deja la incidencia "sin ubicación" en la revisión, visible en la ficha del turno y contada en "Incidencias sin revisar" — sin señal o sin permiso de ubicación el operario igual revisó el punto — (usuario) — reemplaza a: 2026-10-03 (exigencia de coordenadas en el servicio)
- 2026-11-20 — `Producto.unidad_dosis_por_defecto` se renombra a `unidad_dosis_habitual`, junto a `dosis_habitual` y `dosis_variable`; la dosis la define el administrador y el operario la carga solo en productos de dosis variable; el lote sigue obligatorio y se precarga con el último usado; un producto exige dosis habitual o dosis variable, y los existentes se migran como variables — con un QR por estación la dosis casi siempre es la habitual, y la dosis sigue en el certificado — (usuario) — reemplaza a: 2026-09-29 (el empleado completa lote y dosis)
- 2026-11-20 — una revisión del mismo punto el mismo día (fecha local de `realizada_en`) por otro operario se acepta con aviso (`duplicada_hoy`) e incidencia, sin bloquearla; el nombre y la hora del otro operario se exponen solo para revisiones de hoy, en el resolver de QR y en los ítems de los turnos propios; `me/datos-sin-conexion/` sigue con solo `ultima_revision_fecha` — coordinar sin frenar el trabajo — (usuario) — reemplaza a: (nada)
- 2026-11-20 — `POST visitas/<pk>/abrir/` abre un turno pendiente propio sin escanear y deja la incidencia "apertura sin escaneo"; sirve para reportar puntos no revisados y no habilita revisiones sin QR — cuando no se puede escanear ningún punto — (usuario) — reemplaza a: (nada)
- 2026-11-20 — `POST visitas/<pk>/abrir/` no pide ni guarda ubicación: solo admite `abierta_en`; la incidencia "apertura sin escaneo" queda sin dato de dónde se abrió — minimizar datos de localización (Ley 25.326); la revisión de cierre encontró que las coordenadas se aceptaban sin guardarse — (usuario) — reemplaza a: 2026-11-20 (las coordenadas de la apertura sin escaneo se guardan si vienen)

### Cierra

- cierra: P-trabajo-sin-conexion-15 — una hora de cierre o de reporte anterior a la apertura se guarda y deja `incidencia_horas` (T3)
- cierra: P-trabajo-sin-conexion-16 — el reloj atrasado del teléfono entra por la misma incidencia (T3)
- cierra: P-trabajo-sin-conexion-18 — `me/datos-sin-conexion/` con 30 pedidos por hora por usuario (T5)
