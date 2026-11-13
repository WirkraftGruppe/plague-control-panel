#!/usr/bin/env bash
# Integra la rama de una subtarea en paralelo y limpia su worktree (CLAUDE.md raíz § 5,
# párrafo "Paralelismo").
#
# Uso: worktree-integrar.sh <slug> <T<n>> <rama_destino> <ruta>...
#   <slug>, <T<n>>  identifican la rama y el worktree `worktrees/<slug>-T<n>`
#   <rama_destino>  rama (con worktree propio, p. ej. la raíz) donde se mergea
#   <ruta>...       prefijos permitidos (al menos uno); todo archivo cambiado fuera de ellos
#                   hace rechazar la integración
#
# Pasos: rechaza si el worktree de la subtarea o el de destino tienen cambios sin commitear;
# muestra cambios.sh --stat; rechaza si hay archivos fuera de los prefijos; merge --no-ff con
# mensaje "T<n>: integra <slug>-T<n>"; makemigrations --check en el destino y la suite de Django
# solo si la subtarea toca apps/, config/, templates/, manage.py o requirements.txt; quita la
# junction venv con cmd (nunca borra el contenido del venv real), el worktree y la rama.
#
# Validaciones: una <ruta> vacía (o solo "/") es uso inválido; la "/" final de cada prefijo se
# quita y el alcance compara por segmento (`app` admite `app` y `app/…`, no `app_v2/…`);
# la ruta de `worktrees/<slug>-T<n>` sale de la lista de worktrees de git (ruta normalizada), por lo
# que el script puede invocarse desde dentro de otro worktree (pero no del de la subtarea: exit 3).
# Si makemigrations --check o los tests fallan tras el merge, se deshace con
# un reset duro a ORIG_HEAD en el destino (estaba limpio por el paso 1) y el worktree y la rama
# de la subtarea quedan intactos.
#
# exit 0 → integrada y limpia
# exit 2 → uso inválido
# exit 3 → el directorio actual está dentro del worktree de la subtarea (no se tocó nada; salir
#          del worktree y reintentar)
# exit 1 → rechazada o fallida (si falló antes del merge no se modificó nada; si falló después,
#          el merge se deshizo)
set -u

if [ "$#" -lt 4 ]; then
  echo "uso: worktree-integrar.sh <slug> <T<n>> <rama_destino> <ruta>..." >&2
  exit 2
fi

slug="$1"
tarea="$2"
destino="$3"
shift 3

# Prefijos: ninguno vacío y sin "/" final.
prefijos=()
for p in "$@"; do
  p="${p%/}"
  if [ -z "$p" ]; then
    echo "ruta vacía no permitida" >&2
    exit 2
  fi
  prefijos+=("$p")
done

if ! printf '%s' "$slug" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  echo "slug inválido: '$slug'" >&2
  exit 2
fi
if ! printf '%s' "$tarea" | grep -Eq '^T[0-9]+[a-z]?$'; then
  echo "subtarea inválida: '$tarea'" >&2
  exit 2
fi

dir_hooks="$(cd "$(dirname "$0")" && pwd)"
toplevel="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "no se está dentro de un repositorio git" >&2
  exit 2
}

nombre="$slug-$tarea"
normalizar() { cygpath -m "$1" 2>/dev/null | tr 'A-Z' 'a-z'; }

# La ruta de la subtarea sale de `git worktree list`: el registrado cuya ruta normalizada termina en
# `/worktrees/<nombre>`, prefiriendo el que cuelga del toplevel actual (así funciona invocado desde
# dentro del propio worktree, donde el toplevel es el worktree y no la raíz).
lista_wt="$(git -C "$toplevel" worktree list --porcelain)"
sufijo="/worktrees/$nombre"
sufijo_norm="$(printf '%s' "$sufijo" | tr 'A-Z' 'a-z')"
top_norm="$(normalizar "$toplevel")"
ruta_sub=""
while IFS= read -r linea; do
  case "$linea" in
    "worktree "*)
      cand="${linea#worktree }"
      cand_norm="$(normalizar "$cand")"
      case "$cand_norm" in
        *"$sufijo_norm")
          if [ -z "$ruta_sub" ]; then ruta_sub="$cand"; fi
          case "$cand_norm" in "$top_norm"/*) ruta_sub="$cand" ;; esac
          ;;
      esac
      ;;
  esac
done <<< "$lista_wt"
if [ -z "$ruta_sub" ]; then
  echo "no hay un worktree registrado en git worktree list que termine en $sufijo" >&2
  exit 1
fi
if [ ! -d "$ruta_sub" ]; then
  echo "no existe el worktree $ruta_sub" >&2
  exit 1
fi
# Raíz = el worktree bajo el que `worktree-crear.sh` anidó la subtarea (ruta sin el sufijo).
raiz="${ruta_sub:0:${#ruta_sub}-${#sufijo}}"

# Antes de cualquier modificación: el cwd no puede estar dentro del worktree que se va a borrar.
cwd_norm="$(normalizar "$(pwd -P)")"
sub_norm="$(normalizar "$(cd "$ruta_sub" && pwd -P)")"
if [ "$cwd_norm" = "$sub_norm" ] || [ "${cwd_norm#"$sub_norm"/}" != "$cwd_norm" ]; then
  echo "el directorio actual está dentro de $ruta_sub; salir del worktree antes de integrar" >&2
  exit 3
fi

# Worktree donde está la rama destino.
ruta_dest="$(printf '%s
' "$lista_wt" | awk -v rama="refs/heads/$destino" '
  /^worktree /{ruta=substr($0,10)} $0=="branch " rama {print ruta; exit}')"
if [ -z "$ruta_dest" ]; then
  echo "la rama destino '$destino' no tiene worktree" >&2
  exit 1
fi

# 1. Sin cambios sin commitear en ninguno de los dos.
for wt in "$ruta_sub" "$ruta_dest"; do
  if [ -n "$(git -C "$wt" status --porcelain)" ]; then
    echo "cambios sin commitear en $wt; commitear o descartar antes de integrar" >&2
    exit 1
  fi
done

# 2. Resumen de cambios.
bash "$dir_hooks/cambios.sh" "$raiz" "$destino" --stat

# 3. Alcance: todo archivo cambiado debe caer bajo algún prefijo permitido.
fuera=""
while IFS= read -r -d '' archivo; do
  [ -z "$archivo" ] && continue
  dentro=0
  for prefijo in "${prefijos[@]}"; do
    case "$archivo" in
      "$prefijo"|"$prefijo"/*) dentro=1 ;;
    esac
  done
  [ "$dentro" -eq 0 ] && fuera="$fuera$archivo"$'\n'
done < <(git -C "$raiz" -c core.quotepath=off diff --no-renames --name-only -z "$destino...$nombre")
if [ -n "$fuera" ]; then
  echo "archivos fuera de alcance, no se integra:" >&2
  printf '%s' "$fuera" >&2
  exit 1
fi

# 4. Merge en el worktree destino.
if ! git -C "$ruta_dest" merge --no-ff -m "$tarea: integra $nombre" "$nombre"; then
  echo "el merge falló; resolver en $ruta_dest" >&2
  exit 1
fi

# 5. Migraciones y tests en el destino; si fallan, se deshace el merge.
deshacer_merge() {
  git -C "$ruta_dest" reset --hard ORIG_HEAD >/dev/null
  echo "$1; se deshizo el merge de $nombre en $destino" >&2
}
export PYTHONIOENCODING=utf-8 DJANGO_ENV=development
if ! (cd "$ruta_dest" && ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run); then
  deshacer_merge "makemigrations --check falló tras el merge"
  exit 1
fi
# La suite de Django solo corre si la subtarea toca código o dependencias de Django (P-metodo-v2-23).
rutas_django='^(apps/|config/|templates/|manage\.py$|requirements\.txt$)'
if git -C "$ruta_dest" diff --name-only ORIG_HEAD HEAD | grep -Eq "$rutas_django"; then
  if ! (cd "$ruta_dest" && ./venv/Scripts/python.exe manage.py test --keepdb); then
    deshacer_merge "los tests fallaron tras el merge"
    exit 1
  fi
else
  echo "aviso: $nombre no toca apps/, config/, templates/, manage.py ni requirements.txt; se omite la suite de Django"
fi

# 6. Quita la junction (solo el enlace) y luego el worktree.
if [ -e "$ruta_sub/venv" ]; then
  MSYS2_ARG_CONV_EXCL="*" cmd /c rmdir "$(cygpath -w "$ruta_sub/venv")" || {
    echo "no se pudo quitar la junction venv de $ruta_sub" >&2
    exit 1
  }
fi
git -C "$raiz" worktree remove "$ruta_sub" || {
  echo "no se pudo quitar el worktree $ruta_sub; quizá otro shell tiene el directorio actual adentro" >&2
  exit 1
}

# 7. Borra la rama desde el worktree destino (donde ya está fusionada). Si falla, el merge y los
# tests ya pasaron: es un aviso, no un error (P-metodo-v2-5).
git -C "$ruta_dest" branch -d "$nombre" ||
  echo "aviso: no se pudo borrar la rama $nombre; borrarla a mano con git branch -d $nombre" >&2
echo "integrada $nombre en $destino"
