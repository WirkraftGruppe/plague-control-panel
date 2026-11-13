#!/usr/bin/env bash
# Hook SessionStart de Claude Code (método v2): inyecta en el contexto de la sesión el git real
# comparado con la tabla Carriles de docs/estado.md, los worktrees, el estado, el encabezado y la
# tabla de estado del plan activo, las últimas decisiones y el resumen de pendientes. Lo que se
# imprime por stdout con exit 0 se agrega al contexto. Corre también tras una compactación.
# Termina siempre con exit 0.
set +e

MAX_ANCHO=200    # bytes por línea de plan y decisiones
LIMITE=6000      # bytes de salida

# Recorta cada línea a MAX_ANCHO bytes; iconv descarta el carácter que haya quedado partido.
cortar() {
  if command -v iconv >/dev/null 2>&1; then
    cut -b1-"$MAX_ANCHO" | iconv -c -f UTF-8 -t UTF-8 2>/dev/null
  else
    cut -b1-"$MAX_ANCHO"
  fi
}

raiz="${CLAUDE_PROJECT_DIR:-.}"
raiz_original="$raiz"
if command -v cygpath >/dev/null 2>&1; then
  normalizada="$(cygpath -u "$raiz" 2>/dev/null)"
  [ -n "$normalizada" ] && raiz="$normalizada"
fi

# 0. Registro del inicio de sesión. El JSON de SessionStart llega por stdin; `-t 1` evita colgarse
#    con un stdin abierto y sin datos. No imprime nada.
entrada=""
read -r -t 1 entrada 2>/dev/null
script_inicio="$(dirname "$0")/recibo_pendiente.py"
if [ -n "$entrada" ] && [ -f "$script_inicio" ]; then
  if command -v py >/dev/null 2>&1 && py -3 -c "" >/dev/null 2>&1; then python_cmd=(py -3)
  elif command -v python3 >/dev/null 2>&1; then python_cmd=(python3)
  else python_cmd=(python); fi
  printf '%s\n' "$entrada" | CLAUDE_PROJECT_DIR="$raiz_original" "${python_cmd[@]}" "$script_inicio" --inicio >/dev/null 2>&1
fi

estado="$raiz/docs/estado.md"
decisiones="$raiz/docs/decisiones.md"

# Raíz del repositorio donde corre la sesión (la de un worktree es el propio worktree).
top="$(git -C "$raiz" rev-parse --show-toplevel 2>/dev/null | tr -d '\r')"
if [ -n "$top" ] && command -v cygpath >/dev/null 2>&1; then
  top="$(cygpath -u "$top" 2>/dev/null || echo "$top")"
fi
rama="$(git -C "$raiz" branch --show-current 2>/dev/null | tr -d '\r')"

# Plan de la rama (plan/<slug> o <slug>-T<n>): el único docs/planes/AAAA-MM-DD-<slug>.md.
# Sin rama, slug inválido, cero o varias coincidencias, se usa el de `Plan activo:` de estado.md.
plan_rama=""
slug_rama=""
case "$rama" in
  plan/*) slug_rama="${rama#plan/}" ;;
  *-T*)
    sufijo="${rama##*-T}"
    if printf '%s' "$sufijo" | grep -Eq '^[0-9]+[a-z]?$'; then slug_rama="${rama%-T"$sufijo"}"; fi
    ;;
esac
if [ -n "$slug_rama" ] && printf '%s' "$slug_rama" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  coincidencias=0
  for archivo in "$raiz"/docs/planes/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-"$slug_rama".md; do
    if [ -f "$archivo" ]; then
      coincidencias=$((coincidencias + 1))
      plan_rama="docs/planes/$(basename "$archivo")"
    fi
  done
  if [ "$coincidencias" -ne 1 ]; then plan_rama=""; fi
  if [ -L "$raiz/docs" ] || [ -L "$raiz/docs/planes" ] || { [ -n "$plan_rama" ] && [ -L "$raiz/$plan_rama" ]; }; then
    plan_rama=""
  fi
fi

# Plan de estado.md: primer token tras `Plan activo:`, ruta docs/planes/*.md o slug. Solo se acepta
# un .md directamente dentro de docs/planes/, sin "..", sin ruta absoluta, sin barras invertidas
# y sin symlinks.
plan=""
plan_ignorado=0
if [ -f "$estado" ]; then
  token="$(tr -d '\r' < "$estado" | grep -m1 '^Plan activo:' | sed -e 's/^Plan activo:[[:space:]]*//' \
    | awk '{ print $1 }' | tr -d '`' | sed -e 's/[,.;:]*$//')"
  case "$token" in
    ""|ninguno|"(ninguno)") ;;
    */*|*.md|*\\*|*..*)
      valido=1
      case "$token" in
        docs/planes/*.md) ;;
        *) valido=0 ;;
      esac
      case "$token" in *..*|/*|*\\*|[A-Za-z]:*) valido=0 ;; esac
      resto="${token#docs/planes/}"
      case "$resto" in */*|.md) valido=0 ;; esac
      if [ -L "$raiz/docs" ] || [ -L "$raiz/docs/planes" ] || [ -L "$raiz/$token" ]; then valido=0; fi
      if [ "$valido" -eq 1 ] && [ -f "$raiz/$token" ]; then plan="$token"
      elif [ "$valido" -ne 1 ]; then plan_ignorado=1; fi
      ;;
    *)
      if printf '%s' "$token" | grep -Eq '^[a-z0-9][a-z0-9-]*$' && [ ! -L "$raiz/docs" ] && [ ! -L "$raiz/docs/planes" ]; then
        coincidencias=0
        for archivo in "$raiz"/docs/planes/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-"$token".md; do
          if [ -f "$archivo" ] && [ ! -L "$archivo" ]; then
            coincidencias=$((coincidencias + 1))
            plan="docs/planes/$(basename "$archivo")"
          fi
        done
        [ "$coincidencias" -ne 1 ] && plan=""
      fi
      ;;
  esac
fi
origen="por estado.md"
if [ -n "$plan_rama" ]; then
  plan="$plan_rama"
  plan_ignorado=0
  origen="por rama $rama"
fi

# Slug del plan activo (sin ruta, sin fecha y sin .md): clave de la fila en la tabla Carriles.
slug_plan=""
if [ -n "$plan" ]; then
  slug_plan="$(basename "$plan" .md | sed -e 's/^[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}-//')"
fi

# Todo lo que sigue se arma en una función para poder recortar la salida a $LIMITE bytes.
armar_salida() {
# 1. Git real, comparado con la rama que declara la tabla Carriles. Va primero: es lo que más
#    importa y lo que no puede perderse con el recorte.
echo "=== git ==="
if [ -n "$top" ]; then
  ultimo="$(git -C "$raiz" log -1 --format='%h %s' 2>/dev/null | cut -b1-90 | iconv -c -f UTF-8 -t UTF-8 2>/dev/null)"
  sucios="$(git -C "$raiz" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
  echo "${rama:-(HEAD suelto)} @ ${ultimo:-(sin commits)} · $sucios archivo(s) sucio(s)"
  if [ -f "$estado" ] && [ -n "$slug_plan" ]; then
    declarada="$(tr -d '\r' < "$estado" | awk -F'|' -v p="$slug_plan" '
      { for (i = 2; i <= 3; i++) { gsub(/^[ \t`]+|[ \t`]+$/, "", $i) } }
      $2 == p { print $3; exit }')"
    # Solo el nombre de la rama: se descarta lo que sigue al primer espacio o paréntesis.
    declarada="${declarada%%[ (]*}"
    if [ -n "$declarada" ] && [ "$declarada" != "—" ] && [ "$declarada" != "$rama" ]; then
      echo "DIFERENCIA: estado.md dice '$declarada' para $slug_plan y git está en '${rama:-(HEAD suelto)}'"
    fi
  fi
else
  echo "(sin repositorio git)"
fi
echo

# 2. Worktrees: ruta relativa al toplevel y rama.
if [ -n "$top" ]; then
  echo "=== worktrees ==="
  git -C "$raiz" worktree list --porcelain 2>/dev/null | tr -d '\r' | {
    ruta=""
    while IFS= read -r l; do
      case "$l" in
        "worktree "*)
          ruta="${l#worktree }"
          if command -v cygpath >/dev/null 2>&1; then ruta="$(cygpath -u "$ruta" 2>/dev/null || echo "$ruta")"; fi
          if [ "$ruta" = "$top" ]; then ruta="."; else ruta="${ruta#"$top"/}"; fi
          rama_wt="(HEAD suelto)" ;;
        "branch "*) rama_wt="${l#branch refs/heads/}" ;;
        "") [ -n "$ruta" ] && echo "$ruta [$rama_wt]"; ruta="" ;;
      esac
    done
    [ -n "$ruta" ] && echo "$ruta [$rama_wt]"
  }
  echo
fi

# 3. Estado entero; avisa si pasa de 25 líneas o 3000 bytes.
if [ -f "$estado" ]; then
  echo "=== docs/estado.md ==="
  tr -d '\r' < "$estado"
  lineas="$(tr -d '\r' < "$estado" | wc -l | tr -d ' ')"
  bytes="$(tr -d '\r' < "$estado" | wc -c | tr -d ' ')"
  [ "$lineas" -gt 25 ] && echo "(AVISO: estado.md tiene $lineas líneas; el máximo es 25)"
  [ "$bytes" -gt 3000 ] && echo "(AVISO: estado.md tiene $bytes bytes; el máximo es 3000)"
  echo
else
  echo "(AVISO: falta docs/estado.md)"
  echo
fi

# 4. Plan activo: encabezado hasta el primer "## " y la tabla de estado (v1: "### Estado de
#    subtareas"; v2: la primera tabla bajo "## Registro de verificación").
if [ "$plan_ignorado" -eq 1 ]; then
  echo "(Plan activo ignorado: tiene que ser un archivo de docs/planes/)"
  echo
fi
if [ -n "$plan" ] && [ -f "$raiz/$plan" ]; then
  echo "=== $plan ($origen; encabezado) ==="
  tr -d '\r' < "$raiz/$plan" | awk '/^## / { exit } { print }' | cortar
  echo
  echo "=== $plan (estado de subtareas) ==="
  tabla="$(tr -d '\r' < "$raiz/$plan" | awk '
    /^### Estado de subtareas/ { dentro = 1; print; next }
    dentro && /^#/ { exit }
    dentro && /^[[:space:]]*$/ { if (visto) exit; next }
    dentro { print; if ($0 ~ /^\|/) visto = 1 }
  ')"
  if [ -z "$tabla" ]; then
    tabla="$(tr -d '\r' < "$raiz/$plan" | awk '
      /^## Registro de verificación/ { dentro = 1; next }
      dentro && /^## / { exit }
      dentro && /^\|/ { print; visto = 1; next }
      dentro && visto { exit }
    ')"
  fi
  printf '%s\n' "$tabla"
  echo
fi

# 5. Últimas 5 decisiones.
if [ -f "$decisiones" ]; then
  echo "=== docs/decisiones.md (últimas 5) ==="
  tr -d '\r' < "$decisiones" | grep '^- 20' | tail -n 5 | cortar
  echo
fi

# 6. Resumen de pendientes abiertos de todos los planes (py -3, si no python3).
echo "=== pendientes ==="
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
}

salida="$(armar_salida)"
total="$(printf '%s\n' "$salida" | wc -c | tr -d ' ')"
if [ "$total" -gt "$LIMITE" ]; then
  # Se reserva el largo de la línea final con el mayor N posible (total) y se corta en bytes;
  # `iconv -c` descarta un carácter UTF-8 que haya quedado partido en el corte.
  reserva="$(printf '(recortado: %s bytes; leer docs/estado.md)\n' "$total" | wc -c | tr -d ' ')"
  corte=$((LIMITE - reserva - 1))
  if command -v iconv >/dev/null 2>&1; then
    recortada="$(printf '%s' "$salida" | head -c "$corte" | iconv -f UTF-8 -t UTF-8 -c 2>/dev/null)"
  else
    recortada="$(printf '%s' "$salida" | head -c "$corte")"
  fi
  printf '%s\n' "$recortada"
  printf '(recortado: %s bytes; leer docs/estado.md)\n' "$((total - $(printf '%s\n' "$recortada" | wc -c | tr -d ' ')))"
else
  printf '%s\n' "$salida"
fi

exit 0
