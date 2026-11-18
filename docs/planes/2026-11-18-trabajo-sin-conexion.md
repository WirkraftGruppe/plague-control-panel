# Plan: Soporte del servidor para que la app trabaje sin conexión

- **slug**: `trabajo-sin-conexion`
- **fecha**: 2026-11-18
- **objetivo**: la app descarga por adelantado los puntos activos de su empresa y los servicios con sus planillas, y envía más tarde, en orden y hasta 72 h después, lo que el operario registró sin conexión, sin perder ni duplicar datos.
- **fuera de alcance**: sincronización en segundo plano, notificaciones y envío por lotes; la carga manual del panel (`registrar_visita_manual` sigue con `ATRASO_MAXIMO_HORAS` = 168); `VISITA_ABIERTA_MAXIMO_HORAS` (sigue en 16); `me/puntos/`; la app (`detach-app`).
- **áreas**: panel | api | dominio (modelos y servicios)
- **ruta**: completo
- **seguridad**: sí — endpoint nuevo de la API que expone todos los puntos, sitios y servicios de la empresa (tiene que filtrar por la empresa del usuario, llevar `no-store` y entregar el QR solo como hash, para no romper la prueba de presencia); horas que manda el cliente (`abierta_en`, `cerrada_en`, `reportado_en`) y un `servicio` elegido por el cliente que tiene que ser de su empresa. Corre `auditor-seguridad`.

## Contexto mínimo

- **Atraso**: `_guardar_revision` (`apps/visitas/services.py:611-618`) rechaza `realizada_en` con más de `ATRASO_MAXIMO_HORAS` (168, `config/settings/base.py:39-59`) y responde 400 sin `code`.
  - Decisión del usuario: la app pasa a `ATRASO_MAXIMO_APP_HORAS` (72, configurable) y la carga manual se queda en 168. Reemplaza a las decisiones 2026-10-04 y 2026-10-07.
  - Pasarse del límite da 400 con `code: "atraso_excedido"`.
  - La deduplicación por `cliente_uuid` va antes, así que un reintento tardío sigue recibiendo 409.
- **`code`**: solo se emite lo que está en `CODIGOS_PUBLICOS` (`apps/api/excepciones.py:17`). `docs/contrato-api.md:53` dice "Ningún otro error trae `code`". Se agregan `atraso_excedido` y `visita_no_abierta`. Hoy la conversión de Django a DRF (`excepciones.py:67-73`) pierde el `code` de cada campo.
- **Visita no abierta**: la revisión, el reporte o el cierre del empleado sobre una visita propia `pendiente`, `cancelada` o realizada por el sistema pasa de 400 sin código a 409 con `visita_no_abierta`. Es reintentable: la app reenvía `abrir` con su `abierta_en`.
  - Decisión del usuario: lo atrasado va a una visita nueva y lo cerrado no se toca.
  - El cierre repetido por el mismo empleado sigue en 200 (`services.py:955-957`). Una visita realizada que cerró el sistema o un administrador sigue en 409, que ahora trae `code: "visita_ya_cerrada"`.
- **Apertura**: `abrir_visita` (`services.py:395-478`) fija `abierta_en = now`. Cuando hay un pendiente lo reabre, y si no, crea una visita nueva.
  - Decisión del usuario: con `abierta_en` del cliente, solo se toman pendientes con `programada_para` nula o ≤ `localdate(abierta_en)`.
  - `abierta_en` se guarda como `min(abierta_en, ahora)`, porque `cerrar_visita` cuenta las revisiones con `recibida_en >= abierta_en` (`services.py:965`).
- **Cierre nocturno**: `cerrar_visitas_abiertas` cierra por `abierta_en < ahora - 16 h`.
  - Decisión del usuario: no cierra una visita con actividad recibida en las últimas 16 h, sea por `actualizado` (la apertura guarda la visita), por `recibida_en` de una revisión o por el `creado` de un reporte.
- **Servicio**: `servicio_para_punto` (`services.py:314-331`) usa el `ItemTurno` o `punto.servicio`. El cliente puede mandar `servicio`. Si difiere, tiene que ser un `TipoServicio` activo de la empresa (la búsqueda ya existe en `_servicio_con_campos`, `services.py:104`). Se guarda con `Revision.incidencia_servicio=True`.
  - Esa incidencia cuenta en `condicion_incidencia_sin_revisar` (`services.py:855`) solo con la visita `realizada`, igual que los reportes.
  - `marcar_incidencia_revisada` (`services.py:1208-1214`) tiene que aceptarla, para que el contador pueda volver a cero.
- **`PuntoNoRevisado`**: usa `creado` (`apps/visitas/models.py:369`). Se agrega `reportado_en`, con `default=timezone.now` porque hay tests que crean reportes directo. La migración lo llena con `creado`. El cierre por sistema y `test_cierre_solo_reportes.py:85` pasan a usar `reportado_en`.
- **Descarga**: `_datos_servicio` (`apps/sitios/api_views.py:80-89`) arma las planillas; el ETag sigue el patrón de `CatalogoView` (`apps/productos/api_views.py:17-43`).
  - Decisión del usuario: el QR va como `qr_hash` (SHA-256 hex del UUID en minúsculas con guiones), nunca `qr_codigo`, porque el QR es la prueba de presencia (decisión 2026-10-05). La app sigue mandando el código escaneado.
  - `apps/api/tests/test_contrato_doc.py:46` exige que las rutas del contrato coincidan con las de la API (22). La fila y el conteo entran con la ruta, en T3.
- **Settings** son del principal y nunca van en paralelo (`convenciones-proyecto`, tabla de propiedad).
- **Ficha del turno** (`apps/visitas/templates/visitas/panel/ficha.html:25` y `:65`): muestra `realizada_en`, pero no `recibida_en`. El botón "marcar revisada" no contempla esta incidencia.

## Olas

Las subtareas no comparten archivos (`revisar_plan.py`), así que se reparten por capa y por dueño:

- T1: settings, del principal y sola.
- T2: dominio de `visitas`.
- T3: la descarga en `sitios`, `docs/contrato-api.md` completo y el conteo de `test_contrato_doc`. La ruta y su fila tienen que entrar juntas, porque `worktree-integrar.sh` corre la suite completa y revierte el merge si falla.
- T5: la API de `visitas`, `apps/api/excepciones.py` y el OpenAPI, que se regenera con todo el código.
- T6: panel y doc 01.

T2 y T5 superan los 6 archivos: `services.py` y la API de `visitas` tienen un solo dueño cada uno, y sus tests existentes también. T3 y T5 tocan `apps/api/**` (un test y las excepciones, respectivamente). Es una excepción a "una transversal por plan": van en olas distintas y no comparten archivos (ver Decisiones del plan). T2 conserva los textos de error, así que su integración no rompe tests que recién cambian en T5.

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1 (principal, sin worktree) | config (sin migraciones) |
| 2 | T2, T3, T4 (integración) | visitas (0003), sitios (sin migraciones) |
| 3 | T5, T6, T7 (integración) | visitas y api (sin migraciones) |

## Subtareas

### T1 — `ATRASO_MAXIMO_APP_HORAS` en settings (principal)

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `config/settings/base.py`, `.env.example`, `config/tests/test_ajuste_atraso_app.py`
- **No puede tocar**: `docs/planes/`, `apps/visitas/services.py`, `config/settings/dev.py`, `config/settings/prod.py`, `config/urls.py`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 1: Django Project Structure Best Practices
- **Worktree**: no (lo hace el principal en la rama del plan, antes de crear el worktree de T2)
- **Presupuesto**: 80 líneas agregadas
- **Qué hacer**:
  - `leer_atraso_maximo_horas` se generaliza a `leer_horas(nombre, default)`, con la misma validación de 1 a 8760.
  - `ATRASO_MAXIMO_APP_HORAS = leer_horas("ATRASO_MAXIMO_APP_HORAS", "72")`.
  - `.env.example` documenta la variable.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajuste_atraso_app.AjusteAtrasoAppTests.test_default_72_y_rango_1_a_8760 --keepdb`
  - `[grep-1]` `grep -n "ATRASO_MAXIMO_APP_HORAS" config/settings/base.py`
  - `[grep-1]` `grep -n "ATRASO_MAXIMO_APP_HORAS" .env.example`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T1`

### T2 — Dominio de `visitas`: horas del cliente, visita no abierta, servicio enviado, incidencia y cierre nocturno

- **Ola**: 2
- **Depende de**: T1
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/migrations/0003_revision_incidencia_servicio_reportado_en.py`, `apps/visitas/services.py`, `apps/visitas/management/commands/cerrar_visitas_abiertas.py`, `apps/visitas/tests/test_sin_conexion_servicios.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_atraso.py`, `apps/visitas/tests/test_comandos.py`, `apps/visitas/tests/test_cierre_solo_reportes.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/api/`, `apps/sitios/`, `apps/panel/`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/panel_views.py`, `apps/visitas/templates/`, `apps/visitas/templatetags/`, migraciones existentes
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 2: Model Best Practices y § Task 8: Testing Django Applications
- **Worktree**: sí
- **Presupuesto**: 800 líneas agregadas
- **Qué hacer**:
  - **Helper `validar_hora_cliente(valor, campo)`**:
    - Si la hora es futura más allá de `TOLERANCIA_FUTURO`, `ValidationError` común.
    - Si el atraso supera `ATRASO_MAXIMO_APP_HORAS`, `ValidationError({campo: ValidationError(mensaje, code="atraso_excedido")})`, con un mensaje que dice avisar al administrador para que la cargue como manual.
    - Lo usa `realizada_en` de la revisión. La carga manual sigue con `ATRASO_MAXIMO_HORAS`.
  - **Modelo y migración 0003**:
    - `Revision.incidencia_servicio` (bool, default `False`).
    - `PuntoNoRevisado.reportado_en` con `default=timezone.now`. La migración lo agrega nulo, lo llena con `creado` y después lo pasa a no nulo.
  - **`registrar_no_revisado(reportado_en=None)`**: lo valida con el helper. El cierre por sistema usa `reportado_en`.
  - **`abrir_visita(abierta_en=None)`**:
    - Lo valida con el helper y guarda `min(abierta_en, ahora)`.
    - Con `abierta_en`, solo reabre pendientes con `programada_para` nula o ≤ `localdate(abierta_en)`. Si no hay ninguno, crea una visita nueva. Si ya hay una abierta, la devuelve sin cambios.
  - **`cerrar_visita(cerrada_en=…)`**: cuando la manda el empleado, se valida con el helper y no puede ser anterior a `abierta_en`.
  - **`VisitaNoAbierta(ValidationError)`**, con `code="visita_no_abierta"`:
    - La levantan la revisión y el reporte sobre una visita propia que no está `abierta`.
    - También `cerrar_visita` con `cierre=EMPLEADO` sobre una visita `pendiente` o `cancelada`.
    - El cierre por el mismo empleado de una visita realizada sigue idempotente.
    - Los mensajes no cambian: "La visita no está abierta." en la revisión y el reporte, y "Solo se puede cerrar una visita abierta." en el cierre. Hasta T5 la API los sigue respondiendo como 400, y los tests de T5 no se rompen al integrar T2.
  - **`registrar_revision(servicio=None)`**:
    - Sin servicio, o con el que decide `servicio_para_punto`, no cambia nada.
    - Si difiere, se busca un `TipoServicio` activo de la empresa con `de_empresa`; si no está, 400 en `servicio`. Si está, se guarda con ese servicio, validado contra su `esquema_planilla("punto")` y con `incidencia_servicio=True`. Esto vale también cuando el servidor no encontraba servicio o el suyo estaba de baja.
    - En una visita nueva sin `ItemTurno`, la comparación es contra `punto.servicio`.
  - **Incidencias**:
    - `condicion_incidencia_sin_revisar` agrega `| (Q(estado=REALIZADA) & Exists(Revision con incidencia_servicio=True))`, sin cambiar las ramas que ya existen.
    - `marcar_incidencia_revisada` acepta ese caso.
  - **`cerrar_visitas_abiertas`**: además de `abierta_en < limite`, exige `actualizado < limite`, que no haya revisiones con `recibida_en >= limite` y que no haya reportes con `creado >= limite`.
  - Se ajustan los tests existentes que esperaban 168 h en la app, 400 en una visita no abierta o `creado` en el cierre. Los fixtures del cron (`test_comandos.py`, `test_cierre_solo_reportes.py`) llevan `actualizado`, `recibida_en` y `creado` al pasado con `.update()`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_71_horas_se_guarda --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_73_horas_atraso_excedido --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_manual_sigue_con_168_horas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_reintento_73_horas_mismo_uuid_es_duplicada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_pendiente_con_abierta_en_de_ayer --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_futura_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abierta_en_futura_tolerada_cuenta_revisiones_al_cerrar --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_no_toma_pendiente_de_dia_posterior --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cerrada_en_anterior_a_abierta_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_reporte_guarda_reportado_en --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cierre_por_sistema_usa_reportado_en --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_revision_en_visita_pendiente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_reporte_en_visita_cancelada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_cierre_de_visita_pendiente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_distinto_guarda_servicio_e_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_igual_sin_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_inactivo_o_de_otra_empresa_falla --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_valida_contra_la_planilla_del_servicio_enviado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_visita_nueva_compara_con_servicio_del_punto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.IncidenciaServicioTests.test_cuenta_sin_revisar_y_marcar_revisada_la_saca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_no_cierra_visita_con_actividad_reciente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_cierra_visita_vieja_sin_actividad --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 800 --subtarea T2`

### T3 — `GET /api/v1/me/datos-sin-conexion/` y contrato de API

- **Ola**: 2
- **Depende de**: T1
- **Puede tocar**: `apps/sitios/api_views.py`, `apps/sitios/api_urls.py`, `apps/sitios/serializers.py`, `apps/sitios/tests/test_datos_sin_conexion.py`, `docs/contrato-api.md`, `apps/api/tests/test_contrato_doc.py`
- **No puede tocar**: `docs/planes/`, `docs/01-modelo-y-arquitectura.md`, `docs/api/`, `apps/visitas/`, `apps/api/excepciones.py`, `apps/api/views.py`, `apps/api/urls.py`, `apps/sitios/estado.py`, `apps/sitios/panel_views.py`, `config/`, migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 4: Django REST Framework (DRF) Best Practices y § Task 7: Performance Optimization
- **Worktree**: sí
- **Presupuesto**: 650 líneas agregadas
- **Qué hacer**:
  - **Vista `DatosSinConexionView`**:
    - Permisos `EsEmpleado | EsAdministrador`; la empresa sale de `empresa_de(request)` con `de_empresa`.
    - Puntos activos de sitios y clientes activos, con `select_related("sitio")` y `annotate(ultima_revision=Subquery(...))`. `ultima_revision` es el `realizada_en` de la última revisión en una visita abierta o realizada con `cuenta_como_servicio`.
    - Cada punto: `{id, qr_hash, nombre, sector, sitio{id,nombre,direccion,localidad}, servicio (id o null), estado, proximo_vencimiento, ultima_revision}`. `qr_hash` es el SHA-256 hex de `str(qr_codigo)`. Nunca `qr_codigo`. `estado` sale de `estados_por_vencimiento`.
    - Servicios activos de la empresa con `prefetch_related("campos")`: `{id, nombre, slug, esquema_punto, esquema_visita}`, reutilizando `_datos_servicio`.
    - Responde `{puntos, servicios}`, con ETag y 304 como `CatalogoView` y `Cache-Control: private, no-store` en el 200 y en el 304. El número de consultas no depende de la cantidad de puntos.
  - **Ruta** `me/datos-sin-conexion/`, con `extend_schema`.
  - **`docs/contrato-api.md`**, el contrato completo del plan; lo de T2 y T5 se escribe según este plan:
    - `me/datos-sin-conexion/`: campos, `qr_hash` y cómo lo compara la app, ETag y 304, `no-store`, y la fila de la ruta.
    - `abierta_en`, `cerrada_en`, `reportado_en` y `servicio`, con sus reglas, y `ATRASO_MAXIMO_APP_HORAS`.
    - Los `code` `atraso_excedido`, `visita_no_abierta` y `visita_ya_cerrada`, en lugar de "Ningún otro error trae `code`", con el significado de cada 409.
    - El reenvío de `abrir` tras un 409 `visita_no_abierta`.
  - `test_contrato_doc` pasa de 22 a 23 rutas, en el mismo commit que la ruta: `worktree-integrar.sh` corre la suite completa y revierte el merge si falla.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_solo_puntos_de_la_empresa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_excluye_puntos_sitios_y_clientes_inactivos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_consultas_iguales_con_50_y_500_puntos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_mismo_etag_responde_304 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_cache_control_no_store --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_campos_de_punto_y_servicios_activos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_entrega_qr_hash_y_nunca_qr_codigo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_anonimo_401 --keepdb`
  - `[grep-1]` `grep -n "datos-sin-conexion" docs/contrato-api.md`
  - `[grep-1]` `grep -n "atraso_excedido" docs/contrato-api.md`
  - `[grep-1]` `grep -n "visita_no_abierta" docs/contrato-api.md`
  - `[grep-0]` `grep -n "Ningún otro error trae" docs/contrato-api.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.api.tests.test_contrato_doc --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T3`

### T4 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T2 y T3)
- **Depende de**: T2, T3
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/trabajo-sin-conexion` de T2 y T3, no los informes.
  2. Desde la raíz (rama `plan/trabajo-sin-conexion`), `bash .claude/hooks/worktree-integrar.sh trabajo-sin-conexion T<n> plan/trabajo-sin-conexion <rutas>` por cada subtarea, de a una, con `verificar.py tarea` tras cada integración.
  3. `manage.py migrate` en desarrollo si entró una migración.
  4. Crear los worktrees de T5 y T6 con `bash .claude/hooks/worktree-crear.sh trabajo-sin-conexion T<n> plan/trabajo-sin-conexion`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T4:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T4`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/trabajo-sin-conexion | grep -q "T2: integra trabajo-sin-conexion-T2"`
  - `[cmd]` `git log --oneline plan/trabajo-sin-conexion | grep -q "T3: integra trabajo-sin-conexion-T3"`

### T5 — API de `visitas`, códigos públicos y OpenAPI

- **Ola**: 3
- **Depende de**: T4
- **Puede tocar**: `apps/api/excepciones.py`, `apps/api/esquema.py`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/tests/test_sin_conexion.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_no_revisados.py`, `apps/api/tests/test_raiz_y_codigos.py`, `docs/api/openapi-v1.yaml`
- **No puede tocar**: `docs/planes/`, `docs/01-modelo-y-arquitectura.md`, `docs/contrato-api.md`, `apps/api/tests/test_contrato_doc.py`, `apps/visitas/services.py`, `apps/visitas/models.py`, `apps/visitas/templates/`, `apps/visitas/panel_views.py`, `apps/sitios/`, `apps/panel/`, `config/`, migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 4: Django REST Framework (DRF) Best Practices y § Task 8: Testing Django Applications
- **Worktree**: sí
- **Presupuesto**: 650 líneas agregadas
- **Qué hacer**:
  - **Excepciones**:
    - `CODIGOS_PUBLICOS` suma `atraso_excedido`, `visita_no_abierta` y `visita_ya_cerrada` (hoy sale sin `code`; así la app distingue los tres 409).
    - La conversión de Django a DRF conserva `error_dict` y sus `code`.
    - `manejar_excepcion` emite `code` también cuando el código público viene en un error por campo.
    - El enum de `Error.code` en `apps/api/esquema.py` se deriva de `sorted(CODIGOS_PUBLICOS)`, y `test_raiz_y_codigos.py` pasa a esperar los cuatro códigos.
  - **Serializers**: campos opcionales que se pasan al servicio:
    - `abierta_en` en `AbrirVisitaSerializer`.
    - `cerrada_en` en `CerrarVisitaSerializer`.
    - `servicio` (id) en `CrearRevisionSerializer`.
    - `reportado_en` en `ReportarNoRevisadoSerializer`.
  - **Vistas**:
    - `VisitaNoAbierta` se traduce a 409 con `code: "visita_no_abierta"` en la revisión, el reporte y el cierre.
    - El 409 por `cliente_uuid` repetido sigue teniendo prioridad sobre el 400 por atraso.
    - `extend_schema` documenta los 400 y 409 nuevos.
  - Se ajustan los tests existentes que esperaban 400 por una visita no abierta.
  - Regenerar `openapi-v1.yaml`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_71_horas_201 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_73_horas_400_atraso_excedido --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_reporte_73_horas_400_atraso_excedido --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_abierta_en_de_ayer_abre_el_pendiente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_hora_futura_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cancelado_por_cierre_nocturno_abrir_y_revisiones_201 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_realizada_por_sistema_revision_409_y_abrir_crea_visita_nueva --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_reporte_y_cierre_en_visita_no_abierta_409 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_dos_veces_200 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_con_cerrada_en_del_cliente --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_distinto_201_con_incidencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_inactivo_o_de_otra_empresa_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_revision --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_reporte --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_reintento_73_horas_mismo_uuid_409 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cierre_de_visita_cerrada_por_sistema_409_visita_ya_cerrada --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.EsquemaTests.test_enum_code_coincide_con_codigos_publicos --keepdb`
  - `[grep-1]` `grep -n "visita_no_abierta" docs/api/openapi-v1.yaml`
  - `[grep-1]` `grep -n "reportado_en" docs/api/openapi-v1.yaml`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T5`

### T6 — Ficha del turno (servicio distinto, hora de llegada, marcar revisada) y doc 01

- **Ola**: 3
- **Depende de**: T4
- **Puede tocar**: `apps/visitas/templates/visitas/panel/ficha.html`, `apps/visitas/templatetags/visitas_ui.py`, `apps/visitas/tests/test_panel_sin_conexion.py`, `docs/01-modelo-y-arquitectura.md`
- **No puede tocar**: `docs/planes/`, `docs/contrato-api.md`, `docs/api/`, `apps/visitas/services.py`, `apps/visitas/models.py`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/panel_views.py`, `apps/sitios/`, `apps/api/`, `config/`, migraciones
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 3: Views and URLs Best Practices y § Task 8: Testing Django Applications
- **Worktree**: sí
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**:
  - **Ficha**:
    - Cada revisión muestra "Servicio distinto del asignado" si `incidencia_servicio`.
    - Muestra "Llegó <recibida_en>" solo cuando `|recibida_en - realizada_en| > 10 min`, con un filtro de `visitas_ui`.
    - La condición del botón "marcar revisada" (`ficha.html:25`) suma una visita con revisiones con `incidencia_servicio`, con un filtro de `visitas_ui`.
  - **Doc 01**: `incidencia_servicio`, `reportado_en`, los dos límites de atraso, el 409 `visita_no_abierta`, el cierre nocturno por actividad y la incidencia nueva en "Incidencias sin revisar".
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_servicio_distinto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_llegada_si_difiere_mas_de_10_minutos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_no_muestra_llegada_si_difiere_10_minutos_o_menos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_boton_marcar_revisada_con_incidencia_de_servicio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_menu_cuenta_incidencia_de_servicio --keepdb`
  - `[grep-1]` `grep -n "incidencia_servicio" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "ATRASO_MAXIMO_APP_HORAS" docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T6`

### T7 — Integración ola 3 (principal)

- **Ola**: 3 (después de verificar T5, T6)
- **Depende de**: T5, T6
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/trabajo-sin-conexion` de T5, T6, no los informes.
  2. Desde la raíz (rama `plan/trabajo-sin-conexion`), `bash .claude/hooks/worktree-integrar.sh trabajo-sin-conexion T<n> plan/trabajo-sin-conexion <rutas>` por cada subtarea, de a una, con `verificar.py tarea` tras cada integración.
  3. `manage.py migrate` en desarrollo si entró una migración.
  4. Comparar las secciones de `docs/contrato-api.md` que escribió T3 con los serializers y el `extend_schema` de T5. Si no coinciden, es un hallazgo del cierre.
  5. Cierre: `verificar.py todo`, `revisor` en modo cierre, `auditor-seguridad` y el commit `cierre: trabajo-sin-conexion`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`); si el principal hace commits `T7:` de ajuste, `bash .claude/hooks/presupuesto.sh . '<commit_base>' 60 --subtarea T7`
- **Criterios**:
  - `[cmd]` `git log --oneline plan/trabajo-sin-conexion | grep -q "T5: integra trabajo-sin-conexion-T5"`
  - `[cmd]` `git log --oneline plan/trabajo-sin-conexion | grep -q "T6: integra trabajo-sin-conexion-T6"`

## Registro de verificación

commit_base: 89f2a8d

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | pendiente | | |
| T2 | pendiente | | |
| T3 | pendiente | | |
| T4 | pendiente | | |
| T5 | pendiente | | |
| T6 | pendiente | | |
| T7 | pendiente | | |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-18 20:25 | plan | 6 | 3 | 1 |
| 2026-11-18 20:28 | plan | 1 | 0 | 4 |
| 2026-11-18 20:30 | plan | 1 | 0 | 2 |
| 2026-11-18 20:32 | plan | 1 | 0 | 2 |
| 2026-11-18 20:32 | plan | 0 | 0 | 1 |

Auditoría: pendiente
Hallazgos: ninguno todavía

### Decisiones del plan

- T3/T5 — dueño de `apps/api/**` — una sola subtarea transversal o dos en olas distintas — dos: T3 toca solo `apps/api/tests/test_contrato_doc.py` (ola 2) y T5 `apps/api/excepciones.py`, `apps/api/esquema.py` y `test_raiz_y_codigos.py` (ola 3) — la ruta y su fila deben entrar juntas porque `worktree-integrar.sh` corre la suite completa — autónoma — devolver la fila y el conteo a T5 y mover la ruta a la ola 3 — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

### Decisiones

- 2026-11-18 — Lo registrado en la app se acepta hasta `ATRASO_MAXIMO_APP_HORAS` (72 por defecto, configurable) después de hecho; la carga manual sigue con `ATRASO_MAXIMO_HORAS` (168) — trabajo sin conexión — (usuario) — reemplaza a: 2026-10-04, 2026-10-07
- 2026-11-18 — Si la jornada la cerró el sistema y llegan revisiones atrasadas, responden 409 `visita_no_abierta`; la app reenvía `abrir` con su `abierta_en` y recibe una visita nueva; lo cerrado no se toca — trabajo sin conexión — (usuario) — reemplaza a: (nada)
- 2026-11-18 — `datos-sin-conexion` devuelve todos los puntos activos de la empresa, no solo los de los turnos del empleado — trabajar aunque el turno se cree después de la última conexión — (usuario) — reemplaza a: (nada)
- 2026-11-18 — Una revisión con un servicio distinto del asignado se acepta con ese servicio y una incidencia que cuenta en "Incidencias sin revisar" — trabajo sin conexión — (usuario) — reemplaza a: (nada)
- 2026-11-18 — `cerrar_visitas_abiertas` no cierra una visita con actividad recibida en las últimas `VISITA_ABIERTA_MAXIMO_HORAS` (apertura, revisión o reporte) — la app abre con `abierta_en` de hasta 72 h atrás y el cron cortaba la sincronización — (usuario) — reemplaza a: (nada)
- 2026-11-18 — `datos-sin-conexion` entrega `qr_hash` (SHA-256 del UUID) y nunca `qr_codigo`; la app sigue mandando el código escaneado — el QR sigue siendo la prueba de presencia (2026-10-05) — (usuario) — reemplaza a: (nada)
- 2026-11-18 — `abrir` con `abierta_en` solo reabre pendientes con `programada_para` nula o ≤ el día de `abierta_en`; si no hay, crea una visita nueva, y el servicio de sus revisiones se compara con el del punto — el trabajo atrasado no se pega a un turno futuro — (usuario) — reemplaza a: (nada)
- 2026-11-18 — `code` público nuevo: `atraso_excedido` (400), `visita_no_abierta` (409) y `visita_ya_cerrada` (409) — la app necesita distinguir el error reintentable del definitivo sin leer textos — (agente) — reemplaza a: (nada)

### Cierra
