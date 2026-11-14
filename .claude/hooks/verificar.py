"""Verificación de criterios por script (método v2): `tarea`, `todo` y `cierre`.

Uso, desde el repo o con `--raiz` (por defecto, `git rev-parse --show-toplevel`):

    verificar.py [--raiz R] [--recibo RUTA] tarea <plan> T<n>[,T<m>]   criterios de esas tareas
    verificar.py [--raiz R] [--recibo RUTA] todo <plan>                 todas las tareas y el cierre global
    verificar.py [--raiz R] cierre                                      cierre global, sin plan

Exit 0 si todo pasa, 1 si algo falla y 2 por uso inválido (sin recibo). Hay un solo repo: el HEAD
que se verifica y se registra es el del `--raiz`. El plan se pasa relativo a esa raíz.

Los criterios salen del texto del plan en el commit congelado (`congelado.sh`, del directorio de
este script, corrido sobre el repo de `--raiz`), nunca del disco. Un contrato MODIFICADO cuenta como
aceptado si cada commit `docs(plan): <slug> — modificado…` tiene en `docs/decisiones.md` una línea
`(usuario)` con su hash corto y el plan del disco coincide con el último: los criterios salen de ese
commit. Sin esa línea el contrato queda en FALLA y no se ejecuta ningún criterio (el recibo se
escribe igual, con veredicto FALLA). Las líneas `(usuario)` salen de `git show HEAD:docs/decisiones.md`
y el cierre global de `git show HEAD:.claude/hooks/cierre_global.json`, nunca del disco: una decisión
o un cierre sin commitear no valen. Si solo difiere el plan del disco (sin commits de modificación),
el veredicto es FALLA pero se ejecutan los criterios del commit congelado.

Compatibilidad v1: el cierre global sale del bloque `## Criterios de cierre global` del plan y el
marcador `'<commit_base>'` se reemplaza con la línea `commit_base:` del Registro. Los planes v2 no
traen ese bloque: su cierre global es `cierre_global.json`. El plan nunca se escribe.

Los tres modos agregan el criterio `versionados limpios`, acotado a lo que cada uno toca:
- `tarea`: solo las rutas de `Puede tocar` de las tareas pedidas (comodines incluidos).
- `todo` y `cierre`: cualquier ruta, modificada o sin seguimiento (respetando `.gitignore`), salvo
  `docs/planes/`, `docs/estado.md`, `docs/bitacora.md`, `docs/decisiones.md`, `docs/metodo/` y los
  archivos propios (`.claude/.recibos.json`, `.claude/.verificando`). Lo sin seguimiento se mira
  antes de correr los criterios (los criterios pueden generar archivos) y lo modificado, también
  al final. Con FALLA no se registra el HEAD.
El plan y su recibo quedan excluidos. En `tarea`, lo modificado fuera del alcance se informa en la línea
`- Fuera de alcance (informativo): …` y no cambia el veredicto.

`tarea` agrega además `commits de la tarea dentro de Puede tocar`: cuentan los commits `T<n>:` de las
tareas pedidas y, si la rama actual es `<slug>-T<n>` de una de ellas, todos los commits sin merge de
la rama (`<base>..HEAD`, sin los de `main` ni los de `plan/<slug>`). Un `[test]` que ya existía en la
base es FALLA ("test preexistente"). `todo` es incremental: una tarea cuya última sección del recibo
tiene el mismo HEAD, el mismo contrato y todos sus criterios en PASA no se repite (`PASA (recibo
previo <fecha>)`), pero solo con el árbol limpio. Con PASA, `todo` y `cierre` registran el HEAD
completo y su alcance (`todo <plan>` | `cierre`) en `.claude/.recibos.json`; `tarea` no. El recibo va
a `docs/planes/<slug>.recibo.md` (o `--recibo`: solo `docs/planes/*.recibo.md` dentro de `--raiz` o un
archivo fuera del repo; otra ruta es uso inválido) y se imprime por stdout; el de `cierre` va solo a
stdout. Mientras corre existe `.claude/.verificando` con el PID.

Reutiliza `verificar_plan.py` y `recibo.py` sin modificarlos.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_HOOKS))

import recibo  # noqa: E402
import verificar_plan as vp  # noqa: E402

TIMEOUT_CRITERIO = 900
CIERRE_JSON = DIR_HOOKS / "cierre_global.json"  # copia del disco: solo para los tests; el cierre real sale del HEAD
# Archivos y carpetas que cambian durante el trabajo normal: nunca hacen fallar los versionados.
SILENCIOSAS = ("docs/estado.md", "docs/bitacora.md", "docs/decisiones.md")
PREFIJOS_SILENCIOSOS = ("docs/metodo/",)
PREFIJO_PLANES = "docs/planes/"
# Archivos que el propio verificador crea: nunca hacen fallar los versionados.
PROPIOS = (".claude/.recibos.json", ".claude/.verificando")
RUTA_CIERRE_JSON = ".claude/hooks/cierre_global.json"
RE_CLAVE_TAREAS = re.compile(r"T\d+(,T\d+)*")
RE_ETIQUETA_TAREA = re.compile(r"^T(\d+) \[")
RE_ASUNTO_TAREA = re.compile(r"T(\d+):")
USO = ("uso: verificar.py [--raiz R] [--recibo RUTA] tarea <plan> T<n>[,T<m>] | todo <plan> | cierre")


class UsoInvalido(Exception):
    """Argumentos o plan inválidos: la corrida termina con exit 2 y sin recibo."""


# ---------------------------------------------------------------------------
# Plan: rutas de `Puede tocar`, base y contrato
# ---------------------------------------------------------------------------

def leer_puede_tocar(texto: str) -> dict[int, list[str]]:
    """Rutas de `Puede tocar` de cada `### T<n>` (con comodines); se ignoran los textos que no son rutas."""
    rutas: dict[int, list[str]] = {}
    actual: int | None = None
    en_codigo = False
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        if linea.startswith(vp.CORTE):
            break
        if linea.startswith("#"):
            coincidencia = vp.RE_TAREA.match(linea)
            actual = int(coincidencia.group(1)) if coincidencia else None
            if actual is not None:
                rutas.setdefault(actual, [])
        elif actual is not None and linea.startswith("- **Puede tocar**"):
            rutas[actual] = [r for r in re.findall(r"`([^`]+)`", linea)
                             if re.fullmatch(r"[\w./\-*]+", r) and ("/" in r or "." in r or "*" in r)]
    return rutas


def coincide_ruta(ruta: str, patron: str) -> bool:
    """True si `ruta` es el `patron` (con comodines) o está dentro de él cuando es un directorio."""
    return fnmatch.fnmatchcase(ruta, patron) or ruta.startswith(patron.rstrip("/") + "/")


def base_del_plan(raiz: Path, texto_disco: str, slug: str) -> tuple[str | None, str | None, str | None]:
    """(base del Registro, motivo si no resuelve, base para el resto de los chequeos).

    La base del Registro (`commit_base:` debajo del corte) es la que reemplaza al marcador. Para el
    resto (test preexistente, commits de la tarea) se cae, si el Registro no la tiene, al primer
    commit cuyo asunto es exactamente `docs(plan): <slug>`.
    """
    base, motivo = vp.commit_base_del_registro(texto_disco, raiz, slug)
    if base is not None:
        return base, None, base
    proceso = recibo._git(raiz, "log", "--format=%H%x09%s")
    if proceso is not None and proceso.returncode == 0:
        for linea in reversed(proceso.stdout.splitlines()):
            hash_, _, asunto = linea.partition("\t")
            if asunto == f"docs(plan): {slug}":
                return None, motivo, hash_
    return None, motivo, None


def commits_de_congelado(raiz: Path, slug: str) -> list[tuple[str, str]]:
    """(hash, asunto) de los commits `docs(plan): <slug>` y `docs(plan): <slug> — …`, del más nuevo al más viejo."""
    proceso = recibo._git(raiz, "log", "--format=%H%x09%s")
    if proceso is None or proceso.returncode != 0:
        return []
    asunto = f"docs(plan): {slug}"
    commits = []
    for linea in proceso.stdout.splitlines():
        hash_, _, titulo = linea.partition("\t")
        if titulo == asunto or titulo.startswith(f"{asunto} — "):
            commits.append((hash_, titulo))
    return commits


def recortar_registro(texto: str) -> str:
    """El plan arriba de `## Registro de verificación`, sin CR (como compara congelado.sh)."""
    return texto.replace("\r", "").split(f"\n{vp.CORTE}", 1)[0]


def leer_de_head(raiz: Path, ruta: str) -> str | None:
    """Contenido de `ruta` en el HEAD (`git show HEAD:./<ruta>`), nunca del disco; None si no existe ahí."""
    proceso = recibo._git(raiz, "show", f"HEAD:./{ruta}")
    return proceso.stdout if proceso is not None and proceso.returncode == 0 else None


def modificaciones_aprobadas(raiz: Path, slug: str, commits: list[tuple[str, str]]) -> bool:
    """True si todo commit de congelado salvo el original es una modificación aprobada por el usuario.

    El original es el más viejo y se llama exactamente `docs(plan): <slug>`. Cada otro commit debe
    llamarse `docs(plan): <slug> — modificado…` y tener, en `docs/decisiones.md` del HEAD, una línea
    `(usuario)` que cita su hash corto (una línea `(agente)` no alcanza, ni una decisión sin commitear).
    """
    original = f"docs(plan): {slug}"
    lineas = [linea for linea in (leer_de_head(raiz, "docs/decisiones.md") or "").splitlines() if "(usuario)" in linea]
    for indice, (hash_, titulo) in enumerate(commits):
        if indice == len(commits) - 1 and titulo == original:
            continue
        if not titulo.startswith(f"{original} — modificado") or not any(
            re.search(rf"(?<![0-9a-f]){hash_[:7]}[0-9a-f]*", linea) for linea in lineas
        ):
            return False
    return True


def contrato_aceptado(raiz: Path, plan: Path, slug: str, commits: list[tuple[str, str]]) -> tuple[str, str] | None:
    """Contrato modificado y aceptado por el usuario: (texto del último commit, su hash), o None.

    Se acepta si hay commits de modificación, todos aprobados (`modificaciones_aprobadas`) y el plan
    del disco coincide con el último arriba del corte.
    """
    if len(commits) < 2 or not modificaciones_aprobadas(raiz, slug, commits):
        return None
    texto = vp.texto_congelado(raiz, plan, commits[0][0])
    try:
        disco = plan.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if texto is None or recortar_registro(texto) != recortar_registro(disco):
        return None
    return texto, commits[0][0]


def cargar_contrato(raiz: Path, plan: Path, bash: str) -> tuple[str | None, str, bool]:
    """Comprueba el congelado. Devuelve (texto del plan a ejecutar | None, línea de contrato, aceptado).

    Con commits de modificación sin decisión del usuario en el HEAD no hay texto: no se ejecuta ningún
    criterio. Si las modificaciones están aprobadas pero el plan del disco difiere (o solo difiere el
    disco), el texto es el del último commit de congelado y `aceptado` es False. Sin ningún commit de
    congelado no hay texto.
    """
    slug = vp.slug_de(plan)
    codigo, salida, error = vp.correr_congelado(bash, raiz, plan)
    commit = vp.hash_valido(salida) if codigo == 0 else None
    if commit is not None:
        texto = vp.texto_congelado(raiz, plan, commit)
        if texto is None:
            return None, f"FALLA: no se pudo leer el plan del commit congelado {commit[:7]}", False
        return texto, f"intacto (congelado en {commit[:7]})", True
    detalle = " ".join(error.split())[:300] if error.strip() else "sin detalle"
    if codigo == 1:
        commits = commits_de_congelado(raiz, slug)
        if commits and not modificaciones_aprobadas(raiz, slug, commits):
            return (None, f"FALLA: contrato MODIFICADO sin decisión del usuario; no se ejecuta ningún criterio "
                          f"({detalle})", False)
        aceptado = contrato_aceptado(raiz, plan, slug, commits)
        if aceptado is not None:
            texto, ultimo = aceptado
            return texto, f"modificado y aceptado ({ultimo[:7]}, decisión del usuario)", True
        if commits:
            texto = vp.texto_congelado(raiz, plan, commits[0][0])
            if texto is not None:
                return (texto, f"FALLA: contrato MODIFICADO en el disco; se ejecutan los criterios "
                               f"del último commit congelado {commits[0][0][:7]} ({detalle})", False)
    estado = "error" if codigo is None else codigo
    return None, f"FALLA: contrato MODIFICADO o no congelado: congelado.sh salió con {estado} ({detalle})", False


# ---------------------------------------------------------------------------
# Ejecución de criterios
# ---------------------------------------------------------------------------

def etiqueta_de(criterio: vp.Criterio) -> str:
    """Texto con que un criterio queda en el recibo."""
    return f"{criterio.origen} [{criterio.tipo}] {criterio.comando}"


def ejecutar_criterio(criterio: vp.Criterio, raiz: Path, bash: str, plan: Path | None, base_registro: str | None,
                      motivo_base: str | None, base: str | None, timeout: float) -> dict:
    """Ejecuta un criterio y devuelve el dict que espera `recibo.escribir_recibo`.

    Sin `plan` (cierre global) no hay marcador ni base. Un `[test]` que ya existía en `base` es FALLA.
    """
    etiqueta = etiqueta_de(criterio)
    real = criterio
    if plan is not None:
        a_ejecutar, fallas = vp.reemplazar_commit_base([criterio], base_registro, motivo_base, plan)
        if fallas:
            return {"comando": etiqueta, "pasa": False, "exit": 1, "nuevo": None, "salida": fallas[0].salida}
        real = a_ejecutar[0]
    nuevo = None
    if criterio.tipo == "test" and base:
        nuevo = recibo.test_es_nuevo(raiz, base, real.comando)
        if nuevo is False:
            return {"comando": etiqueta, "pasa": False, "exit": 1, "nuevo": False,
                    "salida": f"test preexistente: ya existía en la base {base[:7]}"}
    resultado = vp.evaluar(real, raiz, bash, timeout)
    codigo = "timeout" if resultado.codigo is None else resultado.codigo
    return {"comando": etiqueta, "pasa": resultado.pasa, "exit": codigo, "nuevo": nuevo, "salida": resultado.salida}


def elementos_de_texto(texto: str, nombre: str) -> list[tuple[str, tuple[str, ...]]]:
    """(comando, prefijos `si_toca`) de cada elemento de `comandos`: una cadena o `{"cmd", "si_toca"}`."""
    try:
        datos = json.loads(texto)
    except ValueError as error:
        raise UsoInvalido(f"no se pudo leer {nombre}: {error}") from error
    comandos = datos.get("comandos") if isinstance(datos, dict) else datos
    elementos: list[tuple[str, tuple[str, ...]]] = []
    for c in comandos if isinstance(comandos, list) else [None]:
        if isinstance(c, str):
            elementos.append((c, ()))
        elif isinstance(c, dict) and isinstance(c.get("cmd"), str) and isinstance(c.get("si_toca", []), list) \
                and all(isinstance(p, str) for p in c.get("si_toca", [])):
            elementos.append((c["cmd"], tuple(c.get("si_toca", []))))
        else:
            raise UsoInvalido(f"{nombre} debe ser una lista de comandos o un objeto con 'comandos'")
    return elementos


def criterios_de_texto(texto: str, nombre: str) -> list[vp.Criterio]:
    """Criterios de cierre global del texto de `cierre_global.json` (lista de comandos `[cmd]`)."""
    return [vp.Criterio("cierre global", "cmd", comando) for comando, _ in elementos_de_texto(texto, nombre)]


def criterios_de_cierre(ruta_json: Path) -> list[vp.Criterio]:
    """Criterios de cierre global según un `cierre_global.json` del disco (solo lo usan los tests)."""
    try:
        texto = ruta_json.read_text(encoding="utf-8")
    except OSError as error:
        raise UsoInvalido(f"no se pudo leer {ruta_json.name}: {error}") from error
    return criterios_de_texto(texto, ruta_json.name)


def criterios_de_cierre_head(raiz: Path) -> list[vp.Criterio]:
    """Criterios de cierre global del `cierre_global.json` que está en el HEAD, nunca el del disco."""
    texto = leer_de_head(raiz, RUTA_CIERRE_JSON)
    if texto is None:
        raise UsoInvalido(f"no hay {RUTA_CIERRE_JSON} en el HEAD de {raiz}")
    return criterios_de_texto(texto, f"HEAD:{RUTA_CIERRE_JSON}")


def comandos_de_cierre(raiz: Path, cierre_json: Path | None) -> list[vp.Criterio]:
    """Cierre global: el JSON del HEAD, o `cierre_json` si el llamador (un test) pasa uno explícito."""
    return criterios_de_cierre(cierre_json) if cierre_json is not None else criterios_de_cierre_head(raiz)


def condiciones_de_cierre(raiz: Path, cierre_json: Path | None) -> dict[str, tuple[str, ...]]:
    """Prefijos `si_toca` por comando del mismo cierre que `comandos_de_cierre` (solo los que lo declaran)."""
    if cierre_json is not None:
        try:
            texto, nombre = cierre_json.read_text(encoding="utf-8"), cierre_json.name
        except OSError as error:
            raise UsoInvalido(f"no se pudo leer {cierre_json.name}: {error}") from error
    else:
        texto, nombre = leer_de_head(raiz, RUTA_CIERRE_JSON), f"HEAD:{RUTA_CIERRE_JSON}"
    return {c: p for c, p in elementos_de_texto(texto or "[]", nombre) if p}


def archivos_cambiados(raiz: Path, base: str | None, modificados: list[tuple[str, str]] | None) -> list[str] | None:
    """Archivos de `base..HEAD` más los modificados que no son de proceso; None si no hay base o git no responde."""
    if base is None or modificados is None:
        return None
    proceso = recibo._git(raiz, "diff", "--name-only", f"{base}..HEAD")
    if proceso is None or proceso.returncode != 0:
        return None
    return [a for a in proceso.stdout.splitlines() if a.strip()] + [r for _, r in modificados if destino(r, "todo", set(), []) == "falla"]


# ---------------------------------------------------------------------------
# Versionados limpios y commits de la tarea
# ---------------------------------------------------------------------------

def destino(ruta: str, regla: str, excluidas: set[str], propias: list[str]) -> str:
    """Qué se hace con un versionado modificado: `falla`, `informa` o `ignora`."""
    if ruta in excluidas or ruta in PROPIOS:
        return "ignora"
    silenciosa = ruta in SILENCIOSAS or ruta.startswith(PREFIJOS_SILENCIOSOS)
    if regla != "tarea":  # `todo` y `cierre`: cualquier ruta fuera de las de proceso falla
        return "ignora" if silenciosa or ruta.startswith(PREFIJO_PLANES) else "falla"
    if any(coincide_ruta(ruta, patron) for patron in propias):
        return "falla"
    return "ignora" if silenciosa else "informa"


def versionados_modificados(raiz: Path, sin_seguimiento: bool = False) -> list[tuple[str, str]] | None:
    """(estado, ruta) de cada archivo modificado (y, si se pide, sin seguimiento: `??`); None si git no responde.

    Los archivos sin seguimiento se listan uno por uno y respetando `.gitignore`.
    """
    proceso = recibo._git(raiz, "status", "--porcelain", f"--untracked-files={'all' if sin_seguimiento else 'no'}", "-z")
    if proceso is None or proceso.returncode != 0:
        return None
    entradas = [e for e in proceso.stdout.split("\0") if e]
    modificados: list[tuple[str, str]] = []
    indice = 0
    while indice < len(entradas):
        entrada = entradas[indice]
        rutas = [entrada[3:]]
        if entrada[0] in "RC":  # renombre o copia: el origen viene como entrada aparte
            indice += 1
            rutas.append(entradas[indice] if indice < len(entradas) else "")
        estado = entrada[:2].strip() or "M"
        indice += 1
        modificados += [(estado, ruta) for ruta in rutas]
    return modificados


def versionados_limpios(raiz: Path, regla: str, excluidas: set[str] = frozenset(), propias: tuple[str, ...] = (),
                        previos: list[tuple[str, str]] | None = ()) -> dict:
    """Criterio de versionados limpios, acotado según `regla` (`tarea`, `todo` o `cierre`).

    Devuelve el dict de criterio con `fuera`: lo informado sin afectar el veredicto. `previos` son
    los archivos modificados o sin seguimiento vistos antes de correr los criterios (que pueden crear
    archivos): se suman a lo modificado de ahora. `None` es que git no respondió entonces.
    """
    alcance = {
        "cierre": "modificados y sin seguimiento; se excluyen docs/planes, estado, bitácora, decisiones y metodo",
        "tarea": "solo las rutas de Puede tocar; plan y recibo excluidos",
        "todo": "modificados y sin seguimiento; se excluyen docs/planes, estado, bitácora, decisiones y metodo",
    }[regla]
    etiqueta = f"versionados limpios (sin cambios versionados; {alcance})"
    modificados = versionados_modificados(raiz)
    if modificados is None or previos is None:
        return {"comando": etiqueta, "pasa": False, "exit": 1, "nuevo": None, "salida": "no se pudo leer git status"}
    vistos = {ruta for _, ruta in modificados}
    modificados += [(estado, ruta) for estado, ruta in previos if ruta not in vistos]
    sucios: list[str] = []
    fuera: list[str] = []
    for estado, ruta in modificados:
        accion = destino(ruta, regla, set(excluidas), list(propias))
        if accion == "falla":
            sucios.append(f"{estado} {ruta}")
        elif accion == "informa":
            fuera.append(f"{estado} {ruta}")
    return {"comando": etiqueta, "pasa": not sucios, "exit": 0 if not sucios else 1, "nuevo": None,
            "salida": "\n".join(sucios) if sucios else "limpia", "fuera": fuera}


def commits_de_tareas(raiz: Path, base: str, slug: str = "",
                      pedidas: list[int] | None = None) -> list[tuple[int, str, list[str]]] | None:
    """(tarea, asunto, archivos) de cada commit sin merge `T<n>:` en `<base>..HEAD`; None si git falla.

    Fuera de `main`, y si `main` existe, se excluyen los commits alcanzables desde `main`. Si la rama
    actual es `<slug>-T<n>` y la T<n> está en `pedidas`, entran todos los commits de la rama.
    """
    pedidas = pedidas or []
    argumentos = ["log", "--no-merges", "--name-only", "--format=%x01%s", f"{base}..HEAD"]
    actual = recibo._git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
    rama = actual.stdout.strip() if actual is not None else ""
    principal = recibo._git(raiz, "rev-parse", "--verify", "--quiet", "refs/heads/main")
    if actual is not None and rama != "main" and principal is not None and principal.returncode == 0:
        argumentos.append("^main")
    # En la rama de la subtarea (`<slug>-T<n>`) cuentan todos sus commits, lleven o no el prefijo `T<n>:`;
    # los que ya están en `plan/<slug>` (la base de la rama) no son de la subtarea.
    de_rama = re.fullmatch(rf"{re.escape(slug)}-T(\d+)", rama) if slug else None
    numero_rama = int(de_rama.group(1)) if de_rama and int(de_rama.group(1)) in pedidas else None
    if numero_rama is not None:
        del_plan = recibo._git(raiz, "rev-parse", "--verify", "--quiet", f"refs/heads/plan/{slug}")
        if del_plan is not None and del_plan.returncode == 0:
            argumentos.append(f"^plan/{slug}")
    proceso = recibo._git(raiz, *argumentos)
    if proceso is None or proceso.returncode != 0:
        return None
    commits: list[tuple[int, str, list[str]]] = []
    for bloque in proceso.stdout.split("\x01")[1:]:
        asunto, _, resto = bloque.partition("\n")
        coincidencia = RE_ASUNTO_TAREA.match(asunto)
        numero = numero_rama if numero_rama is not None else int(coincidencia.group(1)) if coincidencia else None
        if numero is not None:
            commits.append((numero, asunto, [a for a in resto.splitlines() if a.strip()]))
    return commits


def commits_fuera_de_alcance(raiz: Path, rutas: dict[int, list[str]], pedidas: list[int], base: str | None,
                             slug: str = "") -> dict:
    """Criterio: los commits de las tareas pedidas solo tocan archivos de su `Puede tocar`.

    Se compara el número entero del asunto (`T1:` nunca captura `T11:`); en la rama `<slug>-T<n>`
    de una tarea pedida cuentan todos los commits sin merge de la rama.
    """
    etiqueta = "commits de la tarea dentro de Puede tocar"
    if base is None:
        return {"comando": etiqueta, "pasa": False, "exit": 1, "nuevo": None, "salida": "no se pudo resolver la base del plan"}
    commits = commits_de_tareas(raiz, base, slug, pedidas)
    if commits is None:
        return {"comando": etiqueta, "pasa": False, "exit": 1, "nuevo": None,
                "salida": f"no se pudo leer git log desde {base[:7]}"}
    fuera: list[str] = []
    for numero, asunto, archivos in commits:
        if numero not in pedidas:
            continue
        patrones = rutas.get(numero, [])
        fuera += [f"{asunto} -> {a}" for a in archivos if not any(coincide_ruta(a, p) for p in patrones)]
    return {"comando": etiqueta, "pasa": not fuera, "exit": 0 if not fuera else 1, "nuevo": None,
            "salida": "\n".join(fuera) if fuera else "limpia"}


# ---------------------------------------------------------------------------
# Incremental y recibo
# ---------------------------------------------------------------------------

def mismo_head(a: str, b: str) -> bool:
    """Dos HEAD cortos son el mismo commit si uno es prefijo del otro."""
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def fechas_previas(numero: int, criterios: list[vp.Criterio], secciones: list[dict], head: str,
                   contrato: str) -> dict[str, str] | None:
    """Fecha del recibo previo de cada criterio de la tarea si se puede saltear, o None si se repite.

    Se mira la sección más reciente que corrió la tarea. Se salta solo si tiene el mismo HEAD que
    hoy, el mismo texto de contrato y todos los criterios de la tarea (y los versionados) en PASA.
    """
    if not head or not criterios:
        return None
    etiquetas = [etiqueta_de(c) for c in criterios]
    for seccion in reversed(secciones):
        propias = {}
        for linea in seccion["lineas"]:
            coincidencia = RE_ETIQUETA_TAREA.match(linea["comando"])
            if coincidencia and int(coincidencia.group(1)) == numero:
                propias[linea["comando"]] = linea
        if not propias:
            continue
        if seccion["contrato"] != contrato or not mismo_head(seccion["head"], head):
            return None
        versionados = [li for li in seccion["lineas"] if li["comando"].startswith("versionados limpios")]
        if not versionados or not all(li["pasa"] for li in versionados):
            return None
        if not all(e in propias and propias[e]["pasa"] for e in etiquetas):
            return None
        return {e: propias[e]["previo"] or seccion["fecha"] for e in etiquetas}
    return None


def resultado_previo(criterio: vp.Criterio, fecha: str) -> dict:
    """Criterio que no se corre porque un recibo previo ya lo dio por PASA."""
    return {"comando": etiqueta_de(criterio), "pasa": True, "exit": 0, "nuevo": None, "salida": "", "previo": fecha}


def emitir_recibo(ruta: Path | None, seccion: dict) -> None:
    """Imprime la sección por stdout y la agrega a `ruta` (si hay).

    `recibo.escribir_recibo` da el formato; lo informativo (`fuera` de cada criterio) se agrega en
    una línea `- Fuera de alcance (informativo): …` antes de la duración.
    """
    with tempfile.TemporaryDirectory() as carpeta:
        temporal = Path(carpeta) / "seccion.md"
        recibo.escribir_recibo(temporal, seccion)
        texto = temporal.read_bytes().decode("utf-8")
    for comando, prefijos in seccion.get("omitidos", []):
        texto = texto.replace("\n- duración:", f"\n- Omitido (no toca {', '.join(prefijos)}): `{comando}`\n- duración:", 1)
    fuera = [r for c in seccion.get("criterios", []) for r in c.get("fuera", [])]
    if fuera:
        texto = texto.replace("\n- duración:", f"\n- Fuera de alcance (informativo): {'; '.join(fuera)}\n- duración:", 1)
    if ruta is not None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8", newline="\n") as archivo:
            archivo.write(texto)
    print(texto, end="")


def armar_seccion(alcance: str, raiz: Path, contrato: str, aceptado: bool, criterios: list[dict], inicio: float) -> dict:
    """Sección del recibo con HEAD, duración y veredicto calculados."""
    pasa = bool(criterios) and aceptado and all(c["pasa"] for c in criterios)
    return {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "alcance": alcance,
        "head": recibo.head(raiz) or "",
        "contrato": contrato,
        "criterios": criterios,
        "duracion": round(time.monotonic() - inicio, 1),
        "veredicto": "PASA" if pasa else "FALLA",
    }


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

def abrir_plan(raiz: Path, valor: str) -> Path:
    """Valida y resuelve el plan (relativo a la raíz, o absoluto dentro de ella)."""
    candidato = Path(valor)
    if candidato.is_absolute():
        try:
            valor = candidato.resolve().relative_to(raiz.resolve()).as_posix()
        except ValueError as error:
            raise UsoInvalido(f"el plan {valor} no está dentro de la raíz {raiz}") from error
    ruta, motivo = vp.validar_plan(raiz, valor)
    if ruta is None:
        raise UsoInvalido(f"plan inválido {valor!r}: {motivo}")
    return ruta


def relativa(raiz: Path, ruta: Path) -> str | None:
    """`ruta` relativa a la raíz con `/`, o None si queda fuera de ella."""
    try:
        return ruta.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return None


def correr_plan(modo: str, raiz: Path, valor_plan: str, pedidas: list[int], ruta_recibo: Path | None,
                cierre_json: Path | None, timeout: float) -> int:
    """`tarea` y `todo`: ejecuta los criterios del plan congelado y escribe el recibo."""
    inicio = time.monotonic()
    plan = abrir_plan(raiz, valor_plan)
    slug = vp.slug_de(plan)
    bash = vp.buscar_bash()
    ruta_recibo = ruta_recibo or plan.parent / f"{slug}.recibo.md"
    texto, contrato, aceptado = cargar_contrato(raiz, plan, bash)
    if texto is None:
        alcance = f"tarea {','.join(f'T{n}' for n in pedidas)} de {plan.name}" if modo == "tarea" else f"todo {plan.name}"
        emitir_recibo(ruta_recibo, armar_seccion(alcance, raiz, contrato, False, [], inicio))
        return 1

    datos = vp.parsear_plan(texto)
    if modo == "tarea":
        desconocidas = [n for n in pedidas if n not in datos.criterios]
        if desconocidas:
            raise UsoInvalido(f"el plan no tiene la tarea T{desconocidas[0]}")
    else:
        pedidas = sorted(datos.criterios)
    rutas = leer_puede_tocar(texto)
    disco = vp.leer_texto(plan)
    base_registro, motivo_base, base = base_del_plan(raiz, disco, slug)

    seleccion = [c for n in pedidas for c in datos.criterios[n]]
    omitidos: list[tuple[str, tuple[str, ...]]] = []
    if modo == "todo":
        if datos.cierre_global:
            seleccion += datos.cierre_global
        else:
            condiciones = condiciones_de_cierre(raiz, cierre_json)
            cambiados = archivos_cambiados(raiz, base, versionados_modificados(raiz, True)) if condiciones else None
            for c in comandos_de_cierre(raiz, cierre_json):
                prefijos = condiciones.get(c.comando)
                if prefijos and cambiados is not None and not any(a.startswith(prefijos) for a in cambiados):
                    omitidos.append((c.comando, prefijos))
                else:
                    seleccion.append(c)
    head = recibo.head(raiz) or ""
    excluidas = {r for r in (relativa(raiz, plan), relativa(raiz, ruta_recibo)) if r}
    # Estado del árbol antes de los criterios (que pueden crear archivos): solo con el árbol limpio
    # se reutiliza el recibo previo.
    antes = versionados_modificados(raiz, True) if modo == "todo" else []
    limpio = antes is not None and all(destino(r, "todo", excluidas, []) != "falla" for _, r in antes)
    head_completo = recibo.head_completo(raiz)
    previas: dict[int, dict[str, str]] = {}
    if modo == "todo" and limpio:
        secciones = recibo.leer_recibo(ruta_recibo)
        for numero in pedidas:
            fechas = fechas_previas(numero, datos.criterios[numero], secciones, head, contrato)
            if fechas:
                previas[numero] = fechas
    resultados = []
    for criterio in seleccion:
        coincidencia = RE_ETIQUETA_TAREA.match(f"{criterio.origen} [")
        fecha = previas.get(int(coincidencia.group(1)), {}).get(etiqueta_de(criterio)) if coincidencia else None
        resultados.append(resultado_previo(criterio, fecha) if fecha else
                          ejecutar_criterio(criterio, raiz, bash, plan, base_registro, motivo_base, base, timeout))

    if modo == "tarea":
        propias = tuple(r for n in pedidas for r in rutas.get(n, []))
        resultados.append(versionados_limpios(raiz, "tarea", excluidas, propias))
        resultados.append(commits_fuera_de_alcance(raiz, rutas, pedidas, base, slug))
        alcance = f"tarea {','.join(f'T{n}' for n in pedidas)} de {plan.name}"
    else:
        resultados.append(versionados_limpios(raiz, "todo", excluidas, (), antes))
        alcance = f"todo {plan.name}"
    seccion = armar_seccion(alcance, raiz, contrato, aceptado, resultados, inicio)
    seccion["omitidos"] = omitidos
    emitir_recibo(ruta_recibo, seccion)
    registrar_si_pasa(raiz, seccion, head_completo, alcance if modo == "todo" else None)
    return 0 if seccion["veredicto"] == "PASA" else 1


def registrar_si_pasa(raiz: Path, seccion: dict, head_inicial: str | None, alcance: str | None) -> None:
    """Registra el HEAD completo con su `alcance` si el veredicto es PASA y el HEAD no se movió durante la corrida."""
    if alcance is not None and seccion["veredicto"] == "PASA" and head_inicial and recibo.head_completo(raiz) == head_inicial:
        recibo.registrar_head(raiz, head_inicial, alcance)


def correr_cierre(raiz: Path, cierre_json: Path | None, timeout: float) -> int:
    """`cierre`: cierre global del repo, sin plan; el recibo va solo a stdout."""
    inicio = time.monotonic()
    bash = vp.buscar_bash()
    criterios = comandos_de_cierre(raiz, cierre_json)
    antes = versionados_modificados(raiz, True)
    head_inicial = recibo.head_completo(raiz)
    resultados = [ejecutar_criterio(c, raiz, bash, None, None, None, None, timeout) for c in criterios]
    resultados.append(versionados_limpios(raiz, "cierre", frozenset(), (), antes))
    seccion = armar_seccion("cierre global", raiz, "intacto (sin plan)", True, resultados, inicio)
    emitir_recibo(None, seccion)
    registrar_si_pasa(raiz, seccion, head_inicial, "cierre")
    return 0 if seccion["veredicto"] == "PASA" else 1


def validar_recibo(raiz: Path, ruta: Path) -> Path:
    """`--recibo` solo acepta `docs/planes/*.recibo.md` dentro de la raíz o un archivo fuera del repo.

    El recibo se abre en modo append: sin esta regla se podría agregar texto a cualquier archivo
    del repo (por ejemplo `.claude/settings.json`). Otra ruta dentro del repo es uso inválido.
    """
    destino = ruta.resolve()
    proceso = recibo._git(raiz, "rev-parse", "--show-toplevel")
    repos = {raiz.resolve()}
    if proceso is not None and proceso.returncode == 0 and proceso.stdout.strip():
        repos.add(Path(proceso.stdout.strip()).resolve())
    if destino.is_dir():
        raise UsoInvalido(f"--recibo {ruta} es un directorio")
    if not any(destino == repo or repo in destino.parents for repo in repos):
        return destino  # fuera del repo (un temporal)
    if destino.parent == (raiz / "docs" / "planes").resolve() and destino.name.endswith(".recibo.md") \
            and destino.name != ".recibo.md":
        return destino
    raise UsoInvalido(f"--recibo {ruta}: dentro del repo solo se acepta docs/planes/*.recibo.md")


def interpretar(argv: list[str]) -> tuple[Path, Path | None, list[str]]:
    """Separa `--raiz` y `--recibo` de los argumentos posicionales; levanta `UsoInvalido` si sobran o faltan."""
    valores: dict[str, str] = {}
    posicionales: list[str] = []
    pendiente: str | None = None
    for argumento in argv:
        if pendiente is not None:
            valores[pendiente] = argumento
            pendiente = None
        elif argumento in ("--raiz", "--recibo"):
            pendiente = argumento
        elif argumento.startswith(("--raiz=", "--recibo=")):
            clave, _, valor = argumento.partition("=")
            valores[clave] = valor
        elif argumento.startswith("--"):
            raise UsoInvalido(f"opción desconocida {argumento}; {USO}")
        else:
            posicionales.append(argumento)
    if pendiente is not None:
        raise UsoInvalido(f"falta el valor de {pendiente}; {USO}")
    if "--raiz" in valores:
        raiz = Path(valores["--raiz"]).resolve()
    else:
        proceso = recibo._git(Path.cwd(), "rev-parse", "--show-toplevel")
        raiz = Path(proceso.stdout.strip() if proceso is not None and proceso.returncode == 0 and proceso.stdout.strip()
                    else Path.cwd()).resolve()
    if not raiz.is_dir():
        raise UsoInvalido(f"la raíz {raiz} no es un directorio")
    ruta_recibo = validar_recibo(raiz, Path(valores["--recibo"])) if "--recibo" in valores else None
    return raiz, ruta_recibo, posicionales


def despachar(posicionales: list[str], raiz: Path, ruta_recibo: Path | None, cierre_json: Path | None, timeout: float) -> int:
    """Corre el subcomando; levanta `UsoInvalido` si los argumentos no coinciden con ninguno."""
    if len(posicionales) == 3 and posicionales[0] == "tarea" and RE_CLAVE_TAREAS.fullmatch(posicionales[2]):
        pedidas = list(dict.fromkeys(int(t[1:]) for t in posicionales[2].split(",")))
        return correr_plan("tarea", raiz, posicionales[1], pedidas, ruta_recibo, cierre_json, timeout)
    if len(posicionales) == 2 and posicionales[0] == "todo":
        return correr_plan("todo", raiz, posicionales[1], [], ruta_recibo, cierre_json, timeout)
    if posicionales == ["cierre"]:
        if ruta_recibo is not None:
            raise UsoInvalido("cierre no escribe recibo en un archivo: va solo a stdout (sin --recibo)")
        return correr_cierre(raiz, cierre_json, timeout)
    raise UsoInvalido(USO)


def main(argv: list[str], cierre_json: Path | None = None, timeout: float = TIMEOUT_CRITERIO) -> int:
    """Punto de entrada testeable: devuelve el exit (0 pasa, 1 falla, 2 uso inválido).

    Mientras corre existe `.claude/.verificando` con el PID (lo mira el hook Stop); se borra siempre.
    """
    try:
        raiz, ruta_recibo, posicionales = interpretar(argv)
    except UsoInvalido as error:
        sys.stderr.write(f"verificar: {error}\n")
        return 2
    marca = raiz / ".claude" / ".verificando"
    carpeta_nueva = not marca.parent.exists()
    try:
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text(str(os.getpid()), encoding="utf-8")
    except OSError:
        pass  # sin marca la verificación sigue; solo el hook Stop pierde la señal
    try:
        return despachar(posicionales, raiz, ruta_recibo, cierre_json, timeout)
    except (UsoInvalido, FileNotFoundError) as error:
        sys.stderr.write(f"verificar: {error}\n")
        return 2
    finally:
        marca.unlink(missing_ok=True)
        if carpeta_nueva:
            try:
                marca.parent.rmdir()
            except OSError:
                pass  # la carpeta ya tiene otros archivos (p. ej. el índice de recibos)


if __name__ == "__main__":
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # flujo sin reconfigure: se usa tal cual
    sys.exit(main(sys.argv[1:]))
