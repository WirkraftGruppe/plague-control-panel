"""Recibo de verificación (método v2) para un solo repo.

- `head(raiz)`: hash corto del HEAD del repo cuyo toplevel contiene `raiz`.
- `test_es_nuevo(raiz, base, comando)`: dice si el test que nombra un criterio `[test]` no
  existía en el commit `base` (True/False) o None si el formato del comando no se reconoce.
- `escribir_recibo(ruta, seccion)`: agrega una sección al final del recibo.
- `leer_recibo(ruta)`: secciones ya escritas, salteando los bloques de código.
- `registrar_head` / `head_tiene_recibo`: índice `<raiz>/.claude/.recibos.json`
  (lista con los últimos 50 HEAD verificados con veredicto PASA).

`git` se invoca siempre con `-C <directorio>`.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

MAX_HEADS = 50
LINEAS_SALIDA_FALLA = 30


def _git(directorio, *args: str):
    """Corre git en `directorio`; devuelve el proceso o None si git no se puede ejecutar."""
    try:
        return subprocess.run(
            ["git", "-C", str(directorio), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def head(raiz):
    """Hash corto del HEAD del repo de `raiz`; None si no es un repo o no hay commits."""
    proceso = _git(raiz, "rev-parse", "--short", "HEAD")
    if proceso is None or proceso.returncode != 0 or not proceso.stdout.strip():
        return None
    return proceso.stdout.strip()


def _contenido_en_base(raiz, base: str, ruta: str):
    """Contenido de `ruta` (relativa a `raiz`) en el commit `base`; None si no existe ahí."""
    proceso = _git(raiz, "show", f"{base}:./{ruta}")
    if proceso is None or proceso.returncode != 0:
        return None
    return proceso.stdout


def _definido_en_base(raiz, base: str, ruta: str, nombre: str) -> bool:
    """True si `def <nombre>` ya estaba en `ruta` dentro de la base."""
    contenido = _contenido_en_base(raiz, base, ruta)
    return contenido is not None and re.search(rf"\bdef\s+{re.escape(nombre)}\b", contenido) is not None


def test_es_nuevo(raiz, base: str, comando: str):
    """True si el test del criterio no existía en `base`, False si ya existía, None si no se reconoce."""
    raiz = Path(raiz)
    # Ruta punteada de Django: `manage.py test apps.x.tests.test_y.Clase.test_z`.
    coincide = re.search(r"manage\.py\s+test\s+(?:-\S+\s+)*([\w.]+)", comando)
    if coincide:
        partes = coincide.group(1).split(".")
        # Prefijo más largo de la ruta que sea un archivo `.py` (en el árbol o en la base).
        for largo in range(len(partes), 0, -1):
            ruta = "/".join(partes[:largo]) + ".py"
            if (raiz / ruta).is_file() or _contenido_en_base(raiz, base, ruta) is not None:
                return not _definido_en_base(raiz, base, ruta, partes[-1])
        return None

    # pytest: `pytest <archivo>.py::[<Clase>::]<función>`.
    coincide = re.search(r"pytest\s+(?:-\S+\s+)*([^\s:]+\.py)::(\S+)", comando)
    if coincide:
        nombre = coincide.group(2).split("::")[-1].split("[")[0]
        return not _definido_en_base(raiz, base, coincide.group(1), nombre)

    return None


def _ultimas_lineas(salida: str, cuantas: int = LINEAS_SALIDA_FALLA) -> str:
    """Las últimas `cuantas` líneas de `salida`."""
    return "\n".join(salida.rstrip("\n").splitlines()[-cuantas:])


def escribir_recibo(ruta, seccion: dict) -> None:
    """Agrega `seccion` al final del recibo `ruta` (lo crea con sus carpetas si no existe).

    Claves de `seccion`: fecha, alcance, head (hash), contrato, criterios (lista de dicts con
    comando, pasa, exit, nuevo, salida; opcional `previo`: fecha del recibo que se reutiliza),
    duracion (s) y veredicto.
    """
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        f"## {seccion.get('fecha', '')} — {seccion.get('alcance', '')}",
        "",
        f"- HEAD verificado: {seccion.get('head', '')}",
        f"- Contrato: {seccion.get('contrato', '')}",
        "- Criterios:",
    ]
    for criterio in seccion.get("criterios", []):
        nuevo = {True: "sí", False: "no"}.get(criterio.get("nuevo"), "—")
        estado = "PASA" if criterio.get("pasa") else "FALLA"
        if criterio.get("previo"):
            detalle = f"recibo previo {criterio['previo']}"
        else:
            detalle = f"exit {criterio.get('exit')}, nuevo: {nuevo}"
        lineas.append(f"  - {estado} ({detalle}) `{criterio.get('comando', '')}`")
        if not criterio.get("pasa"):
            salida = _ultimas_lineas(criterio.get("salida", "")).splitlines()
            lineas += ["    ```", *("    " + linea for linea in salida), "    ```"]
    lineas += [
        f"- duración: {seccion.get('duracion', 0)} s",
        f"- Veredicto: {seccion.get('veredicto', '')}",
        "",
        "",
    ]
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lineas))


RE_ENCABEZADO = re.compile(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) — (.*)$")
RE_LINEA_CRITERIO = re.compile(r"^  - (PASA|FALLA) \(([^)]*)\) `(.*)`\s*$")


def leer_recibo(ruta) -> list[dict]:
    """Secciones del recibo en orden de escritura; lista vacía si el archivo no existe.

    Cada sección: `fecha`, `alcance`, `head`, `contrato` y `lineas` (dicts con `pasa`,
    `previo` —fecha o None— y `comando`). Los bloques de código (salidas de FALLA) se saltean.
    """
    try:
        texto = Path(ruta).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    secciones: list[dict] = []
    en_codigo = False
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        encabezado = RE_ENCABEZADO.match(linea)
        if encabezado:
            secciones.append({"fecha": encabezado.group(1), "alcance": encabezado.group(2),
                              "head": "", "contrato": "", "lineas": []})
        elif not secciones:
            continue
        elif linea.startswith("- HEAD verificado:"):
            secciones[-1]["head"] = linea[len("- HEAD verificado:"):].strip()
        elif linea.startswith("- Contrato:"):
            secciones[-1]["contrato"] = linea[len("- Contrato:"):].strip()
        else:
            criterio = RE_LINEA_CRITERIO.match(linea)
            if criterio:
                previo = re.match(r"recibo previo (.+)$", criterio.group(2))
                secciones[-1]["lineas"].append({"pasa": criterio.group(1) == "PASA",
                                                "previo": previo.group(1) if previo else None,
                                                "comando": criterio.group(3)})
    return secciones


def _ruta_indice(raiz) -> Path:
    """Ruta del índice de recibos."""
    return Path(raiz) / ".claude" / ".recibos.json"


def _leer_indice(raiz) -> list:
    """Lista de HEAD registrados; vacía si el índice no existe o está corrupto."""
    try:
        datos = json.loads(_ruta_indice(raiz).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [h for h in datos if isinstance(h, str)] if isinstance(datos, list) else []


def registrar_head(raiz, hash_: str) -> None:
    """Agrega `hash_` al índice conservando los últimos 50. Solo se llama con veredicto PASA."""
    lista = [h for h in _leer_indice(raiz) if h != hash_]
    lista = (lista + [hash_])[-MAX_HEADS:]
    ruta = _ruta_indice(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(lista, indent=2), encoding="utf-8", newline="\n")


def head_tiene_recibo(raiz, hash_: str) -> bool:
    """True si `hash_` figura en el índice; compara por prefijo (hash corto contra largo)."""
    if not hash_:
        return False
    return any(h.startswith(hash_) or hash_.startswith(h) for h in _leer_indice(raiz))
