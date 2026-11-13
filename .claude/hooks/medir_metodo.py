"""Mide el costo del método de trabajo de Detach y lo compara con las metas.

Uso (desde la raíz del proyecto):
    py -3 .claude/hooks/medir_metodo.py                 # informe en pantalla
    py -3 .claude/hooks/medir_metodo.py --planes 5      # solo los últimos 5 planes
    py -3 .claude/hooks/medir_metodo.py --registrar docs/metodo/metricas.md

Qué mide:
- Peso de arranque: bytes de `CLAUDE.md` y de la salida de `.claude/hooks/contexto.sh`
  (con stdin cerrado), que es lo que entra en cada sesión antes de trabajar.
- Agentes: cuántos `.claude/agents/*.md` hay.
- Planes: commits de proceso (`docs(plan):`, `registro:`, `cierre:`) por plan y la
  verificación final, leída del recibo `docs/planes/<slug>.recibo.md` (línea `duración:`
  de las secciones `todo`).
- Permisos: reglas `allow` con comodín sobre un ejecutor genérico, que anulan los `deny`.
- Pendientes abiertos (`pendientes.py --json`) y tamaño de `docs/estado.md`.

Solo lee: no modifica nada salvo el archivo de `--registrar`, al que le agrega una fila.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Metas del método v2. Un valor por encima de la meta se marca ALTO.
METAS = {
    "claude_md_bytes": 8_000,
    "inyeccion_bytes": 6_000,
    "agentes": 3,
    "commits_proceso_por_plan": 2,
    "verificacion_final_min": 30,
    "permisos_comodin": 0,
    "estado_lineas": 25,
    "estado_bytes": 3_000,
}

RE_PLAN = re.compile(r"^docs\(plan\): ([a-z0-9-]+)")
RE_PROCESO = re.compile(r"^(registro|cierre|docs\(plan\)): ([a-z0-9-]+)")
RE_RUTA = re.compile(r"^- \*\*ruta\*\*:\s*`?([a-zñ]+)", re.MULTILINE)
RE_REVISIONES = re.compile(r"^### Revisiones[ \t]*\r?$", re.MULTILINE)
RE_DURACION = re.compile(r"^- duración:\s*(\d+(?:\.\d+)?)\s*s", re.MULTILINE)
RE_SECCION_TODO = re.compile(r"## [^\n]* — todo ")
# Ejecutores genéricos: una regla allow que los habilita con comodín permite cualquier cosa.
EJECUTORES = r"(cmd(\.exe)?|powershell(\.exe)?|pwsh|bash|sh|py|python3?(\.exe)?|node|xargs|find|env|[^ ()]*venv/Scripts/python\.exe)"
RE_COMODIN = re.compile(r"^Bash\(" + EJECUTORES + r"(:\*| \*| -c[^)]*\*)\)$")


def git_log(repo: Path) -> list[tuple[int, str]]:
    """Commits del repo en orden cronológico como (timestamp, asunto)."""
    git = shutil.which("git")
    if not git or not (repo / ".git").exists():
        return []
    salida = subprocess.run(
        [git, "-C", str(repo), "log", "--reverse", "--format=%ct%x09%s"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    filas = []
    for linea in salida.stdout.splitlines():
        if "\t" in linea:
            ts, asunto = linea.split("\t", 1)
            if ts.isdigit():
                filas.append((int(ts), asunto))
    return filas


def plan_del_ultimo_commit(commits: list[tuple[int, str]], raiz: Path) -> Path | None:
    """Archivo del plan del último commit `docs(plan): <slug>`, resuelto por slug."""
    for _, asunto in reversed(commits):
        m = RE_PLAN.match(asunto)
        if m:
            archivos = sorted((raiz / "docs" / "planes").glob(f"*-{m.group(1)}.md"))
            return archivos[-1] if archivos else None
    return None


def leer_revisiones(plan: Path | None) -> tuple[str, str, str]:
    """Ruta del plan y rondas `b/d/m` sumadas por modo (plan, cierre).

    Lee `- **ruta**:` del encabezado y las tablas bajo cada línea `### Revisiones` (solo
    el encabezado real: el texto del plan puede nombrar la tabla antes). Sin dato, sin
    filas del modo o con un valor no numérico, devuelve `—` en lugar de inventar un número.
    """
    if plan is None or not plan.exists():
        return "—", "—", "—"
    texto = plan.read_text(encoding="utf-8", errors="replace")
    m = RE_RUTA.search(texto)
    ruta = m.group(1) if m else "—"
    sumas: dict[str, list[int]] = {}
    invalidos: set[str] = set()
    for encabezado in RE_REVISIONES.finditer(texto):
        seccion = texto[encabezado.end():].split("\n#", 1)[0]
        for linea in seccion.splitlines():
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if len(celdas) < 5 or celdas[1] not in ("plan", "cierre"):
                continue
            modo = celdas[1]
            if not all(c.isdigit() for c in celdas[2:5]):
                invalidos.add(modo)
                continue
            acum = sumas.setdefault(modo, [0, 0, 0])
            for i, c in enumerate(celdas[2:5]):
                acum[i] += int(c)
    por_modo = ["—" if modo in invalidos or modo not in sumas else "/".join(map(str, sumas[modo]))
                for modo in ("plan", "cierre")]
    return ruta, por_modo[0], por_modo[1]


def peso_arranque(raiz: Path) -> tuple[int, int]:
    """Bytes de `CLAUDE.md` y de la salida del hook de inicio (stdin cerrado)."""
    claude_md = raiz / "CLAUDE.md"
    tam_claude = claude_md.stat().st_size if claude_md.exists() else 0
    hook = raiz / ".claude" / "hooks" / "contexto.sh"
    bash = shutil.which("bash")
    tam_inyeccion = 0
    if hook.exists() and bash:
        entorno = dict(os.environ, CLAUDE_PROJECT_DIR=str(raiz))
        res = subprocess.run([bash, str(hook)], capture_output=True, cwd=raiz, env=entorno,
                             timeout=60, stdin=subprocess.DEVNULL)
        tam_inyeccion = len(res.stdout)
    return tam_claude, tam_inyeccion


def contar_agentes(raiz: Path) -> int:
    """Cantidad de definiciones en `.claude/agents/*.md`."""
    return len(list((raiz / ".claude" / "agents").glob("*.md")))


def medir_planes(commits: list[tuple[int, str]], raiz: Path) -> list[dict]:
    """Una fila por plan con sus commits de proceso y la verificación final del recibo."""
    planes: dict[str, dict] = {}
    for ts, asunto in commits:
        m = RE_PLAN.match(asunto)
        if m:
            planes.setdefault(m.group(1), {"slug": m.group(1), "inicio": ts, "proceso": 0})
        m = RE_PROCESO.match(asunto)
        if m and m.group(2) in planes:
            planes[m.group(2)]["proceso"] += 1

    filas = []
    for p in planes.values():
        fila = {"slug": p["slug"], "inicio": p["inicio"], "proceso": p["proceso"], "verif_min": None}
        recibo = raiz / "docs" / "planes" / f"{p['slug']}.recibo.md"
        if recibo.exists():
            duraciones = []
            texto = recibo.read_text(encoding="utf-8", errors="replace")
            for seccion in re.split(r"^(?=## )", texto, flags=re.MULTILINE):
                if RE_SECCION_TODO.match(seccion):
                    duraciones += [float(x) for x in RE_DURACION.findall(seccion)]
            if duraciones:
                fila["verif_min"] = int(duraciones[-1]) // 60
        filas.append(fila)
    filas.sort(key=lambda f: f["inicio"])
    return filas


def permisos_comodin(raiz: Path) -> list[str]:
    """Reglas allow de `.claude/settings.json` que habilitan un ejecutor con comodín."""
    archivo = raiz / ".claude" / "settings.json"
    if not archivo.exists():
        return []
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return ["settings.json: JSON inválido"]
    return [f"settings.json: {r}" for r in datos.get("permissions", {}).get("allow", [])
            if RE_COMODIN.match(r)]


def pendientes_abiertos(raiz: Path) -> int | None:
    """Pendientes abiertos según `pendientes.py --json`; None si no se puede medir."""
    script = raiz / ".claude" / "hooks" / "pendientes.py"
    if not script.exists():
        return None
    res = subprocess.run([sys.executable, str(script), "--raiz", str(raiz), "--json"],
                         capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    try:
        return len(json.loads(res.stdout.decode("utf-8", errors="replace"))["abiertos"])
    except (ValueError, KeyError):
        return None


def texto_estado(archivo: Path) -> str | None:
    """Contenido de estado.md; None si no existe."""
    if not archivo.exists():
        return None
    return archivo.read_text(encoding="utf-8", errors="replace")


def lineas_estado(archivo: Path) -> int | None:
    contenido = texto_estado(archivo)
    return None if contenido is None else len(contenido.splitlines())


def bytes_estado(archivo: Path) -> int | None:
    contenido = texto_estado(archivo)
    return None if contenido is None else len(contenido.encode("utf-8"))


def marca(valor, meta) -> str:
    """`OK` si el valor entra en la meta, `ALTO` si la supera, `—` si no hay dato."""
    if valor is None:
        return "—"
    return "OK" if valor <= meta else "ALTO"


def promedios(planes: list[dict]) -> tuple[float | None, int | None]:
    """Promedio de commits de proceso por plan y de minutos de verificación final."""
    proceso = [p["proceso"] for p in planes]
    verifs = [p["verif_min"] for p in planes if p["verif_min"] is not None]
    return (round(sum(proceso) / len(proceso), 1) if proceso else None,
            round(sum(verifs) / len(verifs)) if verifs else None)


def registrar(destino: Path, valores: dict) -> None:
    """Agrega una fila a `destino`; si no existe, crea título y encabezado."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not destino.exists()
    with destino.open("a", encoding="utf-8", newline="\n") as f:
        if nuevo:
            f.write("# Métricas del método\n\n")
            f.write("| Fecha | CLAUDE.md (B) | Inyección (B) | Agentes | Proceso/plan | Verif. final (min) | "
                    "Comodines | Pendientes | Ruta | Rev. plan (b/d/m) | Rev. cierre (b/d/m) |\n")
            f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        f.write(
            f"| {dt.date.today().isoformat()} | {valores['claude']} | {valores['inyeccion']} | "
            f"{valores['agentes']} | {valores['proceso']} | {valores['verif']} | {valores['comodines']} | "
            f"{valores['pendientes']} | {valores['ruta']} | {valores['rev_plan']} | {valores['rev_cierre']} |\n"
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raiz", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    parser.add_argument("--planes", type=int, default=10, help="cuántos planes recientes medir")
    parser.add_argument("--plan", help="ruta del plan a registrar; por defecto, el del último commit docs(plan):")
    parser.add_argument("--registrar", help="archivo markdown al que agregar una fila de resumen")
    args = parser.parse_args(argv)
    raiz = Path(args.raiz).resolve()

    tam_claude, tam_inyeccion = peso_arranque(raiz)
    agentes = contar_agentes(raiz)
    commits = git_log(raiz)
    planes = medir_planes(commits, raiz)[-args.planes:]
    comodines = permisos_comodin(raiz)
    estado = lineas_estado(raiz / "docs" / "estado.md")
    estado_b = bytes_estado(raiz / "docs" / "estado.md")
    pendientes = pendientes_abiertos(raiz)
    proceso_prom, verif_prom = promedios(planes)

    print(f"# Medición del método — {dt.date.today().isoformat()}\n")
    print("| Métrica | Valor | Meta | |")
    print("|---|---|---|---|")
    print(f"| CLAUDE.md | {tam_claude:,} B | {METAS['claude_md_bytes']:,} B | {marca(tam_claude, METAS['claude_md_bytes'])} |")
    print(f"| Inyección del hook de inicio | {tam_inyeccion:,} B | {METAS['inyeccion_bytes']:,} B | {marca(tam_inyeccion, METAS['inyeccion_bytes'])} |")
    print(f"| Agentes | {agentes} | {METAS['agentes']} | {marca(agentes, METAS['agentes'])} |")
    print(f"| Commits de proceso por plan (prom.) | {proceso_prom if proceso_prom is not None else '—'} | {METAS['commits_proceso_por_plan']} | {marca(proceso_prom, METAS['commits_proceso_por_plan'])} |")
    print(f"| Verificación final (prom., min) | {verif_prom if verif_prom is not None else '—'} | {METAS['verificacion_final_min']} | {marca(verif_prom, METAS['verificacion_final_min'])} |")
    print(f"| Permisos allow con comodín ejecutor | {len(comodines)} | {METAS['permisos_comodin']} | {marca(len(comodines), METAS['permisos_comodin'])} |")
    print(f"| Líneas de docs/estado.md | {estado if estado is not None else 'no existe'} | {METAS['estado_lineas']} | {marca(estado, METAS['estado_lineas'])} |")
    print(f"| Bytes de docs/estado.md | {f'{estado_b:,} B' if estado_b is not None else 'no existe'} | {METAS['estado_bytes']:,} B | {marca(estado_b, METAS['estado_bytes'])} |")
    print(f"| Pendientes abiertos | {pendientes if pendientes is not None else '—'} | | |")

    print(f"\n## Últimos {len(planes)} planes\n")
    print("| Plan | Inicio | Commits de proceso | Verificación final (min) |")
    print("|---|---|---|---|")
    for p in planes:
        inicio = dt.datetime.fromtimestamp(p["inicio"]).strftime("%Y-%m-%d %H:%M")
        verif = "—" if p["verif_min"] is None else p["verif_min"]
        print(f"| {p['slug']} | {inicio} | {p['proceso']} | {verif} |")

    if comodines:
        print("\n## Permisos que anulan los deny\n")
        for regla in comodines:
            print(f"- {regla}")

    if args.registrar:
        plan = (raiz / args.plan) if args.plan else plan_del_ultimo_commit(commits, raiz)
        ruta, rev_plan, rev_cierre = leer_revisiones(plan)
        registrar(raiz / args.registrar, {
            "claude": tam_claude, "inyeccion": tam_inyeccion, "agentes": agentes,
            "proceso": proceso_prom if proceso_prom is not None else "—",
            "verif": verif_prom if verif_prom is not None else "—",
            "comodines": len(comodines),
            "pendientes": pendientes if pendientes is not None else "—",
            "ruta": ruta, "rev_plan": rev_plan, "rev_cierre": rev_cierre,
        })
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
