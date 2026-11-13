"""Tests de `verificar.py` (subcomandos `tarea`, `todo` y `cierre`).

    py -3 -m pytest .claude/hooks/test_verificar.py -q

Cada test arma un repo git temporal con un plan congelado (`docs(plan): demo`). Nunca toca el
`docs/planes/` ni el `.claude/.recibos.json` reales, y los criterios solo usan `true`, `false`,
`test`, `echo` y `seq` dentro del repo temporal: no corre la suite de Django ni la de los hooks.
Los planes de ejemplo (v1 y v2) están en `fixtures/verificar/`.
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

DIR_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_HOOKS))
import recibo  # noqa: E402
import verificar  # noqa: E402
import verificar_plan as vp  # noqa: E402

FIXTURES = DIR_HOOKS / "fixtures" / "verificar"
PLAN = "docs/planes/2026-11-13-demo.md"
RECIBO = "docs/planes/demo.recibo.md"
CORTE = "## Registro de verificación\n\n| T1 | hecha | x |\n"
PUEDE_A = "- **Puede tocar**: `a.py`\n"


def plan_texto(tareas: str, extra: str = "") -> str:
    """Plan mínimo: encabezado, subtareas, secciones extra y el corte."""
    return f"# Plan: demo\n\n- **slug**: `demo`\n\n## Subtareas\n\n{tareas}\n{extra}\n{CORTE}"


def tarea(numero: int, *criterios: str, extra: str = "") -> str:
    """Bloque `### T<n>` con criterios `[tipo] comando`."""
    lineas = "\n".join(f"  - `[{c.split(' ', 1)[0]}]` `{c.split(' ', 1)[1]}`" for c in criterios)
    return f"### T{numero} — tarea {numero}\n\n{extra}- **Criterios**:\n{lineas}\n\n"


def fixture(nombre: str) -> str:
    """Texto de un plan de `fixtures/verificar/`."""
    return (FIXTURES / nombre).read_text(encoding="utf-8")


def git(raiz: Path, *args: str) -> str:
    """Corre git en el repo temporal y devuelve su stdout."""
    return subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True, check=True).stdout.strip()


class Repo:
    """Repo git temporal en la rama `main`, con el plan por congelar y atajos para correr `verificar`."""

    def __init__(self, raiz: Path):
        raiz.mkdir(parents=True)
        self.raiz = raiz.resolve()
        git(self.raiz, "init", "-q")
        git(self.raiz, "symbolic-ref", "HEAD", "refs/heads/main")
        for clave, valor in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
            git(self.raiz, "config", clave, valor)

    def escribir(self, ruta: str, contenido: str) -> None:
        archivo = self.raiz / ruta
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding="utf-8", newline="\n")

    def congelar(self, texto: str, otros: dict | None = None) -> None:
        """Escribe el plan (y otros archivos) y los commitea como `docs(plan): demo`."""
        self.escribir(PLAN, texto)
        for ruta, contenido in (otros or {}).items():
            self.escribir(ruta, contenido)
        git(self.raiz, "add", "-A")
        git(self.raiz, "commit", "-q", "-m", "docs(plan): demo")

    def commit(self, asunto: str, archivo: str, contenido: str | None = None) -> None:
        """Commit con ese asunto que escribe `archivo`."""
        self.escribir(archivo, contenido if contenido is not None else f"{asunto}\n")
        git(self.raiz, "add", archivo)
        git(self.raiz, "commit", "-q", "-m", asunto)

    def vacio(self) -> None:
        git(self.raiz, "commit", "-q", "--allow-empty", "-m", "otro")

    def head(self) -> str:
        return git(self.raiz, "rev-parse", "--short", "HEAD")

    def correr(self, *argv: str, cierre_json: Path | None = None) -> tuple[int, str]:
        """Ejecuta `verificar.main` sobre este repo; devuelve (exit, stdout)."""
        salida, error = io.StringIO(), io.StringIO()
        extra = {"cierre_json": cierre_json} if cierre_json else {}
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(error):
            codigo = verificar.main(["--raiz", str(self.raiz), *argv], timeout=60, **extra)
        return codigo, salida.getvalue()

    def recibo(self) -> str:
        return (self.raiz / RECIBO).read_text(encoding="utf-8")

    def cierre(self, *comandos: str) -> Path:
        """`cierre_global.json` de prueba, fuera del repo."""
        ruta = self.raiz.parent / f"{self.raiz.name}-cierre.json"
        ruta.write_text(json.dumps({"comandos": list(comandos)}), encoding="utf-8")
        return ruta

    def modificar_contrato(self, texto: str) -> str:
        """Commitea el plan modificado como `docs(plan): demo — modificado: motivo`; devuelve su hash corto."""
        self.escribir(PLAN, texto)
        git(self.raiz, "add", PLAN)
        git(self.raiz, "commit", "-q", "-m", "docs(plan): demo — modificado: motivo")
        return git(self.raiz, "rev-parse", "--short=7", "HEAD")


@pytest.fixture
def repo(tmp_path):
    return Repo(tmp_path / "repo")


# ---------------------------------------------------------------------------
# tarea
# ---------------------------------------------------------------------------

def test_tarea_pasa_y_escribe_recibo(repo):
    repo.congelar(plan_texto(tarea(1, "cmd echo uno > marca1.txt", extra=PUEDE_A)))
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida
    texto = repo.recibo()
    assert re.search(r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} — tarea T1 de 2026-11-13-demo\.md$", texto, re.M)
    assert f"- HEAD verificado: {repo.head()}" in texto
    assert "- Contrato: intacto (congelado en " in texto
    assert "  - PASA (exit 0, nuevo: —) `T1 [cmd] echo uno > marca1.txt`" in texto
    assert "`versionados limpios" in texto and "`commits de la tarea dentro de Puede tocar`" in texto
    assert re.search(r"^- duración: \d+(\.\d+)? s$", texto, re.M)
    assert re.search(r"^- Veredicto: PASA$", texto, re.M)
    assert texto == salida
    assert not (repo.raiz / ".claude" / ".recibos.json").exists(), "tarea no registra el HEAD"


def test_tarea_corre_solo_los_criterios_de_la_tarea_pedida(repo):
    repo.congelar(plan_texto(tarea(1, "cmd echo uno > marca1.txt") + tarea(2, "cmd echo dos > marca2.txt")))
    codigo, _ = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0
    assert (repo.raiz / "marca1.txt").exists() and not (repo.raiz / "marca2.txt").exists()
    codigo, _ = repo.correr("tarea", PLAN, "T1,T2")
    assert codigo == 0 and (repo.raiz / "marca2.txt").exists()
    assert "tarea T1,T2 de" in repo.recibo()


def test_tarea_commit_fuera_de_puede_tocar_falla(repo):
    otra = "- **Puede tocar**: `k.py`\n"
    repo.congelar(plan_texto(tarea(1, "cmd true", extra=PUEDE_A) + tarea(11, "cmd true", extra=otra)))
    repo.commit("T1: lo propio", "a.py")
    repo.commit("T11: se pasa de su alcance", "otro.py")  # T1 no debe capturar los de T11
    repo.commit("docs: sin tarea", "ajeno.py")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida
    repo.commit("T1: toca lo ajeno", "fuera.py")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1, salida
    assert "T1: toca lo ajeno -> fuera.py" in repo.recibo()
    assert "T11: se pasa" not in repo.recibo()
    assert re.search(r"^- Veredicto: FALLA$", repo.recibo(), re.M)


def test_tarea_commit_que_vino_de_main_no_cuenta(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true", extra=PUEDE_A)))
    repo.commit("T1: de otro plan en main", "ajeno.py")
    git(repo.raiz, "checkout", "-q", "-b", "rama-tarea")
    repo.commit("T1: propio", "a.py")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida


def test_tarea_test_preexistente_falla(repo):
    preexistente = "py -3 -m pytest .claude/hooks/test_x.py::test_a -q"
    nuevo = "py -3 -m pytest .claude/hooks/test_x.py::test_b -q"
    repo.congelar(plan_texto(tarea(1, f"test {preexistente}", f"test {nuevo}", extra=PUEDE_A)),
                  {".claude/hooks/test_x.py": "def test_a():\n    pass\n"})
    repo.commit("T1: agrega test_b", ".claude/hooks/test_x.py", "def test_a():\n    pass\n\n\ndef test_b():\n    pass\n")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1
    assert "test preexistente" in repo.recibo() and "test preexistente" in salida
    assert f"  - FALLA (exit 1, nuevo: no) `T1 [test] {preexistente}`" in repo.recibo()


def test_tarea_ejecuta_un_test_nuevo_y_lo_marca_nuevo(repo):
    nuevo = "py -3 -m pytest .claude/hooks/test_x.py::test_b -q"
    repo.congelar(plan_texto(tarea(1, f"test {nuevo}", extra="- **Puede tocar**: `.claude/hooks/test_x.py`\n")))
    repo.commit("T1: agrega test_b", ".claude/hooks/test_x.py", "def test_b():\n    pass\n")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida
    assert f"  - PASA (exit 0, nuevo: sí) `T1 [test] {nuevo}`" in repo.recibo()


def test_criterios_salen_del_commit_congelado_no_del_disco(repo):
    repo.congelar(plan_texto(tarea(1, "cmd echo ok > ok.txt")))
    # El disco cambia después del congelado: el criterio nuevo no debe ejecutarse.
    repo.escribir(PLAN, plan_texto(tarea(1, "cmd echo ok > ok.txt", "cmd echo x > intruso.txt")))
    codigo, _ = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1  # el contrato cambió: congelado.sh sale con 1
    assert not (repo.raiz / "intruso.txt").exists()
    assert (repo.raiz / "ok.txt").exists(), "los criterios del commit congelado se ejecutan igual"
    assert "- Contrato: FALLA: contrato MODIFICADO" in repo.recibo()


def test_contrato_modificado_sin_decision_del_usuario_falla(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true")))
    corto = repo.modificar_contrato(plan_texto(tarea(1, "cmd echo nuevo > nuevo.txt"), extra=""))
    casos = {
        "sin decisiones.md": None,
        "línea del agente": f"- 2026-10-28 (agente) cambió los criterios {corto}\n",
        "usuario sin el hash": "- 2026-10-28 (usuario) acepta otra cosa abcdef1\n",
    }
    for nombre, contenido in casos.items():
        (repo.raiz / "nuevo.txt").unlink(missing_ok=True)
        if contenido is not None:
            repo.escribir("docs/decisiones.md", contenido)
        codigo, salida = repo.correr("tarea", PLAN, "T1")
        assert codigo == 1, f"{nombre}: {salida}"
        texto = repo.recibo()
        assert "- Contrato: FALLA: contrato MODIFICADO sin decisión del usuario" in texto, nombre
        assert (repo.raiz / "nuevo.txt").exists(), f"{nombre}: se ejecutan los criterios del último commit"
        assert texto.rstrip().endswith("- Veredicto: FALLA"), nombre
        assert "  - PASA (exit 0, nuevo: —) `T1 [cmd] echo nuevo > nuevo.txt`" in texto, nombre


def test_contrato_modificado_con_decision_del_usuario_pasa(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true")))
    corto = repo.modificar_contrato(plan_texto(tarea(1, "cmd true", "cmd echo nuevo > nuevo.txt")))
    repo.escribir("docs/decisiones.md", f"- 2026-11-13 (usuario) acepta el cambio de criterios {corto}\n")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida
    assert (repo.raiz / "nuevo.txt").exists()
    assert f"- Contrato: modificado y aceptado ({corto}, decisión del usuario)" in repo.recibo()
    assert "- Veredicto: PASA" in repo.recibo()
    # El disco cambia después del último commit de modificación: vuelve a ser FALLA.
    repo.escribir(PLAN, plan_texto(tarea(1, "cmd true", "cmd false")))
    codigo, _ = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1


def test_tarea_versionados_limpios_solo_cuentan_puede_tocar(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true", extra="- **Puede tocar**: `a.py`, `carpeta/`\n")),
                  {"a.py": "a = 1\n", "otro.py": "x = 1\n", "carpeta/b.py": "b = 1\n", "docs/estado.md": "uno\n"})
    repo.escribir("otro.py", "x = 2\n")
    repo.escribir("docs/estado.md", "dos\n")
    repo.escribir(PLAN, (repo.raiz / PLAN).read_text(encoding="utf-8") + "\nnota del registro\n")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida
    assert "- Fuera de alcance (informativo): M otro.py\n" in salida
    assert "M docs/estado.md" not in salida and "M docs/planes" not in salida
    repo.escribir("carpeta/b.py", "b = 2\n")
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1, salida
    assert "M carpeta/b.py" in salida and "FALLA" in salida


def test_falla_copia_como_maximo_30_lineas_de_salida(repo):
    repo.congelar(plan_texto(tarea(1, "cmd for i in $(seq 1 50); do echo linea$i; done; false")))
    codigo, _ = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1
    texto = repo.recibo()
    assert "    linea50" in texto and "    linea21" in texto
    assert "    linea20\n" not in texto


# ---------------------------------------------------------------------------
# Plan v1
# ---------------------------------------------------------------------------

def plan_v1(repo: Repo) -> tuple[str, str]:
    """Congela el plan v1 y deja en el disco el Registro con `commit_base:`; devuelve (hash, texto del disco)."""
    repo.congelar(fixture("plan_v1.md"))
    base = git(repo.raiz, "rev-parse", "HEAD")
    disco = fixture("plan_v1.md").replace("{{BASE}}", base[:9])
    repo.escribir(PLAN, disco)
    return base, disco


def test_plan_v1_lee_estado_y_cierre_global_sin_modificarlo(repo):
    _, disco = plan_v1(repo)
    assert vp.parsear_plan(disco, estados_solo_bajo_corte=True).estados == {1: "hecha", 2: "en curso"}
    antes = (repo.raiz / PLAN).read_bytes()
    json_cierre = repo.cierre("echo json > cierre_json.txt")
    codigo, salida = repo.correr("todo", PLAN, cierre_json=json_cierre)
    assert codigo == 0, salida
    assert (repo.raiz / "marca1.txt").exists() and (repo.raiz / "marca2.txt").exists()
    assert (repo.raiz / "cierre_v1.txt").exists(), "el cierre global sale del bloque del plan"
    assert not (repo.raiz / "cierre_json.txt").exists(), "con bloque en el plan no se usa cierre_global.json"
    assert "`cierre global [cmd] echo cierre_v1 >> cierre_v1.txt`" in repo.recibo()
    assert (repo.raiz / PLAN).read_bytes() == antes, "verificar nunca escribe el plan"


def test_plan_v1_reemplaza_marcador_commit_base(repo):
    base, _ = plan_v1(repo)
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida
    assert (repo.raiz / "base_usada.txt").read_text(encoding="utf-8").strip() == base
    # Sin `commit_base:` en el Registro el criterio con el marcador es FALLA y no se ejecuta.
    (repo.raiz / "base_usada.txt").unlink()
    repo.escribir(PLAN, fixture("plan_v1.md").replace("commit_base: {{BASE}}\n", ""))
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 1
    assert "commit_base sin resolver en 2026-11-13-demo.md" in repo.recibo()
    assert not (repo.raiz / "base_usada.txt").exists()


# ---------------------------------------------------------------------------
# todo
# ---------------------------------------------------------------------------

def test_todo_pasa_registra_head(repo):
    repo.congelar(fixture("plan_v2.md"))
    cierre = repo.cierre("echo json >> cierre_json.txt")
    codigo, salida = repo.correr("todo", PLAN, cierre_json=cierre)
    assert codigo == 0, salida
    head = repo.head()
    texto = repo.recibo()
    assert f"- HEAD verificado: {head}" in texto
    assert "— todo 2026-11-13-demo.md" in texto
    assert re.search(r"^- duración: \d+(\.\d+)? s$", texto, re.M)
    assert "- Veredicto: PASA" in texto
    assert (repo.raiz / "marca1.txt").exists() and (repo.raiz / "marca2.txt").exists()
    assert (repo.raiz / "cierre_json.txt").exists(), "un plan v2 usa el cierre_global.json"
    assert recibo.head_tiene_recibo(repo.raiz, head)
    # Con FALLA el HEAD nuevo no se registra.
    repo.vacio()
    codigo, _ = repo.correr("todo", PLAN, cierre_json=repo.cierre("false"))
    assert codigo == 1
    assert not recibo.head_tiene_recibo(repo.raiz, repo.head())


def test_todo_incremental_reutiliza_tarea_con_mismo_head(repo):
    repo.congelar(plan_texto(tarea(1, "cmd echo uno >> marca1.txt")))
    cierre = repo.cierre("true")
    assert repo.correr("todo", PLAN, cierre_json=cierre)[0] == 0
    codigo, salida = repo.correr("todo", PLAN, cierre_json=cierre)
    assert codigo == 0, salida
    assert (repo.raiz / "marca1.txt").read_text(encoding="utf-8").splitlines() == ["uno"]
    assert re.search(r"PASA \(recibo previo \d{4}-\d\d-\d\d \d\d:\d\d\) `T1 \[cmd\] echo uno", salida)


def test_todo_repite_tarea_si_cambio_el_head(repo):
    repo.congelar(plan_texto(tarea(1, "cmd echo uno >> marca1.txt")))
    cierre = repo.cierre("true")
    repo.correr("todo", PLAN, cierre_json=cierre)
    repo.vacio()
    codigo, _ = repo.correr("todo", PLAN, cierre_json=cierre)
    assert codigo == 0
    assert (repo.raiz / "marca1.txt").read_text(encoding="utf-8").splitlines() == ["uno", "uno"]


def test_todo_repite_tarea_si_cambio_el_contrato_o_hubo_falla(repo):
    repo.congelar(plan_texto(tarea(1, "cmd echo uno >> marca1.txt")))
    cierre = repo.cierre("true")
    repo.correr("todo", PLAN, cierre_json=cierre)
    ruta = repo.raiz / RECIBO
    texto = ruta.read_text(encoding="utf-8")
    ruta.write_text(re.sub(r"congelado en [0-9a-f]+", "congelado en 0000000", texto), encoding="utf-8", newline="\n")
    repo.correr("todo", PLAN, cierre_json=cierre)
    assert len((repo.raiz / "marca1.txt").read_text(encoding="utf-8").splitlines()) == 2
    # Un criterio de la tarea en FALLA en el recibo previo tampoco se reutiliza.
    ruta.write_text(ruta.read_text(encoding="utf-8").replace("  - PASA (exit 0", "  - FALLA (exit 1"), encoding="utf-8", newline="\n")
    repo.correr("todo", PLAN, cierre_json=cierre)
    assert len((repo.raiz / "marca1.txt").read_text(encoding="utf-8").splitlines()) == 3


def test_todo_falla_por_versionados_de_claude_y_solo_informa_el_resto(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true")), {"codigo.py": "x = 1\n", "CLAUDE.md": "a\n", ".claude/h.py": "h = 1\n"})
    cierre = repo.cierre("true")
    repo.escribir("codigo.py", "x = 2\n")
    codigo, salida = repo.correr("todo", PLAN, cierre_json=cierre)
    assert codigo == 0, salida
    assert "- Fuera de alcance (informativo): M codigo.py" in salida
    for ruta in ("CLAUDE.md", ".claude/h.py"):
        repo.escribir(ruta, "cambiado\n")
        codigo, salida = repo.correr("todo", PLAN, cierre_json=cierre)
        assert codigo == 1, salida
        assert f"M {ruta}" in salida
        git(repo.raiz, "checkout", "-q", "--", ruta)


# ---------------------------------------------------------------------------
# cierre
# ---------------------------------------------------------------------------

def test_cierre_usa_cierre_global_json(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true")), {"codigo.py": "x = 1\n", "docs/metodo/m.md": "a\n", "docs/estado.md": "a\n"})
    cierre = repo.cierre("echo uno > c1.txt", "echo dos > c2.txt")
    # Plan, estado, metodo y decisiones modificados no cuentan en el cierre.
    repo.escribir(PLAN, plan_texto(tarea(1, "cmd false")))
    repo.escribir("docs/metodo/m.md", "b\n")
    repo.escribir("docs/estado.md", "b\n")
    codigo, salida = repo.correr("cierre", cierre_json=cierre)
    head = repo.head()
    assert codigo == 0, salida
    assert (repo.raiz / "c1.txt").exists() and (repo.raiz / "c2.txt").exists()
    assert "— cierre global" in salida and "- Veredicto: PASA" in salida
    assert "`cierre global [cmd] echo uno > c1.txt`" in salida
    assert not (repo.raiz / RECIBO).exists(), "el recibo de cierre va solo a stdout"
    assert recibo.head_tiene_recibo(repo.raiz, head)
    # Un versionado fuera de las exclusiones, o un comando en FALLA, dan FALLA y no registran el HEAD.
    repo.vacio()
    repo.escribir("codigo.py", "x = 2\n")
    codigo, salida = repo.correr("cierre", cierre_json=cierre)
    assert codigo == 1 and "M codigo.py" in salida and "- Veredicto: FALLA" in salida
    assert not recibo.head_tiene_recibo(repo.raiz, repo.head())
    git(repo.raiz, "checkout", "-q", "--", "codigo.py")
    codigo, salida = repo.correr("cierre", cierre_json=repo.cierre("false"))
    assert codigo == 1 and "- Veredicto: FALLA" in salida


def test_cierre_global_json_del_repo_trae_los_cinco_comandos_de_detach():
    criterios = verificar.criterios_de_cierre(verificar.CIERRE_JSON)
    comandos = [c.comando for c in criterios]
    manage = "PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py"
    assert comandos == [
        f"{manage} check",
        f"{manage} makemigrations --check --dry-run",
        f"{manage} test --keepdb",
        "./venv/Scripts/python.exe -m ruff check .",
        "py -3 -m pytest .claude/hooks -q",
    ]
    assert {c.tipo for c in criterios} == {"cmd"}


# ---------------------------------------------------------------------------
# Uso, recibo y marca
# ---------------------------------------------------------------------------

def test_uso_invalido_sale_2_sin_recibo(repo):
    repo.congelar(plan_texto(tarea(1, "cmd true")))
    casos = [
        [], ["nada"], ["tarea", PLAN], ["tarea", PLAN, "X1"], ["tarea", PLAN, "T9"], ["todo"],
        ["tarea", "docs/planes/no-existe.md", "T1"], ["tarea", "../fuera.md", "T1"],
        ["cierre", "extra"], ["cierre", "--recibo", "x.md"], ["--opcion-rara", "cierre"], ["--recibo"],
    ]
    for argv in casos:
        codigo, salida = repo.correr(*argv)
        assert codigo == 2, f"{argv}: exit {codigo}"
        assert salida == "", f"{argv}: no debe imprimir recibo"
    assert not (repo.raiz / RECIBO).exists()
    asignado = subprocess.run([sys.executable, str(DIR_HOOKS / "verificar.py"), "--raiz", str(repo.raiz), "nada"],
                              capture_output=True, text=True)
    assert asignado.returncode == 2 and "uso: verificar.py" in asignado.stderr
    sin_raiz = subprocess.run([sys.executable, str(DIR_HOOKS / "verificar.py"), "--raiz", str(repo.raiz / "no-existe"),
                               "cierre"], capture_output=True, text=True)
    assert sin_raiz.returncode == 2


def test_marca_verificando_se_borra_al_terminar(repo):
    marca = repo.raiz / ".claude" / ".verificando"
    repo.congelar(plan_texto(tarea(1, f'cmd test "$(cat .claude/.verificando)" = {os.getpid()}')))
    assert not marca.exists()
    codigo, salida = repo.correr("tarea", PLAN, "T1")
    assert codigo == 0, salida  # durante la corrida la marca existe y trae el PID
    assert not marca.exists()
    # También se borra si la corrida termina con uso inválido o con FALLA.
    assert repo.correr("tarea", PLAN, "T9")[0] == 2
    assert not marca.exists()
    assert repo.correr("nada")[0] == 2
    assert not marca.exists()
    assert repo.correr("cierre", cierre_json=repo.cierre("false"))[0] == 1
    assert not marca.exists()


def test_recibo_en_la_ruta_indicada_y_cli_de_punta_a_punta(repo, tmp_path):
    repo.congelar(plan_texto(tarea(1, "cmd echo uno > marca1.txt")))
    destino = tmp_path / "otro" / "r.md"
    proceso = subprocess.run(
        [sys.executable, str(DIR_HOOKS / "verificar.py"), "--raiz", str(repo.raiz), "--recibo", str(destino), "tarea", PLAN, "T1"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert proceso.returncode == 0, proceso.stdout + proceso.stderr
    assert re.search(r"^- Veredicto: PASA$", destino.read_text(encoding="utf-8"), re.M)
    assert not (repo.raiz / RECIBO).exists()
    assert not (repo.raiz / ".claude" / ".verificando").exists()
