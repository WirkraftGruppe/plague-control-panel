# Detach — Sistema visual del panel

Dirección elegida: **A · "Industrial certificada"**. Un solo tema, **claro**, para el panel de gestión: los administradores lo usan horas, el fondo claro cansa menos y las tablas se leen mejor. El amarillo de marca se reserva para acciones, acentos y estado; nunca para grandes fondos de texto. El sitio público de cada empresa tiene su propio sistema visual en su repositorio.

## Color

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#f4f3ef` | fondo de página |
| `--surface` | `#ffffff` | tarjetas, paneles, filas |
| `--surface-2` | `#eceae4` | bloques secundarios, hover de filas |
| `--border` | `#d9d6cf` | líneas divisorias, bordes de tarjeta |
| `--border-strong` | `#b9b5ab` | bordes de inputs, botones secundarios |
| `--text` | `#15191c` | texto principal |
| `--text-muted` | `#4f565c` | texto secundario |
| `--text-faint` | `#7f8890` | metadatos |
| `--brand` | `#ffc600` | amarillo del logo (medido sobre el PNG: rgb 255,198,0) |
| `--brand-hover` | `#e6b200` | hover de enlaces y botones |
| `--on-brand` | `#0f1417` | texto sobre amarillo |
| `--on-brand-muted` | `#3a3410` | texto secundario sobre amarillo |
| `--brand-tint` | `#fff7d6` | fondo de avisos, con borde `#e6c95c` |

Estados (semáforo de proyectos y visitas):

| Estado | Color | Uso |
|---|---|---|
| `--ok` | `#2e9e5b` | al día / visita realizada |
| `--warn` | `#ffc600` | próxima a vencer (usa el amarillo de marca) |
| `--danger` | `#d9463e` | vencida / incidencia |
| `--neutral` | `#7f8890` | sin programar / pausado |

Los marcadores del mapa Leaflet usan estos cuatro colores con el mismo significado.

## Tipografía

- **Display**: `Barlow Condensed` 600 / 700 / 800 — títulos, cifras grandes, botones. Mayúsculas solo en cifras y etiquetas.
- **Texto**: `Barlow` 400 / 500 / 600 — cuerpo, tablas, formularios.
- Fallback: `system-ui, sans-serif`. Se sirven desde `static/fonts/` (woff2, subconjunto latin, licencia OFL), sin pedidos a terceros.

Escala (px):

| Rol | Tamaño / interlineado | Fuente |
|---|---|---|
| H1 panel | 32 / 1.1 | Barlow Condensed 700 |
| H2 panel / título de tarjeta | 22–26 / 1.1 | Barlow Condensed 700 |
| Cifra destacada | 30–34 / 1.05 | Barlow Condensed 700, color `--brand` |
| Etiqueta ("eyebrow") | 13–14, uppercase, tracking 0.12–0.14em | Barlow 600, color `--brand` |
| Cuerpo | 15–17 / 1.5 | Barlow 400 |
| Texto de tabla | 14 / 1.4 | Barlow 400/500 |
| Metadato | 13 | Barlow 400, `--text-faint` |

## Espaciado y forma

- Base 4 px. Margen lateral de página: 64 px en escritorio, 20 px en móvil. Ancho máximo de contenido: 1280 px.
- Radio: 4 px (botones, inputs), 6 px (tarjetas), 8 px (bloques grandes). Sin píldoras salvo las etiquetas de estado (999 px).
- Bordes de 1 px con `--border`; sombra suave opcional `0 1px 2px rgba(0,0,0,.06)`.

## Componentes

- **Botón primario**: fondo `--brand`, texto `--on-brand`, Barlow 700 15–16 px uppercase tracking 0.06em, alto 46–54 px, padding 0 22–28 px, radio 4.
- **Botón secundario**: transparente, borde 1.5 px `--border-strong`, texto `--text`.
- **Enlace**: color `--brand`, hover `--brand-hover`, subrayado al hover.
- **Tarjeta**: fondo `--surface`, borde `--border`, radio 6, padding 22–24 px; número o etiqueta en `--brand` arriba, título 19 px 600, descripción 14 px `--text-muted`.
- **Tabla**: cabecera Barlow 600 13 px uppercase `--text-muted`; filas 44 px con borde inferior `--border`; hover `--surface-2`; estado con punto de color + texto.
- **Formulario**: etiqueta 13 px uppercase tracking 0.08em `--text-muted`; input alto 46–48 px, fondo `--surface`, borde `--border-strong`, radio 4, foco con borde `--brand`.
- **Etiqueta de estado**: 12 px 600 uppercase, padding 4 px 8 px, radio 999, fondo tenue del color del estado.

Responsive: a menos de 900 px las grillas pasan a 1 columna y la barra de navegación se reduce a logo + menú.

## Recursos

- Logo: `static/img/logo.png` (amarillo, fondo transparente). En las plantillas el texto alternativo sale de `NOMBRE_EMPRESA`.
