# Detach — Sistema visual del panel

Un solo tema, claro y neutro, para el panel de gestión. Fuente de verdad del código: `templates/base.html` (tokens), `static/css/panel.css` (componentes), `templates/panel/base.html` (barra lateral y panel lateral) y `apps/panel/static/panel/panel_lateral.js` (comportamiento del panel lateral). Los contrastes los verifica `apps/panel/tests/test_diseno_tokens.py`. El sitio público vive en otro repositorio y tiene su propio sistema visual.

## Alcance

- Uso solo en computadora. Ancho mínimo soportado: 1280 px (`.panel { min-width: 1280px }`). No hay versión móvil ni puntos de corte.
- Las plantillas de dominio consumen los tokens y las clases; no declaran colores propios ni editan `base.html` ni `panel.css`.
- El nombre de la empresa sale de `NOMBRE_EMPRESA`; ninguna plantilla lo escribe. El logo es `static/img/logo.png`, con el texto alternativo tomado de `NOMBRE_EMPRESA`.

## Color

Tokens declarados en `:root` de `templates/base.html`.

### Superficies, bordes y texto

| Variable | Valor | Uso |
|---|---|---|
| `--bg` | `#F5F6F7` | fondo de página |
| `--surface` | `#FFFFFF` | tarjetas, tablas, formularios, panel lateral |
| `--surface-2` | `#EEF0F2` | bloques secundarios, hover de botón secundario y de menú |
| `--border` | `#DFE2E6` | divisorias y bordes de bloque |
| `--border-strong` | `#C5CAD1` | bordes de campos y botón secundario |
| `--text` | `#1A1E23` | texto principal |
| `--text-muted` | `#545C66` | texto secundario |
| `--text-faint` | `#646C76` | metadatos, ayudas, grupo "Administración" |

`--text-faint` es `#646C76` y no `#6B737D` (el valor aprobado en el Adjunto): `#6B737D` sobre `--bg` da 4,44:1, bajo el mínimo de 4,5:1; `#646C76` da 4,92:1.

### Acción y navegación activa

| Variable | Valor | Uso |
|---|---|---|
| `--accion` | `#1F5FD1` | botón primario, enlaces, foco, borde de pestaña activa |
| `--accion-hover` | `#174AA6` | hover de `--accion` |
| `--sobre-accion` | `#FFFFFF` | texto sobre `--accion`, `--accion-hover` y `--vencido-texto` |
| `--activo-fondo` | `#EAF1FD` | fondo del menú activo, fila elegida, aviso informativo |
| `--activo-texto` | `#1F5FD1` | texto del menú activo y de la pestaña activa |

### Estados

Cada estado tiene tres tokens: punto (marcadores, puntos de color), fondo y texto del chip.

| Estado | `--*-punto` | `--*-fondo` | `--*-texto` |
|---|---|---|---|
| vencido | `--vencido-punto` `#D92D20` | `--vencido-fondo` `#FDECEA` | `--vencido-texto` `#B42318` |
| próximo | `--proximo-punto` `#E0A100` | `--proximo-fondo` `#FFF4D6` | `--proximo-texto` `#7A4F00` |
| al día | `--al-dia-punto` `#2E9E5B` | `--al-dia-fondo` `#E6F4EC` | `--al-dia-texto` `#1B6B3C` |
| sin fecha | `--sin-fecha-punto` `#9AA1A9` | `--sin-fecha-fondo` `#EEF0F2` | `--sin-fecha-texto` `#4A525B` |

Los marcadores del mapa Leaflet usan los cuatro colores `*-punto` con el mismo significado.

Alias temporales en `base.html`: `--ok`, `--warn`, `--danger` y `--neutral` apuntan a los `*-punto` de al día, próximo, vencido y sin fecha. Existen solo para hojas de otras apps que aún los usan; el código nuevo usa los tokens de estado y los alias se eliminan cuando nada los referencie.

### Reglas de color

- Rojo, ámbar y verde se usan solo para estados (vencido, próximo, al día) y errores. Nunca decoran.
- Un estado nunca se comunica solo con color: el chip lleva siempre texto ("Vencido", "Próximo", "Al día", "Sin fecha") además del punto.
- El texto de un chip usa `--*-texto`, no `--*-punto`.
- El azul `--accion` se reserva para acciones, enlaces, foco y selección.

### Contrastes medidos (WCAG, mínimo 4,5:1)

| Texto | Fondo | Razón |
|---|---|---|
| `--text` | `--bg` / `--surface` / `--surface-2` | 15,48 / 16,75 / 14,66 |
| `--text-muted` | `--bg` / `--surface` / `--surface-2` | 6,26 / 6,77 / 5,93 |
| `--text-faint` | `--bg` / `--surface` | 4,92 / 5,32 |
| `--sobre-accion` | `--accion` / `--accion-hover` / `--vencido-texto` | 5,81 / 8,18 / 6,57 |
| `--accion` | `--surface` / `--bg` | 5,81 / 5,37 |
| `--accion-hover` | `--surface` | 8,18 |
| `--activo-texto` | `--activo-fondo` | 5,12 |
| `--vencido-texto` | `--vencido-fondo` | 5,75 |
| `--proximo-texto` | `--proximo-fondo` | 6,51 |
| `--al-dia-texto` | `--al-dia-fondo` | 5,76 |
| `--sin-fecha-texto` | `--sin-fecha-fondo` | 6,94 |

`--text-faint` no se usa sobre `--surface-2`.

## Tipografía

- Una sola familia: `Barlow`, pesos 400, 500, 600 y 700. Fallback: `system-ui, sans-serif`.
- Vendorizada: `static/fonts/barlow-latin-<peso>-normal.woff2` (subconjunto latin), declarada con `@font-face` en `base.html`. Sin pedidos a terceros.
- Cuerpo 16 px / 1.5. `h1`, `h2` y `h3` en 700. Título del panel (`.panel-contenido h1`): 28 px; subtítulo (`h2`): 20 px; cifra de contador: 32 px / 1.1 en 700. Texto de tabla: 15 px. Ayudas y metadatos: `--text-faint`.
- Mayúsculas solo en cabeceras de tabla, etiquetas de campo y la marca del pie de la barra.

## Forma y medidas

| Variable | Valor | Uso |
|---|---|---|
| `--radio-control` | `6px` | botones, campos, miniaturas |
| `--radio-bloque` | `8px` | tablas, formularios, contadores, mapa |
| `--radio-chip` | `999px` | chips de estado |
| `--ancho-barra` | `232px` | ancho de la barra lateral |

- Alturas de control: botón 36 px (`.boton`), botón grande 46 px (`.boton-grande`), campo mínimo 40 px, fila de tabla 46 px, enlace de menú 38 px (secundario 34 px). Rango de controles: 36–46 px.
- Bordes de 1 px con `--border`; campos y botón secundario con `--border-strong`.
- Contenido: relleno de 24 px vertical y 32 px lateral (`.panel-contenido`).

## Barra lateral

`<aside class="barra-lateral">` de 232 px, fija a la altura de la ventana, en `templates/panel/base.html`. Orden:

1. Logo (`.panel-logo`), enlace a `/panel/`.
2. `<nav aria-label="Principal">` con dos grupos (`.menu-grupo`):
   - **Trabajo**: Sitios (con contador de vencidos, `.contador-vencidos`), Turnos (con contador de incidencias sin revisar, `.contador-menu`), Mapa.
   - **Administración** (`.menu-grupo-secundario`, enlaces `.menu-enlace-secundario`, más discretos): Clientes, Catálogo (servicios y productos), Usuarios.
3. Pie (`.barra-pie`): nombre del usuario, formulario "Salir" (`.formulario-en-linea`) y la marca.

El enlace de la sección actual lleva `aria-current="page"`; el estilo activo (`--activo-fondo`, `--activo-texto`, peso 600) se aplica sobre ese atributo, no sobre una clase. Cada enlace aparece solo si su ruta existe (`{% url ... as u %}`). El bloque `barra_lateral` puede sustituirse; `cabecera` reemplaza el pie.

## Componentes

Todos en `static/css/panel.css`.

- **Botones** (`.boton`): 36 px, Barlow 600 15 px, radio 6. Variantes: `.boton-primario` (`--accion` con texto `--sobre-accion`), `.boton-secundario` (fondo `--surface`, borde `--border-strong`), `.boton-peligro` (`--vencido-texto`, hover `--vencido-punto`; solo para acciones destructivas) y `.boton-grande` (46 px). Una acción principal por pantalla.
- **Enlace** (`.enlace` y `a`): `--accion`, hover `--accion-hover`.
- **Chips de estado** (`.etiqueta-estado` con `.etiqueta-ok`, `.etiqueta-warn`, `.etiqueta-danger` o `.etiqueta-neutral`): radio 999, punto de 8 px a la izquierda y texto obligatorio. Fondo y texto salen de los tokens del estado.
- **Tablas** (`.tabla`): fondo `--surface`, borde `--border`, radio 8, filas de 46 px con borde inferior, hover `--bg`; cabecera en mayúsculas `--text-muted`; encabezados ordenables con `.th-orden`; fila elegida `.fila-elegida`, fila resaltada `.fila-resaltada`. `.planilla` es la variante de pares campo/valor.
- **Formularios** (`.formulario`, `.confirmar`): cada campo en `.campo` con `label` visible; campo de 40 px mínimo con borde `--border-strong` y foco en `--accion`; `.campo-error` pinta el borde con `--vencido-punto` y el mensaje (`.error`, `.errores`) usa `--vencido-texto`; `.ayuda` en `--text-faint`; botones en `.acciones`. `.buscador` es el campo de búsqueda de los listados.
- **`.formulario-en-linea`**: formulario sin margen ni relleno, `display: inline`, para un botón de envío (POST) dentro de una fila o de la barra, como "Salir".
- **Pestañas** (`.pestanas`): enlaces con borde inferior; la activa lleva `aria-current="page"`, `--activo-texto`, borde `--accion` y peso 600.
- **Avisos** (`.mensajes` > `.mensaje` con `.mensaje-success`, `.mensaje-info`, `.mensaje-warning` o `.mensaje-error`): fondo, borde y texto de los tokens del estado correspondiente. Se renderizan con `panel/partials/mensajes.html`.
- **Contadores** (`.contadores` > `.contador`): cifra grande (`.contador-cifra`) y etiqueta; `.contador-danger` pinta la cifra con `--vencido-texto`.
- **Paginación** (`.paginacion`, `.paginacion-estado`) y **línea de tiempo** (`.linea-tiempo`) del historial de un punto o sitio.
- **Páginas de error** (`.pagina-error`): autónomas, sin `base.html`; cada `var()` trae su valor de respaldo.

### Panel lateral

Contenedor único `#panel-lateral` en `templates/panel/base.html`: `role="dialog"`, `aria-modal="true"`, `aria-label="Panel lateral"` y `hidden`. Abre desde la derecha, 520 px de ancho (máximo 100 vw), por encima de la página. Estructura interna: `.panel-lateral-cabecera` (título `h2` y botón de cierre), `.panel-lateral-cuerpo` (con desplazamiento) y `.panel-lateral-pie` (fijo abajo, acciones alineadas a la derecha).

Comportamiento (`panel_lateral.js`, cargado con `defer` desde el panel):

- Un elemento con `data-abre-panel` y atributos HTMX (`hx-get`, `hx-target="#panel-lateral"`) pide el contenido; tras el swap el panel se muestra y el foco pasa al primer control.
- Un elemento con `data-cierra-panel` cierra el panel.
- `Escape` cierra el panel.
- `Tab` y `Shift+Tab` circulan solo dentro del panel mientras está abierto.
- Al cerrar se vacía el contenedor y el foco vuelve al elemento que lo abrió.

## Textos de interfaz

- Obligatorios: "Turno" (la unidad de trabajo), "Cargar visita" y "Próximo vencimiento".
- Prohibidos: "Proyecto", "Tablero" y "Visita manual".
- Menú: Sitios, Turnos, Mapa, Clientes, Catálogo, Usuarios. Grupos: "Trabajo" y "Administración".

## CSP

La política usa nonce (`django-csp`). No hay `style=""` ni `<script>` inline sin nonce: los estilos van en `panel.css` o en `<style nonce="{{ request.csp_nonce }}">`, y los scripts en archivos estáticos (`static/…`, `apps/panel/static/panel/`). Los valores dinámicos (por ejemplo posiciones en el plano) se pasan con atributos `data-*` y los aplica un script estático.
