# Contrato de la API v1

Actualizado: 2026-10-19

Resumen legible para la app móvil de Detach. La fuente completa (cuerpos, campos,
códigos de error) es `docs/api/openapi-v1.yaml`; este archivo agrega, por ruta, el
límite de pedidos (throttle) y el rol que la puede usar. Todas las rutas cuelgan de
`/api/v1/` y responden JSON.

- **Auth**: `JWT` es un token de acceso en `Authorization: Bearer <token>` de cualquier
  usuario autenticado; `Empleado o administrador`, `Administrador` y `Empleado` piden
  además ese rol; `Pública` no pide token.
- **Catálogo de productos** (`GET /api/v1/productos/`): cada producto trae `unidad_base`
  (unidad en que se lleva el stock), `modo_unidad` (`unica` o `equivalentes`) y
  `unidades_permitidas` (las unidades en que se puede declarar una cantidad: solo la base
  en `unica`; todas las de su magnitud en `equivalentes`).
- **Revisiones** (`POST /api/v1/revisiones/`, multipart): `productos_aplicados` es texto
  JSON con una lista; cada ítem lleva `producto`, `lote`, `dosis`, `unidad_dosis`,
  `cantidad` y `unidad` (una de las `unidades_permitidas`). El servidor convierte a la
  unidad base y descuenta el stock en la misma transacción. Los errores de validación
  van anidados por ítem: `productos_aplicados.<i>.<campo>`.
- **Throttle**: `-` es sin límite propio. Los cupos salen de `DEFAULT_THROTTLE_RATES`
  (`token` 10/min, `qr` 30/min, `crear_visita` 120/hora, `alta_campo` 300/hora) y de
  la renovación de tokens (30/min). Al excederlos la API responde 429.

| Método | Ruta | Auth | Throttle | Respuesta |
|---|---|---|---|---|
| GET | `/api/v1/` | JWT | - | 200 con el rol del usuario |
| POST | `/api/v1/auth/token/` | Pública | token, 10/min por IP | 200 con `access` y `refresh`; 401, 415, 429 |
| POST | `/api/v1/auth/token/refresh/` | Pública | renovación, 30/min por IP | 200 con un `access` nuevo; 401, 415, 429 |
| GET | `/api/v1/schema/` | JWT | - | 200 con el esquema OpenAPI |
| GET | `/api/v1/docs/` | JWT | - | 200 con la documentación interactiva |
| POST | `/api/v1/qr/<codigo>/resolver/` | Empleado o administrador | qr, 30/min | 200 con el punto de control |
| GET | `/api/v1/planos/<pk>/imagen/` | Empleado o administrador | - | 200 con la imagen; 404 |
| POST | `/api/v1/sitios/` | Administrador | alta_campo, 300/hora | 201 con el sitio; 400, 403, 404 |
| POST | `/api/v1/sitios/<pk>/puntos/` | Administrador | alta_campo, 300/hora | 201 con el punto; 400, 403, 404 |
| POST | `/api/v1/puntos/<pk>/ubicacion/` | Administrador | alta_campo, 300/hora | 200 con el punto; 400, 403, 404 |
| GET | `/api/v1/me/puntos/` | Empleado o administrador | - | 200 con los puntos del usuario |
| GET | `/api/v1/productos/` | Empleado o administrador | - | 200 con el catálogo; 304 |
| GET | `/api/v1/me/visitas/` | Empleado o administrador | - | 200 con las visitas del usuario |
| POST | `/api/v1/visitas/abrir/` | Empleado o administrador | crear_visita, 120/hora | 201 con la visita; 200 si ya estaba abierta; 400 |
| POST | `/api/v1/visitas/<pk>/cerrar/` | Empleado o administrador | crear_visita, 120/hora | 200 con la visita; 400, 404, 409 |
| POST | `/api/v1/revisiones/` | Empleado o administrador | crear_visita, 120/hora | 201 con la revisión; 400, 404, 409, 413 |
| GET | `/api/v1/me/historial/` | Empleado | - | 200 con el historial paginado |
| GET | `/api/v1/fotos/<codigo>/` | Empleado o administrador | - | 200 con la imagen; 403, 404 |
