"""Hook `commit-msg`: un commit `cierre: <slug>` exige un recibo en PASA del HEAD actual y del plan.

    py -3 .claude/hooks/commit_msg.py <archivo-del-mensaje>

Solo lectura: consulta el índice `.claude/.recibos.json` y el índice de git, y no escribe nada.
Exit 0 deja pasar el commit; exit 1 lo rechaza y explica en stderr qué falta. Para aceptar un
`cierre: <slug>` hacen falta tres cosas:
- el plan `docs/planes/AAAA-MM-DD-<slug>.md`;
- un recibo del HEAD con alcance `todo <plan>` (plan completo) o `cierre` (plan `ligero`);
- que el commit solo toque `docs/planes/`, `docs/estado.md`, `docs/bitacora.md`,
  `docs/decisiones.md` y `docs/metodo/` (`git diff --cached --name-only`).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_HOOKS))

import recibo  # noqa: E402

# El slug termina en el primer espacio o raya: `cierre: <slug> — <texto>` también es un cierre.
RE_CIERRE = re.compile(r"^cierre:\s*(?P<slug>[^\s—]+)(?:\s|$)")
# Rutas que un commit de cierre puede tocar: el proceso, no el código.
RUTAS_DE_CIERRE = ("docs/planes/", "docs/estado.md", "docs/bitacora.md", "docs/decisiones.md", "docs/metodo/")


def raiz_por_defecto() -> Path:
    """Toplevel del repo donde se hace el commit (o dos niveles sobre los hooks si git falla)."""
    try:
        proceso = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return DIR_HOOKS.parent.parent
    if proceso.returncode == 0 and proceso.stdout.strip():
        return Path(proceso.stdout.strip())
    return DIR_HOOKS.parent.parent


def slug_del_mensaje(archivo: str) -> str | None:
    """Slug si la primera línea del mensaje empieza con `cierre: <slug>`; si no, None."""
    try:
        lineas = Path(archivo).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    coincidencia = RE_CIERRE.match(lineas[0].strip()) if lineas else None
    return coincidencia.group("slug") if coincidencia else None


def plan_del_slug(raiz: Path, slug: str) -> Path | None:
    """El plan `AAAA-MM-DD-<slug>.md` más nuevo (el slug debe coincidir entero, no solo el final)."""
    patron = re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(slug)}\.md")
    planes = sorted(p for p in (raiz / "docs" / "planes").glob("*.md") if patron.fullmatch(p.name))
    return planes[-1] if planes else None


def rutas_fuera_de_proceso(raiz: Path) -> list[str] | None:
    """Rutas del commit en curso (`git diff --cached`) fuera de `RUTAS_DE_CIERRE`; None si git falla."""
    proceso = recibo._git(raiz, "diff", "--cached", "--name-only", "--no-renames", "-z")
    if proceso is None or proceso.returncode != 0:
        return None
    rutas = [r for r in proceso.stdout.split("\0") if r]
    return [r for r in rutas if not any(r == p or (p.endswith("/") and r.startswith(p)) for p in RUTAS_DE_CIERRE)]


def main(argv: list[str], raiz=None) -> int:
    """Punto de entrada: devuelve el exit del hook."""
    if not argv:
        return 0
    slug = slug_del_mensaje(argv[0])
    if slug is None:
        return 0
    raiz = Path(raiz) if raiz is not None else raiz_por_defecto()

    plan = plan_del_slug(raiz, slug)
    if plan is None:
        print(f"commit-msg: no hay plan docs/planes/AAAA-MM-DD-{slug}.md para el cierre «{slug}».", file=sys.stderr)
        return 1
    texto = plan.read_text(encoding="utf-8", errors="replace")
    ligero = re.search(r"^- \*\*ruta\*\*:\s*ligero", texto, re.MULTILINE | re.IGNORECASE) is not None
    alcance = "cierre" if ligero else f"todo {plan.name}"
    head = recibo.head_completo(raiz)
    if head is None or not recibo.head_tiene_recibo(raiz, head, alcance):
        comando = ("py -3 .claude/hooks/verificar.py cierre" if ligero
                   else f"py -3 .claude/hooks/verificar.py todo {plan.relative_to(raiz).as_posix()}")
        print(f"commit-msg: «cierre: {slug}» rechazado, el HEAD {recibo.head(raiz)} no tiene recibo en PASA "
              f"con alcance «{alcance}»: corré `{comando}`", file=sys.stderr)
        return 1

    fuera = rutas_fuera_de_proceso(raiz)
    if fuera is None or fuera:
        detalle = "no se pudo leer git diff --cached" if fuera is None else ", ".join(fuera)
        print(f"commit-msg: «cierre: {slug}» rechazado, solo puede tocar docs/planes/, docs/estado.md, "
              f"docs/bitacora.md, docs/decisiones.md y docs/metodo/: {detalle}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
