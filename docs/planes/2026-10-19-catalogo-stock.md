# Plan: catalogo-stock — servicios editables y productos con unidades, envases y stock

- **slug**: `catalogo-stock`
- **fecha**: 2026-10-19
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): catalogo-stock`. No se escribe acá: el
  hash se anota en `## Registro de verificación`.
- **objetivo**: el administrador da de alta y edita tipos de servicio desde el panel; cada producto tiene unidad base, envase y stock calculado por movimientos, y toda revisión (API o carga manual del panel) descuenta lo aplicado convertido a la unidad base.
- **fuera de alcance**: Proyecto, Visita, turnos, fotos y navegación del panel (plan `flujo-sitio`); rediseño visual (plan `diseno-panel`); unidades editables desde el panel, alertas de stock bajo, compras y proveedores; multiempresa; `templates/panel/base.html`; borrado de tipos de servicio.
- **áreas**: panel | api | dominio (productos, servicios, visitas) | docs
- **seguridad**: sí — rutas nuevas del panel que escriben (solo administrador) y cambio de la entrada de `POST /api/v1/revisiones/`; corren `verificador`, `verificador-b` y `auditor-seguridad`.

## Contexto mínimo

- `Producto` (`apps/productos/models.py:4`) no tiene unidad ni stock; el panel tiene listado, alta y edición, sin ficha (`apps/productos/panel_urls.py`). El catálogo de la API es `ProductoSerializer` (`apps/productos/serializers.py:8`) con ETag en `CatalogoView`.
- `TipoServicio` (`apps/servicios/models.py:6`) no genera su slug (lo llenan el admin con `prepopulated_fields`, el fixture y `cargar_demo`); el panel solo lista servicios y edita campos de planilla.
- `ProductoAplicado` (`apps/visitas/models.py:258`) tiene `unidad` (hoy la unidad de la **dosis**) y `cantidad` opcional. Se arma en `_armar_productos` (`apps/visitas/services.py:113`) y lo guardan `registrar_revision` (`:416`, dentro de `_transaccion_con_archivos`) y `registrar_visita_manual` (`:625`). Los errores de producto salen como texto plano "Producto n: …".
- `apps/panel/tests/test_acceso.py` recorre los urlpatterns; `/panel/productos/@PK@/` y `/panel/servicios/@PK@/` ya están en `MODELO_POR_RUTA`, así que las rutas nuevas quedan cubiertas. `RutasProductosTests` (`apps/productos/tests/test_rutas.py:18`) fija la lista exacta de rutas.
- La foto inválida de los tests (`SimpleUploadedFile("x.jpg", b"no es imagen", "image/jpeg")`) falla en `Foto.save()` dentro de la transacción.
- `docs/01-modelo-y-arquitectura.md` § 3.3, 3.8, 3.9 y 4.1; comando del OpenAPI en docs/01:197.

## Decisiones

- 2026-10-19 — `ProductoAplicado.unidad` pasa a ser la unidad de la cantidad; la de la dosis se renombra `unidad_dosis` (texto libre, precargado con `Producto.unidad_dosis_por_defecto`) — no se pierde el dato regulatorio de la dosis — decisión del usuario — reemplaza a: (nada)
- 2026-10-19 — `registrar_visita_manual` descuenta stock igual que la API (mismo movimiento `consumo`, misma transacción) — el stock no depende de por dónde entró la revisión — decisión del usuario — reemplaza a: (nada)
- 2026-10-19 — Las unidades viven en `apps/productos/unidades.py`: diccionario fijo código → (magnitud, factor `Decimal` a la unidad de referencia), `convertir(cantidad, desde, hacia)` cuantiza a `Decimal("0.0001")` con `ROUND_HALF_UP` y lanza `ValueError` si cambia la magnitud — una sola fuente de conversión, sin `float` — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — `MovimientoStock` vive en `productos`; la relación con el producto aplicado es `ProductoAplicado.movimiento` (`OneToOneField` nulo, `PROTECT`, `related_name="producto_aplicado"`) en `visitas`, y el movimiento llega a su aplicado por el acceso inverso — `productos` no depende de `visitas` y el grafo de FK de `convenciones-proyecto` no se invierte (juez-plan, ronda 1) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — Los campos nuevos de `Producto` tienen valor por defecto en el modelo (`unidad_base="unidad"`, `contenido_por_envase=1`, `modo_unidad="unica"`); el formulario del panel los pide igual — el código y los tests que crean productos fuera de `productos` siguen funcionando (juez-plan, ronda 1) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — El stock es `Sum` de `cantidad_base` de los movimientos, sin campo cacheado; envases = stock / `contenido_por_envase`, a 2 decimales sin ceros sobrantes; el stock negativo se marca con la etiqueta de estado de peligro — una sola fuente de verdad — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — `ProductoAplicado.cantidad` pasa a obligatoria y se agrega `cantidad_base` `Decimal(14,4)`; `MovimientoStock.cantidad_base` `Decimal(14,4)`; `Producto.contenido_por_envase` `Decimal(12,4)` > 0; la migración de `visitas` usa un valor por defecto descartable, sin migración de datos — nada está en producción — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — Los errores de producto de la API pasan a anidados (`campos["productos_aplicados.<i>.<campo>"]`) en lugar de "Producto n: …" — la app sabe qué ítem y qué campo falló (cubre parte de P-api-movil-2) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — El `usuario` de un consumo es quien registra la revisión (empleado en la API, administrador en la carga manual) — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — El slug de `TipoServicio` se genera en `save()` solo si viene vacío: `slugify(nombre)` y, si choca, `-2`, `-3`…; el formulario del panel no lo expone; la desactivación es el campo `activo` de la edición, como en productos — decidida por Claude, revisable — reemplaza a: (nada)
- 2026-10-19 — `Producto.presentacion` queda como texto descriptivo; el dato calculable es `contenido_por_envase` — decidida por Claude, revisable — reemplaza a: (nada)

## Olas

| Ola | Subtareas | Apps (migraciones) |
|---|---|---|
| 1 | T1, T2, T3 (integración) | productos, servicios |
| 2 | T4, T5 (integración) | visitas |
| 3 | T6, T7 (integración y cierre) | — |

## Subtareas

<!-- Común a las subtareas delegadas, salvo que se diga otra cosa:
No puede tocar: `docs/planes/`, `docs/bitacora.md`, `docs/decisiones.md`, `config/`, `apps/api/urls.py`, `apps/panel/urls.py`, migraciones existentes, `templates/panel/base.html`, archivos de otro dueño.
Skill a leer antes: `.claude/skills/convenciones-proyecto/SKILL.md`.
Worktree: sí (`worktrees/catalogo-stock-T<n>`, base `plan/catalogo-stock`). Ruta: delegada (`implementador`). -->

### T1 — Productos: unidades, envase, movimientos de stock, ficha y catálogo

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/productos/models.py`, `apps/productos/unidades.py` (nuevo), `apps/productos/services.py` (nuevo), `apps/productos/panel_views.py`, `apps/productos/panel_forms.py`, `apps/productos/panel_urls.py`, `apps/productos/serializers.py`, `apps/productos/admin.py`, `apps/productos/migrations/0002_*.py` (generada con `makemigrations`), `apps/productos/tests/test_unidades.py`, `apps/productos/tests/test_stock.py`, `apps/productos/tests/test_panel_stock.py` (nuevos), `apps/productos/tests/test_api.py` (agrega `CatalogoUnidadesTests` y ajusta lo existente), `apps/productos/tests/test_rutas.py`, `apps/productos/tests/test_panel.py`, `apps/productos/tests/test_models.py`, `apps/productos/templates/productos/panel/**`
- **No puede tocar**: lo común, `apps/visitas/`, `apps/panel/`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models; `.agents/skills/django-rest-framework/SKILL.md` § Serializers
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 700 líneas agregadas
- **Qué hacer**: `unidades.py` con ml, l, gal (3,785411784 l), g, kg, lb (0,45359237 kg) y unidad; `convertir`, `unidades_de(magnitud)`, `unidades_permitidas(producto)` (modo `unica`: solo `unidad_base`; `equivalentes`: las de su magnitud). `Producto` suma `unidad_base` (choices), `contenido_por_envase`, `modo_unidad` (`unica` | `equivalentes`). `MovimientoStock` (producto, tipo `ingreso`|`ajuste`|`consumo`, `cantidad_base` con signo, usuario, `creado`, `nota`; sin FK a `visitas`). `services.py`: `stock(producto)`, `registrar_ingreso` (en envases o en unidad base, > 0), `registrar_ajuste` (con signo, distinto de 0), `registrar_consumo(producto, cantidad_base, usuario, nota="")` (crea el movimiento con signo negativo y lo devuelve). Los campos nuevos llevan valor por defecto en el modelo (ver Decisiones). Ficha `<int:pk>/` con stock, envases e historial; alta de ingreso y ajuste en `<int:pk>/movimientos/nuevo/`; sin rutas de edición ni borrado de movimientos. El listado muestra stock y envases. El catálogo de la API expone `unidad_base`, `modo_unidad` y `unidades_permitidas`.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidades.UnidadesTests.test_dos_litros_son_0_5283_galones --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidades.UnidadesTests.test_otra_magnitud_lanza_error --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidades.UnidadesTests.test_conteo_solo_admite_unidad --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_stock.StockTests.test_ingreso_de_3_envases_de_5_l_suma_15_l --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_stock.StockTests.test_stock_puede_quedar_negativo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_stock.StockTests.test_contenido_por_envase_debe_ser_positivo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_stock.FichaProductoTests.test_ficha_muestra_3_envases --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_stock.FichaProductoTests.test_ficha_marca_stock_negativo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_stock.FichaProductoTests.test_ajuste_negativo_resta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_stock.FichaProductoTests.test_empleado_no_accede --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_panel_stock.FichaProductoTests.test_no_hay_rutas_para_editar_ni_borrar_movimientos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_api.CatalogoUnidadesTests.test_expone_unidad_base_modo_y_unidades_permitidas --keepdb`
  - `[grep-0]` `grep -nE "float\(" apps/productos/unidades.py apps/productos/services.py`
  - `[grep-1]` `grep -n "class MovimientoStock" apps/productos/models.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos apps.panel --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 700 --subtarea T1`

### T2 — Servicios: alta y edición de TipoServicio con slug único

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/servicios/models.py`, `apps/servicios/panel_views.py`, `apps/servicios/panel_forms.py`, `apps/servicios/panel_urls.py`, `apps/servicios/tests/test_panel_abm.py` (nuevo), `apps/servicios/migrations/0005_*.py` (solo si `makemigrations` la genera), `apps/servicios/templates/servicios/panel/**`
- **No puede tocar**: lo común, `apps/servicios/fixtures/`, `apps/servicios/admin.py`
- **Skill a leer antes**: `.agents/skills/django-conventions/SKILL.md` § Models
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 350 líneas agregadas
- **Qué hacer**: rutas `nuevo/` y `<int:pk>/editar/` con un formulario de `nombre` y `activo` (sin `slug`); `TipoServicio.save()` genera el slug si viene vacío (`slugify` más sufijo `-2`, `-3`… si choca) y no lo cambia al editar. El listado enlaza a "Editar" y "Nuevo servicio"; el título de la sección pasa a "Servicios". Sin ruta de borrado.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_abm.TipoServicioAbmTests.test_alta_genera_slug --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_abm.TipoServicioAbmTests.test_dos_servicios_con_el_mismo_nombre_tienen_slugs_distintos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_abm.TipoServicioAbmTests.test_edicion_no_cambia_el_slug --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_abm.TipoServicioAbmTests.test_desactivar_desde_la_edicion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_abm.TipoServicioAbmTests.test_empleado_no_accede_a_alta_ni_edicion --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_panel_abm.TipoServicioAbmTests.test_no_hay_ruta_de_borrado_de_servicio --keepdb`
  - `[grep-0]` `grep -n '"slug"' apps/servicios/panel_forms.py`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios apps.panel --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T2`

### T3 — Integración ola 1 (principal)

- **Ola**: 1 (después de verificar T1 y T2)
- **Depende de**: T1, T2
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/catalogo-stock` de cada subtarea, no los informes.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh catalogo-stock T<n> plan/catalogo-stock <rutas de Puede tocar>` para T1 y T2.
  3. Crear el worktree de T4: `bash .claude/hooks/worktree-crear.sh catalogo-stock T4 plan/catalogo-stock`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/catalogo-stock | grep -q "T1: integra catalogo-stock-T1"`
  - `[cmd]` `git log --oneline plan/catalogo-stock | grep -q "T2: integra catalogo-stock-T2"`

### T4 — Visitas: cantidad con unidad, conversión, consumo de stock y datos demo

- **Ola**: 2
- **Depende de**: T3
- **Propiedad**: T4 es la única subtarea de este plan que toca `apps/visitas/**` y `apps/proyectos/**`, y la única subtarea transversal de `apps/api/**` y `apps/panel/**`.
- **Puede tocar**: `apps/visitas/models.py`, `apps/visitas/migrations/0010_*.py` (generada), `apps/visitas/services.py`, `apps/visitas/serializers.py`, `apps/visitas/api_views.py`, `apps/visitas/panel_forms.py`, `apps/visitas/panel_views.py`, `apps/visitas/admin.py`, `apps/visitas/templates/visitas/**`, `apps/visitas/management/commands/registrar_revision_demo.py`, `apps/visitas/tests/test_stock_api.py`, `apps/visitas/tests/test_stock_services.py` (nuevos), `apps/visitas/tests/test_admin.py`, `apps/visitas/tests/test_api.py`, `apps/visitas/tests/test_migraciones.py`, `apps/visitas/tests/test_models.py`, `apps/visitas/tests/test_panel.py`, `apps/visitas/tests/test_services.py`, `apps/visitas/tests/test_ubicacion.py`, `apps/proyectos/templates/proyectos/panel/ficha.html`, `apps/proyectos/tests/test_panel.py`, `apps/api/tests/test_errores.py`, `apps/api/tests/test_flujo.py`, `apps/panel/demo.py`, `apps/panel/demo_datos.py`, `apps/panel/demo_historia.py`, `apps/panel/management/commands/cargar_demo.py`, `apps/panel/tests/test_cargar_demo.py`, `apps/panel/tests/test_recorrido.py`
- **No puede tocar**: lo común, `apps/productos/` (usa `unidades` y `services`, no los cambia), `apps/panel/tests/test_acceso.py`
- **Skill a leer antes**: `.agents/skills/django-rest-framework/SKILL.md` § Serializers; `.agents/skills/django-conventions/SKILL.md` § Models
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 900 líneas agregadas
- **Qué hacer**: renombrar `unidad` → `unidad_dosis` y agregar `unidad` (choices de `apps.productos.unidades`); `cantidad` obligatoria; `cantidad_base`; `movimiento` (`OneToOneField` nulo a `productos.MovimientoStock`, `PROTECT`, `related_name="producto_aplicado"`). `_armar_productos` valida la unidad según `modo_unidad` y magnitud, convierte con `apps.productos.unidades.convertir` y emite errores anidados `{i: {campo: [...]}}`. Tras guardar cada aplicado, `registrar_consumo` en la misma transacción y se guarda `aplicado.movimiento`, en `registrar_revision` (usuario: empleado) y en `registrar_visita_manual` (usuario: administrador). El formulario manual ofrece las unidades del producto. Las fichas de visita y de proyecto muestran cantidad y unidad, y la dosis con `unidad_dosis`. Datos demo: productos en las tres magnitudes y ambos modos, con un ingreso inicial cada uno (`registrar_ingreso`); `GeneradorHistoria` carga los campos nuevos y crea el consumo; la limpieza demo borra los aplicados antes que los movimientos. Los tests existentes listados se ajustan al formato nuevo sin dejar de probar lo que prueban.
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_api.StockRevisionApiTests.test_dos_litros_en_producto_en_galones_guarda_0_5283_y_descuenta --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_api.StockRevisionApiTests.test_modo_unica_con_otra_unidad_da_400_en_el_producto --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_api.StockRevisionApiTests.test_unidad_de_otra_magnitud_da_400 --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_api.StockRevisionApiTests.test_foto_invalida_no_deja_movimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_api.StockRevisionApiTests.test_cantidad_es_obligatoria --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_services.ConsumoTests.test_un_consumo_por_producto_aplicado_con_el_empleado --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_services.ConsumoTests.test_carga_manual_crea_consumo_del_administrador --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_stock_services.ConsumoTests.test_carga_manual_fallida_no_deja_movimiento --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoStockTests.test_productos_en_las_tres_magnitudes_y_ambos_modos --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoStockTests.test_cada_producto_tiene_ingreso_inicial --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoStockTests.test_cada_aplicado_tiene_su_consumo --keepdb`
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoStockTests.test_segunda_corrida_limpia_movimientos_sin_error --keepdb`
  - `[grep-1]` `grep -n "unidad_dosis" apps/visitas/models.py`
  - `[grep-1]` `grep -n "registrar_consumo" apps/visitas/services.py`
  - `[cmd]` `D=$(mktemp -d) && export DATABASE_URL="sqlite:///$(cygpath -m "$D")/vacia.sqlite3" MEDIA_ROOT="$(cygpath -m "$D")/media" && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py migrate --noinput && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py cargar_demo; r=$?; rm -rf "$D"; exit $r`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 900 --subtarea T4`

### T5 — Integración ola 2 (principal)

- **Ola**: 2 (después de verificar T4)
- **Depende de**: T4
- **Pasos**:
  1. Revisar `bash .claude/hooks/cambios.sh . plan/catalogo-stock` de T4.
  2. Desde la raíz, `bash .claude/hooks/worktree-integrar.sh catalogo-stock T4 plan/catalogo-stock <rutas de Puede tocar>`.
  3. Crear el worktree de T6 con `worktree-crear.sh`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/catalogo-stock | grep -q "T4: integra catalogo-stock-T4"`

### T6 — Contrato y documentación

- **Ola**: 3
- **Depende de**: T5
- **Puede tocar**: `docs/01-modelo-y-arquitectura.md` (§ 3.3, 3.8, 3.9 y 4.1), `docs/contrato-api.md`, `docs/api/openapi-v1.yaml` (regenerado con `spectacular`, nunca a mano)
- **No puede tocar**: lo común, `apps/`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md`
- **Worktree**: sí
- **Ruta**: delegada
- **Presupuesto**: 300 líneas agregadas
- **Qué hacer**: docs/01 § 3.3 (alta y edición de servicios desde el panel, slug generado), § 3.8 (`cantidad`, `unidad`, `unidad_dosis`, `cantidad_base`), § 3.9 (unidad base, modo, envase, `MovimientoStock` y stock), § 4.1 (la revisión envía cantidad y unidad por producto y descuenta stock). `docs/contrato-api.md`: nota del catálogo (`unidad_base`, `modo_unidad`, `unidades_permitidas`) y de `productos_aplicados` con errores anidados; actualizar `Actualizado:`. Regenerar el OpenAPI.
- **Criterios**:
  - `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - `[grep-1]` `grep -n "unidades_permitidas" docs/api/openapi-v1.yaml`
  - `[grep-1]` `grep -n "MovimientoStock" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -nE "unidad_dosis([^_]|$)" docs/01-modelo-y-arquitectura.md`
  - `[grep-1]` `grep -n "modo_unidad" docs/contrato-api.md`
  - `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - `[cmd]` `bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T6`

### T7 — Integración ola 3 y cierre (principal)

- **Ola**: 3 (después de verificar T6)
- **Depende de**: T6
- **Pasos**:
  1. Revisar `cambios.sh` de T6.
  2. Desde la raíz, `worktree-integrar.sh` de T6 en `plan/catalogo-stock`.
  3. `verificador` y `verificador-b` sobre `TODO`; `refutador` si discrepan; `auditor-seguridad` sobre las rutas nuevas del panel y la entrada de `POST /api/v1/revisiones/`.
- **Presupuesto**: no aplica (solo merges y commits `registro:`)
- **Criterios**:
  - `[cmd]` `git log --oneline plan/catalogo-stock | grep -q "T6: integra catalogo-stock-T6"`

## Criterios de cierre global

- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
- `[cmd]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
- `[cmd]` `./venv/Scripts/python.exe -m ruff check .`
- `[cmd]` `test "$(git status --porcelain | grep -v '^??' | wc -l)" -eq 0`
- `[cmd]` `bash .claude/hooks/congelado.sh docs/planes/2026-10-19-catalogo-stock.md catalogo-stock`
- `[cmd]` `T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
- `[grep-0]` `grep -rnE "float\(" apps/productos/unidades.py apps/productos/services.py`

## Registro de verificación

<!-- Corte del congelado: desde este encabezado hacia abajo, el principal lo actualiza durante la
ejecución. Lo de arriba no se toca sin un commit `docs(plan): catalogo-stock — modificado: <motivo>`. -->

commit_base: f9a7b64

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | pendiente |
| T2 | pendiente |
| T3 | pendiente |
| T4 | pendiente |
| T5 | pendiente |
| T6 | pendiente |
| T7 | pendiente |

### Corridas

| Fecha/hora | Alcance | HEAD verificado | Veredicto | Notas |
|---|---|---|---|---|
| 2026-10-19 | juez-plan ronda 1 | (sin commit) | RECHAZADO | 7 bloqueantes (campos obligatorios de Producto, FK productos→visitas, tests y templates fuera de Puede tocar, dos transversales, grep que ya pasaba), corregidos |
| 2026-10-19 | juez-plan ronda 2 | (sin commit) | APROBADO | sin hallazgos |

## Pendientes que deja este plan

### Problemas

### Decisiones

### Cierra

- cierra: P-nombre-empresa-prod-3 — corregido en dd97c78 (`README.md` y `.env.example` marcan `NOMBRE_EMPRESA` obligatoria en producción)
