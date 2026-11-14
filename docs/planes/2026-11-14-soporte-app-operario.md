# Plan: soporte del servidor para la app del operario

- **slug**: `soporte-app-operario`
- **fecha**: 2026-11-14
- **objetivo**: la app del operario muestra el nombre y el logo de su empresa y registra una estación que no pudo revisar sin que cuente como revisión; el administrador ve esos reportes en el panel, da de alta decenas de puntos numerados de una vez e imprime sus QR filtrando por sector y por "sin imprimir".
- **fuera de alcance**: abrir una visita o registrar una revisión sin QR; alta de sitios o puntos desde la app; cambios visuales fuera de las pantallas tocadas; pendientes con etiqueta `despliegue` o `despues`.
- **áreas**: panel | api | dominio (modelos y servicios)
- **ruta**: completo
- **seguridad**: sí — endpoint nuevo de la API con fotos y coordenadas del empleado, el logo de la empresa servido por la API, una vista del panel que sirve fotos, y el aislamiento por empresa de todo eso; corre `auditor-seguridad`.

## Contexto mínimo

- Cada estación lleva su propio QR (un punto = una estación), así que un sitio tiene decenas de puntos; el operario ve el logo de su empresa en la app (decisiones del usuario). Una estación faltante o con el código ilegible no se puede escanear y hoy no hay cómo registrarlo.
- El logo se procesa en `apps/empresas/logos.py` y solo lo sirve el panel (`EmpresaLogoView`, `apps/empresas/panel_views.py:41`, `AdministradorRequeridoMixin`).
- Las revisiones entran por `CrearRevisionView` (`apps/visitas/api_views.py:138`: 413 por `MAX_BYTES_PEDIDO`, throttle `crear_visita`) y `registrar_revision` (`apps/visitas/services.py:649`: `cliente_uuid` → `RevisionDuplicada`, bloqueo Sitio, Visita); la foto pasa por `procesar_imagen` (`apps/visitas/imagenes.py:25`) y `validar_tamano_foto` (`apps/visitas/serializers.py:18`). `cerrar_visita` (`services.py:764`) exige al menos una revisión; `actualizar_vencimiento` (`services.py:525`) solo mira `Revision`.
- "Incidencias sin revisar" es una marca de la visita (`incidencia_revisada_en`, `marcar_incidencia_revisada`, `services.py:1041`, exige visita realizada), filtrada en tres lugares: `apps/visitas/templatetags/visitas_ui.py:11`, `apps/visitas/panel_views.py:184` y `apps/sitios/panel_views.py:197`.
- No existe impresión de QR en lote: solo `PuntoQRPng` (`apps/sitios/panel_views.py:508`, `?inline=1`). `PuntoControl.qr_impreso_el` es una fecha cargada a mano; `PuntoControl.sector` es texto libre.
- Decisiones del usuario (2026-11-14): la hoja de QR en lote es por sitio, filtra por sector y "sin imprimir" y tiene un botón que fija `qr_impreso_el = hoy` en los puntos mostrados; los puntos no revisados se dan por vistos con la marca de incidencia de la visita.
- Referencias: `docs/01-modelo-y-arquitectura.md` (Visitas y revisiones, multiempresa), `docs/contrato-api.md`.

## Olas

Solo T1 crea migraciones (`visitas`). `apps/api/tests/test_contrato_doc.py` exige que la tabla de `docs/contrato-api.md` coincida con las rutas resueltas, y `worktree-integrar.sh` deshace un merge con la suite en rojo; por eso T1 y T2 no cablean sus rutas (sus tests llaman a las vistas) y T3 las cablea y actualiza el contrato en el mismo commit.

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | visitas (T1), empresas (ninguna) |
| 2 | T4, T5, T6, T7 (integración y cierre) | sitios, visitas (ninguna) |

## Subtareas

### T1 — Reporte de punto no revisado: modelo, servicios y vista de la API

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/migrations/0002_punto_no_revisado.py`, `apps/visitas/services.py`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/admin.py`, `apps/visitas/tests/test_no_revisados.py`, `apps/visitas/tests/test_api_mis_turnos.py`, `apps/empresas/tests/test_no_nula.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/`, `apps/visitas/api_urls.py`, `docs/`, migraciones existentes, archivos de otras apps (salvo `apps/empresas/tests/test_no_nula.py`)
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Serializers y § Throttling; `.agents/skills/django-security/SKILL.md` § Authorization
- **Worktree**: sí
- **Presupuesto**: 750 líneas agregadas
- **Qué hacer**:
  - Modelo `PuntoNoRevisado(ModeloDeEmpresa)` en `apps/visitas/models.py`, `padre_de_empresa = "visita"`, `referencias_de_empresa = ("punto",)`: `visita` (FK, `related_name="no_revisados"`), `punto` (FK a `sitios.PuntoControl`, PROTECT), `motivo` (TextChoices `falta_estacion`, `codigo_ilegible`, `sin_acceso`, `otro`), `detalle` (opcional), `latitud`, `longitud`, `precision_m`, `distancia_m` opcionales (mismos tipos que `Revision`), `foto` (ImageField opcional, nombre aleatorio como `ruta_foto`), `foto_codigo` (UUID único), `cliente_uuid` (UUID, `null=True, blank=True` como `Revision.cliente_uuid`; obligatorio en el serializer y el servicio), `creado`. Restricciones únicas `(empresa, cliente_uuid)` y `(visita, punto)`. Sin historial de coordenadas. Migración con `makemigrations visitas --name punto_no_revisado`. Admin de solo lectura. `test_no_nula.py` pasa de 13 a 14 modelos de empresa.
  - Servicio `registrar_no_revisado(*, empleado, visita_pk, punto, motivo, detalle="", latitud=None, longitud=None, precision_m=None, foto=None, cliente_uuid)`: `cliente_uuid` ya usado en la empresa → `NoRevisadoDuplicado` (como `RevisionDuplicada`, también en la carrera de `IntegrityError`); bloquea Sitio y Visita filtrando por la empresa del empleado, `pk` y `empleado`; visita inexistente, ajena o de otra empresa → `VisitaNoEncontrada` (404); visita propia no abierta → `ValidationError` "La visita no está abierta" (400, como `registrar_revision`); punto de otro sitio, inactivo o ya reportado en la visita → `ValidationError`; la foto pasa por `procesar_imagen` dentro de `_transaccion_con_archivos`; distancia con `ubicacion.verificar` si hay coordenadas. No crea `Revision`, no llama a `actualizar_vencimiento` y no cambia `cerrar_visita`.
  - `condicion_incidencia_sin_revisar()` (un `Q` sobre `Visita`): `incidencia_revisada_en` nulo y (`incidencia=True` o `estado=realizada` con algún `PuntoNoRevisado`). `marcar_incidencia_revisada` acepta una visita realizada que solo tiene reportes.
  - Vista `ReportarNoRevisadoView` en `api_views.py` (sin ruta; la cablea T3 como `visitas/<int:pk>/no-revisados/`, kwarg `pk`): multipart, `EsEmpleado | EsAdministrador`, `throttle_scope = "crear_visita"`, 413 antes de leer el cuerpo como `CrearRevisionView`; busca la visita (`de_empresa`, `pk`, `empleado`) **antes** de validar el cuerpo, como `CerrarVisitaView`, para que una visita de otra empresa dé 404 aun con el cuerpo vacío; serializer de escritura con campos explícitos (`punto`, `motivo`, `detalle`, `latitud`, `longitud`, `precision_m`, `foto` con `validar_tamano_foto`, `cliente_uuid` obligatorio); 201 con el reporte sin coordenadas ni foto; 404 con `VisitaNoEncontrada`; 409 con el duplicado, sin datos de otro empleado. `extend_schema` con 201, 400, 404, 409 y 413.
  - `ItemTurnoSerializer` suma `no_revisado` (motivo o `null`), calculado en `VisitaActivaSerializer.get_items`, con `no_revisados` en el `prefetch_related` de `MisVisitasView` y de `AbrirVisitaView` (que usa el mismo serializer). `test_api_mis_turnos.py` suma `no_revisado` al ítem esperado.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_reporte_en_visita_abierta_propia_da_201 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_ajena_inexistente_o_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_de_otra_empresa_con_cuerpo_vacio_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_propia_cerrada_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_punto_de_otro_sitio_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_punto_inactivo_o_ya_reportado_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_respuesta_sin_coordenadas_ni_foto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_reporte_no_crea_revision_ni_cambia_vencimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_solo_con_reportes_no_se_cierra --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_mismo_cliente_uuid_no_duplica --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_409_no_expone_datos_de_otro_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_foto_se_procesa_y_respeta_el_limite --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_mis_visitas_trae_no_revisado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.IncidenciaNoRevisadoTests.test_condicion_cuenta_solo_visitas_realizadas_con_reporte --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.IncidenciaNoRevisadoTests.test_marcar_revisada_acepta_visita_solo_con_reportes --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.empresas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 750 --subtarea T1`

### T2 — Datos y logo de la empresa para la API

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/empresas/api_views.py`, `apps/empresas/api_urls.py`, `apps/empresas/serializers.py`, `apps/empresas/tests/test_api.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/api/`, `apps/empresas/models.py`, `apps/empresas/panel_views.py`, `docs/`, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Permissions
- **Worktree**: sí
- **Presupuesto**: 250 líneas agregadas
- **Qué hacer**:
  - `apps/empresas/api_urls.py` (`app_name = "empresas"`): `me/empresa/` (`name="me"`) y `empresas/<int:pk>/logo/` (`name="logo"`). No se cablea en `apps/api/urls.py` (lo hace T3). La URL del logo en la respuesta sale de `request.build_absolute_uri(reverse("api:empresas:logo", args=[pk]))`. Los tests de T2 usan `@override_settings(ROOT_URLCONF=...)` con una urlconf de prueba en el propio módulo de tests que monta `apps.empresas.api_urls` bajo `api/v1/` con los namespaces `api` y `empresas`.
  - `GET me/empresa/` (`EsEmpleado | EsAdministrador`): `{"nombre": empresa.nombre, "logo": <URL absoluta del logo> | null}` con la empresa de `empresa_de(request)`.
  - `GET empresas/<pk>/logo/` (`EsEmpleado | EsAdministrador`): si `pk` no es la empresa del usuario o no hay logo, 404; si no, `FileResponse` con las cabeceras de `EmpresaLogoView` (`private, no-store`, `nosniff`) y un renderer que no negocia `Accept`, como `FotoView`.
  - `extend_schema` en las dos vistas.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_me_empresa_devuelve_nombre_y_logo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_me_empresa_sin_logo_devuelve_null --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_logo_propio_lo_ve_un_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_logo_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_logo_lleva_cabeceras_privadas --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_plataforma_da_403 --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`

### T3 — Integración ola 1, rutas y contrato (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Puede tocar**: `apps/api/urls.py`, `apps/visitas/api_urls.py`, `apps/api/tests/test_contrato_doc.py`, `apps/api/tests/test_routers.py`, `apps/api/tests/test_aislamiento.py`, `docs/contrato-api.md`, `config/tests/test_soporte_app_operario.py`
- **Transversal**: T3 es la subtarea transversal de `apps/api/` de este plan (tabla de propiedad).
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/soporte-app-operario` de cada subtarea, no los informes.
  2. Desde la raíz (rama `plan/soporte-app-operario`), `bash .claude/hooks/worktree-integrar.sh soporte-app-operario T<n> plan/soporte-app-operario <rutas>` por T1 y T2, de a una, con `verificar.py tarea` tras cada integración.
  3. Un commit `T3:` que deja la suite en verde: `path("visitas/<int:pk>/no-revisados/", …)` en `apps/visitas/api_urls.py`; `path("", include("apps.empresas.api_urls"))` en `apps/api/urls.py`; las tres filas y sus secciones en `docs/contrato-api.md` (cuerpo, respuestas, errores, `no_revisado` en `me/visitas` y en `visitas/abrir/`, `Actualizado:`); el conteo de `test_contrato_doc.py` de 18 a 21; `empresas` en `APPS` de `test_routers.py`; las dos rutas con parámetro en `OBJETO_POR_RUTA` de `test_aislamiento.py`; tests de integración contra las URL reales.
  4. Crear los worktrees de T4, T5 y T6 desde `plan/soporte-app-operario`.
- **Presupuesto**: 250 líneas agregadas
- **Criterios**:
  - `[cmd]` `git log --oneline plan/soporte-app-operario | grep -q "T1: integra soporte-app-operario-T1"`
  - `[cmd]` `git log --oneline plan/soporte-app-operario | grep -q "T2: integra soporte-app-operario-T2"`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_soporte_app_operario.IntegracionSoporteAppTests.test_reporte_no_revisado_por_url_da_201 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_soporte_app_operario.IntegracionSoporteAppTests.test_me_empresa_por_url --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_soporte_app_operario.IntegracionSoporteAppTests.test_logo_de_otra_empresa_por_url_da_404 --keepdb`
  - `[grep-1]` `grep -n "no-revisados" docs/contrato-api.md`
  - `[grep-1]` `grep -n "me/empresa" docs/contrato-api.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas apps.visitas config --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T3`

### T4 — Sitios: alta múltiple, hoja de QR y reportes en la ficha del sitio

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/sitios/panel_forms.py`, `apps/sitios/panel_views.py`, `apps/sitios/panel_urls.py`, `apps/sitios/services.py`, `apps/sitios/templates/sitios/panel/puntos_alta_multiple.html`, `apps/sitios/templates/sitios/panel/hoja_qr.html`, `apps/sitios/templates/sitios/panel/_pestana_puntos.html`, `apps/sitios/templates/sitios/panel/listado.html`, `apps/sitios/tests/test_alta_multiple.py`, `apps/sitios/tests/test_hoja_qr.py`, `apps/sitios/tests/test_no_revisados_sitio.py`
- **No puede tocar**: `docs/planes/`, `config/`, `apps/sitios/models.py`, `apps/sitios/migrations/`, `apps/panel/urls.py`, `templates/`, `static/`, `docs/`, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Task 1 (1.4 URL Configuration Patterns); `.agents/skills/frontend-design/SKILL.md` solo para la hoja de impresión
- **Worktree**: sí
- **Presupuesto**: 600 líneas agregadas
- **Qué hacer**:
  - `PuntosAltaMultipleForm`: `cantidad` (1 a 100), `prefijo` (obligatorio), `numero_inicial` (≥ 0), `sector` (opcional), `servicio` (opcional, queryset `TipoServicio.objects.de_empresa(empresa)`), `frecuencia_dias` y `proximo_vencimiento` opcionales.
  - Servicio `crear_puntos_numerados(sitio, *, cantidad, prefijo, numero_inicial, sector, servicio, frecuencia_dias, proximo_vencimiento)` en `apps/sitios/services.py`: en `transaction.atomic`, crea `"<prefijo> <n>"` para `n` de `numero_inicial` a `numero_inicial + cantidad - 1` con `save()` por punto (no `bulk_create`), `orden` a continuación del último del sitio y sitio activo exigido como en `crear_punto_en_campo` (`apps/sitios/services.py:190`, `_exigir_activo`; reutilizar esa lógica); devuelve la lista.
  - Vista `PuntosAltaMultiple` (`<pk>/puntos/nuevos/`, `AdministradorRequeridoMixin`, sitio por `de_empresa`) y enlace en `_pestana_puntos.html`.
  - Vista `HojaQR` (`<pk>/qr/`): puntos activos del sitio en una grilla de `<img>` que apuntan a `panel:sitios:punto_qr_png` con `?inline=1`, CSS `@media print`; filtros GET `sector` (exacto) y `sin_imprimir=1` (`qr_impreso_el` nulo); un POST con los mismos filtros fija `qr_impreso_el = localdate()` en los puntos mostrados con `save()` por punto y redirige a la hoja. Enlace en `_pestana_puntos.html`.
  - Pestaña de puntos de la ficha del sitio: los 20 reportes `PuntoNoRevisado` más recientes de puntos del sitio (`de_empresa`; punto, motivo, fecha y enlace al turno). `SitioListado._incidencias` usa `condicion_incidencia_sin_revisar()` de `apps/visitas/services.py`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_doce_puntos_desde_cinco_con_servicio_y_frecuencia --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_ciento_uno_da_error_de_formulario --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_servicio_de_otra_empresa_no_se_acepta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_sitio_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_puntos_siguen_el_orden_de_los_existentes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_filtra_por_sector --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_filtra_sin_imprimir --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_marcar_impresos_fija_la_fecha_solo_en_los_filtrados --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_sitio_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_marcar_impresos_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_no_revisados_sitio.NoRevisadosSitioTests.test_ficha_del_sitio_lista_los_reportes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_no_revisados_sitio.NoRevisadosSitioTests.test_inicio_lista_la_visita_en_incidencias --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T4`

### T5 — Visitas: reportes en la ficha del turno y en el contador

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `apps/visitas/panel_views.py`, `apps/visitas/panel_urls.py`, `apps/visitas/templatetags/visitas_ui.py`, `apps/visitas/templates/visitas/panel/ficha.html`, `apps/visitas/templates/visitas/panel/_no_revisados.html`, `apps/visitas/tests/test_panel_no_revisados.py`, `apps/panel/tests/test_acceso.py`
- **Transversal**: T5 es la subtarea transversal de `apps/panel/` de este plan (solo `test_acceso.py`).
- **No puede tocar**: `docs/planes/`, `config/`, `apps/visitas/models.py`, `apps/visitas/services.py`, `apps/visitas/migrations/`, `apps/panel/urls.py`, `templates/`, `static/`, `docs/`, archivos de otras apps
- **Skill a leer antes**: `.agents/skills/django-security/SKILL.md` § Authorization
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas
- **Qué hacer**:
  - El tag `incidencias_sin_revisar` y `ListadoVisitas` usan `condicion_incidencia_sin_revisar()` de `apps/visitas/services.py`; en `ListadoVisitas`, en sus tres usos: el filtro GET `incidencia=sin_revisar` (`panel_views.py:121-124`), el grupo `sin_revisar` (`:186-188`) y el `exclude` de los grupos (`:189`).
- `test_acceso.py`: la ruta de la foto en `UUID_POR_RUTA`, con un `PuntoNoRevisado` real entre los objetos del test.
  - Ficha del turno: bloque "Puntos no revisados" (punto, motivo, detalle, enlace a la foto) en el parcial `_no_revisados.html`; el botón "Marcar como revisada" aparece también cuando la visita realizada solo tiene reportes.
  - Vista `FotoNoRevisado` (`no-revisados/<uuid:codigo>/foto/`, `AdministradorRequeridoMixin`, `PuntoNoRevisado.objects.de_empresa(request.empresa)`; 404 si no existe, es de otra empresa o no tiene foto; `private, no-store` y `nosniff`).
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_contador_cuenta_visita_realizada_con_reporte --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_visita_abierta_con_reporte_no_cuenta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_marcar_revisada_la_saca_del_contador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_ficha_del_turno_lista_los_reportes --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_foto_de_reporte_de_otra_empresa_da_404 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_empleado_no_ve_la_foto --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T5`

### T6 — Doc 01 y openapi

- **Ola**: 2
- **Depende de**: T3
- **Puede tocar**: `docs/01-modelo-y-arquitectura.md`, `docs/api/openapi-v1.yaml`
- **No puede tocar**: `docs/planes/`, `docs/contrato-api.md`, `apps/`, `config/`
- **Skill a leer antes**: ninguna (documentación)
- **Worktree**: sí
- **Presupuesto**: 400 líneas agregadas (el yaml regenerado cuenta)
- **Qué hacer**: en el doc 01, el modelo `PuntoNoRevisado` y la regla: no es revisión, no mueve el vencimiento, no habilita el cierre y se da por visto con la marca de incidencia de la visita; las dos rutas de `empresas` en la sección de la API. Regenerar `docs/api/openapi-v1.yaml` con `manage.py spectacular --validate --file docs/api/openapi-v1.yaml`.
- **Criterios**:
  - `[grep-1]` `grep -n "PuntoNoRevisado" docs/01-modelo-y-arquitectura.md`
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T6`

### T7 — Integración ola 2 y cierre (principal)

- **Ola**: 2 (después de verificar T4, T5 y T6)
- **Depende de**: T4, T5, T6
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/soporte-app-operario` de T4, T5 y T6 e integrarlas desde la raíz, de a una, con `verificar.py tarea`.
  2. `verificar.py todo docs/planes/2026-11-14-soporte-app-operario.md`, `revisor` en modo cierre y `auditor-seguridad`; bloqueantes en una ronda y `todo` de nuevo.
  3. `medir_metodo.py --registrar docs/metodo/metricas.md`, `docs/estado.md`, decisiones y un solo commit `cierre: soporte-app-operario`; push de `plan/soporte-app-operario` y PR. La fusión en `main` es del usuario.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/soporte-app-operario | grep -q "T4: integra soporte-app-operario-T4"`
  - `[cmd]` `git log --oneline plan/soporte-app-operario | grep -q "T5: integra soporte-app-operario-T5"`
  - `[cmd]` `git log --oneline plan/soporte-app-operario | grep -q "T6: integra soporte-app-operario-T6"`

## Registro de verificación

commit_base: 2229493

| Tarea | Estado | Commit | Recibo |
|---|---|---|---|
| T1 | pendiente | | |
| T2 | hecha | 2fc1214 | PASA 2026-11-14 |
| T3 | pendiente | | |
| T4 | pendiente | | |
| T5 | pendiente | | |
| T6 | pendiente | | |
| T7 | pendiente | | |

### Revisiones

| Fecha | Modo | Bloqueantes | Decisiones | Menores |
|---|---|---|---|---|
| 2026-11-14 15:53 | plan | 5 | 1 | 4 |

<!-- Plan: test_no_nula (14 modelos y cliente_uuid nulo), test_api_mis_turnos, test_routers, test_aislamiento de la API (y 404 antes de validar el cuerpo) y test_acceso del panel asignados a T1, T3 y T5; decisión del código de una visita cerrada, del usuario (400); menores incorporados: tres usos en ListadoVisitas, orden y sitio activo en el alta múltiple, no_revisado en visitas/abrir, tests de cobertura sumados; el throttle queda como P-soporte-app-operario-1. -->

Auditoría: pendiente
Hallazgos: —

### Decisiones del plan

- T1 — reportes por punto en una visita — uno o varios — uno por `(visita, punto)` — la app muestra un estado por ítem — autónoma — quitar la restricción — decidida por Claude, revisable
- T1 — `cliente_uuid` repetido — 200 con el existente o 409 — 409 — mismo patrón que `RevisionDuplicada` — autónoma — cambiar la vista — decidida por Claude, revisable
- T1 — reporte de un punto ya revisado en la visita — rechazar o aceptar — aceptar — el reporte queda como historial y la revisión manda — autónoma — validar en el servicio — decidida por Claude, revisable
- T1 — cuándo cuenta un reporte como incidencia — siempre o con la visita realizada — realizada — `marcar_incidencia_revisada` exige la visita cerrada — autónoma — cambiar `condicion_incidencia_sin_revisar` — decidida por Claude, revisable
- T2 — URL del logo — `me/empresa/logo/` o `empresas/<pk>/logo/` — `empresas/<pk>/logo/` con 404 si no es la propia — URL estable por empresa para la caché de la app — autónoma — cambiar la ruta — decidida por Claude, revisable

## Pendientes que deja este plan

### Problemas

- P-soporte-app-operario-1 [menor] El scope `crear_visita` (120/hora, `config/settings/base.py:225`) lo comparten abrir, revisiones, cierre y reportes; con sitios de decenas de puntos puede quedar corto para un operario en un día largo. Revisar con datos reales antes del despliegue.

### Decisiones

- 2026-11-14 — un reporte de punto no revisado sobre una visita propia cerrada da 400 "La visita no está abierta", como las revisiones; ajena, de otra empresa o inexistente, 404 — la app distingue un reporte tardío de una visita inexistente — (usuario) — reemplaza a: (nada)

- 2026-11-14 — la impresión de QR en lote es una hoja por sitio con filtros de sector y "sin imprimir" y un botón que marca los mostrados como impresos — el panel solo tenía la descarga por punto — (usuario) — reemplaza a: (nada)
- 2026-11-14 — un punto no revisado se da por visto con la marca de incidencia de la visita — un solo criterio de revisión en el panel — (usuario) — reemplaza a: (nada)

### Cierra
