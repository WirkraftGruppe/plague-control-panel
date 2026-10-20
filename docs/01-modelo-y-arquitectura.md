# Detach — Modelo de datos y arquitectura

Versión 0.4 · 20/10/2026 · sin agrupador de trabajos: servicio, frecuencia y vencimiento por punto, turnos con ítems (`docs/planes/2026-10-20-flujo-sitio.md`) · Base para `CLAUDE.md` y las migraciones iniciales.

## 1. Alcance

Una sola aplicación Django con dos superficies sobre una misma base de datos. El sitio público de cada empresa vive en otro repositorio y no forma parte de esta aplicación; `/` solo redirige al login del panel.

| Superficie | Quién la usa | Tecnología |
|---|---|---|
| Panel de gestión (`/panel/`) | Administradores | Django templates + HTMX + Leaflet |
| API (`/api/v1/`) | App móvil Expo (última etapa) | Django REST Framework + JWT |

**Fuera de alcance (etapa 1):** presupuestos, facturación, acceso de clientes, notificaciones push/correo, diseño de rutas, QR para clientes.

## 2. Roles

Dos roles, sobre `AUTH_USER_MODEL` propio (`accounts.User`) con campo `rol`:

- **Administrador** — accede al panel. Crea clientes y sitios (con su responsable y la programación de cada punto); arma turnos para los empleados; carga visitas manuales; genera QR, informes y certificados; crea cuentas (no hay autorregistro).
- **Empleado** — accede solo a la API desde la app. Ve sus visitas asignadas, escanea QR, completa la planilla, consulta su historial y lo descarga.

El superusuario de Django es un administrador con acceso al `/admin/` técnico; el panel de gestión es una interfaz propia, no el admin.

## 3. Entidades

```
Cliente 1──n Sitio 1──n PuntoControl (qr_codigo, servicio, frecuencia_dias, proximo_vencimiento)
              │  │            │
              │  └──n Plano 1──n PuntoControl (x, y)
              │
              ├── responsable n──1 Empleado
              └──n Visita (turno) n──1 Empleado
                    │
                    ├──n ItemTurno n──1 PuntoControl, n──1 TipoServicio
                    └──n Revision n──1 PuntoControl, n──1 TipoServicio
                            └── n Foto, n ProductoAplicado
PuntoControl n──1 TipoServicio 1──n CampoPlanilla (ámbito punto | visita)
```

### 3.1 `clientes.Cliente`
`razon_social`, `cuit` (opcional), `contacto_nombre`, `contacto_telefono`, `contacto_email`, `notas`, `activo`, `creado`, `actualizado`.

### 3.2 `sitios.Sitio` — el lugar físico; lo que aparece en el mapa
- `cliente` (FK), `nombre` (ej. "Planta Chascomús"), `direccion`, `localidad`, `latitud`, `longitud`
- `sector` (choices: industria, puerto, gastronomía, hotelería, edificio, salud, educación, rural, espacio_verde, transporte, hogar, otro)
- `contacto_en_sitio`, `telefono_en_sitio`, `horario_acceso`, `notas`
- `responsable` (FK User, opcional): empleado activo a cargo del sitio
- `activo`, `creado`, `actualizado`

Regla: el sitio no tiene QR propio; los QR son de sus puntos de control. Al crear un sitio se crea el punto `General` (orden 0), de modo que todo sitio tiene al menos un QR. Desactivar un sitio desactiva todos sus puntos.

#### 3.2.1 `sitios.PuntoControl` — el lugar concreto con su propio QR
- `sitio` (FK), `nombre` (ej. "Depósito 2"), `sector` (texto libre, opcional), `orden`, `activo`
- `qr_codigo` — UUID único, generado al crear; **es el contenido del QR**. Un QR por punto. `qr_impreso_el` (fecha, opcional) para saber si la etiqueta ya fue colocada. El administrador puede regenerar el QR de un punto (invalida la etiqueta impresa y queda en el historial)
- `servicio` (FK a `TipoServicio`, opcional), `frecuencia_dias` (entero positivo, opcional) y `proximo_vencimiento` (fecha, opcional): la programación del punto; el administrador la edita en línea desde la ficha del sitio y cada cambio queda en el historial. Editar la frecuencia no recalcula el vencimiento: la fecha se ajusta a mano y la próxima revisión que cuenta la recalcula
- `plano` (FK a `Plano`, opcional) y `x`, `y` (fracciones de 0 a 1 de la imagen): ubicación en el plano
- `latitud`, `longitud` (opcionales): si el punto no tiene coordenadas, la primera revisión con precisión de 50 m o mejor las fija, sea de un empleado o de un administrador, y queda en el historial del punto. Se corrigen en Editar punto
- Un punto activo exige un sitio activo, y el plano debe ser del mismo sitio. Un punto se desactiva, no se borra: conserva sus revisiones

Regla: el QR identifica un punto; abre el turno del empleado en el sitio de ese punto. Al escanearlo, la app recibe el punto (con su plano, su servicio y si está en el turno del empleado), el sitio, el cliente y las visitas propias pendiente o abierta del sitio. El estado de un punto sale de su `proximo_vencimiento` (`apps/sitios/estado.py`): `vencida` (fecha anterior a hoy), `proxima` (dentro de los próximos 7 días, `UMBRAL_PROXIMA_DIAS`), `al_dia`, o `sin_programar` (sin fecha). Para el sitio vale el peor estado de sus puntos activos, con esta gravedad: `vencida` > `proxima` > `sin_programar` > `al_dia`; un sitio sin puntos activos queda `sin_programar`. Los puntos inactivos no se resuelven ni se muestran.

#### 3.2.2 `sitios.Plano` — imagen de una planta o zona
`sitio` (FK), `nombre`, `imagen`, `ancho_px`, `alto_px` (calculados), `orden`, `activo`. Se sube JPG, PNG o PDF (máx. 20 MB y 40 millones de píxeles) y se guarda siempre como PNG, sin metadatos, con el lado mayor de 4000 px como máximo y un nombre aleatorio. Del PDF se usa la primera página; se rasteriza en un subproceso (`rasterizar_pdf.py`) con tiempo máximo de 15 s (`TIEMPO_MAXIMO_PDF`): si se pasa, se rechaza pidiendo exportarlo como PNG o JPG. Un PDF cifrado, corrupto o sin páginas también se rechaza. Al borrar el plano se borra el archivo y sus puntos quedan sin ubicar (`plano = null`).

### 3.3 `servicios.TipoServicio` — catálogo
`nombre`, `slug`, `activo`. Sirve al panel (planillas) y a la API. Carga inicial: los 12 servicios de la Carta de Servicios más mantenimiento edilicio. El administrador da de alta y edita servicios desde el panel: el `slug` se genera a partir del nombre al crear y no se puede editar. Un servicio no se borra: se desactiva (`activo = false`) y deja de ofrecerse para puntos y turnos nuevos, sin tocar los existentes.

### 3.4 `servicios.CampoPlanilla` — la planilla de cada revisión y de la visita
Cada tipo de servicio define sus campos; la app los renderiza dinámicamente y el panel los muestra en el historial. La planilla de `punto` se completa tras escanear cada QR, con los campos del servicio de esa revisión; la de `visita`, al cerrar, una por cada servicio presente en el turno. `TipoServicio.esquema_planilla(ambito)` devuelve los campos activos de un ámbito, y `Revision` y `Visita` guardan una copia del esquema usado (`esquema_planilla`).
- `tipo_servicio` (FK), `orden`, `etiqueta`, `clave` (slug interno)
- `tipo` (choices: texto, numero, booleano, opcion, opcion_multiple, fecha)
- `ambito` (choices: `punto` = se responde en cada revisión; `visita` = se responde una vez al cerrar la jornada; por defecto `punto`)
- `opciones` (JSON, para tipo opción), `obligatorio`, `ayuda`, `activo`

Ejemplo — Control de roedores: `estaciones_revisadas` (número), `estaciones_con_consumo` (número), `cebo_repuesto` (booleano), `observaciones` (texto).
Ejemplo — Exclusión de aves: `estado_redes` (opción: bueno/dañado/no aplica), `estado_pinches` (opción), `sellado_realizado` (booleano).

### 3.5 Programación por punto
El trabajo recurrente no se modela aparte: no hay una entidad que agrupe sitio, servicio y frecuencia. Cada `PuntoControl` lleva su `servicio`, su `frecuencia_dias` y su `proximo_vencimiento` (ver 3.2.1) y el sitio, su `responsable` (3.2). El vencimiento lo recalcula `actualizar_vencimiento(punto)` (`apps/visitas/services.py`): toma la revisión más reciente del punto en visitas abiertas o realizadas que cuentan como servicio (`cuenta_como_servicio`) y fija `proximo_vencimiento = fecha de esa revisión + frecuencia_dias`. Sin frecuencia o sin revisiones que cuenten no cambia nada, y una revisión anterior a la última no pisa la fecha. Lo llaman `registrar_revision` y `registrar_visita_manual`; cerrar una visita no toca el punto ni el sitio. Las visitas abiertas por un administrador no cuentan como servicio.

### 3.6 `visitas.Visita` — el turno de un empleado en un sitio
- `sitio` (FK), `empleado` (FK User)
- `origen` (choices: `app` = abierta escaneando un QR o asignada como turno, `manual` = cargada por un administrador). La app **no puede** abrir visitas sin escanear un punto válido; el administrador sí, con `origen=manual` y campo `motivo_manual` obligatorio (ej. "QR ilegible, datos enviados por WhatsApp")
- `programada_para` (fecha, opcional) y `asignada_por` (FK User, opcional): un turno existe antes de realizarse, como asignación del administrador
- `estado`: `pendiente` (asignada, sin abrir), `abierta` (en curso), `realizada` (cerrada con al menos una revisión) o `cancelada`
- `abierta_en` y `cerrada_en` (datetime). `realizada_en` es una propiedad: el valor de `cerrada_en`
- `cierre` (choices: `empleado`, `sistema`, `administrador`): quién cerró la jornada
- `cuenta_como_servicio` (booleano): `False` si la abrió un administrador
- `datos` (JSON) — respuestas a los `CampoPlanilla` de ámbito `visita`, **por servicio**: `{slug_del_servicio: {clave: valor}}`, con un servicio por cada uno de los ítems y las revisiones del turno; `esquema_planilla` guarda el esquema usado, con la misma forma. Los errores de validación vuelven como `"slug: clave: mensaje"` bajo `datos`
- `observaciones`, `incidencia` (booleano) + `incidencia_detalle`
- `incidencia_asignacion` (otro empleado tenía un turno pendiente en el sitio cuando esta visita se abrió), `incidencia_revisada_por` e `incidencia_revisada_en`
- `creado`, `actualizado`

Coherencia: una `realizada` lleva `cerrada_en`; una `cancelada` no; una `abierta` lleva `abierta_en`; una `pendiente` no tiene revisiones.

**`visitas.ItemTurno`.** Un punto del turno con el servicio que se le hará: `visita` (FK), `punto` (FK a `PuntoControl`), `servicio` (FK a `TipoServicio`); un punto aparece una sola vez por visita. El administrador arma el turno tildando puntos (`crear_turno(sitio, empleado, programada_para, items, asignada_por)`), cada uno con su servicio (por defecto el del punto); exige al menos un ítem, puntos activos del sitio sin repetir, servicios activos y un empleado activo. Una visita abierta por QR sin turno previo no tiene ítems.

**Cierre.** `cerrar_visita` (`apps/visitas/services.py`) exige que la visita esté abierta y al menos una revisión recibida durante la jornada (hora del servidor). Con `cierre=empleado` solo cierra el dueño de la visita; con `cierre=administrador`, solo un administrador, y cuentan todas las revisiones. Con `cierre=sistema` (comando `cerrar_visitas_abiertas`, pensado para un cron diario: cierra las abiertas hace más de `VISITA_ABIERTA_MAXIMO_HORAS`, 16 por defecto) la visita toma la hora de la última revisión; sin revisiones, si venía asignada vuelve a `pendiente` y si no queda `cancelada`. La planilla de visita se valida por servicio contra el esquema de cada uno (salvo en el cierre por sistema). Orden de bloqueo único: Sitio, Visita, PuntoControl.

### 3.6.1 `visitas.Revision` — el escaneo de un punto dentro de una visita
- `visita` (FK), `punto` (FK a `PuntoControl`), `orden`
- `servicio` (FK a `TipoServicio`, obligatorio) y `fuera_de_turno` (booleano): el servicio lo decide el servidor, nunca el cliente. Es el del `ItemTurno` de la visita para ese punto; si la visita no tiene ítem para él, es el `servicio` del punto y la revisión queda `fuera_de_turno = true`. Si el punto tampoco tiene servicio, la revisión se rechaza con 400 ("El punto no tiene servicio asignado.", bajo `qr_codigo`)
- `realizada_en` (hora del teléfono) y `recibida_en` (hora del servidor)
- `cliente_uuid` (UUID único, opcional): lo genera la app para reintentar sin duplicar; un reintento recibe 409
- `latitud`, `longitud`, `precision_m` — ubicación del teléfono al escanear
- `datos` (JSON, planilla de ámbito `punto` del servicio de la revisión) y `esquema_planilla`
- `observaciones`, `incidencia` (booleano) + `incidencia_detalle`

Reglas: la visita debe estar abierta y ser del empleado; el QR debe ser de un punto activo del sitio de la visita; coordenadas obligatorias; de 0 a 2 fotos (`MAX_FOTOS = 2`, sin mínimo); `realizada_en` no puede ser futura ni tener más de `ATRASO_MAXIMO_HORAS` (168 por defecto) de atraso: pasado ese límite el administrador la carga como visita manual. Si el punto no tiene ubicación, la revisión propone la suya (ver 3.2.1).

### 3.7 `visitas.Foto`
`revision` (FK), `codigo` (UUID, usado en la URL de descarga), `imagen`, `tomada_en`, `orden`. De 0 a 2 fotos por revisión (validación en el servicio); no hay mínimo.

### 3.8 `visitas.ProductoAplicado` — confirmado por la empresa
`revision` (FK), `producto` (FK a `productos.Producto`), `lote`, `dosis`, `unidad_dosis` (texto libre, por ejemplo `ml/l`: la concentración, no lo gastado), `cantidad` y `unidad` (lo efectivamente usado y la unidad en que se lo declara, una de las permitidas para el producto), `cantidad_base` (calculada por el servidor: la cantidad convertida a la `unidad_base` del producto, nunca enviada por el cliente) y `movimiento` (FK uno a uno, opcional, al `MovimientoStock` de consumo que generó). La planilla de toda revisión incluye una sección "Productos utilizados": el empleado **elige de la lista precargada** (no escribe nombres) y completa lote, dosis, cantidad y unidad. Puede agregar varios. `CampoPlanilla` no la modela porque es común a todos los servicios; se define en el serializer.

### 3.9 `productos.Producto` — catálogo precargado por administradores
`nombre_comercial`, `principio_activo`, `registro` (ANMAT/SENASA), `presentacion`, `unidad_dosis_por_defecto`, `unidad_base`, `contenido_por_envase`, `modo_unidad`, `activo`. Los administradores lo mantienen desde el panel; la app lo descarga y lo guarda en caché para funcionar sin conexión.

**Unidades.** `unidad_base` es la unidad en que se lleva el stock: `ml`, `l`, `gal`, `g`, `kg`, `lb` o `unidad`. Cada una pertenece a una magnitud (volumen, masa o conteo) y solo se convierte dentro de su magnitud, con factores fijos y sin `float`: 1 gal (US) = 3,785411784 l y 1 lb = 0,45359237 kg; el resto son potencias de mil. Las conversiones se redondean a 4 decimales. `contenido_por_envase` es la cantidad de `unidad_base` que trae cada envase. `modo_unidad` es `unica` (la cantidad solo se declara en `unidad_base`) o `equivalentes` (se acepta cualquier unidad de la magnitud de `unidad_base`). La API expone `unidades_permitidas` según ese modo.

**`MovimientoStock`.** Registro de cada cambio de stock: `producto` (FK), `tipo` (`ingreso`, `ajuste` o `consumo`), `cantidad_base` (con signo, en `unidad_base`), `usuario`, `creado` y `nota`. El stock de un producto es la suma de sus `cantidad_base` y los envases son stock / `contenido_por_envase`; el stock puede quedar negativo (no se bloquea una revisión por falta de stock registrado). Un `ingreso` suma y un `ajuste` corrige en cualquiera de los dos sentidos; un `consumo` lo genera el servidor al registrar un `ProductoAplicado`. Un consumo no se edita ni se borra: una corrección se carga como `ajuste`.

### 3.10 `informes.Certificado` — generado automáticamente
Reemplaza el certificado que hoy se hace a mano. Se crea desde la ficha del sitio o del cliente eligiendo un rango de fechas; toma:
- del cliente: `razon_social`, `cuit`, domicilio del sitio
- de las visitas del rango: fechas, tipo de servicio, productos aplicados con registro ANMAT/SENASA, lote y dosis, empleado que aplicó
- de la empresa: el nombre sale de `NOMBRE_EMPRESA`; los datos legales, las habilitaciones y el director técnico no tienen modelo todavía y se definen cuando la empresa entregue su certificado actual

Campos: `sitio` (FK) o `cliente` (FK), `desde`, `hasta`, `numero` (correlativo anual, ej. `2026-0041`), `generado_por`, `generado_el`, `pdf` (archivo), `visitas` (M2M con las incluidas). Una vez emitido no se edita; si hay que corregir, se emite uno nuevo que referencia al anterior. El diseño del PDF se ajusta cuando la empresa envíe un ejemplo del certificado actual; la estructura de datos no cambia.

### 3.11 `accounts.User`
Extiende `AbstractUser`: `rol` (administrador/empleado), `telefono`, `activo`. Los empleados no tienen `is_staff`.

## 4. Flujos

### 4.1 Empleado (app)
1. Inicia sesión (JWT). `GET /api/v1/me/visitas/` → sus visitas `pendiente` y `abierta` (las abiertas primero). `GET /api/v1/me/puntos/` (con `?sitio=<id>` opcional) → los puntos activos, con coordenadas y estado, de los sitios activos donde tiene visitas pendientes o abiertas.
2. Escanea el QR de un punto → `POST /api/v1/qr/{codigo}/resolver/` → devuelve el punto (con su plano, su estado, `proximo_vencimiento`, su servicio con el esquema de planilla y `en_turno`), el sitio, el cliente y sus visitas propias del sitio (`visita_pendiente_propia`, `visita_abierta_propia`). Si tiene varios turnos propios con ese punto, elige el abierto antes que el pendiente y después el de `programada_para` más antigua. Un QR inexistente o de un punto, sitio o cliente inactivo da el mismo 404.
3. Abre la jornada: `POST /api/v1/visitas/abrir/` con `qr_codigo` (el UUID del punto escaneado, de un punto activo) y su ubicación opcional. Si tiene una visita abierta en el sitio del punto la devuelve (200, idempotente); si tiene un turno pendiente, abre el más antiguo; si no, crea una nueva con `origen=app` y sin ítems (201). Un QR inexistente o inactivo da 400 genérico.
4. En cada punto que revisa: completa la planilla de ámbito `punto`, agrega los productos utilizados eligiendo del catálogo (lote, dosis, cantidad usada y su unidad, entre las `unidades_permitidas` del producto), saca de 0 a 2 fotos (la app redimensiona a 1600 px de lado mayor antes de subir: el servidor rechaza JPEG progresivos de más de 16 MP y WebP de más de 8 MP) y opcionalmente marca incidencia. `POST /api/v1/revisiones/` con multipart (`visita`, `qr_codigo` del punto, `cliente_uuid`, `realizada_en`, geolocalización, `datos`, `productos_aplicados`, con `cantidad` y `unidad` por producto, y `fotos`). El servidor convierte cada cantidad a la unidad base del producto, calcula `cantidad_base` y descuenta el stock con un `MovimientoStock` de consumo, todo en la misma transacción que la revisión: si algo falla no queda nada a medias. Los errores de cada producto vuelven anidados como `productos_aplicados.<i>.<campo>` (por ejemplo `productos_aplicados.0.unidad`). Sin conexión: se guarda local y se reintenta con el mismo `cliente_uuid`; el servidor acepta `realizada_en` del cliente y guarda además `recibida_en`. El servicio de la revisión lo decide el servidor (3.6.1). Puede revisar tantos puntos como quiera en la misma visita, estén o no en su turno: los que no están quedan `fuera_de_turno`. Cada revisión recalcula el vencimiento del punto (3.5).
5. Cierra la jornada: `POST /api/v1/visitas/{id}/cerrar/` con la planilla de ámbito `visita`, observaciones e incidencia (todo opcional). Exige al menos una revisión; la visita queda `realizada` con `cierre=empleado` y la planilla de visita se guarda por servicio (3.6). Una visita abierta que se olvida se cierra por sistema (comando `cerrar_visitas_abiertas`).
6. Planos: `GET /api/v1/planos/{id}/imagen/` sirve el PNG del plano. Exige una visita propia abierta o pendiente en ese sitio, con el sitio y el cliente activos; si no, 404 (el mismo que un plano inexistente o inactivo). Los administradores acceden siempre. La respuesta no se cachea (`private, no-store`).
7. `GET /api/v1/me/historial/` para consultar su propio historial de visitas realizadas (`GET /api/v1/me/historial.pdf` para descargarlo está previsto en `informes` y aún no existe); `GET /api/v1/fotos/{codigo}/` descarga una foto propia.

### 4.2 Administrador (panel)
- **Inicio** (`/panel/`): redirige al listado de sitios. No hay tablero.
- **Menú**: Sitios, Mapa, Turnos (con el contador de incidencias sin revisar), Clientes, Catálogo (Servicios y Productos) y Usuarios.
- **Mapa** (`/panel/mapa/`): todos los sitios activos con coordenadas, color por el peor estado de sus puntos activos (3.2.1) y su vencimiento más cercano; el popup enlaza a la ficha y a "nuevo turno". Calcula el estado de todos los sitios con un número fijo de consultas.
- **Nuevo turno** (`/panel/visitas/sitios/<id>/turnos/nuevo/`): el administrador tilda los puntos del sitio (lista o plano; atajos "Todos", "Solo vencidos", "Ninguno"), elige el servicio de cada uno (por defecto el del punto), el empleado y la fecha → `crear_turno`: visita `pendiente` con un `ItemTurno` por punto. El empleado la ve en su lista.
- **Cargar visita** (`/panel/visitas/sitios/<id>/cargar/`): el administrador elige empleado, los puntos revisados con su servicio, fecha y motivo (obligatorio) → una revisión por punto y visita cerrada con `cierre=administrador`. Si completa un turno pendiente, los puntos sin ítem quedan `fuera_de_turno`; una carga nueva crea un `ItemTurno` por cada (punto, servicio). Una fecha anterior a la creación del sitio se rechaza. Una carga con más de `ATRASO_MAXIMO_HORAS` de atraso exige confirmación.
- **Turnos** (`/panel/visitas/`): listado filtrable por empleado, sitio, estado e incidencia; la ficha de cada turno muestra sus ítems, revisiones, fotos y planillas por servicio.
- **Sitios**: alta con geocodificación asistida (mapa clicable para fijar el punto). La ficha lista los turnos pendientes y realizados del sitio, con el botón "Nuevo turno", y tiene pestañas `puntos` (por defecto, con servicio, frecuencia y vencimiento editables en línea), `planos` (plano coloreado por estado) y `mapa`: alta, edición y baja de puntos de control, subida de planos, ubicación de cada punto sobre el plano (con modos explícitos para crear y para ubicar puntos existentes). La pestaña `mapa` muestra solo la ubicación del sitio, de solo lectura. Cada punto tiene su botón "descargar QR" (PNG con sitio, punto y sector, listo para plastificar).
- **Estado en vivo**: la ficha del sitio sondea `/panel/sitios/<id>/estado/` cada 5 s con HTMX (`hx-trigger="every 5s"`) y recolorea los puntos. El sondeo se pausa mientras la pestaña está oculta (`sondeo.js`). Esa vista (`apps/panel/estado.py`) es el único punto de transporte del estado: si más adelante se pasa a SSE, solo cambia ella.
- **Usuarios**: alta manual de administradores y empleados.
- **Productos**: catálogo con alta/baja y registro ANMAT/SENASA; lo que el empleado ve en la app.
- **Certificados** (diseño; `apps/informes` aún sin código): desde la ficha del sitio o del cliente, rango de fechas → PDF numerado con cliente, CUIT, fechas, productos con registro, lote y dosis. Se guarda y se puede volver a descargar.
- **Informes**: por cliente y rango de fechas → PDF con visitas, planillas, fotos y productos (más detallado que el certificado, uso interno o para el cliente).

## 5. Estructura del repositorio

```
detach/
├── CLAUDE.md
├── .claude/                 # skills y comandos de Claude Code (etapa siguiente)
├── docs/
│   ├── bitacora.md · decisiones.md · plantilla-plan.md · planes/
│   ├── 01-modelo-y-arquitectura.md   # este documento
│   └── 02-diseno.md                  # tokens del sistema visual del panel
├── config/                  # settings (base/dev/prod), urls, asgi/wsgi
├── apps/
│   │                        # cada app de dominio es dueña de lo suyo:
│   │                        #   models · services · admin · migrations
│   │                        #   serializers · api_views · api_urls.py (app_name = "<app>")
│   │                        #   panel_views · panel_urls.py · panel_forms
│   │                        #   templates/<app>/{panel,pdf}/… · tests/
│   ├── accounts/            # User, roles, permisos
│   ├── clientes/
│   ├── sitios/              # Sitio, PuntoControl, Plano, estado por vencimiento, QR, geocodificación, página pública /q/<uuid>/
│   ├── servicios/           # TipoServicio, CampoPlanilla
│   ├── visitas/             # Visita, ItemTurno, Revision, Foto, ProductoAplicado, turnos y vencimiento
│   ├── productos/
│   ├── informes/            # generación de PDF (informes, certificados, historial, QR)
│   ├── panel/               # layout, login, mapa, estado en vivo; urls.py = router de una línea por app
│   └── api/                 # transversal: JWT, permisos base, paginación; urls.py = router por app
├── templates/               # solo base.html y panel/base.html
├── static/                  # tailwind, htmx, leaflet, logo
├── media/                   # fotos de visitas, logos, QR generados (fuera de git)
├── pyproject.toml           # ruff; dependencias en requirements.txt
├── docker-compose.yml       # postgres + app
└── .env.example
```

## 6. Decisiones técnicas

- **Python 3.13, Django 5.x, PostgreSQL (SQLite por defecto en desarrollo si no hay `DATABASE_URL`).** Sin PostGIS en etapa 1: lat/lng como `DecimalField`; el mapa es Leaflet con OpenStreetMap (sin costo ni clave de API). Si más adelante hacen falta consultas espaciales, migrar a PostGIS es directo.
- **Panel con templates + HTMX**, no un frontend separado: menos superficie de mantenimiento y sin un frontend aparte que mantener.
- **API versionada** (`/api/v1/`) desde el primer día aunque la app llegue al final: el panel también puede consumirla para el mapa.
- **JWT** (`djangorestframework-simplejwt`) con refresh largo para el empleado.
- **Contrato de la app**: `docs/api/openapi-v1.yaml` es el contrato de `/api/v1/` que consume la app. Todo cambio de respuesta, de parámetro o de versión de drf-spectacular exige regenerarlo en el mismo commit con `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file docs/api/openapi-v1.yaml`; un criterio de cierre lo compara con el generado.
- **Fotos**: redimensionadas al subir (máx. 1600 px) con `Pillow`; almacenamiento local en etapa 1, backend intercambiable (`django-storages`) para S3/R2.
- **PDF**: WeasyPrint desde templates HTML (`templates/pdf/`), mismo sistema visual que el panel.
- **QR**: `segno`, uno por punto de control, contenido `{SITE_URL}/q/{uuid}` (`SITE_URL` es obligatoria en producción; el UUID es el `qr_codigo` del punto). Abierto en un navegador común muestra solo "use la app" (`apps.sitios`, con `X-Robots-Tag`); la app intercepta la URL.
- **Auditoría**: `django-simple-history` en Sitio, PuntoControl, Plano, Visita, Revision y ProductoAplicado para saber quién cambió qué.
- **Tests**: runner de Django (`manage.py test --keepdb`), un `tests/` por app; los flujos 4.1 y 4.2 tienen tests de integración desde el inicio.
- **Calidad**: `ruff` para lint y formato.

## 7. Pendientes de definición

1. Un ejemplo del certificado que entregan hoy, para respetar su diseño y texto legal (una foto o PDF alcanza).
2. Si lote y dosis son obligatorios siempre o pueden quedar vacíos en algún servicio (por defecto: obligatorios).
3. Campos concretos de la planilla para cada uno de los 12 servicios (propongo un borrador y la empresa corrige).
