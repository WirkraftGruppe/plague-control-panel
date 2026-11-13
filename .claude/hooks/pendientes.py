#!/usr/bin/env python3
"""Consolida los pendientes que declara cada plan en docs/planes/.

Lee, de cada `AAAA-MM-DD-<slug>.md`, solo la sección `## Pendientes que deja este plan`
que está debajo de `## Registro de verificación`. Abiertos = problemas declarados menos
los cerrados con `cierra:` (de cualquier plan). Los avisos no hacen fallar: sale con 0.

Etiquetas: la subsección `### Etiquetas` admite líneas `- etiqueta: <id> → <destino>` con un
` — nota` opcional (`<destino>` en `[a-z0-9-]+`). Un id puede tener varias etiquetas (no el
mismo destino dos veces) y valen desde cualquier plan, como `cierra:`. Cada abierto lleva
`etiquetas` (lista ordenada) y `--etiqueta <nombre>` deja solo los abiertos que la tienen.

`--resumen` es la salida corta que inyecta el hook de inicio (`contexto.sh`): el recuento por
severidad y solo los `bloqueante` e `importante`, una línea recortada por cada uno.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ENCABEZADO_CORTE = "## Registro de verificación"
ENCABEZADO_SECCION = "## Pendientes que deja este plan"
SEVERIDADES = ["bloqueante", "importante", "menor", "observación"]
SEVERIDADES_DEL_RESUMEN = ("bloqueante", "importante")
MAX_LINEAS_RESUMEN = 10
MAX_TEXTO_RESUMEN = 120

RE_PLAN = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)\.md$")
RE_ID = r"P-([a-z0-9][a-z0-9-]*)-\d+"
RE_PROBLEMA = re.compile(rf"^- ({RE_ID}) \[([^\]]*)\] (.*)$")
RE_CIERRA = re.compile(rf"^- cierra: ({RE_ID})(?: — .*)?$")
RE_ETIQUETA = re.compile(rf"^- etiqueta: ({RE_ID}) → ([a-z0-9-]+)(?: — .*)?$")
RE_DECISION = re.compile(r"^- \d{4}-\d{2}-\d{2} — .+ — .+ — reemplaza a: .+$")
RE_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)


def sin_comentarios(texto):
    """Quita los comentarios HTML conservando la cantidad de líneas."""
    return RE_COMENTARIO.sub(lambda m: "\n" * m.group(0).count("\n"), texto)


def leer_seccion(texto):
    """Devuelve [(número de línea, línea)] de la sección de pendientes bajo el corte."""
    lineas = sin_comentarios(texto).splitlines()
    corte = next((i for i, l in enumerate(lineas) if l.strip() == ENCABEZADO_CORTE), None)
    if corte is None:
        return []
    inicio = next(
        (i for i in range(corte + 1, len(lineas)) if lineas[i].strip() == ENCABEZADO_SECCION),
        None,
    )
    if inicio is None:
        return []
    resultado = []
    for i in range(inicio + 1, len(lineas)):
        if lineas[i].startswith("## "):
            break
        resultado.append((i + 1, lineas[i].rstrip()))
    return resultado


def analizar_plan(archivo, slug, problemas, cierres, etiquetas, avisos):
    """Agrega a `problemas`, `cierres` y `etiquetas` lo declarado en `archivo`; los avisos van a `avisos`."""
    texto = archivo.read_text(encoding="utf-8", errors="replace")
    subseccion = None
    ultimo = None  # problema al que se pegan las líneas sangradas
    for numero, linea in leer_seccion(texto):
        donde = f"{archivo.name}:{numero}"
        if not linea.strip():
            continue
        if linea.startswith("### "):
            subseccion = linea[4:].strip().lower()
            ultimo = None
            continue
        if linea[0] in " \t":
            if ultimo is not None:
                ultimo["texto"] += "\n" + linea.strip()
            continue
        ultimo = None
        if subseccion == "problemas":
            m = RE_PROBLEMA.match(linea)
            if not m:
                avisos.append(f"{donde}: línea con forma inválida en Problemas: {linea}")
                continue
            id_, id_slug, severidad, cuerpo = m.group(1), m.group(2), m.group(3), m.group(4)
            if id_slug != slug:
                avisos.append(f"{donde}: el id {id_} tiene slug ajeno (el plan es {slug})")
            if severidad not in SEVERIDADES:
                avisos.append(f"{donde}: severidad desconocida {severidad!r} en {id_}")
            ultimo = {"id": id_, "severidad": severidad, "plan": slug, "texto": cuerpo, "donde": donde}
            problemas.append(ultimo)
        elif subseccion == "decisiones":
            if not RE_DECISION.match(linea):
                avisos.append(f"{donde}: línea con forma inválida en Decisiones: {linea}")
        elif subseccion == "cierra":
            m = RE_CIERRA.match(linea)
            if m:
                cierres.append((m.group(1), donde))
            else:
                avisos.append(f"{donde}: línea con forma inválida en Cierra: {linea}")
        elif subseccion == "etiquetas":
            m = RE_ETIQUETA.match(linea)
            if m:
                etiquetas.append((m.group(1), m.group(3), donde))
            else:
                avisos.append(f"{donde}: línea con forma inválida en Etiquetas: {linea}")
        else:
            avisos.append(f"{donde}: línea con forma inválida fuera de una subsección: {linea}")


def consolidar(raiz):
    """Devuelve (abiertos, avisos) recorriendo docs/planes/ de la raíz."""
    problemas, cierres, etiquetas, avisos = [], [], [], []
    carpeta = Path(raiz) / "docs" / "planes"
    archivos = sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []
    for archivo in archivos:
        m = RE_PLAN.match(archivo.name)
        if m:
            analizar_plan(archivo, m.group(1), problemas, cierres, etiquetas, avisos)
    vistos = set()
    for p in problemas:
        if p["id"] in vistos:
            avisos.append(f"{p['donde']}: id duplicado {p['id']}")
        vistos.add(p["id"])
    cerrados = set()
    for id_, donde in cierres:
        if id_ not in vistos:
            avisos.append(f"{donde}: cierra un id inexistente {id_}")
        elif id_ in cerrados:
            avisos.append(f"{donde}: cierre repetido de {id_}")
        cerrados.add(id_)
    destinos = {}
    for id_, destino, donde in etiquetas:
        if id_ not in vistos:
            avisos.append(f"{donde}: etiqueta de un id inexistente {id_}")
        elif destino in destinos.setdefault(id_, set()):
            avisos.append(f"{donde}: etiqueta repetida {destino} en {id_}")
        destinos.setdefault(id_, set()).add(destino)
    abiertos = [
        {
            **{k: p[k] for k in ("id", "severidad", "plan", "texto")},
            "etiquetas": sorted(destinos.get(p["id"], ())),
        }
        for p in problemas
        if p["id"] not in cerrados
    ]
    return abiertos, avisos


def imprimir_texto(abiertos, avisos):
    """Salida legible: agrupada por severidad y con los avisos al final."""
    orden = SEVERIDADES + sorted({p["severidad"] for p in abiertos} - set(SEVERIDADES))
    print(f"Pendientes abiertos: {len(abiertos)}")
    for severidad in orden:
        grupo = [p for p in abiertos if p["severidad"] == severidad]
        if not grupo:
            continue
        print(f"\n[{severidad}] ({len(grupo)})")
        for p in grupo:
            sangrado = "\n    ".join(p["texto"].split("\n"))
            marcas = f"[{', '.join(p['etiquetas'])}] " if p["etiquetas"] else ""
            print(f"- {p['id']} ({p['plan']}) {marcas}{sangrado}")
    if avisos:
        print("\nAvisos:")
        for aviso in avisos:
            print(f"- {aviso}")


def imprimir_resumen(abiertos, avisos):
    """Salida corta: recuento por severidad y los bloqueantes e importantes, recortados."""
    recuento = ", ".join(
        f"{sum(1 for p in abiertos if p['severidad'] == s)} {s}" for s in SEVERIDADES
    )
    print(f"Pendientes abiertos: {len(abiertos)} ({recuento})")
    graves = [p for s in SEVERIDADES_DEL_RESUMEN for p in abiertos if p["severidad"] == s]
    for p in graves[:MAX_LINEAS_RESUMEN]:
        texto = " ".join(p["texto"].split())
        if len(texto) > MAX_TEXTO_RESUMEN:
            texto = texto[: MAX_TEXTO_RESUMEN - 1].rstrip() + "…"
        print(f"- {p['id']} [{p['severidad']}] {texto}")
    if len(graves) > MAX_LINEAS_RESUMEN:
        print(f"- … y {len(graves) - MAX_LINEAS_RESUMEN} más entre bloqueantes e importantes")
    if avisos:
        print(f"Avisos de formato: {len(avisos)}")
    print("Lista completa: py -3 .claude/hooks/pendientes.py")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", default=".", help="raíz del proyecto (por defecto, el directorio actual)")
    parser.add_argument("--json", action="store_true", help="imprime JSON en vez de texto")
    parser.add_argument("--etiqueta", help="deja solo los abiertos con esta etiqueta")
    parser.add_argument("--resumen", action="store_true", help="recuento y solo bloqueantes e importantes")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    abiertos, avisos = consolidar(args.raiz)
    if args.etiqueta:
        abiertos = [p for p in abiertos if args.etiqueta in p["etiquetas"]]
    if args.json:
        print(json.dumps({"abiertos": abiertos, "avisos": avisos}, ensure_ascii=False, indent=2))
    elif args.resumen:
        imprimir_resumen(abiertos, avisos)
    else:
        imprimir_texto(abiertos, avisos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
