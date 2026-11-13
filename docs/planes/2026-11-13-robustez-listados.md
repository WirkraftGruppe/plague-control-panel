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
| T1 | pendiente | | |
| T2 | pendiente | | |
| T3 | pendiente | | |
| T4 | pendiente | | |
| T5 | pendiente | | |
| T6 | pendiente | | |
| T7 | pendiente | | |
| T8 | pendiente | | |
| T9 | pendiente | | |
| T10 | pendiente | | |
| T11 | pendiente | | |
| T12 | pendiente | | |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-13 17:31 | plan | 4 | 0 | 6 |
| 2026-11-13 18:30 | plan | 0 | 0 | 2 |

Auditoría: pendiente
Hallazgos: —

### Decisiones del plan

## Pendientes que deja este plan

### Problemas

### Decisiones

- 2026-11-13 — P-multiempresa-75 (mensaje distinto para empresa inactiva en el token) y P-multiempresa-86 (el alta de usuarios revela un nombre de otra empresa) se aceptan sin cambios — decisión de alcance de `robustez-listados` — (usuario) — reemplaza a: (nada)
- 2026-11-13 — `incidencia_asignacion` se marca solo si una visita pendiente de otro empleado incluye ese punto — menos ruido con varios operarios por sitio — (usuario) — reemplaza a: (nada)
- 2026-11-13 — un punto inactivo no se programa y una revisión con un servicio dado de baja da 400; un servicio desactivado ya asignado se conserva al editar la fila — cierra la decisión de producto de P-flujo-sitio-14 — (usuario) — reemplaza a: (nada)

- 2026-11-13 — las líneas con forma inválida de planes ajenos (`demo-cliente`, `demo-portatil`, `separacion-web`, `multiempresa`) no se editan: lo vigente se re-registra o se cierra desde `robustez-listados` y los 10 avisos de forma se aceptan — los planes de otro dueño no se tocan (convenciones-proyecto § Tabla de propiedad) — (usuario) — reemplaza a: (nada)

### Cierra
