# Plan: robustez previa al lanzamiento (panel, admin, contrato de la API y pendientes)

- **slug**: `robustez-listados`
- **fecha**: 2026-11-13
- **objetivo**: un administrador, un operario o el operador de plataforma no ve errores 500 en el uso normal del panel, el admin y la API; el contrato de la API queda listo para generar la app móvil; y la lista de pendientes queda reducida a lo vigente, con etiqueta.
- **fuera de alcance**: pendientes con etiqueta `despliegue` (plan `despliegue-detach`), `empresa` (certificado y planillas) o `despues`; casos internos de la guardia de consultas sin uso en el código; cambios visuales fuera de P-diseno-panel-1 a -4; cambios al método de trabajo; cambios de comportamiento de la API fuera de los listados en las subtareas.
- **áreas**: panel | api | dominio (modelos y servicios)
- **ruta**: completo
- **seguridad**: sí — toca autenticación (JWT de un usuario `plataforma`, autenticación por sesión del esquema y la documentación de la API), el admin del operador (validación de empresa y referencias a `User`, logo), el aislamiento por empresa de la caché de geocodificación y el resolver del QR; corre `auditor-seguridad`.

## Contexto mínimo

- `multiempresa` y `metodo-v2` están en `main` y nada está en producción. `pendientes.py` lista 222 abiertos, muchos ya resueltos sin su `cierra:`, y 10 líneas con forma inválida.
- Siguen presentes, entre otros: `?orden=--x` y `?q=%00` en `apps/panel/listados.py:23-29`; un `plataforma` obtiene y renueva JWT (`apps/api/serializers.py:13-19`, `apps/api/views.py:69-70`); `_aplanar` de `apps/api/excepciones.py:30` pierde la ruta de un `non_field_errors` anidado y deja `__all__` en `campos`; el 429 del balde de fallos no lleva `Retry-After`; el resolver con un UUID mal formado da el 404 HTML (`apps/sitios/api_urls.py:11`); `CampoJSON` parsea números como `float` (`apps/visitas/serializers.py:40`); el admin da 500 cuando el error del modelo cae en un campo que no está en el formulario (`apps/empresas/models.py:129-163`, `apps/clientes/empresa.py:50-58`); `productos_aplicados` sale como texto en `docs/api/openapi-v1.yaml`.
- Ya resueltos en el código (se cierran en T11, sin cambios): P-metodo-v2-25 y -26, P-multiempresa-63, -72 y -73, la inmutabilidad de P-multiempresa-20 y `unidad_base` en el panel.
- Decisiones del usuario: P-multiempresa-75 y -86 se aceptan sin cambios; `incidencia_asignacion` solo si el turno ajeno incluye el punto; no se programa un punto inactivo ni se registra una revisión con un servicio dado de baja.
- Diseño: un formulario base del admin que lleva a errores generales los de campos ausentes del formulario cierra de una vez los 500 del admin; un hook de postproceso de drf-spectacular documenta 401, 415 y 429 en todas las rutas que los dan; el esquema y la documentación usan una autenticación por sesión que exige empresa activa. Sin migraciones. Referencias: `docs/01-modelo-y-arquitectura.md` (multiempresa y roles), `docs/contrato-api.md`.

## Olas

Ninguna subtarea crea migraciones; las olas separan archivos y dependencias de comportamiento (el contrato se regenera al final).

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3, T4, T5, T6 (integración) | panel, api, clientes, accounts, empresas, servicios, productos, sitios (ninguna) |
| 2 | T7, T8, T9 (integración) | visitas (ninguna) |
| 3 | T10, T11, T12 (integración y cierre) | ninguna |

## Subtareas

### T1 — Listados del panel sin 500 por orden o búsqueda inválidos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/panel/listados.py`, `apps/panel/tests/test_listados_robustez.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/panel/urls.py`, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § SQL Injection Prevention
- **Worktree**: sí
- **Presupuesto**: 150 líneas agregadas
- **Qué hacer**: en `ListadoPanelMixin.get_orden`, quitar un solo `-` inicial antes de comparar contra `orden_permitido` (un `--x` se ignora y usa el orden por defecto). En `get_busqueda`, descartar el carácter NUL de `q`. El test recorre los 6 listados (`panel:usuarios:listado`, `panel:visitas:listado`, `panel:productos:listado`, `panel:servicios:listado`, `panel:clientes:listado`, `panel:sitios:listado`) con un administrador; para el NUL, además de pedir la página, comprueba que `get_busqueda` no devuelve `\x00` (SQLite no reproduce el rechazo de Postgres). Cierra P-robustez-panel-9 y -10.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_orden_con_doble_guion_responde_200_en_todos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_busqueda_con_nul_responde_200_en_todos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_get_busqueda_descarta_nul --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T1`

### T2 — API: plataforma sin JWT, errores con ruta, Retry-After y esquema documentado

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/api/serializers.py`, `apps/api/views.py`, `apps/api/excepciones.py`, `apps/api/autenticacion.py`, `apps/api/esquema.py`, `apps/api/tests/test_plataforma_api.py`, `apps/api/tests/test_errores_robustez.py`, `apps/api/tests/test_esquema_robustez.py`, `apps/api/tests/test_limites.py`, `apps/api/tests/test_auth.py`, `apps/api/tests/test_errores.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/urls.py`, `docs/api/openapi-v1.yaml`, `docs/contrato-api.md`, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Authentication, § Throttling y § Error Handling; `.agents/skills/jwt-security/SKILL.md` § Token Creation
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - Un usuario con `es_plataforma` recibe 401 al pedir el token (`TokenNormalizadoSerializer.get_token`) y al renovarlo (`RenovacionSerializer.validate`), con el mismo `detalle` que una credencial inválida (P-multiempresa-74, -81).
  - El 429 del balde de fallos (`raise Throttled()` en `ObtenerToken.post`) pasa `wait` y sale con `Retry-After` (P-api-movil-6).
  - En `apps/api/excepciones.py`, el `__all__` de un `ValidationError` de Django va a `detalle`. Un `non_field_errors` anidado va a `campos` con su ruta (`productos_aplicados.0`), aplanado con `_aplanar` y sin `repr` de `ErrorDetail` (P-api-movil-1, -2). El `non_field_errors` de primer nivel sigue en `detalle`.
  - Una vista `no_encontrado(request, exception)` en `apps/api/views.py` devuelve el 404 JSON `{"detalle", "campos": {}}` de la API para rutas bajo `/api/` y delega en la página HTML de Django para el resto; la cablea T6 como `handler404`.
  - `SesionAutenticacionEmpresa` (`apps/api/autenticacion.py`, subclase de `SessionAuthentication`): rechaza con `AuthenticationFailed` una sesión sin empresa (incluye `plataforma`) o con empresa inactiva (P-multiempresa-6); la registra T6 en `SERVE_AUTHENTICATION`.
  - Hook de postproceso `apps/api/esquema.py` (`agregar_respuestas_comunes(result, generator, request, public)`): agrega 401 a toda operación con seguridad y 429 a las rutas con throttle que aún no lo declaran (las que tienen `throttle_scope`), con el esquema de error `{detalle, campos}` y la cabecera `Retry-After`; no duplica lo que `extend_schema` ya declara. `auth/token/` ya documenta 200 con `Tokens`, 401, 415 y 429 (`apps/api/views.py:82-100`, `apps/api/tests/test_schema.py:59-80`): solo se le agrega el 400 por cuerpo incompleto (P-contrato-app-9, P-cierre-puntos-15 en lo que toca a `auth/`). T6 lo registra en `POSTPROCESSING_HOOKS`.
  - Un `plataforma` con la contraseña correcta cuenta como un fallo en los baldes, igual que una credencial inválida (no revela que la contraseña es correcta).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_plataforma_api.PlataformaApiTests.test_plataforma_no_obtiene_token --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_plataforma_api.PlataformaApiTests.test_plataforma_no_renueva_token --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_non_field_errors_anidado_conserva_ruta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_all_de_django_va_a_detalle --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_429_del_balde_lleva_retry_after --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_no_encontrado_bajo_api_devuelve_json --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_esquema_robustez.EsquemaRobustezTests.test_sesion_sin_empresa_activa_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_esquema_robustez.EsquemaRobustezTests.test_postproceso_agrega_401_y_429 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T2`

### T3 — Admin del operador: errores de formulario en lugar de 500 y logo procesado

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/clientes/empresa.py`, `apps/clientes/tests/test_admin_errores.py`, `apps/accounts/admin.py`, `apps/accounts/tests/test_admin_rol_plataforma.py`, `apps/empresas/admin.py`, `apps/empresas/tests/test_admin_logo.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/empresas/models.py`, `apps/accounts/models.py`, migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § File Upload Security; `.agents/skills/django-conventions/SKILL.md` § Templates (solo si toca plantillas del admin)
- **Worktree**: sí
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - Formulario base del admin para `AdminRaizMixin` y `AdminHijoMixin`. Lleva a `NON_FIELD_ERRORS` todo error del modelo cuya clave no es un campo del formulario: un padre o una referencia a `User` de solo lectura, como `ubicacion_fijada_por` o `incidencia_revisada_por`. Cierra P-multiempresa-20 residual y -68. Además no excluye `empresa` de la validación de restricciones, como `FormularioDeEmpresa._get_validation_exclusions`, así que un slug repetido de `TipoServicio` en la misma empresa da error de formulario (P-multiempresa-28).
  - `CuentaAdmin` aplica la misma reconducción de errores. El mensaje de `ReglaRolEmpresaMixin` indica la salida: cambiar el rol a administrador o empleado (P-multiempresa-38).
  - `EmpresaAdmin` usa un formulario con `clean_logo` que pasa por `procesar_logo` (`apps/empresas/logos.py`); un archivo inválido da error de formulario (P-multiempresa-30).
  - Un test por caso, por `self.client` contra `admin:<app>_<modelo>_change` con `crear_plataforma`, que espera 200 y el error en el formulario.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_admin_errores.AdminErroresTests.test_padre_de_otra_empresa_da_error_de_formulario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_admin_errores.AdminErroresTests.test_slug_repetido_en_la_empresa_da_error_de_formulario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_admin_errores.AdminErroresTests.test_referencia_plataforma_de_solo_lectura_da_error_de_formulario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_admin_rol_plataforma.RolPlataformaAdminTests.test_plataforma_con_empresa_da_error_que_indica_la_salida --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_admin_logo.EmpresaAdminLogoTests.test_logo_del_admin_se_guarda_procesado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_admin_logo.EmpresaAdminLogoTests.test_logo_invalido_da_error_de_formulario --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes apps.accounts apps.empresas apps.sitios apps.visitas apps.servicios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T3`

### T4 — Catálogo: slug concurrente y unidades bloqueadas con movimientos

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/servicios/models.py`, `apps/servicios/tests/test_slug_concurrente.py`, `apps/productos/panel_forms.py`, `apps/productos/admin.py`, `apps/productos/tests/test_unidad_bloqueada.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/clientes/empresa.py`, migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Best Practices Summary
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `TipoServicio.save`: si el slug se generó automáticamente y el `INSERT` choca con `IntegrityError` de `(empresa, slug)`, reintenta dentro de `transaction.atomic()` con el siguiente sufijo libre (unos pocos intentos), en lugar de propagar un 500 (P-catalogo-stock-4). El test simula la carrera con un `patch` de `_slug_libre` con `side_effect` que devuelve el slug ya tomado solo en la primera llamada y después delega en el original (`wraps`); afirma que se guarda `<base>-2` y que un slug explícito repetido no se reintenta (sigue siendo error).
  - `ProductoForm` del panel: `modo_unidad` no cambia si el producto tiene movimientos, con el mismo patrón que `clean_unidad_base`. En `ProductoAdmin`, `unidad_base` y `modo_unidad` son de solo lectura al editar un producto con movimientos (P-catalogo-stock-3).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_slug_concurrente.SlugConcurrenteTests.test_choque_de_slug_reintenta_con_sufijo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidad_bloqueada.UnidadBloqueadaTests.test_modo_unidad_con_movimientos_da_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidad_bloqueada.UnidadBloqueadaTests.test_admin_unidades_de_solo_lectura_con_movimientos --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios apps.productos --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T4`

### T5 — Sitios: programación de puntos, caché por empresa y resolver

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/sitios/panel_forms.py`, `apps/sitios/panel_views.py`, `apps/sitios/geocodificacion.py`, `apps/sitios/api_urls.py`, `apps/sitios/api_views.py`, `apps/sitios/services.py`, `apps/sitios/templates/sitios/panel/_fila_punto.html`, `apps/sitios/tests/test_robustez_sitios.py`, `apps/sitios/tests/test_geocodificacion.py`, `apps/sitios/tests/test_api.py`, `apps/api/tests/test_aislamiento.py` (solo para tratar `<str:codigo>` del resolver como UUID)
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/`, migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Error Handling
- **Worktree**: sí
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**:
  - `ProgramacionForm` y el select de cada fila (contexto `servicios` de `apps/sitios/panel_views.py:318` y `:552-554`, dibujado en `apps/sitios/templates/sitios/panel/_fila_punto.html:8`): las opciones son los servicios activos de la empresa más el servicio actual del punto aunque esté desactivado, que sale seleccionado; así editar la fila no lo cambia (P-flujo-sitio-2). El test pide la fila o la pestaña por GET y comprueba la opción seleccionada del servicio inactivo, y después guarda la fila sin tocar el servicio.
  - `PuntoProgramacion`: un punto inactivo no se programa (404, desde el `get_queryset` del POST); `actualizar_programacion` rechaza un servicio inactivo distinto del actual (P-flujo-sitio-14, parte de programación).
  - `geocodificar`: la clave de caché lleva `empresa_id` y `Geocodificar.post` pasa `request.empresa.pk` (P-multiempresa-85).
  - Resolver: la ruta pasa a `qr/<str:codigo>/resolver/`; la vista valida con `UUID(codigo)` y ante `ValueError` responde el mismo `NotFound` JSON que un QR inexistente (no el 400 que daría el campo UUID) (P-api-movil-11). El parámetro se declara `OpenApiParameter("codigo", OpenApiTypes.UUID, OpenApiParameter.PATH)` para no perder `format: uuid`. El `extend_schema` del resolver documenta el cliente inactivo, el código mal formado, el punto sin servicio (su revisión fuera de turno da 400 hasta que el administrador asigne uno) y el punto con plano sin `x`/`y` (no aparece en `plano.puntos`) (P-saneamiento-5, P-flujo-sitio-6, P-puntos-control-19).
  - `POST sitios/` deja de documentar el 404 que no puede dar (P-cierre-puntos-15, parte de sitios).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ProgramacionRobustezTests.test_servicio_desactivado_se_conserva_al_editar_la_fila --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ProgramacionRobustezTests.test_punto_inactivo_no_se_programa --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ProgramacionRobustezTests.test_no_se_asigna_otro_servicio_inactivo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.GeocodificacionEmpresaTests.test_cache_de_una_empresa_no_responde_a_otra --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ResolverRobustezTests.test_codigo_mal_formado_da_404_json --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T5`

### T6 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1 a T5)
- **Depende de**: T1, T2, T3, T4, T5
- **Puede tocar**: `config/settings/base.py`, `config/urls.py`, `config/tests/test_robustez_listados.py`
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/robustez-listados` de cada subtarea, no los informes.
  2. Desde `worktrees/robustez-listados`, `bash .claude/hooks/worktree-integrar.sh robustez-listados T<n> plan/robustez-listados <rutas>` por T1 a T5, de a una, con `verificar.py tarea` tras cada integración.
  3. Commits `T6:`: `SERVE_AUTHENTICATION` con `apps.api.autenticacion.SesionAutenticacionEmpresa` en lugar de `SessionAuthentication`; `POSTPROCESSING_HOOKS` con el hook por defecto y `apps.api.esquema.agregar_respuestas_comunes`; `handler404 = "apps.api.views.no_encontrado"` en `config/urls.py`; tests de integración.
  4. Crear los worktrees de T7 y T8 desde `plan/robustez-listados`.
- **Presupuesto**: 120 líneas agregadas
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T1: integra robustez-listados-T1"`
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T2: integra robustez-listados-T2"`
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T3: integra robustez-listados-T3"`
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T4: integra robustez-listados-T4"`
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T5: integra robustez-listados-T5"`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_ruta_inexistente_bajo_api_da_404_json --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_esquema_con_sesion_de_plataforma_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_esquema_con_sesion_de_empresa_inactiva_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_esquema_con_sesion_de_empresa_activa_responde --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T6`

### T7 — Visitas: revisiones, incidencia de asignación y resolver

- **Ola**: 2
- **Depende de**: T6
- **Puede tocar**: `apps/visitas/serializers.py`, `apps/visitas/services.py`, `apps/visitas/api_views.py`, `apps/visitas/tests/test_robustez_visitas.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_visita_destino.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/admin.py`, `apps/visitas/static/`, `apps/visitas/templates/`, `apps/visitas/panel_views.py`, migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Custom Fields and Validation y § Serializers
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - `CampoJSON`: `json.loads` con `parse_float=Decimal` y un `parse_constant` que rechaza `NaN`, `Infinity` y `-Infinity`. Una `cantidad` o `dosis` numérica se guarda con su valor exacto (P-catalogo-stock-2).
  - `abrir_visita` marca `incidencia_asignacion` solo si una visita pendiente de otro empleado en el sitio tiene un `ItemTurno` de ese punto (P-flujo-sitio-5).
  - `_servicio_de_la_revision`: un servicio dado de baja da 400 con un mensaje en español (P-flujo-sitio-14, parte de revisiones).
  - `_pendiente_para` pierde el parámetro `bloquear` y la rama `select_for_update` sin llamadores (P-ajustes-flujo-2).
  - `servicio_para_punto` devuelve el servicio con `campos` precargados y el test fija el número de consultas del resolver (P-ajustes-flujo-4).
  - Tests de `visita_destino` y del campo del resolver con una visita de otro empleado y una del mismo empleado en otro sitio (P-ajustes-flujo-3).
  - `extend_schema` de `POST revisiones/`: `productos_aplicados` como arreglo de objetos con sus campos, mediante `extend_schema_field` en `CampoJSON` o un serializer de ítem solo para el esquema, y en el pedido multipart `encoding: {productos_aplicados: {contentType: application/json}}`, porque viaja como una parte JSON y no como campos sueltos (P-catalogo-stock-6). El test comprueba las dos cosas. Se documentan el 400 por atraso de `POST visitas/` y el 400 por servicio dado de baja (P-contrato-app-9).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.CantidadNumericaTests.test_cantidad_como_numero_json_da_201_y_valor_exacto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.CantidadNumericaTests.test_nan_se_rechaza --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.IncidenciaAsignacionTests.test_turno_ajeno_sin_el_punto_no_marca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.IncidenciaAsignacionTests.test_turno_ajeno_con_el_punto_marca --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.ServicioDadoDeBajaTests.test_revision_con_servicio_dado_de_baja_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.ResolverConsultasTests.test_resolver_precarga_campos_del_servicio --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.VisitaDestinoAjenaTests.test_visita_de_otro_empleado_no_es_destino --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.VisitaDestinoAjenaTests.test_visita_propia_en_otro_sitio_no_es_destino --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_robustez_visitas.EsquemaRevisionesTests.test_productos_aplicados_tiene_esquema_de_item --keepdb`
  - `[grep-0]` `grep -nE "bloquear=|\*, bloquear" apps/visitas/services.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.sitios apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T7`

### T8 — Visitas: nuevo turno, filtros de turnos y admin

- **Ola**: 2
- **Depende de**: T6
- **Puede tocar**: `apps/visitas/static/visitas/nuevo_turno.js`, `apps/visitas/static/visitas/nuevo_turno.css`, `apps/visitas/templates/visitas/panel/_listado.html`, `apps/visitas/templates/visitas/panel/_nuevo_turno_lateral.html`, `apps/visitas/templates/visitas/panel/nuevo_turno.html`, `apps/visitas/templates/visitas/panel/_puntos_servicio.html`, `apps/visitas/admin.py`, `apps/visitas/tests/test_panel_robustez.py`, `apps/visitas/tests/test_admin.py`
- **No puede tocar**: `docs/planes/`, `config/`, `templates/`, `static/src/`, `static/css/`, `apps/visitas/serializers.py`, `apps/visitas/services.py`, `apps/visitas/api_views.py`, migraciones, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/frontend-design/SKILL.md` § Frontend Aesthetics Guidelines; `docs/02-diseno.md`
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - En el `L.map` de `nuevo_turno.js`, `keyboard: false` (el test lo busca con una regex dentro de las opciones de `L.map(`, no en cualquier parte del archivo; los marcadores ya lo tienen). Si hace falta, el contenedor se enfoca con `preventScroll`, para que el primer clic sobre un marcador del panel lateral tilde el punto (P-diseno-panel-1).
  - En `nuevo_turno.css` y `_puntos_servicio.html`, la columna "Punto" no corta palabras, la insignia "Sin programar" se separa del select y los selects de servicio no truncan el nombre (P-diseno-panel-2).
  - Los filtros de `/panel/visitas/` pasan a un `form.filtros` como el de Usuarios (`apps/accounts/templates/accounts/panel/listado.html`), con el buscador aparte y el mismo comportamiento htmx (P-diseno-panel-3).
  - "Sitio: …" queda dentro de la tarjeta del formulario en la página completa y en el panel lateral (P-diseno-panel-4).
  - `VisitaAdmin`: en una visita pendiente con ítems, `sitio` es de solo lectura (P-flujo-sitio-12).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_robustez.MapaPanelLateralTests.test_mapa_del_panel_lateral_sin_teclado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_robustez.FiltrosTurnosTests.test_listado_de_turnos_usa_la_fila_filtros --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_robustez.NuevoTurnoTarjetaTests.test_sitio_dentro_de_la_tarjeta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_robustez.AdminSitioConItemsTests.test_sitio_de_solo_lectura_en_pendiente_con_items --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T8`

### T9 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T7 y T8)
- **Depende de**: T7, T8
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/robustez-listados` de T7 y T8.
  2. Desde `worktrees/robustez-listados`, `worktree-integrar.sh` de T7 y después de T8, con `verificar.py tarea` tras cada una.
  3. Prueba manual en el navegador con el servidor de desarrollo. El primer clic sobre un marcador del panel lateral de nuevo turno tilda el punto. Las columnas y los selects no cortan texto. Los filtros de turnos se ven en la fila `.filtros`. El resultado, con fecha, va a `### Decisiones del plan`.
  4. Crear el worktree de T10 desde `plan/robustez-listados`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T7: integra robustez-listados-T7"`
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T8: integra robustez-listados-T8"`

### T10 — Contrato de la API y OpenAPI regenerado

- **Ola**: 3
- **Depende de**: T9
- **Puede tocar**: `docs/contrato-api.md`, `docs/api/openapi-v1.yaml`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Error Handling
- **Worktree**: sí
- **Presupuesto**: 500 líneas agregadas (incluye el YAML regenerado)
- **Qué hacer**:
  - Regenerar `docs/api/openapi-v1.yaml` con `manage.py spectacular --validate --file docs/api/openapi-v1.yaml`.
  - Reflejar en `docs/contrato-api.md`:
    - el 401 de un usuario `plataforma` en `auth/token/` y `auth/token/refresh/`, y la sesión con empresa activa para el esquema y la documentación;
    - `Retry-After` en todo 429;
    - el `non_field_errors` anidado, que va a `campos` con su ruta, y el `__all__`, que va a `detalle`;
    - los 404 JSON de una ruta inexistente bajo `/api/` y de un código de QR mal formado;
    - `productos_aplicados` como arreglo de objetos y sus valores numéricos exactos;
    - el 400 por servicio dado de baja;
    - el punto sin servicio y el punto con plano sin coordenadas.
  - Si el YAML regenerado cambia algo que ninguna subtarea declaró, se informa y no se oculta.
- **Criterios**:
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$TEMP/openapi-robustez.yaml" && diff -q --strip-trailing-cr "$TEMP/openapi-robustez.yaml" docs/api/openapi-v1.yaml`
  - `[cmd]` `./venv/Scripts/python.exe -c "import yaml; d=yaml.safe_load(open('docs/api/openapi-v1.yaml', encoding='utf-8')); S=d['components']['schemas']; r=lambda x: S[x['\$ref'].split('/')[-1]] if '\$ref' in x else x; p=[r(s['properties']['productos_aplicados']) for s in S.values() if 'productos_aplicados' in s.get('properties', {})]; assert p and all(x.get('type') == 'array' and r(x['items']).get('type') == 'object' and r(x['items']).get('properties') for x in p), p"`
  - `[cmd]` `./venv/Scripts/python.exe -c "import yaml; d=yaml.safe_load(open('docs/api/openapi-v1.yaml', encoding='utf-8')); c=[v for k, v in d['paths'].items() if k.endswith('/revisiones/')][0]['post']['requestBody']['content']['multipart/form-data']; assert c['encoding']['productos_aplicados']['contentType'] == 'application/json', c"`
  - `[grep-1]` `grep -n "Retry-After" docs/contrato-api.md`
  - `[grep-1]` `grep -n "plataforma" docs/contrato-api.md`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 500 --subtarea T10`

### T11 — Limpieza de pendientes (principal)

- **Ola**: 3
- **Depende de**: T9
- **Puede tocar**: `docs/planes/2026-11-13-robustez-listados.md` (debajo del corte); ningún otro plan (decisión del usuario del 2026-11-13)
- **Worktree**: no (pasivo: solo documentación del plan, en `worktrees/robustez-listados`)
- **Presupuesto**: 450 líneas agregadas
- **Qué hacer**:
  - Exploradores de solo lectura, uno por grupo de planes, comprueban contra el código cada abierto de `multiempresa`, `metodo-v2`, `flujo-sitio`, `robustez-panel`, `robustez-datos`, `demo-cliente`, `separacion-web` y `nombre-empresa-prod`. Devuelven una tabla: id, resuelto, sin objeto o vigente, y la evidencia con archivo y línea.
  - El principal escribe en `### Cierra` de este plan:
    - los resueltos;
    - los sin objeto (Proyecto, Tablero, `NOMBRE_EMPRESA`, demo portátil);
    - los que corrigieron T1 a T10;
    - P-multiempresa-75 y -86, aceptados por el usuario.
  - En `### Etiquetas` va el resto, con `despliegue`, `expo`, `empresa` o `despues`, incluidos los de `catalogo-stock`, `diseno-panel`, `ajustes-flujo` y `protocolo-decisiones`. Los importantes que hoy tienen solo `informes`, `robustez-dominio` o `saneamiento` reciben además una de las cuatro.
  - Las 10 líneas con forma inválida de otros planes no se editan (decisión del usuario). Desde este plan:
    - las decisiones de `demo-cliente.md:269` y `demo-portatil.md:162-163` se re-registran en `### Decisiones` con su forma válida y su fecha original;
    - P-demo-portatil-1 a -5 ya los cerró `separacion-web` al borrar la demo portátil (su `cierra:` múltiple es el aviso); se anota en `### Decisiones del plan`;
    - la línea sin id de `multiempresa.md:623` (orden de integración de la ola 3) quedó sin objeto al fusionar `multiempresa`; se anota igual.
    Esos 10 avisos siguen apareciendo; el criterio exige que este plan no agregue ninguno.
- **Criterios**:
  - `[cmd]` `PYTHONIOENCODING=utf-8 py -3 .claude/hooks/pendientes.py --json | PYTHONIOENCODING=utf-8 py -3 -c "import json, sys; d = json.load(sys.stdin); sin = [a['id'] for a in d['abiertos'] if not a['etiquetas']]; av = [x for x in d['avisos'] if 'robustez-listados' in x]; print(av, sin); sys.exit(1 if av or sin else 0)"`
  - `[cmd]` `PYTHONIOENCODING=utf-8 py -3 .claude/hooks/pendientes.py --json | PYTHONIOENCODING=utf-8 py -3 -c "import json, sys; d = json.load(sys.stdin); ok = {'despliegue', 'expo', 'empresa', 'despues'}; mal = [a['id'] for a in d['abiertos'] if a['severidad'] == 'bloqueante' or (a['severidad'] == 'importante' and not ok & set(a['etiquetas']))]; print(mal); sys.exit(1 if mal else 0)"`
  - `[cmd]` `PYTHONIOENCODING=utf-8 py -3 .claude/hooks/pendientes.py --json | PYTHONIOENCODING=utf-8 py -3 -c "import json, sys; d = json.load(sys.stdin); ids = {a['id'] for a in d['abiertos']}; plan = 'P-robustez-panel-9 P-robustez-panel-10 P-diseno-panel-1 P-diseno-panel-2 P-diseno-panel-3 P-diseno-panel-4 P-flujo-sitio-2 P-flujo-sitio-5 P-flujo-sitio-6 P-flujo-sitio-12 P-flujo-sitio-14 P-catalogo-stock-2 P-catalogo-stock-3 P-catalogo-stock-4 P-catalogo-stock-6 P-multiempresa-6 P-multiempresa-20 P-multiempresa-28 P-multiempresa-30 P-multiempresa-38 P-multiempresa-63 P-multiempresa-68 P-multiempresa-72 P-multiempresa-73 P-multiempresa-74 P-multiempresa-75 P-multiempresa-81 P-multiempresa-85 P-multiempresa-86 P-api-movil-1 P-api-movil-2 P-api-movil-6 P-api-movil-11 P-contrato-app-9 P-cierre-puntos-15 P-puntos-control-19 P-saneamiento-5 P-ajustes-flujo-2 P-ajustes-flujo-3 P-ajustes-flujo-4 P-metodo-v2-25 P-metodo-v2-26'.split(); quedan = [i for i in plan if i in ids]; print(quedan); sys.exit(1 if quedan else 0)"`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 450 --subtarea T11`

### T12 — Integración ola 3 y cierre (principal)

- **Ola**: 3 (después de verificar T10 y T11)
- **Depende de**: T10, T11
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/robustez-listados` de T10 e integrarla desde `worktrees/robustez-listados` con `verificar.py tarea`.
  2. `verificar.py todo docs/planes/2026-11-13-robustez-listados.md`, `revisor` en modo cierre y `auditor-seguridad`; bloqueantes en una ronda y `todo` de nuevo.
  3. `medir_metodo.py --registrar docs/metodo/metricas.md`, `docs/estado.md`, decisiones y un solo commit `cierre: robustez-listados`; push de `plan/robustez-listados` y PR. La fusión en `main` es del usuario.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/robustez-listados | grep -q "T10: integra robustez-listados-T10"`

## Registro de verificación

commit_base: ccb6738

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | hecha | b1f560b | PASA 2026-11-13 |
| T2 | hecha | b79b01b | PASA 2026-11-13 |
| T3 | hecha | 7ee5383 | PASA 2026-11-13 |
| T4 | hecha | 506b64b | PASA 2026-11-13 |
| T5 | hecha | 898c4c7 | PASA 2026-11-13 |
| T6 | hecha | 96facef | PASA 2026-11-13 |
| T7 | hecha | 5ecc174 | PASA 2026-11-13 |
| T8 | hecha | 3364aab | PASA 2026-11-13 |
| T9 | hecha | — | sin commits propios; prueba en navegador pendiente del usuario |
| T10 | hecha | 43e91eb | PASA 2026-11-13 |
| T11 | hecha | 0b3c364 | PASA 2026-11-13 |
| T12 | hecha | — | PASA 2026-11-13 (todo sobre 21f539b) |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-13 17:31 | plan | 4 | 0 | 6 |
| 2026-11-13 18:30 | plan | 0 | 0 | 2 |
| 2026-11-13 20:07 | cierre | 4 | 0 | 4 |

Auditoría: auditor-seguridad 2026-11-13 — se puede cerrar; 0 bloqueantes, 0 decisiones, 2 observaciones (P-robustez-listados-12 y -13)
Hallazgos: revisor de cierre — 4 bloqueantes de documentación corregidos en una ronda (docs/contrato-api.md: 404 del QR mal formado y alcance de `plataforma`; docs/01-modelo-y-arquitectura.md: `plataforma` sin API e `incidencia_asignacion` por punto); 4 menores → pendiente P-robustez-listados-8 a -11. Auditoría: 2 observaciones → pendiente P-robustez-listados-12 y -13

### Decisiones del plan

- T3 — dónde vive el formulario base del admin — `apps/clientes/empresa.py` o `apps/empresas/admin.py` — `apps/empresas/admin.py` (lo importan `clientes` y `accounts`) — `accounts` no depende de `clientes` — autónoma — mover el mixin — decidida por Claude, revisable
- T6 — el test de T2 del postproceso daba por hecho el esquema sin el hook — cambiar el contrato o corregir el test dentro de `Puede tocar` de T2 — commit `T2:` que arma el esquema sin hooks (`mock.patch.object(spectacular_settings, ...)`) y nueva verificación de T2 — el archivo es de T2 y el cambio no altera lo que prueba — autónoma — revertir b79b01b — decidida por Claude, revisable
- T7 — `parse_float=Decimal` en todo `CampoJSON` o solo en `productos_aplicados` — solo en `productos_aplicados` (P-catalogo-stock-2 habla de `cantidad` y `dosis`); `NaN` e `Infinity` se rechazan en ambos — con `Decimal` en `datos`, `validar_datos` rechazaba `3.5` — autónoma — `decimales_exactos=True` en `datos`, con adaptación — decidida por Claude, revisable (P-robustez-listados-6)
- T7 — el 400 por atraso de `POST visitas/` de P-contrato-app-9 — esa ruta ya no existe (`test_post_visitas_ya_no_existe`); el atraso está documentado en `POST revisiones/` — nada que agregar — autónoma — no aplica — decidida por Claude, revisable
- T9 — prueba manual en navegador — esta sesión no tuvo navegador (ni la extensión de Chrome ni el navegador integrado) — la hace el usuario: `manage.py cargar_demo` y `runserver`, ingresar como `demo-admin` / `demo1234`, nuevo turno desde el panel lateral de un sitio con plano, primer clic sobre un marcador — sin acceso a navegador — autónoma — no aplica — decidida por Claude, revisable (P-robustez-listados-7)
- T11 — líneas con forma inválida de planes ajenos — editar o resolver desde este plan — resolver desde este plan (decisión del usuario); las decisiones de `demo-portatil` no se re-registran porque la demo portátil se borró; la línea sin id de `multiempresa.md:623` quedó sin objeto al fusionar `multiempresa` — usuario — editar las líneas — decidida por el usuario

## Pendientes que deja este plan

### Problemas

- P-robustez-listados-1 [menor] `apps/api/views.py` (`segundos_de_espera`) importa `_baldes` y `_fallos_vigentes`, privadas de `apps/accounts/limites.py`; conviene una función pública que devuelva la espera (implementador T2).
- P-robustez-listados-2 [observación] `apps/api/esquema.py` usa `generator._get_paths_and_endpoints()`, privado de drf-spectacular, para saber qué vista tiene throttle; puede romperse al actualizar la librería (implementador T2).
- P-robustez-listados-3 [menor] `apps/visitas/templates/visitas/panel/_listado.html` dibuja los filtros y el buscador solo si el pedido no es htmx (`request.headers.hx_request`), porque `listado.html` no estaba en el alcance de T8; moverlos a `listado.html` lo haría explícito.
- P-robustez-listados-4 [menor] En `/panel/visitas/` el `orden` oculto del formulario de filtros y el del buscador pueden quedar desfasados si se cambia el orden desde la cabecera de la tabla (pasa igual en Usuarios).
- P-robustez-listados-5 [observación] `manage.py spectacular` avisa "multiple names for the same choice set (UnidadEnum)"; se resuelve con `ENUM_NAME_OVERRIDES` en `config/settings/base.py`.
- P-robustez-listados-6 [menor] Los `datos` de la planilla siguen parseándose con `float` (solo `productos_aplicados` usa `Decimal`): con `Decimal` en `datos`, `validar_datos` rechazaba `3.5`; unificarlo exige adaptar la validación y el guardado en JSON (implementador T7).
- P-robustez-listados-7 [menor] Falta la prueba en navegador de P-diseno-panel-1 a -3 (primer clic en un marcador del panel lateral, columnas y selects, filtros de turnos): esta sesión no tuvo navegador; la hace el usuario con `cargar_demo` y `runserver`. Si el primer clic sigue perdiéndose, falta `preventScroll` o quitar el foco del contenedor en `nuevo_turno.js`.

- P-robustez-listados-8 [menor] El OpenAPI documenta el 429 de `auth/token/` y `auth/token/refresh/` sin la cabecera `Retry-After` ni el esquema `Error` (`RESPUESTAS_DE_CONTRATO`, `apps/api/views.py:122`; `apps/api/tests/test_esquema_robustez.py:62` lo fija así), aunque la respuesta real la lleva y `docs/contrato-api.md` la promete (revisor, cierre).
- P-robustez-listados-9 [menor] `test_orden_con_doble_guion_responde_200_en_todos` usa `--creado`, que solo está en la lista blanca de visitas y clientes: en los otros 4 listados el caso pasaba antes de la corrección; usar un campo permitido de cada listado (revisor, cierre).
- P-robustez-listados-10 [menor] El rechazo de un servicio inactivo distinto del actual en `actualizar_programacion` (`apps/sitios/services.py:260-265`) no tiene test propio: `test_no_se_asigna_otro_servicio_inactivo` lo frena el queryset del formulario (revisor, cierre).
- P-robustez-listados-11 [observación] `test_plataforma_no_renueva_token` no compara el `detalle` con el de una credencial inválida; el código ya lo cumple (revisor, cierre).
- P-robustez-listados-12 [observación] `JWTAutenticacionEmpresa` (`apps/empresas/autenticacion.py:27-39`) acepta `empresa=None`: un JWT de `plataforma` emitido antes de este plan leería el esquema hasta vencer (15 min). Defensa en profundidad: rechazar también `empresa is None`, con test (auditor-seguridad).
- P-robustez-listados-13 [observación] `Retry-After` del balde global por usuario revela la antigüedad del fallo más viejo vigente de ese usuario; valor despreciable, sin cambio propuesto (auditor-seguridad).

### Decisiones

- 2026-11-13 — P-multiempresa-75 (mensaje distinto para empresa inactiva en el token) y P-multiempresa-86 (el alta de usuarios revela un nombre de otra empresa) se aceptan sin cambios — decisión de alcance de `robustez-listados` — (usuario) — reemplaza a: (nada)
- 2026-11-13 — `incidencia_asignacion` se marca solo si una visita pendiente de otro empleado incluye ese punto — menos ruido con varios operarios por sitio — (usuario) — reemplaza a: (nada)
- 2026-11-13 — un punto inactivo no se programa y una revisión con un servicio dado de baja da 400; un servicio desactivado ya asignado se conserva al editar la fila — cierra la decisión de producto de P-flujo-sitio-14 — (usuario) — reemplaza a: (nada)

- 2026-11-13 — las líneas con forma inválida de planes ajenos (`demo-cliente`, `demo-portatil`, `separacion-web`, `multiempresa`) no se editan: lo vigente se re-registra o se cierra desde `robustez-listados` y los 10 avisos de forma se aceptan — los planes de otro dueño no se tocan (convenciones-proyecto § Tabla de propiedad) — (usuario) — reemplaza a: (nada)

- 2026-10-12 — alojamiento preparado para Railway (`railway.json`) sin Procfile — el proyecto ya tiene el plugin de Railway; re-registrada desde `demo-cliente`, cuya línea tiene forma inválida — (agente) — reemplaza a: (nada)

### Cierra

- cierra: P-robustez-panel-9 — T1: get_orden quita un solo guion; `?orden=--creado` da 200 en los 6 listados
- cierra: P-robustez-panel-10 — T1: get_busqueda descarta el NUL de `q`
- cierra: P-diseno-panel-1 — T8: `keyboard: false` en el mapa del panel lateral (prueba en navegador en T9)
- cierra: P-diseno-panel-2 — T8: columna Punto sin cortes, insignia separada y selects de servicio a ancho completo
- cierra: P-diseno-panel-3 — T8: filtros de turnos en la fila `.filtros`, con el buscador aparte
- cierra: P-diseno-panel-4 — T8: "Sitio:" dentro de la tarjeta del formulario
- cierra: P-flujo-sitio-2 — T5: la fila ofrece y conserva el servicio desactivado ya asignado
- cierra: P-flujo-sitio-5 — T7: incidencia_asignacion solo si la pendiente ajena incluye el punto
- cierra: P-flujo-sitio-6 — T5 y T10: el resolver y el contrato explican el punto sin servicio
- cierra: P-flujo-sitio-12 — T8: `sitio` de solo lectura en una pendiente con ítems
- cierra: P-flujo-sitio-14 — T5 y T7: un punto inactivo no se programa y una revisión con servicio dado de baja da 400
- cierra: P-catalogo-stock-2 — T7: `productos_aplicados` con parse_float=Decimal y rechazo de NaN e Infinity
- cierra: P-catalogo-stock-3 — T4: modo_unidad bloqueado con movimientos en el panel y unidades de solo lectura en el admin
- cierra: P-catalogo-stock-4 — T4: TipoServicio.save reintenta ante el choque de slug
- cierra: P-catalogo-stock-6 — T7 y T10: `productos_aplicados` como arreglo de objetos con encoding application/json
- cierra: P-multiempresa-6 — T2 y T6: el esquema y la documentación exigen sesión de empresa activa
- cierra: P-multiempresa-20 — T3: el formulario del admin lleva a errores generales los de campos ausentes
- cierra: P-multiempresa-28 — T3: el admin valida la restricción (empresa, slug) con empresa de solo lectura
- cierra: P-multiempresa-30 — T3: EmpresaAdmin procesa el logo con procesar_logo
- cierra: P-multiempresa-38 — T3: el mensaje indica cambiar el rol y el error ya no da 500
- cierra: P-multiempresa-63 — resuelto antes de este plan: una referencia a plataforma cuenta como de otra empresa (apps/empresas/models.py)
- cierra: P-multiempresa-68 — T3: error general en lugar de 500 con una referencia de solo lectura
- cierra: P-multiempresa-72 — resuelto antes de este plan: docs/contrato-api.md documenta el 401 sin `code`
- cierra: P-multiempresa-73 — resuelto antes de este plan: docs/contrato-api.md dice que una visita inexistente da 404
- cierra: P-multiempresa-74 — T2: plataforma no obtiene token (401)
- cierra: P-multiempresa-75 — aceptado sin cambios por el usuario (decisión de este plan)
- cierra: P-multiempresa-81 — T2: plataforma no renueva token (401)
- cierra: P-multiempresa-85 — T5: la clave de caché de geocodificación lleva la empresa
- cierra: P-multiempresa-86 — aceptado sin cambios por el usuario (decisión de este plan)
- cierra: P-api-movil-1 — T2: non_field_errors anidados se aplanan con su ruta
- cierra: P-api-movil-2 — T2 y T6: `__all__` va a detalle, el anidado conserva su ruta y una ruta inexistente bajo /api/ da 404 JSON
- cierra: P-api-movil-6 — T2: el 429 del balde lleva Retry-After
- cierra: P-api-movil-11 — T5: un código QR mal formado da el 404 JSON de la API
- cierra: P-contrato-app-9 — T2, T7 y T10: 400 de auth/token/ y de revisiones documentados; 415 y 200 ya estaban; POST visitas/ ya no existe
- cierra: P-cierre-puntos-15 — T2, T5 y T10: 401 y 429 documentados por el hook y POST sitios/ sin el 404 imposible
- cierra: P-puntos-control-19 — T5 y T10: el contrato explica el punto con plano sin coordenadas
- cierra: P-saneamiento-5 — T5: la descripción del resolver menciona el cliente inactivo
- cierra: P-ajustes-flujo-2 — T7: _pendiente_para sin el parámetro bloquear
- cierra: P-ajustes-flujo-3 — T7: tests de visita_destino con visitas de otro empleado y de otro sitio
- cierra: P-ajustes-flujo-4 — T7: servicio_para_punto precarga los campos del servicio
- cierra: P-metodo-v2-25 — resuelto antes de este plan: commit-msg corre con `py -3 -I` y commit_msg.py usa sys.path.append
- cierra: P-metodo-v2-26 — resuelto antes de este plan: commit_msg.py toma la primera línea no vacía
- cierra: P-multiempresa-1 — ya resuelto: apps/empresas/consultas.py:109-119 quita la marca si una parte no es segura
- cierra: P-multiempresa-2 — ya resuelto: apps/empresas/consultas.py:154-158 aiterator sobrescrito y verifica
- cierra: P-multiempresa-3 — ya resuelto: apps/empresas/consultas.py:79 exige not instancia._state.adding
- cierra: P-multiempresa-4 — ya resuelto: .env.example:22-23 documenta CORREO_PLATAFORMA; EMPRESA_GUARDIA ya no está en settings
- cierra: P-multiempresa-5 — ya resuelto: apps/empresas/logos.py:12 MAX_PIXELES = 16_000_000
- cierra: P-multiempresa-8 — ya resuelto: apps/empresas/consultas.py:90-108 re-envuelve si el resultado no es EmpresaQuerySet
- cierra: P-multiempresa-9 — ya resuelto: apps/empresas/consultas.py:43-44 documenta la exención por Prefetch
- cierra: P-multiempresa-11 — ya resuelto: apps/empresas/tests/test_consultas.py:153-184 cubren xor, intersection, difference, cadenas y slice
- cierra: P-multiempresa-12 — ya resuelto: apps/empresas/consultas.py:88-89 chequeo de identidad antes del re-envoltorio
- cierra: P-multiempresa-13 — ya resuelto: apps/empresas/consultas.py:104 copia _known_related_objects
- cierra: P-multiempresa-15 — ya resuelto: apps/empresas/models.py:141-146 empresa efectiva = la del padre si falta
- cierra: P-multiempresa-16 — ya resuelto: apps/empresas/models.py:103-111 save() lanza si cambia la empresa
- cierra: P-multiempresa-17 — ya resuelto: apps/visitas/models.py:325 referencias_de_empresa incluye movimiento
- cierra: P-multiempresa-18 — ya resuelto: empresa no nula (apps/empresas/models.py:50-56) y _duplicada filtra por empresa (apps/visitas/services.py:639-646)
- cierra: P-multiempresa-21 — ya resuelto: apps/empresas/models.py:97-105 ignora _state.adding y compara solo si se escribe empresa
- cierra: P-multiempresa-24 — ya resuelto: apps/sitios/models.py:308 usa todos.filter().first(); apps/empresas/models.py:122-127 captura ObjectDoesNotExist
- cierra: P-multiempresa-26 — ya resuelto: apps/accounts/admin.py empresa de solo lectura si el usuario ya la tiene
- cierra: P-multiempresa-29 — ya resuelto: apps/accounts/models.py CheckConstraint: plataforma sin empresa
- cierra: P-multiempresa-32 — ya resuelto: apps/productos/api_views.py:20 EsEmpleado | EsAdministrador
- cierra: P-multiempresa-35 — ya resuelto: apps/accounts/admin.py bloquea empresa de usuarios con empresa
- cierra: P-multiempresa-36 — ya resuelto: apps/accounts/admin.py: el error va a rol si empresa no está en el formulario
- cierra: P-multiempresa-37 — ya resuelto: CheckConstraint en apps/accounts/models.py y full_clean en crear_usuario
- cierra: P-multiempresa-40 — ya resuelto: apps/sitios/estado.py:60-62 usa PuntoControl.objects.de_empresa(empresa)
- cierra: P-multiempresa-41 — ya resuelto: ningún usuario sin empresa salvo plataforma (CheckConstraint) y permisos de rol en la API de productos
- cierra: P-multiempresa-42 — ya resuelto: Visita.empresa no nula: el comando no puede recibir visitas sin empresa
- cierra: P-multiempresa-44 — sin objeto: nota de proceso de multiempresa; PublicoSinEmpresaTests existe (apps/sitios/tests/test_publico.py:37)
- cierra: P-multiempresa-47 — ya resuelto: registrar_revision_demo.py:104-106 filtra por empresa
- cierra: P-multiempresa-50 — ya resuelto: apps/api/serializers.py rechaza plataforma en get_token (T2)
- cierra: P-multiempresa-55 — ya resuelto: apps/visitas/tests/test_comandos.py:117-121 borra media_temporal, no MEDIA_ROOT
- cierra: P-multiempresa-57 — ya resuelto: docs/despliegue.md:56-57 documenta --all y sin_filtro_empresa()
- cierra: P-multiempresa-62 — ya resuelto: apps/empresas/models.py:118-120 _empresa_original solo se actualiza si se escribió empresa
- cierra: P-multiempresa-69 — ya resuelto: docs/despliegue.md:50 excluye sessions, token_blacklist, contenttypes y auth.permission
- cierra: P-multiempresa-77 — ya resuelto: docs/despliegue.md:50 comando completo con exclusiones y -o
- cierra: P-multiempresa-78 — ya resuelto: CLAUDE.md:18 y convenciones-proyecto/SKILL.md:218 listan los usos permitidos de sin_filtro_empresa
- cierra: P-multiempresa-80 — ya resuelto: docs/01-modelo-y-arquitectura.md:231 incluye padre y referencias_de_empresa
- cierra: P-demo-cliente-10 — ya resuelto: .claude/hooks/worktree-integrar.sh:192 borra la rama desde el worktree destino, con aviso
- cierra: P-nombre-empresa-prod-2 — sin objeto: las líneas con forma inválida de planes ajenos se aceptan sin editar (decisión del usuario de este plan)
- cierra: P-protocolo-decisiones-1 — sin objeto: decisión del usuario: docs/ARRANQUE.md hace de kit (docs/decisiones.md)
- cierra: P-metodo-v2-2 — ya resuelto: commit-msg y pre-push instalados (decisión del 2026-11-13 en docs/decisiones.md)
- cierra: P-metodo-v2-3 — ya resuelto: línea (usuario) con hash para multiempresa en docs/decisiones.md
- cierra: P-metodo-v2-4 — sin objeto: multiempresa cerrado en main; su criterio T1 ya no corre
- cierra: P-metodo-v2-5 — ya resuelto: .claude/hooks/worktree-integrar.sh:192 branch -d desde el worktree destino, con aviso
- cierra: P-metodo-v2-10 — ya resuelto: .claude/agents/implementador.md:62 el nombre sale de Empresa.nombre
- cierra: P-metodo-v2-11 — ya resuelto: CLAUDE.md exige solo la línea (usuario) con hash, como verificar.py
- cierra: P-metodo-v2-12 — ya resuelto: .claude/settings.json Stop usa recibo_pendiente.py; test_permisos.py lo verifica
- cierra: P-metodo-v2-16 — sin objeto: CLAUDE.md: la regla de datos de empresa es la 5; la 7 ya no existe
- cierra: P-metodo-v2-17 — ya resuelto: .claude/hooks/verificar.py:219-221 con contrato modificado sin aprobación no ejecuta criterios
- cierra: P-metodo-v2-18 — ya resuelto: .claude/hooks/guardia_bash.py:113-118 es_prefijo cubre abreviaturas de --no-verify y --amend
- cierra: P-metodo-v2-19 — ya resuelto: .claude/hooks/commit_msg.py:86-102 exige plan, recibo del HEAD y rutas del commit
- cierra: P-metodo-v2-20 — ya resuelto: .claude/hooks/verificar.py:28 todo y cierre miran archivos sin seguimiento
- cierra: P-metodo-v2-23 — ya resuelto: .claude/hooks/worktree-integrar.sh:168-169 suite de Django solo si la subtarea toca rutas de Django
- cierra: P-metodo-v2-27 — sin objeto: aceptado por el usuario como límite del control local (docs/decisiones.md, 2026-11-13)
- cierra: P-metodo-v2-28 — sin objeto: aceptado por el usuario como límite del control local (docs/decisiones.md, 2026-11-13)
- cierra: P-metodo-v2-29 — sin objeto: aceptado por el usuario como límite del control local (docs/decisiones.md, 2026-11-13)
- cierra: P-robustez-datos-6 — sin objeto: sin Proyecto en apps/ (grep vacío)
- cierra: P-robustez-panel-3 — ya resuelto: .claude/hooks/worktree-integrar.sh:192 usa git -C "$ruta_dest" branch -d
- cierra: P-robustez-panel-11 — ya resuelto: apps/visitas/panel_views.py:215-218 trae HISTORIAL_MAXIMO+1 y compara el último
- cierra: P-robustez-panel-12 — ya resuelto: apps/visitas/templatetags/visitas_ui.py:23-26 y panel_views.py:121-124 sin filtro de estado
- cierra: P-flujo-sitio-3 — ya resuelto: apps/panel/tests/test_inicio.py:17,69 arma el nombre sin la palabra prohibida
- cierra: P-flujo-sitio-4 — sin objeto: paso de T5 de flujo-sitio ya ejecutado; migraciones rehechas en 0001_initial

### Etiquetas

- etiqueta: P-multiempresa-7 → despliegue
- etiqueta: P-multiempresa-10 → despues
- etiqueta: P-multiempresa-14 → despues
- etiqueta: P-multiempresa-19 → despues
- etiqueta: P-multiempresa-22 → despues
- etiqueta: P-multiempresa-23 → despues
- etiqueta: P-multiempresa-25 → despues
- etiqueta: P-multiempresa-27 → despues
- etiqueta: P-multiempresa-31 → despues
- etiqueta: P-multiempresa-33 → despues
- etiqueta: P-multiempresa-34 → despues
- etiqueta: P-multiempresa-39 → despues
- etiqueta: P-multiempresa-43 → despues
- etiqueta: P-multiempresa-45 → despues
- etiqueta: P-multiempresa-46 → despues
- etiqueta: P-multiempresa-48 → despues
- etiqueta: P-multiempresa-49 → despues
- etiqueta: P-multiempresa-51 → expo
- etiqueta: P-multiempresa-52 → despues
- etiqueta: P-multiempresa-53 → despues
- etiqueta: P-multiempresa-54 → despliegue
- etiqueta: P-multiempresa-56 → despues
- etiqueta: P-multiempresa-58 → despues
- etiqueta: P-multiempresa-59 → despues
- etiqueta: P-multiempresa-60 → despues
- etiqueta: P-multiempresa-61 → despues
- etiqueta: P-multiempresa-64 → despues
- etiqueta: P-multiempresa-65 → despues
- etiqueta: P-multiempresa-66 → despues
- etiqueta: P-multiempresa-67 → despues
- etiqueta: P-multiempresa-70 → despues
- etiqueta: P-multiempresa-71 → despues
- etiqueta: P-multiempresa-76 → despues
- etiqueta: P-multiempresa-79 → despues
- etiqueta: P-multiempresa-82 → despues
- etiqueta: P-multiempresa-83 → expo
- etiqueta: P-multiempresa-84 → despues
- etiqueta: P-demo-cliente-1 → despliegue
- etiqueta: P-demo-cliente-2 → despues
- etiqueta: P-demo-cliente-3 → despliegue
- etiqueta: P-demo-cliente-4 → despliegue
- etiqueta: P-demo-cliente-5 → despliegue
- etiqueta: P-demo-cliente-6 → despliegue
- etiqueta: P-demo-cliente-7 → despliegue
- etiqueta: P-demo-cliente-9 → despliegue
- etiqueta: P-demo-cliente-11 → despues
- etiqueta: P-demo-cliente-12 → despues
- etiqueta: P-demo-cliente-13 → despliegue
- etiqueta: P-nombre-empresa-prod-1 → despues
- etiqueta: P-nombre-empresa-prod-4 → despues
- etiqueta: P-separacion-web-1 → empresa
- etiqueta: P-separacion-web-2 → despliegue
- etiqueta: P-separacion-web-6 → despues
- etiqueta: P-separacion-web-7 → despues
- etiqueta: P-separacion-web-8 → despues
- etiqueta: P-separacion-web-9 → despues
- etiqueta: P-protocolo-decisiones-2 → despues
- etiqueta: P-metodo-v2-1 → despues
- etiqueta: P-metodo-v2-6 → despues
- etiqueta: P-metodo-v2-7 → despues
- etiqueta: P-metodo-v2-8 → despues
- etiqueta: P-metodo-v2-9 → despues
- etiqueta: P-metodo-v2-13 → despues
- etiqueta: P-metodo-v2-14 → despues
- etiqueta: P-metodo-v2-15 → despues
- etiqueta: P-metodo-v2-21 → despues
- etiqueta: P-metodo-v2-22 → despues
- etiqueta: P-metodo-v2-24 → despues
- etiqueta: P-robustez-datos-2 → despues
- etiqueta: P-robustez-datos-5 → despues
- etiqueta: P-robustez-datos-10 → despues
- etiqueta: P-robustez-datos-12 → despues
- etiqueta: P-robustez-panel-1 → despues
- etiqueta: P-robustez-panel-2 → despues
- etiqueta: P-robustez-panel-6 → despues
- etiqueta: P-robustez-panel-14 → despues
- etiqueta: P-catalogo-stock-5 → despues
- etiqueta: P-catalogo-stock-7 → expo
- etiqueta: P-catalogo-stock-9 → despues
- etiqueta: P-ajustes-flujo-1 → despues
- etiqueta: P-flujo-sitio-7 → despues
- etiqueta: P-flujo-sitio-9 → despues
- etiqueta: P-flujo-sitio-13 → despues
- etiqueta: P-flujo-sitio-15 → despliegue
- etiqueta: P-diseno-panel-5 → despues
- etiqueta: P-diseno-panel-6 → despues
- etiqueta: P-diseno-panel-7 → despues
- etiqueta: P-diseno-panel-8 → despues
- etiqueta: P-diseno-panel-9 → despues
- etiqueta: P-robustez-listados-1 → despues
- etiqueta: P-robustez-listados-2 → despues
- etiqueta: P-robustez-listados-3 → despues
- etiqueta: P-robustez-listados-4 → despues
- etiqueta: P-robustez-listados-5 → expo
- etiqueta: P-robustez-listados-6 → despues
- etiqueta: P-robustez-listados-7 → despliegue
- etiqueta: P-robustez-listados-8 → expo
- etiqueta: P-robustez-listados-9 → despues
- etiqueta: P-robustez-listados-10 → despues
- etiqueta: P-robustez-listados-11 → despues
- etiqueta: P-robustez-listados-12 → despliegue
- etiqueta: P-robustez-listados-13 → despues
