"""Hook `commit-msg`: un commit `cierre: <slug>` exige recibo en PASA del HEAD actual.

    py -3 .claude/hooks/commit_msg.py <archivo-del-mensaje>

Solo lectura: consulta el índice `.claude/.recibos.json` y no escribe nada. Exit 0 deja pasar el
commit; exit 1 lo rechaza y explica en stderr qué falta.
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


def main(argv: list[str], raiz=None) -> int:
    """Punto de entrada: devuelve el exit del hook."""
    if not argv:
        return 0
    slug = slug_del_mensaje(argv[0])
    if slug is None:
        return 0
    raiz = Path(raiz) if raiz is not None else raiz_por_defecto()

    planes = sorted((raiz / "docs" / "planes").glob(f"*-{slug}.md"))
    if not planes:
        print(f"commit-msg: no hay plan docs/planes/*-{slug}.md para el cierre «{slug}».", file=sys.stderr)
        return 1
    plan = planes[-1]
    head = recibo.head(raiz)
    if head is not None and recibo.head_tiene_recibo(raiz, head):
        return 0

    texto = plan.read_text(encoding="utf-8", errors="replace")
    ligero = re.search(r"^- \*\*ruta\*\*:\s*ligero", texto, re.MULTILINE | re.IGNORECASE) is not None
    comando = ("py -3 .claude/hooks/verificar.py cierre" if ligero
               else f"py -3 .claude/hooks/verificar.py todo {plan.relative_to(raiz).as_posix()}")
    print(f"commit-msg: «cierre: {slug}» rechazado, el HEAD {head} no tiene recibo en PASA: "
          f"corré `{comando}`", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
