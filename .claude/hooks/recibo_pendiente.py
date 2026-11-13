"""Hook Stop liviano (método v2): avisa si falta el recibo de verificación de lo que hizo la sesión.

Flujo:

1. `--inicio` (lo invoca `contexto.sh` en SessionStart): lee el JSON del hook por stdin y guarda el
   HEAD del toplevel en `<tmp>/heads_inicio_<sesion>.json`. No pisa un registro existente
   (compactar y reanudar conservan el `session_id`). Sin `session_id` no hace nada. Sale con 0.
2. Sin argumentos (hook Stop): lee el JSON por stdin. Con `stop_hook_active` verdadero o un stdin
   inválido sale con 0; también con `.claude/.verificando` de menos de 2 horas (uno más viejo es
   huérfano y se ignora).
3. Si la sesión no hizo commits (HEAD igual al inicial o sin entrada `commit` en el reflog desde el
   inicial) no pide nada.
4. Plan: el de la rama (`plan/<slug>` o `<slug>-T<n>`) o la línea `Plan activo:` de `docs/estado.md`
   (ruta o slug, confinado a `docs/planes/*.md`).
   - Plan `completo` (línea `- **ruta**:`; sin ella, v1, cuenta como completo) con todas las tareas
     `hecha` o `PASA` y HEAD sin recibo: pide `verificar.py todo <plan>`.
   - Plan `ligero` o sin plan, con commits y sin recibo: pide `verificar.py cierre`.
5. Avisa una sola vez por sesión y HEAD (marca en el directorio temporal); para pedir, sale con 2.

Nunca ejecuta criterios: solo `git rev-parse`, `git branch` y `git reflog`.
El directorio temporal se puede cambiar con `RECIBO_PENDIENTE_TMP` (los tests lo pasan por parámetro).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import recibo  # noqa: E402

HORAS_VERIFICANDO = 2
ENTRADAS_REFLOG = 50
RE_SLUG = re.compile(r"[a-z0-9][a-z0-9.\-]*")
RE_RAMA = re.compile(r"^(?:plan/(?P<a>[a-z0-9][a-z0-9.\-]*)|(?P<b>[a-z0-9][a-z0-9.\-]*?)-T\d+[a-z]?)$")


def _dir_marcas(dir_marcas=None) -> Path:
    """Directorio de marcas: parámetro, variable `RECIBO_PENDIENTE_TMP` o el temporal del sistema."""
    return Path(dir_marcas or os.environ.get("RECIBO_PENDIENTE_TMP") or tempfile.gettempdir())


def _toplevel(raiz) -> Path:
    """Toplevel del repo que contiene `raiz` (o `raiz` si git no responde)."""
    proceso = recibo._git(raiz, "rev-parse", "--show-toplevel")
    if proceso is None or proceso.returncode != 0 or not proceso.stdout.strip():
        return Path(raiz)
    return Path(proceso.stdout.strip())


def _plan_por_slug(raiz: Path, slug: str):
    """Ruta relativa del único `docs/planes/*-<slug>.md`, o None si no hay uno solo."""
    if not RE_SLUG.fullmatch(slug) or slug == "ninguno":
        return None
    coincidencias = sorted((raiz / "docs" / "planes").glob(f"*-{slug}.md"))
    return f"docs/planes/{coincidencias[0].name}" if len(coincidencias) == 1 else None


def _plan_de_rama(raiz: Path):
    """Plan derivado de la rama `plan/<slug>` o `<slug>-T<n>`, o None."""
    proceso = recibo._git(raiz, "branch", "--show-current")
    if proceso is None or proceso.returncode != 0:
        return None
    coincide = RE_RAMA.match(proceso.stdout.strip())
    if not coincide:
        return None
    return _plan_por_slug(raiz, coincide.group("a") or coincide.group("b"))


def _plan_de_estado(raiz: Path):
    """Plan de la línea `Plan activo:` de `docs/estado.md` (ruta o slug), o None."""
    try:
        texto = (raiz / "docs" / "estado.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for linea in texto.replace("\r", "").splitlines():
        if linea.startswith("Plan activo:"):
            coincide = re.search(r"docs/planes/([^\s`/]+\.md)", linea)
            if coincide:
                return None if ".." in linea else f"docs/planes/{coincide.group(1)}"
            resto = linea[len("Plan activo:"):].strip().split()
            return _plan_por_slug(raiz, resto[0].strip("`")) if resto else None
    return None


def plan_activo(raiz: Path):
    """Ruta relativa del plan de la sesión: el de la rama o, si no, el de `docs/estado.md`."""
    return _plan_de_rama(raiz) or _plan_de_estado(raiz)


def _leer_plan(raiz: Path, plan: str) -> str:
    """Texto del plan o cadena vacía si no se puede leer (los symlinks no se siguen)."""
    ruta = raiz / plan
    if ruta.is_symlink():
        return ""
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def todas_hechas(texto: str) -> bool:
    """True si hay al menos una tarea y todas están `hecha` o `PASA`.

    Lee la tabla v1 (`### Estado de subtareas`) y la v2 (bajo `## Registro de verificación`), de 2 o
    4 columnas: una fila `| T<n> | … |` cuenta como hecha si alguna celda tras la primera empieza con
    `hecha` o `PASA`. Si una tarea aparece varias veces, vale la última fila.
    """
    estados: dict[str, bool] = {}
    dentro = False
    for linea in texto.replace("\r", "").splitlines():
        if re.match(r"##\s+Registro de verificaci[oó]n\b|###\s+Estado de subtareas\b", linea):
            dentro = True
            continue
        if dentro and re.match(r"##\s", linea):
            dentro = False
        if not dentro or not linea.lstrip().startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if len(celdas) in (2, 4) and re.fullmatch(r"T\d+[a-z]?", celdas[0]):
            estados[celdas[0]] = any(c.startswith(("hecha", "PASA")) for c in celdas[1:])
    return bool(estados) and all(estados.values())


def _ruta_del_plan(texto: str) -> str:
    """Valor de `- **ruta**:` (`ligero`, `completo`); un plan v1 sin la línea cuenta como completo."""
    ruta = re.search(r"^- \*\*ruta\*\*:\s*(\w+)", texto, re.MULTILINE)
    return ruta.group(1).lower() if ruta else "completo"


def _commiteo_desde(raiz: Path, inicial: str) -> bool:
    """True si el reflog, desde el HEAD inicial, tiene una entrada `commit`.

    Si el HEAD inicial no aparece en las últimas ENTRADAS_REFLOG entradas, se asume que sí.
    """
    proceso = recibo._git(raiz, "reflog", "-n", str(ENTRADAS_REFLOG), "--format=%H %gs")
    if proceso is None or proceso.returncode != 0:
        return False
    nuevas = []
    for linea in proceso.stdout.splitlines():
        hash_, _, accion = linea.partition(" ")
        if hash_.startswith(inicial) or inicial.startswith(hash_):
            return any(a.startswith("commit") for a in nuevas)
        nuevas.append(accion)
    return True


def _hay_verificacion(raiz: Path, ahora: float) -> bool:
    """True si `.claude/.verificando` existe y es de menos de HORAS_VERIFICANDO horas."""
    try:
        return ahora - (raiz / ".claude" / ".verificando").stat().st_mtime < HORAS_VERIFICANDO * 3600
    except OSError:
        return False


def pendiente(raiz: Path, inicial):
    """Devuelve (mensaje, head) si falta un recibo, o None si no hay nada que avisar."""
    actual = recibo.head(raiz)
    if not actual or not inicial or actual == inicial:
        return None
    if recibo.head_tiene_recibo(raiz, actual) or not _commiteo_desde(raiz, inicial):
        return None
    plan = plan_activo(raiz)
    if plan:
        texto = _leer_plan(raiz, plan)
        if _ruta_del_plan(texto) != "ligero":
            if not todas_hechas(texto):
                return None
            return f"corre `py -3 .claude/hooks/verificar.py todo {plan}`", actual
    return "corre `py -3 .claude/hooks/verificar.py cierre`", actual


def _nombre_sesion(session_id: str) -> str:
    """`session_id` saneado para usarlo en un nombre de archivo."""
    return re.sub(r"[^\w\-]", "_", session_id) or "sin_sesion"


def _archivo_inicio(dir_marcas, session_id: str) -> Path:
    """Archivo con el HEAD de inicio de la sesión."""
    return _dir_marcas(dir_marcas) / f"heads_inicio_{_nombre_sesion(session_id)}.json"


def registrar_inicio(entrada: str, raiz, dir_marcas=None) -> int:
    """`--inicio`: guarda el HEAD del toplevel una sola vez; nunca rompe (siempre 0)."""
    try:
        datos = json.loads(entrada)
        session_id = str(datos.get("session_id", "")) if isinstance(datos, dict) else ""
        if not session_id:
            return 0
        archivo = _archivo_inicio(dir_marcas, session_id)
        if not archivo.exists():
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(json.dumps({"head": recibo.head(_toplevel(raiz))}), encoding="utf-8")
    except (ValueError, OSError):
        pass
    return 0


def _leer_inicio(dir_marcas, session_id: str):
    """HEAD de inicio de la sesión o None si no hay registro legible."""
    if not session_id:
        return None
    try:
        datos = json.loads(_archivo_inicio(dir_marcas, session_id).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return datos.get("head") if isinstance(datos, dict) else None


def _marca(dir_marcas, session_id: str, head: str) -> Path:
    """Archivo de marca para esta sesión y este HEAD."""
    clave = hashlib.sha1(head.encode()).hexdigest()[:16]
    return _dir_marcas(dir_marcas) / f"recibo_pendiente_{_nombre_sesion(session_id)}_{clave}"


def ejecutar(entrada: str, raiz, dir_marcas=None, ahora=None, err=sys.stderr) -> int:
    """Lógica del hook: devuelve el código de salida (0 no avisa, 2 bloquea con el mensaje en `err`)."""
    try:
        datos = json.loads(entrada)
    except ValueError:
        return 0
    if not isinstance(datos, dict) or datos.get("stop_hook_active"):
        return 0
    raiz = _toplevel(raiz)
    ahora = time.time() if ahora is None else ahora
    if _hay_verificacion(raiz, ahora):
        return 0
    session_id = str(datos.get("session_id", ""))
    resultado = pendiente(raiz, _leer_inicio(dir_marcas, session_id))
    if resultado is None:
        return 0
    mensaje, head = resultado
    marca = _marca(dir_marcas, session_id, head)
    if marca.exists():
        return 0
    try:
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text("1", encoding="utf-8")
    except OSError:
        pass
    print(f"Falta el recibo de verificación: {mensaje}", file=err)
    return 2


def main() -> int:
    """Punto de entrada del hook: nunca rompe la sesión ante un error inesperado."""
    try:
        raiz = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if "--inicio" in sys.argv[1:]:
            return registrar_inicio(sys.stdin.read(), raiz)
        return ejecutar(sys.stdin.read(), raiz)
    except Exception:  # noqa: BLE001 - un hook Stop no debe romper la sesión
        return 0


if __name__ == "__main__":
    sys.exit(main())
