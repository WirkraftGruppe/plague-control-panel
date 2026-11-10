#!/usr/bin/env bash
# Hook SessionStart de Claude Code: inyecta en el contexto de la sesión el estado actual de la
# bitácora y su última entrada, el encabezado y la tabla de estado del plan activo, las últimas
# decisiones y el resumen de pendientes. Lo que se imprime por stdout con exit 0 se agrega al
# contexto. Termina siempre con exit 0.
#
# Todo va recortado (líneas por sección y caracteres por línea): esto entra en cada sesión antes
# de trabajar, y el detalle está a un comando de distancia. Meta: menos de 8000 bytes en total.
set +e

MAX_ANCHO=240            # bytes por línea
MAX_ENTRADA=12           # líneas de la última entrada de la bitácora
MAX_ENCABEZADO_PLAN=16   # líneas del encabezado del plan
MAX_DECISIONES=5         # últimas decisiones

# Recorta cada línea a MAX_ANCHO bytes; iconv descarta el carácter que haya quedado partido.
cortar() {
  if command -v iconv >/dev/null 2>&1; then
    cut -b1-"$MAX_ANCHO" | iconv -c -f UTF-8 -t UTF-8 2>/dev/null
  else
    cut -b1-"$MAX_ANCHO"
  fi
}

raiz="${CLAUDE_PROJECT_DIR:-.}"
if command -v cygpath >/dev/null 2>&1; then
  normalizada="$(cygpath -u "$raiz" 2>/dev/null)"
  [ -n "$normalizada" ] && raiz="$normalizada"
fi

bitacora="$raiz/docs/bitacora.md"
decisiones="$raiz/docs/decisiones.md"

# 1. Bitácora: todo lo anterior a "## Entradas" (el estado actual) y la entrada más reciente.
if [ -f "$bitacora" ]; then
  echo "=== docs/bitacora.md (estado actual y última entrada) ==="
  tr -d '\r' < "$bitacora" 2>/dev/null | awk -v max="$MAX_ENTRADA" '
    /^## Entradas/ { entradas = 1; print; next }
    !entradas { if (++estado <= 40) print; next }
    /^### / { if (++vistas > 1) exit }
    vistas == 1 { if (++n <= max) print; else if (n == max + 1) print "(… la entrada sigue en docs/bitacora.md)" }
  ' | cortar
  echo
fi

# 2. Plan activo: encabezado hasta el primer "### T" y la tabla "### Estado de subtareas".
# El plan se deriva primero de la rama (plan/<slug> o <slug>-T<n>): el único
# docs/planes/AAAA-MM-DD-<slug>.md. Sin rama, slug inválido, cero o varias coincidencias,
# se cae en "Plan activo:" de la bitácora.
plan_rama=""
rama="$(git -C "$raiz" branch --show-current 2>/dev/null | tr -d '\r')"
slug=""
case "$rama" in
  plan/*) slug="${rama#plan/}" ;;
  *-T*)
    sufijo="${rama##*-T}"
    if printf '%s' "$sufijo" | grep -Eq '^[0-9]+[a-z]?$'; then slug="${rama%-T"$sufijo"}"; fi
    ;;
esac
if [ -n "$slug" ] && printf '%s' "$slug" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  coincidencias=0
  for archivo in "$raiz"/docs/planes/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-"$slug".md; do
    if [ -f "$archivo" ]; then
      coincidencias=$((coincidencias + 1))
      plan_rama="docs/planes/$(basename "$archivo")"
    fi
  done
  if [ "$coincidencias" -ne 1 ]; then
    plan_rama=""
  fi
  if [ -L "$raiz/docs" ] || [ -L "$raiz/docs/planes" ] || [ -L "$raiz/$plan_rama" ]; then
    plan_rama=""
  fi
fi

if [ -f "$bitacora" ] || [ -n "$plan_rama" ]; then
  plan="$(grep -m1 '^Plan activo:' "$bitacora" 2>/dev/null | tr -d '\r' \
    | sed -e 's/^Plan activo:[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^`//' -e 's/`$//')"
  # Solo se acepta un archivo .md directamente dentro de docs/planes/, sin "..", sin ruta
  # absoluta, sin subcarpetas, sin barras invertidas y sin symlinks.
  plan_valido=0
  case "$plan" in
    docs/planes/*.md)
      resto="${plan#docs/planes/}"
      plan_valido=1
      case "$plan" in
        *..*|/*|*\\*|[A-Za-z]:*) plan_valido=0 ;;
      esac
      case "$resto" in
        */*|.md) plan_valido=0 ;;
      esac
      if [ -L "$raiz/docs" ] || [ -L "$raiz/docs/planes" ] || [ -L "$raiz/$plan" ]; then
        plan_valido=0
      fi
      ;;
  esac
  origen="por bitácora"
  if [ -n "$plan_rama" ]; then
    plan="$plan_rama"
    plan_valido=1
    origen="por rama $rama"
  fi
  if [ -z "$plan_rama" ] && [ -n "$plan" ] && [ "$plan" != "(ninguno)" ] && [ "$plan_valido" -ne 1 ]; then
    echo "(Plan activo ignorado: fuera de docs/planes/)"
    echo
  fi
  if [ "$plan_valido" -eq 1 ] && [ -f "$raiz/$plan" ]; then
    echo "=== Plan activo ($origen): $plan (encabezado, sin subtareas) ==="
    tr -d '\r' < "$raiz/$plan" 2>/dev/null | awk -v max="$MAX_ENCABEZADO_PLAN" '
      /^### T/ { exit }
      { if (++n <= max) print; else resto++ }
      END { if (resto) print "(… " resto " líneas más del encabezado en el plan)" }
    ' | cortar
    echo
    echo "=== Plan activo ($origen): $plan (estado de subtareas) ==="
    tr -d '\r' < "$raiz/$plan" 2>/dev/null | awk '
      /^### Estado de subtareas/ { dentro = 1; print; next }
      dentro && /^#/ { exit }
      dentro && /^[[:space:]]*$/ { if (visto_tabla) exit; next }
      dentro { print; if ($0 ~ /^\|/) visto_tabla = 1 }
    '
    echo
  fi
fi

# 3. Últimas decisiones.
if [ -f "$decisiones" ]; then
  echo "=== docs/decisiones.md (últimas $MAX_DECISIONES líneas) ==="
  tail -n "$MAX_DECISIONES" "$decisiones" 2>/dev/null | tr -d '\r' | cortar
  echo
fi

# 4. Resumen de pendientes abiertos de todos los planes: recuento y solo bloqueantes e
#    importantes (py -3, si no python3). Sin Python, avisa y sigue.
echo "=== Pendientes abiertos (pendientes.py) ==="
raiz_py="$raiz"
if command -v cygpath >/dev/null 2>&1; then
  convertida="$(cygpath -w "$raiz" 2>/dev/null)"
  [ -n "$convertida" ] && raiz_py="$convertida"
fi
guion="$(dirname "$0")/pendientes.py"
if command -v py >/dev/null 2>&1 && py -3 -c "" >/dev/null 2>&1; then
  py -3 "$guion" --raiz "$raiz_py" --resumen 2>/dev/null | tr -d '\r'
elif command -v python3 >/dev/null 2>&1; then
  python3 "$guion" --raiz "$raiz_py" --resumen 2>/dev/null | tr -d '\r'
else
  echo "(Python no disponible: no se pudieron listar los pendientes)"
fi
echo

exit 0
