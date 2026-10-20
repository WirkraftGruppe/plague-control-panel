"""Hook Stop de Claude Code: ejecuta los criterios de las subtareas `hecha` del plan activo.

Flujo (ver T4 de docs/planes/2026-09-23-esquema-agentes.md, H1 de
docs/planes/2026-09-23-endurecer-hooks.md y T2 de docs/planes/2026-09-23-endurecer-hooks-2.md):

1. Lee el JSON del hook por stdin. Si `stop_hook_active` es true, sale con 0 (anti-bucle).
   Un stdin vacío o malformado también sale con 0: el hook nunca rompe la sesión.
2. La raíz sale de `CLAUDE_PROJECT_DIR` o, si no está definida, del directorio actual.
3. Deriva el plan de la rama de git: `plan/<slug>` o `<slug>-T<n>` (p. ej. `demo-T5a`) apuntan
   al único `docs/planes/AAAA-MM-DD-<slug>.md`. Sin rama, con slug inválido, sin plan o con
   varios, se cae en `Plan activo:` de `<raíz>/docs/bitacora.md`. `(ninguno)` o archivo
   inexistente → 0.
   Solo se acepta una ruta relativa, sin `..`, a un `.md` que no sea symlink y cuyo padre
   resuelto sea exactamente `<raíz>/docs/planes`. Cualquier otro valor → aviso por stderr y 0.
4. Corre `congelado.sh <plan> <slug>` (el de la carpeta de este hook). Si no sale con 0, o si
   su stdout no es un hash de commit válido, no se ejecuta ningún criterio: se informa el
   motivo por stderr y se sale según el modo.
5. Lee el plan congelado con `git -C <raíz> show <hash>:./docs/planes/<archivo>` y parsea de
   ahí las subtareas `### T<n>`, sus bloques `Criterios` y los de `## Criterios de cierre
   global` (solo arriba del corte). Del disco solo se lee la tabla `### Estado de subtareas`,
   debajo del corte. Así lo que se ejecuta es exactamente el texto del commit congelado, aunque
   el disco cambie entre la comprobación de `congelado.sh` y la lectura (TOCTOU).
6. Si el plan congelado tiene bloques `Criterios` o cierre global pero ninguna subtarea
   `### T<n>`, no pasa en silencio: avisa por stderr y sale según el modo.
7. Caché en `<raíz>/.claude/.ultimo-verificado`: firma por contenido y resultado de la última
   corrida. La firma cubre, por repo (raíz, backend, mobile), el HEAD, un hash de
   `git diff HEAD --binary` y un hash del contenido de los archivos sin seguimiento no
   ignorados, más el hash del plan en disco. Firma igual y corrida limpia → 0; firma igual y
   con fallas → reemite el informe guardado sin volver a ejecutar criterios.
8. Ejecuta los criterios de las subtareas `hecha` con `bash -c` desde la raíz, cada uno en un
   grupo de procesos propio, con la salida a un archivo temporal y con timeout por criterio
   (`VERIFICAR_PLAN_TIMEOUT`, 300 s por defecto; 700 s para la suite completa o por app,
   `VERIFICAR_PLAN_TIMEOUT_SUITE`, ver `es_suite`). Al vencer se mata el árbol entero
   (`taskkill /T /F /PID` en Windows, `os.killpg` en POSIX). Todo el hook (congelado.sh, git
   y criterios) tiene un presupuesto de 780 s: cada criterio recibe
   `min(timeout, presupuesto_restante)` y, agotado el presupuesto, los que faltan se reportan
   como no ejecutados. Así el peor caso queda por debajo de los 900 s del hook. Los criterios
   con el mismo tipo y comando se ejecutan una sola vez por corrida y su resultado se reutiliza
   en el informe de cada subtarea.
9. Si todas las subtareas están `hecha`, ejecuta además los criterios de cierre global.
10. Sin fallas → 0. Con fallas → stderr con el detalle y exit según `.claude/hooks/modo`:
    `aviso` → 1 (no bloquea), `bloqueo` → 2 (bloquea y se lo muestra al modelo).
11. En modo bloqueo lleva un contador por `session_id` en el directorio temporal: al cuarto
    intento sale con 1 y "revisar a mano".
12. Antes de ejecutar, reemplaza el marcador `<commit_base>` (con o sin comillas simples) de los
    comandos por el hash completo de la línea `commit_base:` del Registro (ver
    `commit_base_del_registro`). Si no resuelve, los criterios con marcador son FALLA sin
    ejecutarse. La CLI `verificar_plan.py --commit-base [plan]` imprime ese hash (exit 0) o el
    motivo por stderr (exit 2); no lee stdin.

Seguridad: los criterios corren con `bash -c`, es decir, con toda la potencia de un shell:
pueden hacer red, escribir archivos o salir del árbol del proyecto. El control no está en
restringir los comandos sino en su origen: solo se ejecuta texto congelado (leído con
`git show` del commit `docs(plan): <slug>` que identifica `congelado.sh`) de un plan de
`docs/planes/` de la raíz.
Nada que venga del JSON de stdin llega a un comando, y `git`, `bash` y `taskkill` se invocan
por ruta absoluta, sin buscarlos en el directorio actual.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath

TIMEOUT_CRITERIO = 300
TIMEOUT_SUITE = 700
PRESUPUESTO_TOTAL = 780
TIMEOUT_CONGELADO = 60
LINEAS_DE_SALIDA = 20
MAX_INTENTOS_BLOQUEO = 3
TIPOS = ("cmd", "cmd-falla", "existe", "no-existe", "grep-1", "grep-0", "test")
CONGELADO_SH = Path(__file__).resolve().parent / "congelado.sh"
NOMBRE_CACHE = ".ultimo-verificado"
TAMANO_BLOQUE = 1 << 16

RE_ETIQUETA_APP = re.compile(r"apps\.\w+")
RE_HASH_COMMIT = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
RE_PLAN_ACTIVO = re.compile(r"^Plan activo:\s*(.*?)\s*$")
RE_FECHA_SLUG = re.compile(r"^\d{4}-\d{2}-\d{2}-")
RE_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
RE_RAMA_PLAN = re.compile(r"^plan/(?P<slug>.+)$")
RE_RAMA_SUBTAREA = re.compile(r"^(?P<slug>.+)-T[0-9]+[a-z]?$")
RE_COMMIT_BASE = re.compile(r"^commit_base:\s*(\S+)\s*$")
RE_HASH_ABREVIADO = re.compile(r"[0-9a-f]{4,64}")
RE_MARCADOR_BASE = re.compile(r"'<commit_base>'|<commit_base>")
RE_TAREA = re.compile(r"^### T(\d+)\b")
RE_ESTADO = re.compile(r"^\| T(\d+) \| (pendiente|en curso|hecha) \|")
RE_CRITERIO = re.compile(
    r"^(?P<sangria>\s*)- `\[(?P<tipo>" + "|".join(re.escape(t) for t in TIPOS) + r")\]` `(?P<cmd>[^`]+)`"
)
CORTE = "## Registro de verificación"
CIERRE_GLOBAL = "## Criterios de cierre global"


@dataclass(frozen=True)
class Criterio:
    """Un criterio comprobable por máquina, con el origen (`T<n>` o `cierre global`)."""

    origen: str
    tipo: str
    comando: str


@dataclass(frozen=True)
class Resultado:
    """Resultado de ejecutar un criterio."""

    criterio: Criterio
    pasa: bool
    codigo: int | None
    salida: str


@dataclass(frozen=True)
class Plan:
    """Lo que el hook necesita del plan: estados, criterios por tarea y de cierre global."""

    estados: dict[int, str]
    criterios: dict[int, list[Criterio]]
    cierre_global: list[Criterio]
    # Bloques `- **Criterios**` o `## Criterios de cierre global` arriba del corte, estén o no
    # dentro de una subtarea `### T<n>` (sirve para detectar planes fuera de formato).
    bloques_de_criterios: int = 0

    def tareas(self) -> list[int]:
        """Todas las subtareas conocidas (por encabezado o por fila de la tabla)."""
        return sorted(set(self.criterios) | set(self.estados))

    def estado(self, numero: int) -> str:
        """Una subtarea sin fila en la tabla se considera pendiente."""
        return self.estados.get(numero, "pendiente")


def leer_texto(ruta: Path) -> str:
    """Lee un archivo como UTF-8 quitando los `\\r` (CRLF → LF)."""
    return ruta.read_text(encoding="utf-8", errors="replace").replace("\r", "")


def leer_entrada(texto: str) -> dict | None:
    """Parsea el JSON del hook. Devuelve None si está vacío, malformado o no es un objeto."""
    try:
        datos = json.loads(texto)
    except (ValueError, TypeError):
        return None
    return datos if isinstance(datos, dict) else None


def resolver_raiz(entorno: dict[str, str]) -> Path:
    """Raíz del proyecto: `CLAUDE_PROJECT_DIR` (acepta `C:\\...`) o el directorio actual."""
    valor = entorno.get("CLAUDE_PROJECT_DIR", "").strip()
    return Path(valor).resolve() if valor else Path.cwd().resolve()


# ---------------------------------------------------------------------------
# Plan activo: contención
# ---------------------------------------------------------------------------

def es_ruta_absoluta(valor: str) -> bool:
    """True si el valor es absoluto o con unidad en POSIX o Windows (`/x`, `\\x`, `C:x`, UNC)."""
    ventanas = PureWindowsPath(valor)
    return valor.startswith(("/", "\\")) or bool(ventanas.drive) or ventanas.is_absolute()


def validar_plan(raiz: Path, valor: str) -> tuple[Path | None, str | None]:
    """Contención del plan activo. Devuelve (ruta, None) si es aceptable o (None, motivo) si no.

    Acepta solo una ruta relativa, sin `..`, a un archivo `.md` que no sea symlink y cuyo
    padre resuelto sea exactamente `<raíz>/docs/planes`.
    """
    if es_ruta_absoluta(valor):
        return None, "ruta absoluta"
    if ".." in PureWindowsPath(valor).parts:
        return None, "contiene '..'"
    candidato = raiz / valor
    if candidato.suffix != ".md":
        return None, "no es un archivo .md"
    if candidato.is_symlink():
        return None, "es un symlink"
    if not candidato.is_file():
        return None, "no existe"
    resuelto = candidato.resolve()
    if resuelto.parent != (raiz / "docs" / "planes").resolve():
        return None, "no está en docs/planes/ de la raíz"
    return resuelto, None


def rama_actual(raiz: Path) -> str:
    """Rama actual (`git branch --show-current`), o "" si no hay git, repo o es HEAD separado."""
    salida = salida_git(raiz, "branch", "--show-current", timeout=10)
    return (salida or "").strip()


def plan_de_rama(raiz: Path) -> Path | None:
    """Plan derivado de la rama `plan/<slug>` o `<slug>-T<n>`, o None si no corresponde.

    El plan es el único `docs/planes/AAAA-MM-DD-<slug>.md` y pasa por `validar_plan`. Un slug
    inválido o varias coincidencias avisan por stderr; en todos los casos None significa
    "usar `Plan activo:` de la bitácora".
    """
    rama = rama_actual(raiz)
    coincidencia = RE_RAMA_PLAN.match(rama) or RE_RAMA_SUBTAREA.match(rama)
    if not coincidencia:
        return None
    slug = coincidencia.group("slug")
    if not RE_SLUG.fullmatch(slug):
        sys.stderr.write(f"verificar_plan: la rama {rama!r} tiene un slug inválido; se usa la bitácora.\n")
        return None
    carpeta = raiz / "docs" / "planes"
    if not carpeta.is_dir():
        return None
    candidatos = [
        archivo.name
        for archivo in carpeta.glob("*.md")
        if RE_FECHA_SLUG.match(archivo.name) and RE_FECHA_SLUG.sub("", archivo.stem) == slug
    ]
    if len(candidatos) > 1:
        sys.stderr.write(f"verificar_plan: la rama {rama!r} coincide con varios planes; se usa la bitácora.\n")
        return None
    if not candidatos:
        return None
    ruta, _ = validar_plan(raiz, f"docs/planes/{candidatos[0]}")
    return ruta


def plan_activo(raiz: Path) -> Path | None:
    """Ruta del plan activo según la bitácora, o None si no hay plan o no es aceptable.

    Un valor que no pasa la contención (ver `validar_plan`) se trata como "sin plan" y se
    avisa por stderr; un plan que simplemente no existe sigue siendo un 0 mudo.
    """
    bitacora = raiz / "docs" / "bitacora.md"
    if not bitacora.is_file():
        return None
    for linea in leer_texto(bitacora).splitlines():
        coincidencia = RE_PLAN_ACTIVO.match(linea)
        if coincidencia:
            valor = coincidencia.group(1).strip("`").strip()
            if not valor or valor.startswith("("):
                return None
            ruta, motivo = validar_plan(raiz, valor)
            if ruta is None and motivo != "no existe":
                sys.stderr.write(
                    f"verificar_plan: se ignora el plan activo {valor!r} ({motivo}); "
                    "solo se aceptan planes de docs/planes/ de la raíz.\n"
                )
            return ruta
    return None


def slug_de(plan: Path) -> str:
    """Slug del plan: el nombre sin la fecha `AAAA-MM-DD-` inicial ni la extensión `.md`."""
    return RE_FECHA_SLUG.sub("", plan.stem)


# ---------------------------------------------------------------------------
# Parseo
# ---------------------------------------------------------------------------

def parsear_plan(texto: str, estados_solo_bajo_corte: bool = False) -> Plan:
    """Extrae estados y criterios. Los criterios solo se toman de la parte congelada.

    Con `estados_solo_bajo_corte` la tabla `### Estado de subtareas` solo se acepta debajo
    de `## Registro de verificación` (así se lee la tabla del plan en disco).
    """
    lineas = texto.replace("\r", "").splitlines()
    estados: dict[int, str] = {}
    criterios: dict[int, list[Criterio]] = {}
    cierre: list[Criterio] = []
    bloques = 0

    tarea_actual: int | None = None
    en_criterios = False
    en_cierre = False
    en_tabla_estado = False
    antes_del_corte = True
    en_bloque_codigo = False

    for linea in lineas:
        # Dentro de un bloque ``` los "#" son comentarios, no encabezados.
        if linea.lstrip().startswith("```"):
            en_bloque_codigo = not en_bloque_codigo
            continue
        if en_bloque_codigo:
            continue
        if linea.startswith(CORTE):
            antes_del_corte = False
            tarea_actual, en_criterios, en_cierre = None, False, False
            continue
        if linea.startswith("#"):
            en_tabla_estado = linea.startswith("### Estado de subtareas") and not (
                estados_solo_bajo_corte and antes_del_corte
            )
            coincidencia = RE_TAREA.match(linea) if antes_del_corte else None
            tarea_actual = int(coincidencia.group(1)) if coincidencia else None
            if tarea_actual is not None:
                criterios.setdefault(tarea_actual, [])
            en_criterios = False
            en_cierre = antes_del_corte and linea.startswith(CIERRE_GLOBAL)
            if en_cierre:
                bloques += 1
            continue
        if en_tabla_estado:
            coincidencia = RE_ESTADO.match(linea)
            if coincidencia:
                estados[int(coincidencia.group(1))] = coincidencia.group(2)
            continue
        if not antes_del_corte:
            continue
        if linea.startswith("- **Criterios**"):
            bloques += 1
        if tarea_actual is not None:
            if linea.startswith("- **Criterios**"):
                en_criterios = True
                continue
            if linea.startswith("- **"):
                en_criterios = False
                continue
            if en_criterios:
                coincidencia = RE_CRITERIO.match(linea)
                if coincidencia:
                    criterios[tarea_actual].append(
                        Criterio(f"T{tarea_actual}", coincidencia.group("tipo"), coincidencia.group("cmd"))
                    )
        elif en_cierre:
            coincidencia = RE_CRITERIO.match(linea)
            if coincidencia and coincidencia.group("sangria") == "":
                cierre.append(Criterio("cierre global", coincidencia.group("tipo"), coincidencia.group("cmd")))

    return Plan(estados, criterios, cierre, bloques)


def combinar_planes(texto_congelado: str, texto_disco: str) -> Plan:
    """Plan a ejecutar: subtareas y criterios del commit congelado, estados del disco.

    Del texto congelado se toman solo las subtareas y los criterios (arriba del corte); del
    disco, solo la tabla `### Estado de subtareas` debajo del corte, que es lo único que el
    principal actualiza durante la ejecución.
    """
    congelado = parsear_plan(texto_congelado)
    disco = parsear_plan(texto_disco, estados_solo_bajo_corte=True)
    return Plan(disco.estados, congelado.criterios, congelado.cierre_global, congelado.bloques_de_criterios)


def sin_formato_t(plan: Plan) -> bool:
    """True si el plan tiene bloques de criterios pero ninguna subtarea `### T<n>`."""
    return plan.bloques_de_criterios > 0 and not plan.criterios


# ---------------------------------------------------------------------------
# commit_base del Registro
# ---------------------------------------------------------------------------

def commit_base_del_registro(texto_disco: str, raiz: Path, slug: str) -> tuple[str | None, str | None]:
    """Resuelve la primera línea `commit_base: <hash>` de debajo del corte del plan en disco.

    Devuelve (hash completo, None) o (None, motivo). El hash se resuelve con
    `git rev-parse --verify <hash>^{commit}` y el asunto del commit tiene que ser
    `docs(plan): <slug>` o empezar con `docs(plan): <slug> — `.
    """
    valor = None
    bajo_corte = False
    for linea in texto_disco.replace("\r", "").splitlines():
        if linea.startswith(CORTE):
            bajo_corte = True
        elif bajo_corte and (coincidencia := RE_COMMIT_BASE.match(linea)):
            valor = coincidencia.group(1)
            break
    if valor is None:
        return None, f"no hay una línea 'commit_base: <hash>' debajo de '{CORTE}'"
    if not RE_HASH_ABREVIADO.fullmatch(valor):
        return None, f"'{valor}' no es un hash de commit"
    completo = (salida_git(raiz, "rev-parse", "--verify", "--quiet", f"{valor}^{{commit}}", timeout=30) or "").strip()
    if hash_valido(completo) is None:
        return None, f"'{valor}' no es un commit del repositorio"
    asunto = (salida_git(raiz, "log", "-1", "--format=%s", completo, timeout=30) or "").strip()
    esperado = f"docs(plan): {slug}"
    if asunto != esperado and not asunto.startswith(esperado + " — "):
        return None, f"el asunto de {completo[:10]} es {asunto!r}, no '{esperado}'"
    return completo, None


def reemplazar_commit_base(criterios: list[Criterio], commit_base: str | None, motivo: str | None,
                           plan: Path) -> tuple[list[Criterio], list[Resultado]]:
    """Reemplaza `<commit_base>` en los comandos. Devuelve (criterios a ejecutar, FALLAS previas).

    Sin hash resuelto, los criterios con el marcador no se ejecutan: quedan como FALLA con el
    motivo; los demás pasan sin cambios.
    """
    a_ejecutar: list[Criterio] = []
    fallas: list[Resultado] = []
    for criterio in criterios:
        if not RE_MARCADOR_BASE.search(criterio.comando):
            a_ejecutar.append(criterio)
        elif commit_base is None:
            fallas.append(Resultado(criterio, False, None, f"commit_base sin resolver en {plan.name}: {motivo}"))
        else:
            comando = RE_MARCADOR_BASE.sub(commit_base, criterio.comando)
            a_ejecutar.append(Criterio(criterio.origen, criterio.tipo, comando))
    return a_ejecutar, fallas


# ---------------------------------------------------------------------------
# Ejecutables por ruta absoluta
# ---------------------------------------------------------------------------

def buscar_ejecutable(nombre: str) -> str | None:
    """Ruta absoluta de un ejecutable, buscada con `shutil.which` solo en entradas absolutas
    del PATH. En Windows `shutil.which` antepone el directorio actual a la búsqueda: por eso
    se consulta directorio por directorio y se descarta lo que no esté en ese directorio.
    """
    for directorio in os.environ.get("PATH", "").split(os.pathsep):
        directorio = directorio.strip().strip('"')
        if not directorio or not os.path.isabs(directorio):
            continue
        encontrado = shutil.which(nombre, path=directorio)
        if not encontrado:
            continue
        absoluto = os.path.abspath(encontrado)
        if os.path.normcase(os.path.dirname(absoluto)) == os.path.normcase(os.path.abspath(directorio)):
            return absoluto
    return None


def buscar_taskkill() -> str | None:
    """Ruta absoluta a taskkill.exe: la de System32 o, si no está, la del PATH absoluto."""
    sistema = os.environ.get("SystemRoot") or os.environ.get("windir") or r"C:\Windows"
    candidato = Path(sistema) / "System32" / "taskkill.exe"
    return str(candidato) if candidato.is_file() else buscar_ejecutable("taskkill")


def buscar_bash() -> str:
    """Ruta a bash. En Windows prefiere Git Bash y evita el bash de WSL de System32."""
    if os.name == "nt":
        git = buscar_ejecutable("git")
        if git:
            base_git = Path(git).resolve().parent.parent
            for candidato in (base_git / "bin" / "bash.exe", base_git / "usr" / "bin" / "bash.exe"):
                if candidato.is_file():
                    return str(candidato)
        encontrado = buscar_ejecutable("bash")
        if encontrado and "system32" not in encontrado.lower():
            return encontrado
        raise FileNotFoundError("no se encontró Git Bash (bash.exe) en PATH")
    encontrado = buscar_ejecutable("bash")
    if not encontrado:
        raise FileNotFoundError("no se encontró bash en PATH")
    return encontrado


# ---------------------------------------------------------------------------
# Ejecución de criterios
# ---------------------------------------------------------------------------

class Presupuesto:
    """Tiempo total del hook (congelado.sh, git y criterios), medido con reloj monotónico."""

    def __init__(self, total: float) -> None:
        self.total = total
        self._fin = time.monotonic() + total

    def restante(self) -> float:
        """Segundos que quedan (0 si se agotó)."""
        return max(0.0, self._fin - time.monotonic())

    def recortar(self, timeout: float) -> float:
        """`min(timeout, restante)`: ningún paso puede pasarse del presupuesto total."""
        return min(timeout, self.restante())


def leer_timeout(
    entorno: dict[str, str], variable: str = "VERIFICAR_PLAN_TIMEOUT", defecto: float = TIMEOUT_CRITERIO
) -> float:
    """Timeout en segundos de `variable` (> 0), o `defecto` si falta o no es válido."""
    try:
        valor = float(entorno.get(variable, ""))
    except ValueError:
        return float(defecto)
    return valor if valor > 0 else float(defecto)


def leer_timeout_suite(entorno: dict[str, str]) -> float:
    """Timeout de la suite: `VERIFICAR_PLAN_TIMEOUT_SUITE` (segundos, > 0) o 700 por defecto."""
    return leer_timeout(entorno, "VERIFICAR_PLAN_TIMEOUT_SUITE", TIMEOUT_SUITE)


def es_suite(comando: str) -> bool:
    """True si es `manage.py test` sin etiquetas o solo con etiquetas de app (`apps.<app>`),
    con o sin `--keepdb`. Un módulo, una clase o un test nombrado no es la suite.
    """
    try:
        tokens = shlex.split(comando)
    except ValueError:
        return False
    if "manage.py" not in tokens:
        return False
    indice = tokens.index("manage.py")
    previos = tokens[:indice]
    if not all("=" in t or Path(t).name.lower() in ("python", "python.exe", "python3", "py") for t in previos):
        return False
    resto = tokens[indice + 1 :]
    if not resto or resto[0] != "test":
        return False
    return all(t == "--keepdb" or RE_ETIQUETA_APP.fullmatch(t) for t in resto[1:])


def matar_arbol(proceso: subprocess.Popen) -> None:
    """Mata el proceso del criterio y todos sus descendientes."""
    if os.name == "nt":
        taskkill = buscar_taskkill()
        if taskkill:
            try:
                subprocess.run(
                    [taskkill, "/T", "/F", "/PID", str(proceso.pid)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass  # se intenta igual el kill directo de abajo
    else:
        try:
            os.killpg(proceso.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass  # el grupo ya había terminado
    try:
        proceso.kill()
    except OSError:
        pass  # ya estaba muerto
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass  # no se puede hacer más: el timeout se reporta igual


def correr(bash: str, comando: str, raiz: Path, timeout: float = TIMEOUT_CRITERIO) -> tuple[int | None, str]:
    """Ejecuta `bash -c <comando>` desde la raíz. Devuelve (código, salida combinada).

    La salida va a un archivo temporal y no a un pipe: en Windows un nieto que hereda el pipe
    impide que la espera termine. El criterio corre en un grupo de procesos propio para poder
    matar el árbol completo al vencer el timeout. Código None = timeout o error al lanzar.
    """
    opciones: dict = {}
    if os.name == "nt":
        opciones["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        opciones["start_new_session"] = True
    with tempfile.TemporaryFile() as salida:
        try:
            proceso = subprocess.Popen(
                [bash, "-c", comando],
                cwd=str(raiz),
                stdin=subprocess.DEVNULL,
                stdout=salida,
                stderr=subprocess.STDOUT,
                **opciones,
            )
        except OSError as error:
            return None, f"no se pudo ejecutar bash: {error}"
        codigo: int | None
        try:
            codigo = proceso.wait(timeout=timeout)
            sufijo = ""
        except subprocess.TimeoutExpired:
            matar_arbol(proceso)
            codigo = None
            sufijo = f"\n(timeout de {round(timeout, 1):g} s: se mató el árbol de procesos)"
        salida.seek(0)
        texto = salida.read().decode("utf-8", errors="replace")
    return codigo, texto + sufijo


def evaluar(criterio: Criterio, raiz: Path, bash: str, timeout: float = TIMEOUT_CRITERIO) -> Resultado:
    """Ejecuta un criterio según su tipo y decide si pasa."""
    if criterio.tipo in ("existe", "no-existe"):
        existe = (raiz / criterio.comando.strip()).exists()
        pasa = existe if criterio.tipo == "existe" else not existe
        return Resultado(criterio, pasa, 0 if pasa else 1, "existe" if existe else "no existe")

    codigo, salida = correr(bash, criterio.comando, raiz, timeout)
    if codigo is None:
        pasa = False
    elif criterio.tipo in ("cmd", "test", "grep-1"):
        pasa = codigo == 0
    elif criterio.tipo == "cmd-falla":
        pasa = codigo != 0
    elif criterio.tipo == "grep-0":
        # grep devuelve 1 cuando no hay coincidencias; 2 o más es un error y cuenta como FALLA.
        pasa = codigo == 1
    else:
        raise ValueError(f"tipo de criterio desconocido: {criterio.tipo}")
    return Resultado(criterio, pasa, codigo, salida)


def criterios_a_ejecutar(plan: Plan) -> list[Criterio]:
    """Criterios de las tareas `hecha` y, si todas lo están, los de cierre global."""
    tareas = plan.tareas()
    hechas = [n for n in tareas if plan.estado(n) == "hecha"]
    seleccion = [c for n in hechas for c in plan.criterios.get(n, [])]
    if tareas and len(hechas) == len(tareas):
        seleccion.extend(plan.cierre_global)
    return seleccion


def ejecutar_seleccion(
    seleccion: list[Criterio],
    raiz: Path,
    bash: str,
    timeout: float,
    presupuesto: Presupuesto | None = None,
    timeout_suite: float = TIMEOUT_SUITE,
) -> list[Resultado]:
    """Ejecuta los criterios en orden. Cada uno recibe `min(timeout, presupuesto_restante)`
    (`timeout_suite` si es la suite, ver `es_suite`); agotado el presupuesto, los que faltan se
    reportan como no ejecutados. Un criterio con el mismo tipo y comando que uno ya ejecutado
    reutiliza su resultado.
    """
    if presupuesto is None:
        presupuesto = Presupuesto(PRESUPUESTO_TOTAL)
    resultados: list[Resultado] = []
    ejecutados: dict[tuple[str, str], Resultado] = {}
    for criterio in seleccion:
        clave = (criterio.tipo, criterio.comando)
        if clave in ejecutados:
            resultados.append(replace(ejecutados[clave], criterio=criterio))
            continue
        limite = presupuesto.recortar(timeout_suite if es_suite(criterio.comando) else timeout)
        if limite <= 0:
            resultados.append(
                Resultado(criterio, False, None, f"no se ejecutó: presupuesto total de {presupuesto.total:g} s agotado")
            )
            continue
        ejecutados[clave] = evaluar(criterio, raiz, bash, limite)
        resultados.append(ejecutados[clave])
    return resultados


# ---------------------------------------------------------------------------
# Congelado, firma y caché
# ---------------------------------------------------------------------------

def correr_congelado(
    bash: str, raiz: Path, plan: Path, timeout: float = TIMEOUT_CONGELADO
) -> tuple[int | None, str, str]:
    """Ejecuta `congelado.sh <plan> <slug>` desde la raíz. Devuelve (código, stdout, stderr).

    Con exit 0, el stdout de `congelado.sh` es el hash completo del commit congelado.
    """
    relativa = plan.relative_to(raiz).as_posix()
    try:
        proceso = subprocess.run(
            [bash, CONGELADO_SH.as_posix(), relativa, slug_de(plan)],
            cwd=str(raiz),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "", f"congelado.sh no terminó en {round(timeout, 1):g} s"
    except OSError as error:
        return None, "", f"no se pudo ejecutar congelado.sh: {error}"
    return (
        proceso.returncode,
        proceso.stdout.decode("utf-8", errors="replace"),
        proceso.stderr.decode("utf-8", errors="replace"),
    )


def hash_valido(texto: str) -> str | None:
    """El hash de commit que imprimió `congelado.sh` (40 o 64 hex), o None si no es uno."""
    valor = texto.strip()
    return valor if RE_HASH_COMMIT.fullmatch(valor) else None


def correr_git(raiz: Path, argumentos: list[str], salida, timeout: float = 60) -> bool:
    """Ejecuta git de solo lectura con la salida a `salida` (archivo). True si salió con 0."""
    git = buscar_ejecutable("git")
    if git is None:
        return False
    try:
        proceso = subprocess.run(
            [git, "-C", str(raiz), *argumentos],
            stdin=subprocess.DEVNULL,
            stdout=salida,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proceso.returncode == 0


def salida_git(raiz: Path, *argumentos: str, timeout: float = 60) -> str | None:
    """Salida de un comando git de solo lectura, o None si falla o no hay git."""
    with tempfile.TemporaryFile() as salida:
        if not correr_git(raiz, list(argumentos), salida, timeout):
            return None
        salida.seek(0)
        return salida.read().decode("utf-8", errors="replace")


def texto_congelado(raiz: Path, plan: Path, commit: str, timeout: float = 60) -> str | None:
    """Texto del plan en el commit congelado: `git -C <raíz> show <commit>:./docs/planes/<archivo>`.

    La ruta es relativa a la raíz del proyecto (el `./` la ancla al directorio de `-C`), no al
    directorio actual. Devuelve None si git falla: por ejemplo, si el commit no está en el repo
    de la raíz (un repo anidado en `docs/planes/`) o si el plan no está en ese commit.
    """
    relativa = plan.relative_to(raiz).as_posix()
    with tempfile.TemporaryFile() as salida:
        if not correr_git(raiz, ["-c", "core.quotepath=off", "show", f"{commit}:./{relativa}"], salida, timeout):
            return None
        salida.seek(0)
        return salida.read().decode("utf-8", errors="replace").replace("\r", "")


def hash_de_git(raiz: Path, argumentos: list[str], timeout: float) -> str | None:
    """SHA-256 de la salida de un comando git, sin cargarla entera en memoria (archivo temporal)."""
    resumen = hashlib.sha256()
    with tempfile.TemporaryFile() as salida:
        if not correr_git(raiz, argumentos, salida, timeout):
            return None
        salida.seek(0)
        for bloque in iter(lambda: salida.read(TAMANO_BLOQUE), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def hash_de_archivo(resumen, ruta: Path) -> None:
    """Agrega al resumen el contenido de un archivo sin seguimiento, leído por bloques.

    Un symlink aporta su destino; un directorio (p. ej. un repo anidado) o un archivo ilegible
    aporta solo un marcador: la ruta ya forma parte del resumen.
    """
    try:
        if ruta.is_symlink():
            resumen.update(b"L" + os.readlink(ruta).encode("utf-8", errors="replace"))
            return
        if ruta.is_dir():
            resumen.update(b"D")
            return
        resumen.update(b"F")
        with ruta.open("rb") as archivo:
            for bloque in iter(lambda: archivo.read(TAMANO_BLOQUE), b""):
                resumen.update(bloque)
    except OSError:
        resumen.update(b"E")


def hash_sin_seguimiento(repo: Path, excluir: list[str], timeout: float) -> str | None:
    """SHA-256 de rutas y contenido de los archivos sin seguimiento no ignorados del repo."""
    with tempfile.TemporaryFile() as salida:
        argumentos = ["ls-files", "-z", "--others", "--exclude-standard", "--", ".", *excluir]
        if not correr_git(repo, argumentos, salida, timeout):
            return None
        salida.seek(0)
        rutas = [r for r in salida.read().split(b"\0") if r]
    resumen = hashlib.sha256()
    for ruta in sorted(rutas):
        resumen.update(b"\0" + ruta + b"\0")
        hash_de_archivo(resumen, repo / ruta.decode("utf-8", errors="surrogateescape"))
    return resumen.hexdigest()


def firma_de_repo(repo: Path, excluir: list[str], timeout: float) -> list[str] | None:
    """Componentes de la firma de un repo: HEAD, hash del diff contra HEAD y de los sin seguimiento."""
    cabeza = salida_git(repo, "rev-parse", "HEAD", timeout=timeout)
    diff = hash_de_git(
        repo,
        ["diff", "HEAD", "--binary", "--no-color", "--no-ext-diff", "--no-textconv", "--", ".", *excluir],
        timeout,
    )
    sin_seguimiento = hash_sin_seguimiento(repo, excluir, timeout)
    if cabeza is None or diff is None or sin_seguimiento is None:
        return None
    return [cabeza.strip(), diff, sin_seguimiento]


def firma(
    raiz: Path,
    plan: Path,
    presupuesto: Presupuesto | None = None,
    contenido_plan: bytes | None = None,
    commit_base: str | None = None,
) -> str | None:
    """Firma por contenido del estado de trabajo, para la caché.

    Por repo (raíz, backend, mobile): HEAD, hash de `git diff HEAD --binary` y hash del
    contenido de los archivos sin seguimiento no ignorados; más el hash del plan en disco (así
    marcar una subtarea `hecha` invalida la caché). Un cambio nuevo sobre un archivo que ya
    estaba modificado cambia la firma aunque `git status` no cambie. El archivo de caché queda
    fuera: escribirlo no debe invalidar la firma. `contenido_plan` son los bytes del plan que
    ya se leyeron para los estados (así la firma corresponde exactamente a lo parseado).
    `commit_base` es el hash resuelto del Registro (o None): entra en la firma para que un
    commit_base distinto invalide la caché. Sin la firma de la raíz → None (sin caché);
    backend o mobile que no existen o fallan aportan un componente vacío.
    """
    if presupuesto is None:
        presupuesto = Presupuesto(PRESUPUESTO_TOTAL)
    raiz_partes = firma_de_repo(raiz, [f":(exclude).claude/{NOMBRE_CACHE}"], presupuesto.recortar(60))
    if raiz_partes is None:
        return None
    try:
        if contenido_plan is None:
            contenido_plan = plan.read_bytes()
    except OSError:
        return None
    hash_plan = hashlib.sha256(contenido_plan).hexdigest()
    partes = [str(plan), hash_plan, f"commit_base={commit_base or ''}", *raiz_partes]
    for sub in ("backend", "mobile"):
        partes.append(sub)
        if (raiz / sub).is_dir():
            partes.extend(firma_de_repo(raiz / sub, [], presupuesto.recortar(60)) or [""])
    return hashlib.sha256("\0".join(partes).encode("utf-8")).hexdigest()


def leer_cache(cache: Path) -> dict | None:
    """Contenido de la caché (`firma`, `fallas`, `informe`) o None si no existe o es ilegible."""
    try:
        datos = json.loads(leer_texto(cache))
    except (OSError, ValueError):
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("firma"), str):
        return None
    return datos


def escribir_cache(cache: Path, firma_actual: str, texto_informe: str) -> None:
    """Guarda la firma y el resultado de la corrida (informe vacío = corrida limpia)."""
    datos = {"firma": firma_actual, "fallas": bool(texto_informe), "informe": texto_informe}
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(datos, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError:
        pass  # sin caché la próxima corrida simplemente vuelve a verificar


# ---------------------------------------------------------------------------
# Modo, contador e informe
# ---------------------------------------------------------------------------

def leer_modo(raiz: Path) -> str:
    """Modo del hook: `bloqueo` o, por defecto, `aviso`."""
    archivo = raiz / ".claude" / "hooks" / "modo"
    try:
        valor = leer_texto(archivo).strip()
    except OSError:
        return "aviso"
    return "bloqueo" if valor == "bloqueo" else "aviso"


def archivo_contador(session_id: str) -> Path:
    """Archivo del contador de reintentos para una sesión (nombre saneado)."""
    seguro = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)[:100] or "sin-sesion"
    return Path(tempfile.gettempdir()) / f"territoryos-verificar-plan-{seguro}.cnt"


def sumar_intento(session_id: str) -> int:
    """Incrementa y devuelve el contador de intentos fallidos de la sesión."""
    archivo = archivo_contador(session_id)
    try:
        actual = int(archivo.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        actual = 0
    actual += 1
    try:
        archivo.write_text(str(actual), encoding="utf-8")
    except OSError:
        pass  # sin contador persistente el hook sigue funcionando, solo sin tope de reintentos
    return actual


def reiniciar_intentos(session_id: str) -> None:
    """Borra el contador de la sesión tras una corrida limpia."""
    try:
        archivo_contador(session_id).unlink()
    except OSError:
        pass  # no existía: nada que reiniciar


def ultimas_lineas(texto: str, cantidad: int = LINEAS_DE_SALIDA) -> str:
    """Últimas `cantidad` líneas de un texto."""
    return "\n".join(texto.rstrip("\n").splitlines()[-cantidad:])


def informe(fallas: list[Resultado], plan: Path) -> str:
    """Texto por stderr con cada criterio fallido: comando literal, código y salida."""
    partes = [f"verificar_plan: {len(fallas)} criterio(s) en FALLA en {plan.name}"]
    for resultado in fallas:
        c = resultado.criterio
        codigo = "timeout/error" if resultado.codigo is None else str(resultado.codigo)
        partes.append(f"\n- {c.origen} [{c.tipo}] `{c.comando}` → FALLA (exit {codigo})")
        salida = ultimas_lineas(resultado.salida)
        if salida:
            partes.append("\n".join(f"    {linea}" for linea in salida.splitlines()))
    return "\n".join(partes) + "\n"


def salir_con_falla(texto_informe: str, raiz: Path, session_id: str) -> int:
    """Escribe el informe por stderr y devuelve el exit según el modo y el contador."""
    sys.stderr.write(texto_informe)
    if leer_modo(raiz) != "bloqueo":
        return 1
    if sumar_intento(session_id) > MAX_INTENTOS_BLOQUEO:
        sys.stderr.write("verificar_plan: cuarto intento con criterios en FALLA: revisar a mano.\n")
        return 1
    return 2


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main(texto_stdin: str, entorno: dict[str, str]) -> int:
    """Punto de entrada testeable: devuelve el código de salida del hook."""
    presupuesto = Presupuesto(PRESUPUESTO_TOTAL)
    datos = leer_entrada(texto_stdin)
    if datos is None or datos.get("stop_hook_active") is True:
        return 0
    session_id = str(datos.get("session_id") or "sin-sesion")

    raiz = resolver_raiz(entorno)
    plan = plan_de_rama(raiz) or plan_activo(raiz)
    if plan is None:
        return 0

    try:
        bash = buscar_bash()
    except FileNotFoundError as error:
        sys.stderr.write(f"verificar_plan: {error}\n")
        return 1

    # Congelado previo: sin contrato congelado e intacto no se ejecuta ningún criterio.
    codigo_congelado, salida_congelado, error_congelado = correr_congelado(
        bash, raiz, plan, presupuesto.recortar(TIMEOUT_CONGELADO)
    )
    if codigo_congelado != 0:
        codigo_texto = "error" if codigo_congelado is None else str(codigo_congelado)
        motivo = (
            f"verificar_plan: no se ejecuta ningún criterio de {plan.name}: congelado.sh salió con "
            f"{codigo_texto} (contrato no congelado o modificado arriba de '{CORTE}').\n"
        )
        return salir_con_falla(motivo + error_congelado.rstrip("\n") + "\n", raiz, session_id)
    commit = hash_valido(salida_congelado)
    if commit is None:
        motivo = (
            f"verificar_plan: no se ejecuta ningún criterio de {plan.name}: congelado.sh salió con 0 "
            f"pero no imprimió un hash de commit válido ({salida_congelado.strip()[:80]!r}).\n"
        )
        return salir_con_falla(motivo, raiz, session_id)
    if error_congelado.strip():
        sys.stderr.write(error_congelado.rstrip("\n") + "\n")

    # Criterios: solo del texto del commit congelado. Del disco, solo la tabla de estados.
    congelado = texto_congelado(raiz, plan, commit, presupuesto.recortar(60))
    if congelado is None:
        motivo = (
            f"verificar_plan: no se ejecuta ningún criterio de {plan.name}: no se pudo leer el plan "
            f"del commit congelado {commit} con git show desde la raíz.\n"
        )
        return salir_con_falla(motivo, raiz, session_id)
    try:
        contenido_disco = plan.read_bytes()
    except OSError as error:
        return salir_con_falla(f"verificar_plan: no se pudo leer {plan.name}: {error}\n", raiz, session_id)
    datos_plan = combinar_planes(congelado, contenido_disco.decode("utf-8", errors="replace"))
    if sin_formato_t(datos_plan):
        motivo = (
            f"verificar_plan: {plan.name} tiene bloques de criterios pero ninguna subtarea '### T<n>': "
            "el plan no sigue el formato T<n> y el hook no puede ejecutar sus criterios.\n"
        )
        return salir_con_falla(motivo, raiz, session_id)

    commit_base, motivo_base = commit_base_del_registro(
        contenido_disco.decode("utf-8", errors="replace"), raiz, slug_de(plan)
    )
    firma_actual = firma(raiz, plan, presupuesto, contenido_disco, commit_base)
    cache = raiz / ".claude" / NOMBRE_CACHE
    if firma_actual is not None:
        previo = leer_cache(cache)
        if previo is not None and previo["firma"] == firma_actual:
            informe_previo = str(previo.get("informe") or "")
            if not previo.get("fallas") or not informe_previo:
                return 0
            aviso = "verificar_plan: sin cambios desde la última corrida; se reemite su informe (caché).\n"
            return salir_con_falla(aviso + informe_previo, raiz, session_id)

    seleccion = criterios_a_ejecutar(datos_plan)
    if not seleccion:
        return 0

    seleccion, sin_resolver = reemplazar_commit_base(seleccion, commit_base, motivo_base, plan)
    resultados = sin_resolver + ejecutar_seleccion(
        seleccion, raiz, bash, leer_timeout(entorno), presupuesto, leer_timeout_suite(entorno)
    )
    fallas = [r for r in resultados if not r.pasa]
    texto_informe = informe(fallas, plan) if fallas else ""
    if firma_actual is not None:
        escribir_cache(cache, firma_actual, texto_informe)
    if not fallas:
        reiniciar_intentos(session_id)
        return 0
    return salir_con_falla(texto_informe, raiz, session_id)


def ejecutar_commit_base(argumentos: list[str], entorno: dict[str, str]) -> int:
    """CLI `--commit-base [plan]`: imprime el hash resuelto (0) o el motivo por stderr (2).

    El plan se deriva como en el hook (`plan_de_rama`, luego `plan_activo`) salvo que se pase
    una ruta relativa a la raíz. No lee stdin.
    """
    raiz = resolver_raiz(entorno)
    if argumentos:
        plan, motivo = validar_plan(raiz, argumentos[0])
        if plan is None:
            sys.stderr.write(f"commit_base sin resolver en {argumentos[0]}: plan inválido ({motivo})\n")
            return 2
    else:
        plan = plan_de_rama(raiz) or plan_activo(raiz)
        if plan is None:
            sys.stderr.write("commit_base sin resolver: no hay plan activo ni plan de la rama\n")
            return 2
    completo, motivo = commit_base_del_registro(leer_texto(plan), raiz, slug_de(plan))
    if completo is None:
        sys.stderr.write(f"commit_base sin resolver en {plan.name}: {motivo}\n")
        return 2
    sys.stdout.write(completo + "\n")
    return 0


def ejecutar() -> int:
    """Envuelve `main` para que el hook nunca termine con traceback."""
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # stderr sin reconfigure (p. ej. reemplazado): se usa tal cual
    if sys.argv[1:2] == ["--commit-base"]:
        return ejecutar_commit_base(sys.argv[2:3], dict(os.environ))
    try:
        texto = sys.stdin.buffer.read().decode("utf-8", errors="replace") if sys.stdin else ""
    except (OSError, ValueError):
        texto = ""
    try:
        return main(texto, dict(os.environ))
    except Exception as error:  # noqa: BLE001 — el hook nunca debe cortar la sesión con traceback
        sys.stderr.write(f"verificar_plan: error interno: {error!r}\n")
        return 1


if __name__ == "__main__":
    sys.exit(ejecutar())
