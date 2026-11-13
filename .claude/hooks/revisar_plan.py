#!/usr/bin/env python3
"""Revisión estática de un plan antes de congelarlo (método v2).

Uso: py -3 .claude/hooks/revisar_plan.py <plan.md> [--raiz <directorio>]

Lee el plan del disco y dice qué está mal antes del commit `docs(plan): <slug>`.
Exit 0 si no hay errores (puede haber avisos), 1 si hay errores, 2 si el uso es inválido.

Errores:
- un criterio con un tipo desconocido;
- una `### T<n>` sin criterios;
- la misma ruta, o una carpeta que la contiene, en "Puede tocar" de dos subtareas;
- un `[test]` que ya existe en `HEAD` (formas canónicas: Django con `manage.py test <ruta.punteada>
  --keepdb` y pytest `py -3 -m pytest .claude/hooks/<archivo>::[<Clase>::]<función> -q`);
- un `[test]` que no tiene ninguna de las dos formas canónicas;
- un `[cmd]`, `[cmd-falla]` o `[test]` que invoca `manage.py` sin `./venv/Scripts/python.exe`;
- una `ruta` del encabezado distinta de `ligero` o `completo` (`directo` no lleva plan);
- en un plan `ligero`: más de 10 rutas, `seguridad: sí`, una carpeta o comodín, o `migrations/`;
- dos subtareas de la misma `Ola` con migraciones de la misma app, o que dependen una de otra
  (las subtareas de integración del principal no cuentan);
- un `[grep-1]`/`[grep-0]` sobre un archivo que no existe y que ningún "Puede tocar" cubre;
- una `Skill a leer antes` que no existe en `.agents/skills/` ni en `.claude/skills/`.

Avisos: un `[grep-1]` o `[existe]` que ya pasa hoy; un `[grep-0]` o `[no-existe]` que ya pasa.

Nunca ejecuta `[cmd]`, `[cmd-falla]` ni `[test]`. Un `[grep-1]`/`[grep-0]` solo se corre si empieza
con `grep` o `rg` y no tiene metacaracteres de shell, como lista de argumentos y sin shell; si no,
se salta con un aviso. Reutiliza `RE_TAREA`, `TIPOS` y `CORTE` de `verificar_plan.py`.
"""
from __future__ import annotations

import fnmatch
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verificar_plan  # noqa: E402

TIMEOUT_GREP = 30
MAX_RUTAS_LIGERO = 10
RUTAS_VALIDAS = ("ligero", "completo")
RE_LINEA_CRITERIO = re.compile(r"^\s*- `\[(?P<tipo>[^\]`]*)\]` `(?P<cmd>[^`]+)`")
RE_RUTA = re.compile(r"^- \*\*ruta\*\*:\s*(.*)$", re.MULTILINE)
RE_SEGURIDAD = re.compile(r"^- \*\*seguridad\*\*:\s*`?(sí|si|no)\b", re.MULTILINE | re.IGNORECASE)
RE_RUTA_APP = re.compile(r"^apps/(?P<app>[^/]+)(?:/(?P<resto>.*))?$")
# `manage.py` que no va precedido del Python del venv.
RE_MANAGE_SIN_VENV = re.compile(r"(?<!\./venv/Scripts/python\.exe )\bmanage\.py\b")
# Formas canónicas de `[test]`.
RE_TEST_DJANGO = re.compile(
    r"^PYTHONIOENCODING=utf-8 DJANGO_ENV=development \./venv/Scripts/python\.exe "
    r"manage\.py test (?P<ruta>[\w.]+) --keepdb(?: -v \d)?$"
)
RE_TEST_PYTEST = re.compile(r"^py -3 -m pytest (?P<archivo>\.claude/hooks/[\w.-]+\.py)::(?P<resto>\w+(?:::\w+)?) -q$")
# Opciones de grep/rg que consumen el argumento siguiente.
OPCIONES_CON_VALOR = {"-A", "-B", "-C", "-m", "-g", "-t", "-T", "-d", "--glob", "--type", "--max-count"}
OPCIONES_CON_PATRON = {"-e", "-f", "--regexp", "--file"}
RE_METACARACTERES_SHELL = re.compile(r"[;&|$`><(){}*?\[\]~!\r\n]")


def cortar_registro(texto: str) -> str:
    """La parte del plan que se congela: todo lo que está arriba del registro de verificación."""
    lineas = []
    for linea in texto.replace("\r", "").splitlines():
        if linea.startswith(verificar_plan.CORTE):
            break
        lineas.append(linea)
    return "\n".join(lineas)


def normalizar_ruta(ruta: str) -> str:
    """Ruta con `/`, sin `./` inicial ni `/` final."""
    ruta = ruta.strip().replace("\\", "/")
    while ruta.startswith("./"):
        ruta = ruta[2:]
    return ruta.rstrip("/")


def se_contienen(a: str, b: str) -> bool:
    """True si las rutas son iguales o una es carpeta que contiene a la otra."""
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def leer_tareas(texto: str) -> dict[int, dict]:
    """Por cada `### T<n>`: rutas, criterios, skill, ola, dependencias y si es de integración.

    `criterios` es una lista de (tipo, comando) con cualquier tipo, conocido o no.
    """
    tareas: dict[int, dict] = {}
    actual = None
    en_criterios = False
    en_codigo = False
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        coincidencia = verificar_plan.RE_TAREA.match(linea)
        if coincidencia:
            actual = int(coincidencia.group(1))
            tareas[actual] = {
                "rutas": [], "criterios": [], "skill": None, "ola": None, "depende": [],
                "integracion": "Integración" in linea and "(principal)" in linea,
            }
            en_criterios = False
            continue
        if linea.startswith("#"):
            actual, en_criterios = None, False
            continue
        if actual is None:
            continue
        datos = tareas[actual]
        if linea.startswith("- **Criterios**"):
            en_criterios = True
        elif linea.startswith("- **"):
            en_criterios = False
            if linea.startswith("- **Puede tocar**"):
                datos["rutas"] = re.findall(r"`([^`]+)`", linea)
            elif linea.startswith("- **Skill a leer antes**"):
                citadas = re.findall(r"`([^`]+)`", linea)
                datos["skill"] = citadas[0] if citadas else None
            elif linea.startswith("- **Ola**"):
                numero = re.search(r"\d+", linea)
                datos["ola"] = int(numero.group()) if numero else None
            elif linea.startswith("- **Depende de**"):
                sin_notas = re.sub(r"\([^)]*\)", "", linea)
                datos["depende"] = [int(d) for d in re.findall(r"T(\d+)", sin_notas)]
        elif en_criterios:
            coincidencia = RE_LINEA_CRITERIO.match(linea)
            if coincidencia:
                datos["criterios"].append((coincidencia.group("tipo"), coincidencia.group("cmd")))
    return tareas


def apps_con_migraciones(ruta: str) -> set[str]:
    """Apps cuyas migraciones toca una ruta de "Puede tocar" (`*` = cualquier app)."""
    ruta = normalizar_ruta(ruta)
    if ruta == "apps":
        return {"*"}
    coincidencia = RE_RUTA_APP.match(ruta)
    if coincidencia is None:
        return set()
    app, resto = coincidencia.group("app"), coincidencia.group("resto")
    if "*" in app:
        return {"*"}
    if resto is None or resto == "migrations" or resto.startswith("migrations/"):
        return {app}
    if "*" in resto and fnmatch.fnmatch("migrations/__sonda__.py", resto):
        return {app}
    return set()


def revisar_olas(tareas: dict) -> list[str]:
    """Errores de las olas: migraciones de la misma app y dependencias entre subtareas de una ola."""
    errores: list[str] = []
    olas: dict[int, list[int]] = {}
    for n, datos in tareas.items():
        if datos["ola"] is not None and not datos["integracion"]:
            olas.setdefault(datos["ola"], []).append(n)
    for ola, miembros in sorted(olas.items()):
        for i, n1 in enumerate(miembros):
            for n2 in miembros[i + 1:]:
                if n2 in tareas[n1]["depende"]:
                    errores.append(f"T{n1} depende de T{n2} pero están en la misma ola ({ola})")
                if n1 in tareas[n2]["depende"]:
                    errores.append(f"T{n2} depende de T{n1} pero están en la misma ola ({ola})")
                apps1 = set().union(*(apps_con_migraciones(r) for r in tareas[n1]["rutas"]))
                apps2 = set().union(*(apps_con_migraciones(r) for r in tareas[n2]["rutas"]))
                comunes = apps1 & apps2
                if "*" in apps1:
                    comunes |= apps2
                if "*" in apps2:
                    comunes |= apps1
                if comunes:
                    nombres = ", ".join(f"`{a}`" for a in sorted(comunes) if a != "*") or "cualquier app"
                    errores.append(
                        f"T{n1} y T{n2} (ola {ola}) tocan las migraciones de la app {nombres}: no pueden ir en la misma ola"
                    )
    return errores


def revisar_ruta_plan(texto: str, tareas: dict, raiz: Path) -> tuple[list[str], list[str]]:
    """Valida `ruta` del encabezado y, si es `ligero`, los límites del plan chico."""
    encabezado = texto.split("\n## ", 1)[0]
    coincidencia = RE_RUTA.search(encabezado)
    if coincidencia is None:
        return [], ["el plan no declara `ruta` (ligero o completo)"]
    piezas = coincidencia.group(1).strip().strip("`").split()
    valor = piezas[0].strip("`") if piezas else ""
    if valor not in RUTAS_VALIDAS:
        extra = " (la ruta `directo` no lleva plan)" if valor == "directo" else ""
        return [f"ruta: `{coincidencia.group(1).strip()}` no es `ligero` ni `completo`{extra}"], []
    if valor == "completo":
        return [], []
    errores = []
    rutas = [r for datos in tareas.values() for r in datos["rutas"]]
    if len(rutas) > MAX_RUTAS_LIGERO:
        errores.append(f"ruta ligero: {len(rutas)} rutas en 'Puede tocar' (máximo {MAX_RUTAS_LIGERO})")
    seguridad = RE_SEGURIDAD.search(encabezado)
    if seguridad and seguridad.group(1).lower() in ("sí", "si"):
        errores.append("ruta ligero: un plan con `seguridad: sí` debe ser `completo`")
    for ruta in rutas:
        normal = normalizar_ruta(ruta)
        if ruta.strip().endswith(("/", "\\")) or "*" in ruta or (raiz / normal).is_dir():
            errores.append(f"ruta ligero: `{ruta}` es una carpeta o comodín (listá archivos)")
        if "/migrations/" in f"/{normal}/":
            errores.append(f"ruta ligero: `{ruta}` toca migraciones")
    return errores, []


def revisar_skill(n: int, skill: str | None, raiz: Path) -> list[str]:
    """Error si la ruta citada en `Skill a leer antes` no existe; sugiere la otra carpeta de skills."""
    if not skill:
        return []
    ruta = normalizar_ruta(skill)
    if (raiz / ruta).exists():
        return []
    for origen, destino in ((".agents/skills/", ".claude/skills/"), (".claude/skills/", ".agents/skills/")):
        if ruta.startswith(origen) and (raiz / (destino + ruta[len(origen):])).exists():
            return [f"T{n}: la skill `{ruta}` no existe; la ruta correcta es `{destino + ruta[len(origen):]}`"]
    return [f"T{n}: la skill `{ruta}` no existe"]


def archivos_de_grep(comando: str) -> list[str]:
    """Archivos literales que nombra un `grep`/`rg`, relativos a la raíz.

    Devuelve [] si hay tuberías o encadenados, si no es grep/rg, o si no nombra archivos;
    saltea los argumentos con comodines.
    """
    if re.search(r"[;&|<>`$]", re.sub(r"\"[^\"]*\"|'[^']*'", "", comando)):
        return []
    try:
        piezas = shlex.split(comando)
    except ValueError:
        return []
    if not piezas or piezas[0] not in ("grep", "rg"):
        return []
    posicionales: list[str] = []
    hay_patron = False
    saltar = False
    for pieza in piezas[1:]:
        if saltar:
            saltar = False
        elif pieza in OPCIONES_CON_PATRON:
            hay_patron, saltar = True, True
        elif pieza in OPCIONES_CON_VALOR:
            saltar = True
        elif pieza.startswith("-") and pieza != "-":
            continue
        else:
            posicionales.append(pieza)
    archivos = posicionales if hay_patron else posicionales[1:]
    return [normalizar_ruta(a) for a in archivos if not re.search(r"[*?\[\]{}]", a)]


def cubierto_por_plan(archivo: str, cubiertas: list[str]) -> bool:
    """True si algún "Puede tocar" (archivo, carpeta o comodín) cubre el archivo."""
    return any(archivo == r or archivo.startswith(r + "/") or fnmatch.fnmatch(archivo, r) for r in cubiertas)


def contenido_en_head(raiz: Path, ruta: str) -> str | None:
    """Texto de `ruta` en `HEAD`, o None si no existe allí (o no hay git)."""
    try:
        proceso = subprocess.run(
            ["git", "-C", str(raiz), "show", f"HEAD:{ruta}"], capture_output=True, timeout=TIMEOUT_GREP
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proceso.stdout.decode("utf-8", errors="replace") if proceso.returncode == 0 else None


def hay_head(raiz: Path) -> bool:
    """True si `raiz` es un repo git con al menos un commit."""
    try:
        proceso = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "--verify", "-q", "HEAD"], capture_output=True, timeout=TIMEOUT_GREP
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proceso.returncode == 0


def test_es_preexistente(raiz: Path, comando: str) -> bool | None:
    """True si el test de un `[test]` canónico ya existe en `HEAD`; None si no se puede decidir."""
    if not hay_head(raiz):
        return None
    pytest = RE_TEST_PYTEST.match(comando)
    if pytest:
        archivo, nombre = pytest.group("archivo"), pytest.group("resto").split("::")[-1]
        contenido = contenido_en_head(raiz, archivo)
        return None if contenido is None else re.search(rf"def\s+{nombre}\s*\(", contenido) is not None
    django = RE_TEST_DJANGO.match(comando)
    if not django:
        return None
    partes = django.group("ruta").split(".")
    # El prefijo más largo de la ruta punteada que sea un `.py` versionado es el módulo del test.
    for corte in range(len(partes), 0, -1):
        contenido = contenido_en_head(raiz, "/".join(partes[:corte]) + ".py")
        if contenido is not None:
            if corte == len(partes):
                return None
            return re.search(rf"def\s+{partes[-1]}\s*\(", contenido) is not None
    return False


def argumentos_de_grep(comando: str) -> list[str] | None:
    """Argumentos de un `grep`/`rg` sin metacaracteres de shell, o None si no se puede correr sin shell."""
    if RE_METACARACTERES_SHELL.search(comando) is None:
        try:
            argumentos = shlex.split(comando)
        except ValueError:
            return None
        # `rg --pre` corre un programa por archivo: tampoco se ejecuta.
        if argumentos and argumentos[0] in ("grep", "rg") and not any(a.startswith("--pre") for a in argumentos):
            return argumentos
    return None


def grep_cumple(tipo: str, argumentos: list[str], raiz: Path) -> bool | None:
    """Corre el grep sin shell; True si cumple el tipo, None si no se pudo ejecutar."""
    try:
        proceso = subprocess.run(argumentos, shell=False, cwd=raiz, capture_output=True, timeout=TIMEOUT_GREP)
    except (OSError, subprocess.TimeoutExpired):
        return None
    # grep devuelve 1 sin coincidencias; 2 o más es un error.
    return proceso.returncode == 0 if tipo == "grep-1" else proceso.returncode == 1


def revisar_criterio(
    n: int, tipo: str, comando: str, raiz: Path, avisos: list[str], cubiertas: list[str]
) -> list[str]:
    """Errores de un criterio; agrega a `avisos` los que ya pasan hoy. No ejecuta cmd ni test."""
    if tipo not in verificar_plan.TIPOS:
        return [f"T{n}: tipo de criterio desconocido [{tipo}] en `{comando}`"]
    errores = []
    if tipo in ("cmd", "cmd-falla", "test") and RE_MANAGE_SIN_VENV.search(comando):
        errores.append(f"T{n}: `manage.py` sin ./venv/Scripts/python.exe: `{comando}`")
    if tipo == "test":
        if not (RE_TEST_DJANGO.match(comando) or RE_TEST_PYTEST.match(comando)):
            errores.append(f"T{n}: el [test] no tiene una forma canónica (Django o pytest): `{comando}`")
        elif test_es_preexistente(raiz, comando):
            errores.append(f"T{n}: el [test] ya existe en HEAD: `{comando}`")
    elif tipo in ("grep-1", "grep-0"):
        for archivo in archivos_de_grep(comando):
            if not (raiz / archivo).exists() and not cubierto_por_plan(archivo, cubiertas):
                errores.append(f"T{n}: [{tipo}] sobre `{archivo}`, que no existe ni lo cubre 'Puede tocar'")
        if not errores:
            argumentos = argumentos_de_grep(comando)
            if argumentos is None:
                avisos.append(f"[{tipo}] no se ejecuta (no es grep/rg sin metacaracteres): {comando}")
            elif grep_cumple(tipo, argumentos, raiz):
                nota = " (puede ser una guarda)" if tipo == "grep-0" else ""
                avisos.append(f"T{n}: [{tipo}] ya pasa hoy{nota}: `{comando}`")
    elif tipo in ("existe", "no-existe"):
        existe = (raiz / comando.strip()).exists()
        if existe == (tipo == "existe"):
            nota = " (puede ser una guarda)" if tipo == "no-existe" else ""
            avisos.append(f"T{n}: [{tipo}] ya pasa hoy{nota}: `{comando}`")
    return errores


def revisar(texto: str, raiz: Path) -> tuple[list[str], list[str]]:
    """Revisa el texto de un plan; devuelve (errores, avisos)."""
    texto = cortar_registro(texto)
    tareas = leer_tareas(texto)
    errores: list[str] = []
    avisos: list[str] = []

    rutas = [(n, normalizar_ruta(r)) for n, datos in tareas.items() for r in datos["rutas"]]
    for i, (n1, r1) in enumerate(rutas):
        for n2, r2 in rutas[i + 1:]:
            if n1 != n2 and r1 and r2 and se_contienen(r1, r2):
                errores.append(f"T{n1} y T{n2} se pisan en 'Puede tocar': {r1} / {r2}")

    errores += revisar_olas(tareas)
    errores_ruta, avisos_ruta = revisar_ruta_plan(texto, tareas, raiz)
    errores += errores_ruta
    avisos += avisos_ruta

    cubiertas = [r for _, r in rutas]
    for n, datos in tareas.items():
        errores += revisar_skill(n, datos["skill"], raiz)
        if not datos["criterios"]:
            errores.append(f"T{n}: no tiene criterios")
        for tipo, comando in datos["criterios"]:
            errores += revisar_criterio(n, tipo, comando, raiz, avisos, cubiertas)
    return errores, avisos


def main(argv: list[str]) -> int:
    """Punto de entrada: imprime errores y avisos; exit 1 si hay errores, 2 si el uso es inválido."""
    argumentos = list(argv)
    raiz = Path.cwd()
    if "--raiz" in argumentos:
        indice = argumentos.index("--raiz")
        if indice + 1 >= len(argumentos):
            print("ERROR: --raiz necesita un directorio")
            return 2
        raiz = Path(argumentos[indice + 1])
        del argumentos[indice:indice + 2]
    if len(argumentos) != 1:
        print("uso: revisar_plan.py <plan.md> [--raiz <directorio>]")
        return 2
    try:
        texto = Path(argumentos[0]).read_text(encoding="utf-8")
    except OSError as error:
        print(f"ERROR: no se pudo leer el plan: {error}")
        return 2
    errores, avisos = revisar(texto, raiz)
    for mensaje in errores:
        print(f"ERROR: {mensaje}")
    for mensaje in avisos:
        print(f"AVISO: {mensaje}")
    print(f"{len(errores)} error(es), {len(avisos)} aviso(s)")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
