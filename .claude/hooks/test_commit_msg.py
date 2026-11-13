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
    recibo.registrar_head(raiz, recibo.head(raiz))
    assert correr(raiz, tmp_path, "cierre: demo\n\nTodo verde.\n", capsys) == (0, "")


def test_cierre_con_recibo_de_otro_head_se_rechaza(raiz, tmp_path, capsys):
    recibo.registrar_head(raiz, "0000000")
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


def test_hook_instalado_en_repo_temporal_rechaza_y_acepta(raiz):
    # Se instala el hook y sus dependencias solo en el repo temporal.
    destino = raiz / ".claude" / "hooks"
    destino.mkdir(parents=True)
    for nombre in ("commit_msg.py", "recibo.py"):
        shutil.copy(DIR_HOOKS / nombre, destino / nombre)
    gancho = raiz / ".git" / "hooks" / "commit-msg"
    gancho.write_bytes((DIR_HOOKS / "commit-msg").read_bytes())
    gancho.chmod(0o755)

    (raiz / "y.txt").write_text("y\n", encoding="utf-8", newline="\n")
    git(raiz, "add", "y.txt")
    git(raiz, "commit", "-q", "-m", "T1: algo")  # mensaje común: pasa

    (raiz / "z.txt").write_text("z\n", encoding="utf-8", newline="\n")
    git(raiz, "add", "z.txt")
    rechazado = git(raiz, "commit", "-q", "-m", "cierre: demo — texto", comprobar=False)
    assert rechazado.returncode != 0
    assert "verificar.py todo" in rechazado.stderr

    # El índice de recibos no se versiona en el repo temporal: se registra el HEAD actual.
    recibo.registrar_head(raiz, recibo.head(raiz))
    aceptado = git(raiz, "commit", "-q", "-m", "cierre: demo — texto", comprobar=False)
    assert aceptado.returncode == 0, aceptado.stderr

    # Rama vieja: sin commit_msg.py en el toplevel el hook deja pasar.
    (destino / "commit_msg.py").unlink()
    (raiz / "w.txt").write_text("w\n", encoding="utf-8", newline="\n")
    git(raiz, "add", "w.txt")
    assert git(raiz, "commit", "-q", "-m", "cierre: demo", comprobar=False).returncode == 0
