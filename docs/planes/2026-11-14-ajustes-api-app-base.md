# Plan: ajustes de la API que pidió la app (app-base)

- **slug**: `ajustes-api-app-base`
- **fecha**: 2026-11-14
- **objetivo**: la app del operario arma "Mis turnos" y "Turno" con lo que devuelve la API (usuario y empresa en la raíz, contacto del sitio, estado de cada punto, detalle de un turno), sin cruzar listas, y reconoce la empresa inactiva por un `code` y no por el texto del error.
- **fuera de alcance**: cambios de comportamiento en rutas existentes fuera de los campos agregados; `code` en otros errores que no sean el de empresa inactiva; pendientes con etiqueta `despliegue` o `despues`; cambios en el panel o en la app (`detach-app`).
- **áreas**: api
- **ruta**: completo
- **seguridad**: sí — ruta nueva de la API con un turno del empleado (`me/visitas/<pk>/`), aislamiento entre empleados y entre empresas, datos personales nuevos en respuestas (teléfono del contacto del sitio, nombre del usuario) y el manejador de errores de autenticación.

## Contexto mínimo

- Origen: P-app-base-1 a -5 del repositorio `detach-app`. La app no está publicada.
- `RaizView` (`apps/api/views.py:108`) devuelve `{"usuario": <username>, "rol"}`. Pasa a `usuario{id, nombre_completo, username}`, `empresa{id, nombre}` y `rol`. **Rompe `usuario` como texto**: lo decidió el usuario el 2026-11-14 (la app no está publicada). `nombre_completo` = `get_full_name()` o, si queda vacío, `username`. `empresa` sale de `empresa_de(request)`; para un usuario sin empresa (`plataforma`), `JWTAutenticacionEmpresa` deja pasar y `request.empresa` es `None`, así que `empresa: null` (hoy da 200 y tiene que seguir dando 200).
- `me/visitas/` (`apps/visitas/api_views.py:76`, `VisitaActivaSerializer` en `apps/visitas/serializers.py:248`) ya precarga `items__punto`. `PuntoControl.proximo_vencimiento` es un campo guardado: `estado` sale de `apps/sitios/estado.py:estado_por_vencimiento` sin consultas nuevas, igual que en el resolver de QR (`apps/sitios/api_views.py:172`).
- `sitio.contacto` = `{nombre: contacto_en_sitio, telefono: telefono_en_sitio}`, o `null` si los dos están vacíos, **solo en turnos activos del propio empleado** (decisión del usuario del 2026-11-14): `me/visitas/`, `me/visitas/<pk>/` y `visitas/abrir/` (las tres usan `VisitaActivaSerializer`). `SitioResumenSerializer` también lo usa `VisitaRealizadaSerializer` (`me/historial/` y `visitas/<pk>/cerrar/`), que siguen sin contacto (Ley 25.326 art. 16): el contacto va en un serializer de sitio aparte, solo para `VisitaActivaSerializer`.
- `me/visitas/<pk>/`: mismo queryset que la lista (empresa del pedido, `empleado=request.user`, estado `pendiente` o `abierta`); fuera de eso, 404.
- El `code="empresa_inactiva"` ya se lanza en `apps/api/serializers.py:21`, `apps/api/views.py:86`, `apps/api/autenticacion.py:18` y `apps/empresas/autenticacion.py:34`; `manejar_excepcion` (`apps/api/excepciones.py:62`) lo descarta al armar `{detalle, campos}`. Se agrega `code` al cuerpo solo para los códigos de una lista explícita (`CODIGOS_PUBLICOS = {"empresa_inactiva"}`); el resto de los errores no cambia.

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | ninguna |
| 2 (modificado 2026-11-14) | T4 (y cierre) | ninguna |

## Subtareas

### T1 — Turnos de la app: contacto, estado de los puntos y detalle

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/api_urls.py`, `apps/visitas/tests/test_api_turno_app.py`, `apps/visitas/tests/test_api_mis_turnos.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_turnos_api.py`
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/api/`, `apps/sitios/`, modelos y migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Serializers; `.agents/skills/django-security/SKILL.md` § Authorization; `.agents/skills/django-rest-framework/SKILL.md` § Testing DRF APIs
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - `PuntoItemSerializer` suma `estado` (con `estado_por_vencimiento(punto.proximo_vencimiento, timezone.localdate())`, una sola fecha por respuesta) y `proximo_vencimiento`. Sin consultas nuevas: el número de consultas de `me/visitas/` no depende de la cantidad de ítems.
  - `SitioTurnoSerializer(SitioResumenSerializer)` suma `contacto` (`{nombre, telefono}` o `null` si `contacto_en_sitio` y `telefono_en_sitio` están vacíos), sin coordenadas ni notas; lo usa solo `VisitaActivaSerializer`. `SitioResumenSerializer` y `VisitaRealizadaSerializer` no cambian: `me/historial/` y `visitas/<pk>/cerrar/` siguen sin contacto.
  - `MiVisitaDetalleView` (`RetrieveAPIView`, `EsEmpleado | EsAdministrador`, `VisitaActivaSerializer`) con el mismo queryset que `MisVisitasView` (extraído a una función o mixin común); ruta `me/visitas/<int:pk>/` (`name="mi-visita"`) en `apps/visitas/api_urls.py`. Ajena, de otra empresa, realizada o inexistente → 404. `extend_schema` con 200 y 404.
  - Los tests existentes que comparan el cuerpo exacto de un turno se ajustan solo para sumar los campos nuevos.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_item_vencido_ayer_trae_estado_vencida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_estado_coincide_con_el_resolver_de_qr --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_consultas_iguales_con_5_y_50_items --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_sitio_trae_contacto_o_null --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_historial_y_cierre_no_traen_contacto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otro_empleado_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_realizado_da_404 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`

### T2 — Raíz con usuario y empresa, y `code` del 401 por empresa inactiva

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/api/views.py`, `apps/api/excepciones.py`, `apps/api/esquema.py`, `apps/api/tests/test_raiz_y_codigos.py`, `apps/api/tests/test_auth.py`, `apps/api/tests/test_empresa.py`, `apps/api/tests/test_errores.py`, `apps/api/tests/test_esquema_robustez.py` (solo para sumar `code` a las propiedades esperadas de `Error`)
- **No puede tocar**: `docs/planes/`, `docs/`, `config/`, `apps/api/urls.py`, `apps/api/autenticacion.py`, `apps/api/serializers.py`, `apps/empresas/autenticacion.py`, archivos de otras apps
- **Transversal**: T2 es la subtarea transversal de `apps/api/` de este plan (tabla de propiedad).
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Error Handling y § Authentication
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `RaizView` devuelve `{"usuario": {"id", "nombre_completo", "username"}, "empresa": {"id", "nombre"} | null, "rol"}`; `nombre_completo` es `get_full_name()` o, si queda vacío, `username`; `empresa` sale de `empresa_de(request)`, nunca del pedido, y es `null` para un usuario sin empresa (sigue en 200). `extend_schema` con un `inline_serializer` en lugar de `OpenApiTypes.OBJECT`.
  - `manejar_excepcion`: si el código de la excepción (`exc.get_codes()` cuando es un texto) está en `CODIGOS_PUBLICOS = {"empresa_inactiva"}`, el cuerpo suma `"code"`; ningún otro error cambia su cuerpo. `ESQUEMA_ERROR` (`apps/api/esquema.py`) suma `code` opcional con `enum: ["empresa_inactiva"]`.
  - `test_otros_codigos_de_autenticacion_no_traen_code` prueba un `AuthenticationFailed` con código fuera de la lista (`password_changed`) y un token inválido (`InvalidToken`, código en dict): ninguno trae `code`.
  - Los tests existentes que comparan el cuerpo exacto de la raíz o de ese 401 se ajustan solo para sumar los campos nuevos.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_devuelve_usuario_y_empresa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_sin_nombre_usa_username --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_usuario_sin_empresa_da_200_con_empresa_null --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_token_con_empresa_inactiva_trae_code --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_renovacion_con_empresa_inactiva_trae_code --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_ruta_con_token_vigente_y_empresa_inactiva_trae_code --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_otros_codigos_de_autenticacion_no_traen_code --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_esquema_de_error_documenta_code --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`

### T3 — Integración ola 1, contrato y openapi (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Puede tocar**: `docs/contrato-api.md`, `docs/api/openapi-v1.yaml`, `apps/api/tests/test_contrato_doc.py`, `apps/api/tests/test_aislamiento.py`, `config/tests/test_ajustes_api_app_base.py`
- **Excepción a la propiedad**: T2 es la transversal de `apps/api/`, pero T3 (principal, después de integrar T2) escribe `apps/api/tests/test_contrato_doc.py` y `apps/api/tests/test_aislamiento.py`, porque el conteo 22 y `me/visitas/@PK@/` dependen de la ruta de T1. T2 no toca esos dos archivos y no corre en paralelo con T3.
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/ajustes-api-app-base` de cada subtarea, no los informes.
  2. Desde la raíz (rama `plan/ajustes-api-app-base`), `bash .claude/hooks/worktree-integrar.sh ajustes-api-app-base T<n> plan/ajustes-api-app-base <rutas>` por T1 y T2, de a una, con `verificar.py tarea` tras cada integración.
  3. Un commit `T3:` con: la fila y la sección de `me/visitas/<pk>/` en `docs/contrato-api.md`, los campos nuevos de la raíz y de `me/visitas/` (y `visitas/abrir/`), el `code` del 401 por empresa inactiva y `Actualizado:`; el conteo de `test_contrato_doc.py` de 21 a 22; `me/visitas/@PK@/` en `OBJETO_POR_RUTA` de `test_aislamiento.py`; `openapi-v1.yaml` regenerado con `manage.py spectacular --validate --file docs/api/openapi-v1.yaml`; tests de integración contra las URL reales.
- **Presupuesto**: 300 líneas agregadas
- **Criterios**:
  - `[cmd]` `git log --oneline plan/ajustes-api-app-base | grep -q "T1: integra ajustes-api-app-base-T1"`
  - `[cmd]` `git log --oneline plan/ajustes-api-app-base | grep -q "T2: integra ajustes-api-app-base-T2"`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_turno_por_url --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_otra_empresa_por_url_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_me_visitas_con_empresa_inactiva_trae_code --keepdb`
  - `[cmd]` `grep -qF "/api/v1/me/visitas/<pk>/" docs/contrato-api.md`
  - `[grep-1]` `grep -n "empresa_inactiva" docs/contrato-api.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T3`

### T4 — Contacto `null` con el sitio o el cliente dados de baja (modificado 2026-11-14, decisión del usuario)

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/tests/test_api_turno_app.py`, `docs/contrato-api.md`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/`, `apps/sitios/`, `apps/clientes/`, modelos y migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Serializers
- **Worktree**: sí
- **Presupuesto**: 120 líneas agregadas
- **Qué hacer**:
  - `SitioTurnoSerializer.get_contacto` devuelve `null` si `sitio.activo` o `sitio.cliente.activo` es falso (P-ajustes-api-app-base-6, opción a). Los turnos no cambian: siguen listados, solo pierden el contacto.
  - `visitas_activas_del_usuario` y `AbrirVisitaView` cargan `sitio__cliente` con `select_related`, para que el número de consultas siga sin depender de los ítems.
  - `docs/contrato-api.md`: `contacto` también es `null` con el sitio o el cliente dados de baja.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_contacto_null_con_cliente_dado_de_baja --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_contacto_null_con_sitio_dado_de_baja --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T4`

## Registro de verificación

commit_base: eb1dbda

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | hecha | c6186b2 | PASA 2026-11-14 |
| T2 | hecha | 50d255d | PASA 2026-11-14 |
| T3 | hecha | c2fd363 | PASA 2026-11-14 |
| T4 | pendiente | | |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-14 18:27 | plan | 3 | 2 | 5 |
| 2026-11-14 18:31 | plan | 1 | 0 | 0 |
| 2026-11-14 19:05 | cierre | 0 | 0 | 4 |

Auditoría: hecha 2026-11-14 — 0 bloqueantes, 1 necesita decisión (BAJA: contacto del sitio con el cliente dado de baja), 0 menores nuevos.
Hallazgos: revisor de cierre, 4 menores → pendiente P-ajustes-api-app-base-2 a -5; auditoría, contacto con cliente de baja → espera decisión (P-ajustes-api-app-base-6, "Esperan tu decisión" de `docs/estado.md`); P-ajustes-api-app-base-1 sigue igual.

### Decisiones del plan

- plan — `nombre_completo` vacío — vacío o `username` — `username` — la app nunca muestra un nombre en blanco — autónoma — devolver `get_full_name()` sin respaldo — decidida por Claude, revisable
- plan — `code` en errores — todos los códigos o lista blanca — lista blanca `{"empresa_inactiva"}` — no expone `user_not_found`, `password_changed` ni códigos de simplejwt — autónoma — ampliar `CODIGOS_PUBLICOS` — decidida por Claude, revisable
- plan — `me/visitas/<pk>/` de un turno realizado — 200 o 404 — 404 (mismo queryset que la lista) — mínima exposición y forma idéntica a la lista — autónoma — ampliar el filtro de estado — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-ajustes-api-app-base-1 [menor] `SesionAutenticacionEmpresa` (`apps/api/autenticacion.py:15-18`) usa `code="empresa_inactiva"` también para la sesión de `plataforma`, que no tiene empresa; con `code` público, el esquema servido por sesión lo afirmaría. No afecta a la app (entra por JWT). Revisión de plan del 2026-11-14.
- P-ajustes-api-app-base-2 [menor] `test_consultas_iguales_con_5_y_50_items` (`apps/visitas/tests/test_api_turno_app.py:53`) mide `me/visitas/<pk>/` y no la lista; hoy comparten queryset y serializer, pero falta la misma medición sobre `/api/v1/me/visitas/`.
- P-ajustes-api-app-base-3 [menor] `test_detalle_de_otra_empresa_da_404` (y `config/tests/test_ajustes_api_app_base.py:41`) pasaría sin `de_empresa`, porque el turno de B es de otro empleado; falta el caso de un usuario que cambió de empresa con turnos activos en la anterior.
- P-ajustes-api-app-base-4 [menor] Ningún test comprueba `sitio.contacto`, `estado` y `proximo_vencimiento` en la respuesta de `visitas/abrir/` (`apps/visitas/api_views.py:174`); hoy se cumple por usar el mismo serializer.
- P-ajustes-api-app-base-5 [observación] `apps/api/tests/test_auth.py:50` pasó de comparar el cuerpo exacto de la raíz a dos comprobaciones sueltas; el cuerpo exacto lo compara `test_raiz_y_codigos.py:125`.
- P-ajustes-api-app-base-6 [menor] Espera decisión del usuario (auditoría, BAJA): con el cliente o el sitio dados de baja, un turno pendiente sigue en `me/visitas/` y entrega `sitio.contacto` sin plazo (`apps/visitas/serializers.py:241-247`, `apps/clientes/panel_views.py:85-90`). Opciones: (a) `contacto: null` si el sitio o el cliente están inactivos; (b) cancelar o quitar los turnos pendientes al dar de baja.

### Decisiones

- 2026-11-14 — `GET /api/v1/` devuelve `usuario` como objeto `{id, nombre_completo, username}` en lugar del username como texto — la app no está publicada y lo pide así — (usuario) — reemplaza a: (nada)
- 2026-11-14 — el empleado recibe `sitio.contacto{nombre, telefono}` solo en sus turnos activos (`me/visitas/`, `me/visitas/<pk>/`, `visitas/abrir/`); el historial y el cierre siguen sin contacto — la app lo necesita para llegar al sitio; la Ley 25.326 art. 16 sigue aplicando al historial — (usuario) — reemplaza a: (nada)

### Cierra
