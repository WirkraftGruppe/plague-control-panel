"""Fuente única de los permisos de Claude Code en Detach.

    py -3 .claude/hooks/permisos.py              # escribe settings.json y limpia settings.local.json
    py -3 .claude/hooks/permisos.py --comprobar  # sale con 1 si settings.json no coincide

Bash corre libre (`allow: ["Bash"]`, lista `ask` vacía): Claude hace commits, sube ramas a
`origin` y abre PR sin pedir permiso. Lo que queda en manos del usuario (merge, push a `main`,
push forzado, producción, secretos) lo frenan tres capas:

1. `guardia_bash.py`, hook PreToolUse que mira el comando entero (también `git -C …`,
   `bash -c '…'` y comandos compuestos);
2. la lista `deny` de este archivo, que cubre la forma habitual de cada comando y las
   herramientas de archivos (`Read`, `Edit`);
3. el hook `pre-push` de git, que mira la rama y el remoto reales del push.

Claude no puede editar los settings, este archivo, la guardia ni el `pre-push` (reglas `Edit`
del final de DENY) ni ejecutar este script sin `--comprobar` (lo frena la guardia): todo cambio
de permisos se hace acá y lo ejecuta el usuario.
"""
import argparse
import json
import sys
from pathlib import Path

DIR_CLAUDE = Path(__file__).resolve().parent.parent
SETTINGS = DIR_CLAUDE / "settings.json"
LOCAL = DIR_CLAUDE / "settings.local.json"

ALLOW = ["Bash"]
ASK: list = []
DENY = [
    # Secretos. `.env.example` queda legible: por eso no hay un `Read(**/.env.*)`.
    "Read(**/.env)",
    "Read(**/.env.local)",
    "Read(**/.env.dev*)",
    "Read(**/.env.prod*)",
    "Read(**/.env.staging)",
    "Read(**/.env.test)",
    "Read(**/*.pem)",
    "Read(**/*.key)",
    "Read(**/credenciales*)",
    # Producción la opera el usuario.
    "Bash(railway ssh*)",
    "Bash(railway connect*)",
    "Bash(railway variables*)",
    "Bash(railway run*)",
    "Bash(railway up*)",
    "Bash(railway redeploy*)",
    "Bash(*railway.exe ssh*)",
    "Bash(*railway.exe connect*)",
    "Bash(*railway.exe variables*)",
    "Bash(*railway.exe run*)",
    "Bash(*railway.exe up*)",
    "Bash(*railway.exe redeploy*)",
    # GitHub: push de ramas y PR son libres; fusionar, aprobar y administrar, no.
    "Bash(gh pr merge*)",
    "Bash(gh pr review * --approve*)",
    "Bash(gh pr review --approve*)",
    "Bash(gh repo delete*)",
    "Bash(gh repo edit*)",
    "Bash(gh repo archive*)",
    "Bash(gh repo rename*)",
    "Bash(gh secret set*)",
    "Bash(gh secret delete*)",
    "Bash(gh release create*)",
    "Bash(gh release delete*)",
    "Bash(gh workflow run*)",
    "Bash(gh auth token*)",
    "Bash(gh auth login*)",
    "Bash(gh auth logout*)",
    # Git: nada que pierda trabajo, reescriba historia o saltee los hooks.
    "Bash(git push --force*)",
    "Bash(git push -f*)",
    "Bash(git push * --force*)",
    "Bash(git -C * push --force*)",
    "Bash(git push *+*)",
    "Bash(git push *--no-verify*)",
    "Bash(git stash*)",
    "Bash(git -C * stash*)",
    "Bash(git add -A*)",
    "Bash(git add .)",
    "Bash(git -C * add -A*)",
    "Bash(git -C * add .)",
    "Bash(git reset --hard*)",
    "Bash(git -C * reset --hard*)",
    "Bash(git clean*)",
    "Bash(git -C * clean*)",
    "Bash(git -c *)",
    "Bash(git config core.hooksPath*)",
    "Bash(git commit --amend*)",
    "Bash(git commit * --amend*)",
    "Bash(git commit -a*)",
    "Bash(git commit --all*)",
    "Bash(git branch -D*)",
    "Bash(git branch * -D*)",
    "Bash(git switch --discard-changes*)",
    "Bash(git switch * --discard-changes*)",
    "Bash(git switch -f*)",
    "Bash(git remote add*)",
    "Bash(git remote set-url*)",
    # Los permisos y sus guardias solo los cambia el usuario (las reglas Edit también cubren Write).
    "Edit(**/.git/hooks/**)",
    "Edit(.claude/settings.json)",
    "Edit(.claude/settings.local.json)",
    "Edit(.claude/hooks/permisos.py)",
    "Edit(.claude/hooks/guardia_bash.py)",
    "Edit(.claude/hooks/pre-push)",
    # El control de `cierre:` (H4 de la auditoría de metodo-v2).
    "Edit(.claude/.recibos.json)",
    "Edit(.claude/hooks/recibo.py)",
    "Edit(.claude/hooks/commit-msg)",
    "Edit(.claude/hooks/commit_msg.py)",
    # Abreviaturas de opciones largas que git acepta (H2): `--no-verif`, `--amen`, `--forc`.
    "Bash(git commit *--no-v*)",
    "Bash(git push *--no-v*)",
    "Bash(git commit *--am*)",
    "Bash(git push *--forc*)",
]


def generar(settings: dict) -> dict:
    """Devuelve `settings` con el bloque `permissions` reemplazado; conserva lo demás y el defaultMode."""
    nuevo = dict(settings)
    anterior = settings.get("permissions", {})
    permisos = {}
    if "defaultMode" in anterior:
        permisos["defaultMode"] = anterior["defaultMode"]
    permisos.update({"allow": list(ALLOW), "ask": list(ASK), "deny": list(DENY)})
    nuevo["permissions"] = permisos
    return nuevo


def limpiar_local(local: dict) -> dict:
    """Saca de settings.local.json las reglas Bash(...) sueltas, ya cubiertas por `Bash`."""
    nuevo = dict(local)
    permisos = dict(local.get("permissions", {}))
    if "allow" in permisos:
        permisos["allow"] = [r for r in permisos["allow"] if not r.startswith("Bash(")]
    nuevo["permissions"] = permisos
    return nuevo


def _leer(ruta: Path) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def _escribir(ruta: Path, datos: dict) -> None:
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _diferencias(antes: list, despues: list, nombre: str) -> list:
    lineas = [f"- {nombre}: {r}" for r in antes if r not in despues]
    lineas += [f"+ {nombre}: {r}" for r in despues if r not in antes]
    return lineas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--comprobar", action="store_true", help="no escribe; sale con 1 si hay diferencias")
    args = parser.parse_args()

    actual = _leer(SETTINGS)
    generado = generar(actual)
    if args.comprobar:
        if actual.get("permissions") != generado["permissions"]:
            print("settings.json no coincide con permisos.py: el usuario corre `py -3 .claude/hooks/permisos.py`")
            return 1
        print("settings.json coincide con permisos.py")
        return 0

    cambios = []
    for clave in ("allow", "ask", "deny"):
        cambios += _diferencias(
            actual.get("permissions", {}).get(clave, []), generado["permissions"][clave], f"settings.json {clave}"
        )
    _escribir(SETTINGS, generado)

    if LOCAL.exists():
        local = _leer(LOCAL)
        limpio = limpiar_local(local)
        cambios += _diferencias(
            local.get("permissions", {}).get("allow", []), limpio["permissions"].get("allow", []), "settings.local.json allow"
        )
        _escribir(LOCAL, limpio)

    print("\n".join(cambios) if cambios else "sin cambios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
