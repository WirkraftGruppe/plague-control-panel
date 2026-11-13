"""Tests de `commit_msg.py` (hook commit-msg).

    py -3 -m pytest .claude/hooks/test_commit_msg.py -q

Cada test arma un repo git temporal con un plan; nunca toca el `.git/hooks` ni el
`.claude/.recibos.json` del repo real.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DIR_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_HOOKS))
import commit_msg  # noqa: E402
import recibo  # noqa: E402

PLAN = "docs/planes/2026-11-13-demo.md"
ALCANCE = "todo 2026-11-13-demo.md"


def git(directorio: Path, *args: str, comprobar: bool = True):
    """Corre git en el directorio y devuelve el proceso."""
    return subprocess.run(["git", "-C", str(directorio), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=comprobar)


@pytest.fixture
def raiz(tmp_path):
    """Repo temporal con un commit inicial y un plan `demo`."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    for clave, valor in (("user.name", "t"), ("user.email", "t@t"),
                         ("commit.gpgsign", "false"), ("core.autocrlf", "false")):
        git(repo, "config", clave, valor)
    (repo / "x.txt").write_text("x\n", encoding="utf-8", newline="\n")
    (repo / PLAN).parent.mkdir(parents=True)
    (repo / PLAN).write_text("# Plan: demo\n\n- **slug**: `demo`\n- **ruta**: completo\n",
                             encoding="utf-8", newline="\n")
    git(repo, "add", "x.txt", PLAN)
    git(repo, "commit", "-q", "-m", "inicial")
    return repo


def correr(raiz: Path, tmp_path: Path, texto: str, capsys):
    """Ejecuta el hook sobre `texto` y devuelve (exit, stderr)."""
    archivo = tmp_path / "msg.txt"
    archivo.write_text(texto, encoding="utf-8", newline="\n")
    capsys.readouterr()
    codigo = commit_msg.main([str(archivo)], raiz=raiz)
    return codigo, capsys.readouterr().err


def test_cierre_sin_recibo_se_rechaza(raiz, tmp_path, capsys):
    codigo, error = correr(raiz, tmp_path, "cierre: demo\n", capsys)
    assert codigo == 1
    assert recibo.head(raiz) in error
    assert "verificar.py todo docs/planes/2026-11-13-demo.md" in error


def test_cierre_ligero_sin_recibo_pide_el_cierre_ligero(raiz, tmp_path, capsys):
    (raiz / PLAN).write_text("# Plan: demo\n\n- **ruta**: ligero\n", encoding="utf-8", newline="\n")
    codigo, error = correr(raiz, tmp_path, "cierre: demo\n", capsys)
    assert codigo == 1
    assert "verificar.py cierre" in error
    assert "verificar.py todo" not in error


def test_cierre_con_recibo_en_pasa_se_acepta(raiz, tmp_path, capsys):
    recibo.registrar_head(raiz, recibo.head_completo(raiz), ALCANCE)
    assert correr(raiz, tmp_path, "cierre: demo\n\nTodo verde.\n", capsys) == (0, "")


def test_cierre_con_recibo_de_otro_head_se_rechaza(raiz, tmp_path, capsys):
    recibo.registrar_head(raiz, recibo.head_completo(raiz), ALCANCE)
    git(raiz, "commit", "-q", "--allow-empty", "-m", "otro")
    codigo, _ = correr(raiz, tmp_path, "cierre: demo\n", capsys)
    assert codigo == 1


def test_cierre_con_raya_y_texto_reconoce_el_slug(raiz, tmp_path, capsys):
    assert commit_msg.RE_CIERRE.match("cierre: demo — texto").group("slug") == "demo"
    codigo, error = correr(raiz, tmp_path, "cierre: demo — recibo en PASA\n", capsys)
    assert codigo == 1
    assert "«cierre: demo»" in error


def test_cierre_de_slug_sin_plan_se_rechaza(raiz, tmp_path, capsys):
    codigo, error = correr(raiz, tmp_path, "cierre: inexistente\n", capsys)
    assert codigo == 1
    assert "inexistente" in error


def test_mensaje_comun_pasa(raiz, tmp_path, capsys):
    assert correr(raiz, tmp_path, "T2: algo\n", capsys) == (0, "")
    assert correr(raiz, tmp_path, "docs: cierre: demo\n", capsys) == (0, "")


def instalar_hook(raiz: Path, con_commit_msg: bool = True) -> Path:
    """Instala el hook (y sus dependencias) solo en el repo temporal; devuelve `.claude/hooks`."""
    destino = raiz / ".claude" / "hooks"
    destino.mkdir(parents=True)
    for nombre in (("commit_msg.py", "recibo.py") if con_commit_msg else ("recibo.py",)):
        shutil.copy(DIR_HOOKS / nombre, destino / nombre)
    gancho = raiz / ".git" / "hooks" / "commit-msg"
    gancho.write_bytes((DIR_HOOKS / "commit-msg").read_bytes())
    gancho.chmod(0o755)
    return destino


def preparar(raiz: Path, ruta: str) -> None:
    """Escribe `ruta` y la agrega al índice."""
    archivo = raiz / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text("x" + chr(10), encoding="utf-8", newline=chr(10))
    git(raiz, "add", ruta)


def test_hook_instalado_en_repo_temporal_rechaza_y_acepta(raiz):
    destino = instalar_hook(raiz)
    preparar(raiz, "y.txt")
    git(raiz, "commit", "-q", "-m", "T1: algo")  # mensaje común: pasa

    preparar(raiz, "z.txt")
    rechazado = git(raiz, "commit", "-q", "-m", "cierre: demo — texto", comprobar=False)
    assert rechazado.returncode != 0
    assert "verificar.py todo" in rechazado.stderr

    # Con el recibo del HEAD, un cierre que toca código sigue rechazado: solo valen las rutas de proceso.
    recibo.registrar_head(raiz, recibo.head_completo(raiz), ALCANCE)
    fuera = git(raiz, "commit", "-q", "-m", "cierre: demo — texto", comprobar=False)
    assert fuera.returncode != 0 and "z.txt" in fuera.stderr
    git(raiz, "rm", "-q", "--cached", "z.txt")
    preparar(raiz, "docs/estado.md")
    aceptado = git(raiz, "commit", "-q", "-m", "cierre: demo — texto", comprobar=False)
    assert aceptado.returncode == 0, aceptado.stderr

    # Rama vieja: sin commit_msg.py en el toplevel el hook deja pasar todo salvo los `cierre:`.
    (destino / "commit_msg.py").unlink()
    preparar(raiz, "w.txt")
    assert git(raiz, "commit", "-q", "-m", "cierre: demo", comprobar=False).returncode != 0
    assert git(raiz, "commit", "-q", "-m", "T2: otra cosa", comprobar=False).returncode == 0


def test_hook_sin_commit_msg_py_rechaza_cierre(raiz):
    instalar_hook(raiz, con_commit_msg=False)
    preparar(raiz, "w.txt")
    for mensaje in ("cierre: demo", "cierre:demo — texto", "  cierre: demo"):
        rechazado = git(raiz, "commit", "-q", "-m", mensaje, comprobar=False)
        assert rechazado.returncode != 0, mensaje
        assert "commit_msg.py" in rechazado.stderr
    for mensaje in ("T1: algo", "docs: cierre: demo"):
        pasa = git(raiz, "commit", "-q", "--allow-empty", "-m", mensaje, comprobar=False)
        assert pasa.returncode == 0, pasa.stderr


def test_hook_invoca_python_aislado(raiz):
    """P-metodo-v2-25: un `subprocess.py` junto a los hooks no reemplaza al de la biblioteca estándar."""
    assert "py -3 -I" in (DIR_HOOKS / "commit-msg").read_text(encoding="utf-8")
    destino = instalar_hook(raiz)
    # Si se importara este módulo, el hook saldría con 0 y el cierre pasaría sin recibo.
    (destino / "subprocess.py").write_text("import sys" + chr(10) + "sys.exit(0)" + chr(10),
                                           encoding="utf-8", newline=chr(10))
    preparar(raiz, "docs/estado.md")
    rechazado = git(raiz, "commit", "-q", "-m", "cierre: demo", comprobar=False)
    assert rechazado.returncode != 0
    assert "verificar.py todo" in rechazado.stderr


def test_cierre_tras_linea_en_blanco_se_controla(raiz, tmp_path, capsys):
    """P-metodo-v2-26: las líneas en blanco iniciales no esconden un `cierre:`."""
    codigo, error = correr(raiz, tmp_path, chr(10) + "  " + chr(10) + "cierre: demo" + chr(10), capsys)
    assert codigo == 1
    assert "verificar.py todo" in error
    # El fallback del hook (sin commit_msg.py) tampoco se saltea con `--cleanup=verbatim`.
    instalar_hook(raiz, con_commit_msg=False)
    mensaje = tmp_path / "verbatim.txt"
    mensaje.write_text(chr(10) + "cierre: demo" + chr(10), encoding="utf-8", newline=chr(10))
    preparar(raiz, "w.txt")
    rechazado = git(raiz, "commit", "-q", "--cleanup=verbatim", "-F", str(mensaje), comprobar=False)
    assert rechazado.returncode != 0
    assert "commit_msg.py" in rechazado.stderr


def test_cierre_con_recibo_de_cierre_en_plan_completo_se_rechaza(raiz, tmp_path, capsys):
    recibo.registrar_head(raiz, recibo.head_completo(raiz), "cierre")
    codigo, error = correr(raiz, tmp_path, "cierre: demo\n", capsys)
    assert codigo == 1
    assert "alcance «todo 2026-11-13-demo.md»" in error
    # En un plan ligero, en cambio, el recibo que vale es el de `cierre`.
    (raiz / PLAN).write_text("# Plan: demo\n\n- **ruta**: ligero\n", encoding="utf-8", newline=chr(10))
    assert correr(raiz, tmp_path, "cierre: demo\n", capsys) == (0, "")


def test_cierre_con_todo_de_otro_plan_se_rechaza(raiz, tmp_path, capsys):
    recibo.registrar_head(raiz, recibo.head_completo(raiz), "todo 2026-11-13-otro.md")
    codigo, error = correr(raiz, tmp_path, "cierre: demo\n", capsys)
    assert codigo == 1 and "todo 2026-11-13-demo.md" in error
    # Un plan cuyo slug solo termina igual (`hosts-demo`) no es el plan de `demo`.
    ajeno = raiz / "docs" / "planes" / "2026-11-13-hosts-demo.md"
    ajeno.write_text("# Plan: hosts-demo\n", encoding="utf-8", newline=chr(10))
    recibo.registrar_head(raiz, recibo.head_completo(raiz), "todo 2026-11-13-hosts-demo.md")
    codigo, error = correr(raiz, tmp_path, "cierre: demo\n", capsys)
    assert codigo == 1 and "todo 2026-11-13-demo.md" in error
    recibo.registrar_head(raiz, recibo.head_completo(raiz), ALCANCE)
    assert correr(raiz, tmp_path, "cierre: demo\n", capsys) == (0, "")


def test_cierre_con_rutas_fuera_de_proceso_se_rechaza(raiz, tmp_path, capsys):
    recibo.registrar_head(raiz, recibo.head_completo(raiz), ALCANCE)
    for ruta in ("docs/planes/2026-11-13-demo.md", "docs/estado.md", "docs/bitacora.md", "docs/decisiones.md",
                 "docs/metodo/incidentes.md"):
        preparar(raiz, ruta)
    assert correr(raiz, tmp_path, "cierre: demo\n", capsys) == (0, "")
    for fuera in ("apps/modelo.py", "docs/otro.md", "docs/estado.md.bak", ".claude/hooks/x.py"):
        preparar(raiz, fuera)
        codigo, error = correr(raiz, tmp_path, "cierre: demo\n", capsys)
        assert codigo == 1 and fuera in error, fuera
        git(raiz, "rm", "-q", "--cached", fuera)
    assert correr(raiz, tmp_path, "cierre: demo\n", capsys) == (0, "")
