#!/usr/bin/env python3
"""Hook PreToolUse (Bash): frena los comandos que el método deja en manos del usuario.

Claude corre Bash sin pedir permiso (`allow: ["Bash"]` en `permisos.py`): hace commits, sube
ramas y abre PR por su cuenta. Este hook es lo que mantiene fuera de su alcance lo que no se
deshace o lo que decide el usuario:

- fusionar: `gh pr merge`, aprobar un PR, `gh api` que no sea de lectura;
- reescribir o perder trabajo: push forzado, push a `main`/`master`, push a un remoto que no es
  `origin`, `stash`, `clean`, `reset --hard`, `commit --amend`, `branch -D`, descartar cambios;
- arrastrar archivos ajenos: `git add -A`, `git add .`, `git commit -a`;
- saltear controles: `--no-verify`, `git -c`, `core.hooksPath`, cambiar remotos, tocar
  `.git/hooks/` o los settings, ejecutar `permisos.py` (solo se admite `--comprobar`);
- administrar el repo o la cuenta de GitHub: `gh repo delete|edit|…`, `gh secret`, `gh release`,
  `gh workflow run`, `gh auth` (salvo `status`);
- producción: `railway ssh|connect|variables|run|up|redeploy|…`;
- secretos: cualquier comando que nombre `.env`, `*.pem`, `*.key` o `credenciales*`.

Lee el JSON del hook por stdin (`tool_input.command`). Sale con 2 y el motivo por stderr para
bloquear; con 0 deja pasar. Mira el comando entero: separa los comandos compuestos, saltea
envoltorios (`env`, `timeout`, `xargs`…), sigue las opciones globales de git (`-C`) y entra en
`bash -c '…'`, `eval`, `$(…)` y las comillas invertidas. El cuerpo de un documento en línea
(`<<'EOF'`, como el mensaje de un commit o de un PR) es texto y no se revisa.

Límite: reconoce las formas en que un comando se escribe normalmente, no un comando ofuscado a
propósito. La garantía real del merge y del push a `main` está en GitHub (regla sobre `main`),
no en este archivo. Ante un error interno deja pasar: las reglas `deny` siguen aplicando.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

PUNTUACION = set("();<>|&")
REDIRECCION = set("<>")
PALABRAS_DE_CONTROL = {"{", "}", "!", "then", "do", "else", "elif", "if", "while", "until", "time"}
ENVOLTORIOS = {"env", "timeout", "nice", "nohup", "stdbuf", "command", "builtin", "exec", "sudo", "winpty"}
SHELLS = {"bash", "sh", "zsh", "dash"}
INTERPRETES = {"python", "python3", "py", "node", "perl", "ruby"}
ESCRITORES = {"cp", "mv", "rm", "ln", "install", "chmod", "sed", "tee", "truncate", "dd", "touch"}
RAMAS_PROTEGIDAS = {"main", "master"}
REMOTOS_PERMITIDOS = {"origin"}
RUTAS_PROTEGIDAS = (
    ".git/hooks", ".claude/settings.json", ".claude/settings.local.json",
    ".claude/.recibos.json", ".claude/hooks/recibo.py",
    ".claude/hooks/commit-msg", ".claude/hooks/commit_msg.py",
)
ENV_DE_EJEMPLO = {".env.example", ".env.sample", ".env.template", ".env.dist"}
EXTENSIONES_SECRETAS = (".pem", ".key", ".jks", ".keystore")
RE_ASIGNACION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
RE_SUSTITUCION = re.compile(r"\$\((.*)\)", re.DOTALL)
RE_INVERTIDAS = re.compile(r"`([^`]*)`")
# Documento en línea (`<<EOF … EOF`): el cuerpo es texto, no comandos.
RE_HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1([^\n]*)\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.DOTALL)

GH_SOLO_LECTURA = {
    "repo": {"view", "list", "clone", "sync", "set-default"},
    "secret": {"list"},
    "variable": {"list", "get"},
    "ssh-key": {"list"},
    "gpg-key": {"list"},
    "auth": {"status"},
    "release": {"list", "view", "download"},
    "workflow": {"list", "view"},
    "extension": {"list"},
    "alias": {"list"},
    "config": {"get", "list"},
    "ruleset": {"list", "view", "check"},
}
RAILWAY_PROHIBIDOS = {
    "ssh", "connect", "variables", "variable", "run", "shell", "up", "deploy", "redeploy",
    "restart", "down", "delete", "domain", "volume", "add", "scale",
}
# Para texto que no se pudo separar en comandos (código de `python -c`, comillas sin cerrar).
PATRONES_GRUESOS = [
    (re.compile(r"\bgit\b[^\n;|&]*\b(stash|clean)\b"), "git stash o git clean"),
    (re.compile(r"\bgit\b[^\n;|&]*\bpush\b[^\n;|&]*(--force|--no-verify|\s-f\b)"), "push forzado o sin hooks"),
    (re.compile(r"\bgit\b[^\n;|&]*\breset\b[^\n;|&]*--hard"), "git reset --hard"),
    (re.compile(r"\bgh\b[^\n;|&]*\bpr\s+merge\b"), "gh pr merge"),
    (re.compile(r"\bgh\b[^\n;|&]*\bpr\s+review\b[^\n;|&]*(--approve|\s-a\b)"), "aprobar un PR"),
    (re.compile(r"\bgh\b[^\n;|&]*\bapi\b[^\n;|&]*(/merge\b|\s-X|--method|\s-[fF]\b|--field|--input)"), "gh api que no es de lectura"),
    (re.compile(r"\brailway(\.exe)?\s+(ssh|connect|variables|run|up|redeploy)\b"), "railway contra producción"),
    (re.compile(r"permisos\.py(?![^\n;|&]*--comprobar)"), "ejecutar permisos.py"),
]


def nombre_base(token: str) -> str:
    """Último segmento de una ruta (con `/` o `\\`), sin `.exe` y en minúsculas."""
    base = re.split(r"[\\/]", token.rstrip("\\/"))[-1].lower()
    return base[:-4] if base.endswith(".exe") else base


def es_secreto(token: str) -> bool:
    """True si el token, o lo que sigue a un `=`, nombra un archivo de secretos."""
    for candidato in [token, *token.split("=")[1:]]:
        base = re.split(r"[\\/]", candidato)[-1].lower()
        if base == ".env" or (base.startswith(".env.") and base not in ENV_DE_EJEMPLO):
            return True
        if base.endswith(EXTENSIONES_SECRETAS):
            return True
        if base.startswith("credenciales") and re.fullmatch(r"credenciales[^.]*(\.(txt|json|csv|md))?", base):
            return True
    return False


def grupo_corto(token: str, letra: str) -> bool:
    """True si `token` es un grupo de opciones cortas (`-am`) que incluye `letra`."""
    return bool(re.fullmatch(r"-[A-Za-z]+", token)) and letra in token


def es_prefijo(a: str, *largas: str) -> bool:
    """True si `a` es una opción larga o una abreviatura de alguna (git acepta prefijos únicos)."""
    if not a.startswith("--") or len(a) < 4:
        return False
    nombre = a.split("=", 1)[0]
    return any(larga.startswith(nombre) for larga in largas)


def revisar_grueso(texto: str) -> str | None:
    """Búsqueda por patrón sobre texto que no se pudo separar en comandos."""
    for patron, motivo in PATRONES_GRUESOS:
        if patron.search(texto):
            return motivo
    return None


# ---------------------------------------------------------------------------
# Reglas por programa
# ---------------------------------------------------------------------------

def regla_git(args: list[str]) -> str | None:
    """Motivo de bloqueo de `git <args>` o None."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        opcion = args[i]
        if opcion == "-c" or opcion.startswith("--config-env"):
            return "`git -c` cambia la configuración para un solo comando (sirve para saltear hooks)"
        i += 2 if opcion in {"-C", "--git-dir", "--work-tree", "--namespace"} else 1
    if i >= len(args):
        return None
    sub, resto = args[i], args[i + 1:]
    posicionales = [a for a in resto if not a.startswith("-")]

    if sub in {"stash", "clean", "filter-branch", "filter-repo"}:
        return f"`git {sub}` descarta o reescribe trabajo"
    if sub == "reset" and "--hard" in resto:
        return "`git reset --hard` descarta cambios sin commitear"
    if sub == "add" and (any(a in {"-A", "--all", ".", ":/", "*"} for a in resto) or any(grupo_corto(a, "A") for a in resto)):
        return "`git add` solo con rutas explícitas (sin `-A`, `--all` ni `.`)"
    if sub == "commit":
        con_valor = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--author", "--date", "--fixup", "--squash", "--template"}
        j = 0
        while j < len(resto):
            a = resto[j]
            if es_prefijo(a, "--amend", "--all", "--no-verify") or grupo_corto(a, "a") or grupo_corto(a, "n"):
                return "`git commit` sin `--amend`, `-a`/`--all` ni `--no-verify`"
            j += 2 if a in con_valor or (re.fullmatch(r"-[A-Za-z]+", a) and a[-1] in "mFCct") else 1
        return None
    if sub == "push":
        return regla_push(resto)
    if sub == "branch" and (any(grupo_corto(a, "D") for a in resto) or ({"--delete", "--force"} <= set(resto))):
        return "`git branch -D` borra una rama sin fusionar"
    if sub == "switch" and (any(a in {"--force", "--discard-changes"} for a in resto) or any(grupo_corto(a, "f") for a in resto)):
        return "`git switch -f` descarta cambios sin commitear"
    if sub == "checkout" and ("--force" in resto or any(grupo_corto(a, "f") for a in resto) or "." in posicionales):
        return "`git checkout -f` o `git checkout .` descarta cambios sin commitear"
    if sub == "restore" and "." in posicionales and ("--staged" not in resto and "-S" not in resto or "--worktree" in resto or "-W" in resto):
        return "`git restore .` descarta cambios sin commitear"
    if sub == "config" and any(a.startswith("core.hooksPath") or a in {"--global", "--system"} for a in resto):
        return "`git config` no cambia `core.hooksPath` ni la configuración global"
    if sub == "remote" and posicionales and posicionales[0] in {"add", "set-url", "remove", "rm", "rename"}:
        return "los remotos los cambia el usuario"
    if sub == "reflog" and posicionales and posicionales[0] in {"expire", "delete"}:
        return "`git reflog expire|delete` borra el rastro para recuperar commits"
    return None


def regla_push(resto: list[str]) -> str | None:
    """Motivo de bloqueo de `git push <resto>` o None."""
    con_valor = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
    borrar = False
    posicionales = []
    i = 0
    while i < len(resto):
        a = resto[i]
        if es_prefijo(a, "--force", "--force-with-lease", "--force-if-includes", "--mirror", "--all", "--prune", "--no-verify") or grupo_corto(a, "f"):
            return f"`git push {a}`: sin forzar, sin `--no-verify` y sin subir todas las ramas"
        if a in {"--delete", "-d"} or grupo_corto(a, "d"):
            borrar = True
        elif a in con_valor:
            i += 1
        elif not a.startswith("-"):
            posicionales.append(a)
        i += 1
    if not posicionales:
        return None
    remoto, refs = posicionales[0], posicionales[1:]
    if remoto not in REMOTOS_PERMITIDOS:
        return f"push al remoto `{remoto}`: solo se sube a {', '.join(sorted(REMOTOS_PERMITIDOS))}"
    for ref in refs:
        if ref.startswith("+"):
            return f"`{ref}` es un push forzado"
        destino = ref.split(":")[-1]
        if destino.startswith("refs/heads/"):
            destino = destino[len("refs/heads/"):]
        if destino in RAMAS_PROTEGIDAS:
            accion = "borrar" if borrar or ref.startswith(":") else "push directo a"
            return f"{accion} `{destino}`: a esa rama se entra por PR y el merge lo hace el usuario"
    return None


def regla_gh(args: list[str]) -> str | None:
    """Motivo de bloqueo de `gh <args>` o None."""
    limpios = []
    i = 0
    while i < len(args):
        if args[i] in {"-R", "--repo"}:
            i += 2
            continue
        limpios.append(args[i])
        i += 1
    palabras = [a for a in limpios if not a.startswith("-")]
    if not palabras:
        return None
    sub = palabras[0]
    sub2 = palabras[1] if len(palabras) > 1 else ""
    if sub == "pr" and sub2 == "merge":
        return "`gh pr merge`: el merge de un PR lo hace el usuario"
    if sub == "pr" and sub2 == "review" and ("--approve" in limpios or any(grupo_corto(a, "a") for a in limpios)):
        return "aprobar un PR lo hace el usuario"
    if sub == "api":
        metodo = "GET"
        con_cuerpo = False
        for j, a in enumerate(limpios):
            if a in {"-X", "--method"} and j + 1 < len(limpios):
                metodo = limpios[j + 1].upper()
            elif a.startswith("--method="):
                metodo = a.split("=", 1)[1].upper()
            elif a.startswith("-X") and len(a) > 2:
                metodo = a[2:].upper()
            elif a in {"-f", "-F", "--field", "--raw-field", "--input"} or a.startswith(("--field=", "--raw-field=", "--input=")):
                con_cuerpo = True
        if metodo != "GET" or con_cuerpo:
            return "`gh api` solo de lectura (GET sin campos); para escribir existen `gh pr`, `gh issue`…"
        return None
    if sub in GH_SOLO_LECTURA and sub2 not in GH_SOLO_LECTURA[sub]:
        return f"`{' '.join(['gh', sub, sub2]).strip()}` administra el repositorio o la cuenta: lo hace el usuario"
    return None


def regla_railway(args: list[str]) -> str | None:
    """Motivo de bloqueo de `railway <args>` o None."""
    palabras = [a for a in args if not a.startswith("-")]
    if palabras and palabras[0] in RAILWAY_PROHIBIDOS:
        return f"`railway {palabras[0]}`: producción la opera el usuario"
    return None


# ---------------------------------------------------------------------------
# Separación del comando
# ---------------------------------------------------------------------------

def tokenizar(texto: str) -> list[str]:
    """Tokens del comando, con los operadores de shell como tokens aparte. Puede lanzar ValueError."""
    texto = texto.replace("\r", "").replace("\\\n", " ")
    texto = RE_HEREDOC.sub(lambda m: " " + m.group(3) + " ", texto)
    texto = texto.replace("\n", " ; ")
    lexer = shlex.shlex(texto, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def subcomandos(tokens: list[str]) -> list[list[str]]:
    """Parte los tokens en comandos simples; las redirecciones quedan dentro del comando."""
    grupos, actual = [], []
    for token in tokens:
        if token and set(token) <= PUNTUACION and not set(token) <= REDIRECCION:
            if actual:
                grupos.append(actual)
            actual = []
        elif "`" in token and not RE_INVERTIDAS.search(token):
            # Comillas invertidas sin comillas alrededor: lo de adentro es otro comando.
            antes, _, despues = token.partition("`")
            if antes:
                actual.append(antes)
            if actual:
                grupos.append(actual)
            actual = [despues] if despues else []
        else:
            actual.append(token)
    if actual:
        grupos.append(actual)
    return grupos


def quitar_envoltorios(tokens: list[str]) -> list[str]:
    """Saca palabras de control, asignaciones `VAR=valor` y envoltorios (`env`, `timeout 30`…)."""
    tokens = list(tokens)
    while tokens:
        primero = tokens[0]
        base = nombre_base(primero)
        if primero in PALABRAS_DE_CONTROL or RE_ASIGNACION.match(primero):
            tokens.pop(0)
        elif base in ENVOLTORIOS:
            tokens.pop(0)
            while tokens and (tokens[0].startswith("-") or RE_ASIGNACION.match(tokens[0])):
                tokens.pop(0)
            if base == "timeout" and tokens and re.fullmatch(r"[0-9.]+[smhd]?", tokens[0]):
                tokens.pop(0)
        else:
            break
    return tokens


def revisar_simple(tokens: list[str], nivel: int) -> str | None:
    """Motivo de bloqueo de un comando simple (sin operadores) o None."""
    for token in tokens:
        for patron in (RE_SUSTITUCION, RE_INVERTIDAS):
            for interior in patron.findall(token):
                motivo = revisar(interior, nivel + 1)
                if motivo:
                    return motivo
    tokens = quitar_envoltorios(tokens)
    if not tokens:
        return None
    programa, args = nombre_base(tokens[0]), tokens[1:]

    if programa in SHELLS:
        for i, a in enumerate(args):
            if re.fullmatch(r"-[A-Za-z]*c", a) and i + 1 < len(args):
                return revisar(args[i + 1], nivel + 1)
    if programa == "eval":
        return revisar(" ".join(args), nivel + 1)
    if programa == "xargs":
        con_valor = {"-I", "-n", "-P", "-L", "-d", "-a", "-E", "-s"}
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if args[i] in con_valor else 1
        return revisar_simple(args[i:], nivel + 1)
    if programa == "cmd" and args and args[0].lower() in {"/c", "/k"}:
        return revisar(" ".join(args[1:]), nivel + 1)
    if programa in {"powershell", "pwsh"}:
        for i, a in enumerate(args):
            if a.lower() in {"-command", "-c"}:
                return revisar(" ".join(args[i + 1:]), nivel + 1)
    if programa in INTERPRETES:
        guion = next((a for a in args if not a.startswith("-")), "")
        if nombre_base(guion) == "permisos.py" and "--comprobar" not in args:
            return "`permisos.py` lo ejecuta el usuario (Claude solo puede correr `--comprobar`)"
        for i, a in enumerate(args):
            if a in {"-c", "-e"} and i + 1 < len(args):
                motivo = revisar_grueso(args[i + 1])
                if motivo:
                    return f"{motivo} dentro de `{programa} {a}`"
    if programa == "permisos.py" and "--comprobar" not in args:
        return "`permisos.py` lo ejecuta el usuario (Claude solo puede correr `--comprobar`)"

    if programa == "git":
        motivo = regla_git(args)
        if motivo:
            return motivo
    elif programa == "gh":
        motivo = regla_gh(args)
        if motivo:
            return motivo
    elif programa == "railway":
        motivo = regla_railway(args)
        if motivo:
            return motivo

    solo_consulta = programa in {"test", "[", "ls"} or (
        programa == "git" and any(a in {"check-ignore", "ls-files", "status"} for a in args[:3])
    )
    if not solo_consulta:
        for token in args:
            if es_secreto(token):
                return f"`{token}` es un archivo de secretos: no se lee, no se copia y no se versiona"

    escribe = programa in ESCRITORES and (programa != "sed" or any(a == "--in-place" or grupo_corto(a, "i") or a.startswith("-i") for a in args))
    for i, token in enumerate(args):
        normal = token.replace("\\", "/")
        protegido = any(ruta in normal for ruta in RUTAS_PROTEGIDAS)
        tras_redireccion = i > 0 and args[i - 1] and set(args[i - 1]) <= REDIRECCION and ">" in args[i - 1]
        if protegido and (escribe or tras_redireccion):
            return f"`{token}` solo lo cambia el usuario (hooks de git y settings de Claude Code)"
    return None


def revisar(comando: str, nivel: int = 0) -> str | None:
    """Motivo de bloqueo del comando completo o None si puede correr."""
    if nivel > 5:
        return None
    try:
        tokens = tokenizar(comando)
    except ValueError:
        return revisar_grueso(comando)
    for grupo in subcomandos(tokens):
        motivo = revisar_simple(grupo, nivel)
        if motivo:
            return motivo
    return None


def main(entrada: str, err=sys.stderr) -> int:
    """Punto de entrada testeable: 2 bloquea, 0 deja pasar."""
    try:
        datos = json.loads(entrada)
        comando = datos.get("tool_input", {}).get("command", "")
        if not isinstance(comando, str) or not comando.strip():
            return 0
        motivo = revisar(comando)
    except Exception:  # noqa: BLE001 - ante un error interno no se corta la sesión; `deny` sigue aplicando
        return 0
    if motivo is None:
        return 0
    print(
        f"guardia_bash: bloqueado: {motivo}. Esto queda en manos del usuario: déjale el comando "
        "listo y sigue con lo demás. No lo intentes escrito de otra forma.",
        file=err,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    sys.exit(main(sys.stdin.buffer.read().decode("utf-8", errors="replace")))
