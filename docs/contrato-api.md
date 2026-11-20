# Contrato de la API v1

Actualizado: 2026-11-20

Resumen legible para la app móvil de Detach. La fuente completa (cuerpos, campos,
códigos de error) es `docs/api/openapi-v1.yaml`; este archivo agrega, por ruta, el
límite de pedidos (throttle) y el rol que la puede usar. Todas las rutas cuelgan de
`/api/v1/` y responden JSON.

- **Auth**: `JWT` es un token de acceso en `Authorization: Bearer <token>` de cualquier
  usuario autenticado; `Empleado o administrador`, `Administrador` y `Empleado` piden
  además ese rol; `Pública` no pide token.
- **Empresas**: cada usuario pertenece a una empresa y la API solo le muestra datos de ella.
  Con la empresa inactiva, `POST /api/v1/auth/token/` no emite tokens y cualquier ruta
  con un token vigente responde 401, sin `code`: el cuerpo es
  `{"detalle": "La empresa está inactiva.", "campos": {}}` y se reconoce por `detalle`. Un identificador de otra
  empresa (`<pk>`, `<codigo>`, un `qr_codigo`, una `visita` en el cuerpo) responde igual
  que uno inexistente: 404 en las rutas con identificador en la URL, y también para una
  `visita` en el cuerpo de `revisiones/` (404, no 400); el 400 igual al de un inexistente
  queda para `qr_codigo`, `producto` y `cliente` (en `POST sitios/`) en el cuerpo. Nunca 403 ni un mensaje
  que distinga "existe pero es de otra empresa".
- **Catálogo de productos** (`GET /api/v1/productos/`): cada producto trae `unidad_base`
  (unidad en que se lleva el stock), `modo_unidad` (`unica` o `equivalentes`) y
  `unidades_permitidas` (las unidades en que se puede declarar una cantidad: solo la base
  en `unica`; todas las de su magnitud en `equivalentes`). Trae además la dosis que define el
  administrador (`dosis_habitual` y `unidad_dosis_habitual`, o `null` si no la cargó),
  `dosis_variable` (booleano) y `ultimo_lote`: el lote de la aplicación más reciente del
  producto en la empresa, o `null`. Como `ultimo_lote` sale de lo aplicado, el `ETag` del
  catálogo cambia cuando alguien aplica el producto con un lote nuevo.
- **Dosis** (`dosis` y `unidad_dosis` de cada ítem de `productos_aplicados`, ambas opcionales):
  si el producto no es `dosis_variable`, el servidor guarda siempre su dosis habitual (o nada,
  si no la tiene) e ignora lo enviado; con `dosis_variable`, guarda la enviada o, si falta,
  la habitual. `lote` sigue siendo obligatorio: un lote vacío da 400 en
  `campos."productos_aplicados.<i>.lote"`. La lectura (la respuesta de `revisiones/` y
  `me/historial/`) devuelve `dosis` y `unidad_dosis` de cada producto, o `null` si no hay.
- **Revisiones** (`POST /api/v1/revisiones/`, multipart): `productos_aplicados` es una parte
  multipart con JSON (`encoding` `application/json` en el esquema): un arreglo de objetos;
  cada ítem lleva `producto`, `lote`, `dosis`, `unidad_dosis`,
  `cantidad` y `unidad` (una de las `unidades_permitidas`). `cantidad` y `dosis` numéricas
  se guardan con su valor exacto (decimal, sin pasar por coma flotante); `NaN`, `Infinity`
  y `-Infinity` se rechazan con 400. El servidor convierte a la
  unidad base y descuenta el stock en la misma transacción. Los errores de validación
  van anidados por ítem: `productos_aplicados.<i>.<campo>`.
  Un servicio dado de baja da 400, igual que un punto sin servicio.
  `latitud` y `longitud` son opcionales: sin una de las dos, la revisión se guarda (201) sin
  coordenadas, sin verificar la distancia ni fijar la ubicación del punto, y queda con una
  incidencia de falta de ubicación. La respuesta 201 trae `duplicada_hoy` (booleano):
  verdadero si otro empleado ya había revisado el punto ese mismo día (el de `realizada_en`);
  la revisión se acepta igual y queda con una incidencia. La visita de un administrador nunca
  la marca. Son cuatro incidencias nuevas, junto con la de apertura sin escaneo y la de horas
  inconsistentes; ninguna cambia `proximo_vencimiento` ni el stock, y todas cuentan en
  "Incidencias sin revisar" del panel con la visita realizada.
- **Turnos por sitio**: una visita es un turno en un sitio con `items[]` (punto y servicio).
  `POST /api/v1/visitas/abrir/` recibe solo `qr_codigo` (más coordenadas opcionales): abre
  el turno pendiente más antiguo del empleado en el sitio de ese punto o crea una visita
  sin ítems; no hay `sitio` ni otro id en el pedido. `GET /api/v1/me/visitas/` trae en cada
  turno `sitio{id, nombre, direccion, localidad, contacto}` e `items[]` con `punto{id, nombre,
  sector, estado, proximo_vencimiento}`, `servicio{id, nombre}`, `revisado` y `no_revisado` (el
  motivo si el punto se reportó como no revisado en el turno, o `null`); `visitas/abrir/`
  devuelve la misma forma. `contacto` es `{nombre, telefono}` del contacto en el sitio, o `null`
  si no hay ninguno de los dos o si el sitio o su cliente están dados de baja; solo viene en los turnos activos propios (no en `me/historial/`
  ni en el cierre). `estado` del punto (`al_dia`, `proxima`, `vencida`, `sin_programar`) usa la
  misma regla que el resolver de QR: `proxima` si vence entre hoy y hoy + los días de aviso de
  su `frecuencia_dias` (`ceil(frecuencia_dias / 4)` entre 1 y 7; sin frecuencia, 7; si el aviso cubre la frecuencia entera, `frecuencia_dias - 1`: con frecuencia 1, `proxima` solo el día que vence). `GET /api/v1/me/visitas/<pk>/` devuelve un turno con la
  forma de un elemento de la lista; uno ajeno, de otra empresa, realizado o inexistente da 404.
  Cada ítem trae además `revisado_por_otro`: `{operario{nombre}, realizada_en}` con la última
  revisión de hoy del punto hecha por otro empleado de la empresa, o `null` si nadie más lo
  revisó hoy (las revisiones propias y las de otros días no cuentan; tampoco las de visitas de
  administradores ni canceladas). Es solo informativo: no bloquea nada. Lo traen `me/visitas/`,
  su detalle y las respuestas de apertura.
- **Abrir sin escanear** (`POST /api/v1/visitas/<pk>/abrir/`): abre el turno pendiente `<pk>`
  del usuario sin el QR. Quedan marcados con una incidencia de apertura sin escaneo. Cuerpo
  opcional: `abierta_en` (misma regla de hora y atraso que `visitas/abrir/`), `latitud`,
  `longitud` y `precision_m` (se guardan sin verificar la distancia). Responde con la misma
  forma que `visitas/abrir/`: 201 si abre el turno, 200 si el usuario ya tenía una visita
  abierta en el sitio (la devuelve sin cambios). Una visita ajena, de otra empresa o
  inexistente da 404; 409 si no está pendiente, está programada para un día posterior o su
  sitio o cliente están inactivos. La revisión sigue exigiendo el `qr_codigo` del punto: sin
  él, 400. Comparte el cupo `crear_visita`.
- **Raíz** (`GET /api/v1/`): `{usuario{id, nombre_completo, username}, empresa{id, nombre},
  rol}`; `nombre_completo` cae en `username` si el usuario no tiene nombre cargado y `empresa`
  es `null` para un usuario sin empresa. `usuario` era antes el username como texto.
- **Empresa inactiva**: el 401 de `auth/token/`, de `auth/token/refresh/` y de cualquier ruta
  con un token vigente lleva, además de `detalle` y `campos`, `code: "empresa_inactiva"`.
- **Códigos de error** (`code`): además de `empresa_inactiva`, solo traen `code` tres
  errores de la app, para que distinga el reintentable del definitivo sin leer textos:
  - `atraso_excedido` (400): la hora que manda la app (`realizada_en`, `abierta_en`,
    `cerrada_en` o `reportado_en`) supera `ATRASO_MAXIMO_APP_HORAS`. Viene en `campos`, bajo
    el campo que se pasó. No es reintentable: hay que avisar al administrador para que
    cargue lo hecho como visita manual.
  - `visita_no_abierta` (409): la revisión o el reporte de no revisado sobre una visita
    propia que no está abierta (`pendiente`, `cancelada` o `realizada`), y el cierre de una
    `pendiente` o `cancelada`. Es reintentable: la app reenvía `abrir` y reintenta con la
    visita que le devuelve. El reenvío de `abrir` con una visita abierta responde 200 con
    ella, sin evaluar `abierta_en`.
  - `visita_ya_cerrada` (409): el cierre de una visita `realizada` que cerró el sistema o
    un administrador. Es definitivo y no se reintenta. El cierre repetido por el mismo
    empleado sigue respondiendo 200.
  El resto de los errores no lleva `code`.
- **Hora de la app y atraso**: la app manda cuándo ocurrió cada cosa porque puede trabajar
  sin conexión. `abierta_en` (opcional, en `POST visitas/abrir/`), `cerrada_en` (opcional,
  en `POST visitas/<pk>/cerrar/`), `reportado_en` (opcional, en `POST
  visitas/<pk>/no-revisados/`) y `realizada_en` (en `POST revisiones/`) son fechas con hora.
  Una hora futura más allá de la tolerancia da 400 y una con más atraso que
  `ATRASO_MAXIMO_APP_HORAS` (72 por defecto, configurable por entorno) da 400 con
  `code: "atraso_excedido"`. La carga manual del panel sigue con `ATRASO_MAXIMO_HORAS` (168).
  Un reintento con el mismo `cliente_uuid` ya registrado responde 409 aunque pase el límite:
  la deduplicación va antes que el atraso. Una `cerrada_en` o un `reportado_en`
  anterior a la apertura (`abierta_en`) ya no da 400: se acepta (201 en el reporte, 200 en el
  cierre), se guarda la hora declarada y la visita queda con una incidencia de horas
  inconsistentes.
- **Apertura con `abierta_en`**: el servidor guarda `min(abierta_en, ahora)` y solo reabre
  turnos pendientes con `programada_para` vacía o no posterior al día de `abierta_en`; si no
  hay, crea una visita nueva (el trabajo atrasado no se pega a un turno futuro). Si ya hay
  una abierta, la devuelve sin cambios.
- **Reenvío de `abrir`**: ante un 409 `visita_no_abierta`, la app reenvía `POST visitas/abrir/`
  con el `qr_codigo` del punto y su `abierta_en` original, recibe la visita abierta (la
  nueva o la que ya existía) y reintenta la revisión, el reporte o el cierre contra ese id,
  con el mismo `cliente_uuid`. Lo cerrado no se toca.
- **Servicio enviado** (`servicio`, id opcional en `POST revisiones/`): sin él, o igual al que
  decide el servidor, no cambia nada. Si difiere, el servidor busca un servicio activo de la
  empresa (otro id, inactivo o de otra empresa da 400 en `campos.servicio`), guarda la
  revisión con ese servicio, valida la planilla contra el `esquema_punto` de ese servicio y la
  marca con una incidencia que cuenta en "Incidencias sin revisar" del panel. Vale también
  cuando el servidor no encontraba servicio para el punto o el suyo estaba de baja. En una
  visita nueva sin ítems la comparación es contra el servicio del punto.
- **Datos sin conexión** (`GET /api/v1/me/datos-sin-conexion/`): `{puntos[], servicios[]}`
  con todos los puntos activos de la empresa (de sitios y clientes activos), no solo los de
  los turnos del empleado, y los servicios activos.
  - Cada punto: `{id, qr_hash, nombre, sector, sitio{id, nombre, direccion, localidad},
    servicio, estado, proximo_vencimiento, ultima_revision_fecha}`. `servicio` es el id del servicio
    del punto o `null`; `estado` usa la regla de `me/visitas/`; `ultima_revision_fecha` es la
    fecha local (`AAAA-MM-DD`, sin hora ni operario) de la última revisión del punto en una
    visita abierta o realizada que cuenta como servicio, o `null`.
  - `qr_hash` es el SHA-256 en hexadecimal (minúsculas) de `str(qr_codigo)`, con el UUID en
    minúsculas y con guiones. La respuesta nunca trae `qr_codigo`. La app calcula el mismo
    hash del código que escanea y lo busca entre los `qr_hash` descargados; sigue mandando el
    código escaneado en `abrir` y en `revisiones/`, porque el QR es la prueba de presencia.
  - Cada servicio: `{id, nombre, slug, esquema_punto, esquema_visita}`, igual que en el
    resolver de QR.
  - Límite: 30 pedidos por hora y usuario, y el 304 también cuenta; superado, 429 con
    `Retry-After`.
  - Lleva `ETag`; con `If-None-Match` igual responde 304 sin cuerpo. El 200 y el 304 llevan
    `Cache-Control: private, no-store`: la app guarda el ETag y los datos en su almacenamiento,
    no en una caché HTTP compartida.
- **Puntos no revisados** (`POST /api/v1/visitas/<pk>/no-revisados/`, multipart): registra una
  estación que no se pudo revisar en una visita abierta propia. Lleva `punto` (id de un punto
  activo del sitio de la visita), `motivo` (`falta_estacion`, `codigo_ilegible`, `sin_acceso`
  u `otro`), `cliente_uuid` (obligatorio) y, opcionales, `detalle`, `latitud`, `longitud`,
  `precision_m` y una `foto` (hasta 8 MB). Responde 201 con `{id, visita, punto{id, nombre},
  motivo, detalle, creado}`, sin coordenadas ni foto. No es una revisión: no mueve
  el vencimiento del punto; sí permite cerrar una visita que no tiene revisiones (ver Cierre). Un punto por visita: un segundo
  reporte del mismo punto, un punto de otro sitio o inactivo dan 400 en `campos.punto`; una
  visita propia que no está abierta, 409 con `code: "visita_no_abierta"`; una visita ajena, de
  otra empresa o inexistente, 404, aun con el cuerpo vacío. Un `cliente_uuid` ya registrado
  responde 409; los ids del reporte existente (`reporte`, `visita`) vienen solo si es del
  mismo empleado.
- **Cierre** (`POST /api/v1/visitas/<pk>/cerrar/`): la visita abierta propia necesita al menos
  una revisión o un punto reportado como no revisado; sin ninguno de los dos responde 400. Una
  visita cerrada con solo reportes queda `realizada` con `sin_revisiones: true`, no mueve el
  vencimiento de ningún punto y sus reportes cuentan como incidencia sin revisar en el panel. El
  cierre nocturno del sistema aplica la misma regla. La respuesta del cierre y cada visita de
  `GET /api/v1/me/historial/` traen `sin_revisiones` (booleano); `me/visitas/` no cambia.
- **Empresa** (`GET /api/v1/me/empresa/`): `{nombre, logo}`, con `logo` como URL absoluta de
  `GET /api/v1/empresas/<pk>/logo/` o `null` si la empresa no tiene logo. El logo es un PNG
  con `Cache-Control: private, no-store`; un `<pk>` que no es la empresa del usuario o una
  empresa sin logo dan 404.
- **Resolver un QR** (`POST /api/v1/qr/<codigo>/resolver/`): el `punto` trae `estado`
  (`al_dia`, `proxima`, `vencida` o `sin_programar`; `proxima` según los días de aviso de su
  `frecuencia_dias`, como en `me/visitas/`), `proximo_vencimiento`, `en_turno`,
  `servicio` (`{id, nombre, slug, esquema_punto, esquema_visita}` o `null`) y `revisado_hoy_por`:
  `{operario{id, nombre}, realizada_en, propia}` con la última revisión de hoy del punto (de
  cualquier empleado de la empresa; `propia` indica si es del usuario) o `null`. `visita_destino`
  es el id de la visita en la que se guardará la revisión (la abierta propia del sitio o, si
  no hay, la pendiente que abre `visitas/abrir/`), o `null` si al abrir se crea una nueva.
  `servicio` y `en_turno` se calculan sobre esa visita: el del ítem del punto en ella
  (`en_turno` verdadero) o, si no lo tiene, el del punto (`en_turno` falso); es el mismo
  servicio con el que se guarda la revisión. Además `visita_pendiente_propia` y
  `visita_abierta_propia`.
- **Revisiones**, fotos y servicio: `fotos` se repite de 0 a 2 veces. El servidor decide el
  servicio de la revisión (el del ítem del turno para ese punto o, fuera del turno, el del
  punto) y la respuesta lo devuelve en `servicio{id, nombre}` junto con `fuera_de_turno`.
  Si no hay ítem y el punto no tiene servicio, responde 400 con
  `campos.qr_codigo = "El punto no tiene servicio asignado."`: un punto creado en campo
  nace sin servicio hasta que el administrador le asigne uno. Ese punto llega al resolver
  con `servicio` nulo y su revisión fuera de turno da 400 hasta que lo tenga. Un punto con
  plano pero sin `x`/`y` no aparece en `plano.puntos`, y un cliente inactivo da 404.
- **Throttle**: `-` es sin límite propio. Los cupos salen de `DEFAULT_THROTTLE_RATES`
  (`token` 10/min, `qr` 30/min, `crear_visita` 120/hora, `alta_campo` 300/hora), de
  la renovación de tokens (30/min) y de `me/datos-sin-conexion/` (30/hora por usuario). Al excederlos la API responde 429, siempre con la
  cabecera `Retry-After` (segundos de espera), también la del balde de fallos de login.
- **Usuario `plataforma`**: en `auth/token/` y `auth/token/refresh/` recibe 401 con el mismo
  `detalle` que una credencial inválida (no se distingue). `auth/token/` responde 400 si
  falta el usuario o la contraseña. `plataforma` no obtiene ni renueva tokens, así que no
  usa la API.
- **Esquema y documentación** (`schema/`, `docs/`): exigen token o sesión de una empresa
  activa; `plataforma` no entra. Sin credenciales, 401.
- **Errores**: todo error es `{"detalle", "campos"}`. Un `__all__` de Django va a `detalle`.
  Un `non_field_errors` de primer nivel va a `detalle`; uno anidado va a `campos` bajo su
  ruta (`productos_aplicados.0`).
- **404 JSON**: una ruta inexistente bajo `/api/` responde 404 con
  `{"detalle": "No encontrado.", "campos": {}}`. Un código de QR mal formado en
  `qr/<codigo>/resolver/` responde el mismo 404 que un QR inexistente:
  `{"detalle": "El código QR no corresponde a un sitio activo.", "campos": {}}`.

| Método | Ruta | Auth | Throttle | Respuesta |
|---|---|---|---|---|
| GET | `/api/v1/` | JWT | - | 200 con el usuario, su empresa y su rol |
| POST | `/api/v1/auth/token/` | Pública | token, 10/min por IP | 200 con `access` y `refresh`; 400, 401, 415, 429 |
| POST | `/api/v1/auth/token/refresh/` | Pública | renovación, 30/min por IP | 200 con un `access` nuevo; 401, 415, 429 |
| GET | `/api/v1/schema/` | JWT de empresa activa | - | 200 con el esquema OpenAPI; 401 |
| GET | `/api/v1/docs/` | JWT o sesión de empresa activa | - | 200 con la documentación interactiva; 401 |
| POST | `/api/v1/qr/<codigo>/resolver/` | Empleado o administrador | qr, 30/min | 200 con el punto, su servicio y estado, y mis visitas; 404 |
| GET | `/api/v1/planos/<pk>/imagen/` | Empleado o administrador | - | 200 con la imagen; 404 |
| POST | `/api/v1/sitios/` | Administrador | alta_campo, 300/hora | 201 con el sitio; 400, 403 |
| POST | `/api/v1/sitios/<pk>/puntos/` | Administrador | alta_campo, 300/hora | 201 con el punto; 400, 403, 404 |
| POST | `/api/v1/puntos/<pk>/ubicacion/` | Administrador | alta_campo, 300/hora | 200 con el punto; 400, 403, 404 |
| GET | `/api/v1/me/puntos/` | Empleado o administrador | - | 200 con los puntos del usuario |
| GET | `/api/v1/me/datos-sin-conexion/` | Empleado o administrador | datos_sin_conexion, 30/hora por usuario | 200 con los puntos y servicios de la empresa; 304; 429 |
| GET | `/api/v1/productos/` | Empleado o administrador | - | 200 con el catálogo; 304 |
| GET | `/api/v1/me/visitas/` | Empleado o administrador | - | 200 con los turnos del usuario y sus ítems |
| GET | `/api/v1/me/visitas/<pk>/` | Empleado o administrador | - | 200 con el turno; 404 |
| POST | `/api/v1/visitas/abrir/` | Empleado o administrador | crear_visita, 120/hora | 201 con el turno; 200 si ya estaba abierto; 400 |
| POST | `/api/v1/visitas/<pk>/abrir/` | Empleado o administrador | crear_visita, 120/hora | 201 con el turno; 200 si ya había una abierta en el sitio; 400, 404, 409 |
| POST | `/api/v1/visitas/<pk>/cerrar/` | Empleado o administrador | crear_visita, 120/hora | 200 con la visita; 400, 404, 409 (`visita_no_abierta`, `visita_ya_cerrada`) |
| POST | `/api/v1/visitas/<pk>/no-revisados/` | Empleado o administrador | crear_visita, 120/hora | 201 con el reporte; 400, 404, 409, 413 |
| POST | `/api/v1/revisiones/` | Empleado o administrador | crear_visita, 120/hora | 201 con la revisión, su servicio y `duplicada_hoy`; 400, 404, 409, 413 |
| GET | `/api/v1/me/historial/` | Empleado | - | 200 con el historial paginado |
| GET | `/api/v1/fotos/<codigo>/` | Empleado o administrador | - | 200 con la imagen; 403, 404 |
| GET | `/api/v1/me/empresa/` | Empleado o administrador | - | 200 con el nombre y la URL del logo |
| GET | `/api/v1/empresas/<pk>/logo/` | Empleado o administrador | - | 200 con la imagen; 404 |
