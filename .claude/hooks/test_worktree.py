"""Tests de `worktree-crear.sh` y `worktree-integrar.sh` (T2 de docs/planes/2026-10-02-paralelismo.md).

Se ejecutan con pytest:
    py -3 -m pytest .claude/hooks/test_worktree.py -q

Cada test trabaja sobre un repo git temporal con un `manage.py` de juguete y un `venv` que es una
junction al `venv` REAL del proyecto. Seguridad: el teardown quita primero todas las junctions con
`os.rmdir` (que solo borra el enlace) y recién después borra el árbol temporal, de modo que nunca
se borra contenido del `venv` real.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

DIR_HOOKS = Path(__file__).resolve().parent
CREAR = DIR_HOOKS / "worktree-crear.sh"
INTEGRAR = DIR_HOOKS / "worktree-integrar.sh"
VENV_REAL = DIR_HOOKS.parent.parent / "venv"

MANAGE_JUGUETE = (
    "import sys\n"
    "open('humo.txt', 'w').write(sys.executable + ' ' + ' '.join(sys.argv[1:]))\n"
)


def texto(bytes_):
    """Decodifica una salida como UTF-8, sustituyendo lo que no se pueda decodificar."""
    return bytes_.decode("utf-8", errors="replace")


def git(repo, *argumentos):
    """Ejecuta git en el repo temporal y falla el test si git falla."""
    proceso = subprocess.run(["git", "-C", str(repo), *argumentos], capture_output=True, timeout=60)
    if proceso.returncode != 0:
        raise AssertionError(f"git {argumentos} falló: {texto(proceso.stderr)}")
    return texto(proceso.stdout)


def hacer_junction(enlace, destino):
    """Crea una junction `enlace` -> `destino` con mklink /J."""
    proceso = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(enlace), str(destino)], capture_output=True, timeout=60
    )
    assert proceso.returncode == 0, texto(proceso.stdout) + texto(proceso.stderr)


def quitar_junctions(raiz):
    """Quita las junctions `venv` de la raíz y de cada worktree sin tocar el destino."""
    candidatos = [raiz / "venv"]
    carpeta = raiz / "worktrees"
    if carpeta.is_dir():
        candidatos += [wt / "venv" for wt in carpeta.iterdir()]
    for candidato in candidatos:
        if os.path.lexists(candidato):
            try:
                os.rmdir(candidato)  # en una junction borra solo el enlace; un directorio real con contenido falla
            except OSError:
                pass


@pytest.fixture
def repo(tmp_path):
    """Repo temporal en `main` con manage.py de juguete y venv como junction al venv real."""
    if not (VENV_REAL / "Scripts" / "python.exe").exists():
        pytest.skip("no existe el venv real del proyecto")
    raiz = tmp_path / "raiz"
    raiz.mkdir()
    git(raiz, "init", "-q", "-b", "main")
    git(raiz, "config", "core.autocrlf", "false")
    git(raiz, "config", "user.name", "Test")
    git(raiz, "config", "user.email", "test@example.invalid")
    git(raiz, "config", "commit.gpgsign", "false")
    (raiz / ".gitignore").write_text("worktrees/\nvenv\n*.sqlite3\nhumo.txt\n")
    (raiz / "manage.py").write_text(MANAGE_JUGUETE)
    git(raiz, "add", "-A")
    git(raiz, "commit", "-q", "-m", "base")
    hacer_junction(raiz / "venv", VENV_REAL)
    try:
        yield raiz
    finally:
        quitar_junctions(raiz)
        shutil.rmtree(tmp_path, ignore_errors=True)
        assert (VENV_REAL / "Scripts" / "python.exe").exists()


def correr(script, raiz, *args):
    """Ejecuta un script del hook con bash, con cwd en la raíz temporal."""
    return subprocess.run(
        ["bash", script.as_posix(), *args], cwd=str(raiz), capture_output=True, timeout=300
    )


def crear(raiz, slug="demo", tarea="T1"):
    proceso = correr(CREAR, raiz, slug, tarea)
    assert proceso.returncode == 0, texto(proceso.stdout) + texto(proceso.stderr)
    return raiz / "worktrees" / f"{slug}-{tarea}"


def commitear_archivo(wt, nombre, contenido="x\n"):
    (wt / nombre).write_text(contenido)
    git(wt, "add", "-A")
    git(wt, "commit", "-q", "-m", f"agrega {nombre}")


def test_crear_hace_junction_de_venv(repo):
    wt = crear(repo)
    assert (wt / "venv" / "Scripts" / "python.exe").exists()
    assert git(repo, "branch", "--list", "demo-T1").strip().endswith("demo-T1")


def test_crear_corre_check_de_humo(repo):
    wt = crear(repo)
    marcador = (wt / "humo.txt").read_text()
    assert marcador.endswith("check")
    assert "python" in marcador.lower()


def test_integrar_mergea_rama_limpia_y_borra_worktree(repo):
    wt = crear(repo, "demo", "T5a")
    commitear_archivo(wt, "app.txt")
    proceso = correr(INTEGRAR, repo, "demo", "T5a", "main", "app.txt")
    assert proceso.returncode == 0, texto(proceso.stdout) + texto(proceso.stderr)
    assert (repo / "app.txt").exists()
    assert git(repo, "log", "-1", "--format=%s").strip() == "T5a: integra demo-T5a"
    assert not wt.exists()
    assert git(repo, "branch", "--list", "demo-T5a").strip() == ""
    assert git(repo, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_integrar_rechaza_archivos_fuera_de_alcance(repo):
    wt = crear(repo)
    commitear_archivo(wt, "permitido.txt")
    commitear_archivo(wt, "intruso.txt")
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "permitido.txt")
    assert proceso.returncode == 1
    assert "intruso.txt" in texto(proceso.stderr)
    assert git(repo, "rev-parse", "main").strip() == antes
    assert wt.exists()


def test_integrar_no_borra_el_venv_de_la_raiz(repo):
    wt = crear(repo)
    commitear_archivo(wt, "app.txt")
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "app.txt")
    assert proceso.returncode == 0, texto(proceso.stdout) + texto(proceso.stderr)
    assert (repo / "venv" / "Scripts" / "python.exe").exists()
    assert (VENV_REAL / "Scripts" / "python.exe").exists()


def test_integrar_rechaza_worktree_con_cambios_sin_commitear(repo):
    wt = crear(repo)
    commitear_archivo(wt, "app.txt")
    (wt / "sucio.txt").write_text("sin commitear\n")
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "app.txt", "sucio.txt")
    assert proceso.returncode != 0
    assert git(repo, "rev-parse", "main").strip() == antes
    assert wt.exists()


def test_integrar_rechaza_renombre_desde_fuera_de_alcance(repo):
    (repo / "fuera").mkdir()
    (repo / "fuera" / "x.txt").write_text("contenido protegido\n" * 5)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "archivo fuera de alcance")
    wt = crear(repo)
    (wt / "dentro").mkdir()
    git(wt, "mv", "fuera/x.txt", "dentro/x.txt")
    git(wt, "commit", "-q", "-m", "renombra fuera -> dentro")
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "dentro/")
    assert proceso.returncode != 0
    assert "fuera/x.txt" in texto(proceso.stderr)
    assert git(repo, "rev-parse", "main").strip() == antes
    assert (repo / "fuera" / "x.txt").exists()
    assert wt.exists()


def test_integrar_rechaza_prefijo_vacio(repo):
    wt = crear(repo)
    commitear_archivo(wt, "app.txt")
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "", "app.txt")
    assert proceso.returncode != 0
    assert git(repo, "rev-parse", "main").strip() == antes


def test_integrar_compara_por_segmento(repo):
    wt = crear(repo)
    (wt / "app").mkdir()
    (wt / "app_v2").mkdir()
    commitear_archivo(wt, "app/x.txt")
    commitear_archivo(wt, "app_v2/y.txt")
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "app")
    assert proceso.returncode == 1
    assert "app_v2/y.txt" in texto(proceso.stderr)
    assert git(repo, "rev-parse", "main").strip() == antes


def test_integrar_deshace_merge_si_fallan_tests(repo):
    # manage.py de juguete que falla cuando recibe `test`.
    (repo / "manage.py").write_text(
        MANAGE_JUGUETE + "if 'test' in sys.argv[1:]:\n    sys.exit(1)\n"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "manage.py que falla en test")
    wt = crear(repo)
    (wt / "apps").mkdir()
    commitear_archivo(wt, "apps/app.txt")  # toca apps/: la suite corre (P-metodo-v2-23)
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "apps")
    assert proceso.returncode == 1
    assert git(repo, "rev-parse", "main").strip() == antes
    assert "se deshizo el merge" in texto(proceso.stderr)
    assert not (repo / "apps" / "app.txt").exists()
    assert wt.exists()
    assert git(repo, "branch", "--list", "demo-T1").strip().endswith("demo-T1")


def test_integrar_omite_suite_si_no_toca_django(repo):
    """P-metodo-v2-23: sin cambios en apps/, config/, templates/, manage.py ni requirements.txt no corre `test`."""
    # manage.py de juguete que falla con `test`: si la suite corriera, la integración fallaría.
    (repo / "manage.py").write_text(
        MANAGE_JUGUETE + "if 'test' in sys.argv[1:]:\n    sys.exit(1)\n"
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "manage.py que falla en test")
    wt = crear(repo)
    commitear_archivo(wt, "docs.txt")
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "docs.txt")
    assert proceso.returncode == 0, texto(proceso.stdout) + texto(proceso.stderr)
    assert "se omite la suite de Django" in texto(proceso.stdout)
    assert (repo / "humo.txt").read_text().endswith("makemigrations --check --dry-run")
    assert (repo / "docs.txt").exists()


def test_integrar_rechaza_ruta_que_no_es_worktree(repo):
    # La rama existe con un commit propio, pero worktrees/demo-T1 es un directorio común.
    git(repo, "checkout", "-q", "-b", "demo-T1")
    (repo / "app.txt").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "agrega app.txt")
    git(repo, "checkout", "-q", "main")
    (repo / "worktrees" / "demo-T1").mkdir(parents=True)
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, repo, "demo", "T1", "main", "app.txt")
    assert proceso.returncode == 1
    assert git(repo, "rev-parse", "main").strip() == antes


@pytest.mark.parametrize("rama_base", ["-b", "--orphan", "no-existe"])
def test_crear_rechaza_rama_base_invalida(repo, rama_base):
    proceso = correr(CREAR, repo, "demo", "T1", rama_base)
    assert proceso.returncode == 2, texto(proceso.stdout) + texto(proceso.stderr)
    assert not (repo / "worktrees" / "demo-T1").exists()
    assert git(repo, "branch", "--list", "demo-T1").strip() == ""


def _aborta_con_cwd_en(repo, subcarpeta):
    """Corre integrar con cwd dentro del worktree (o una subcarpeta) y verifica que no tocó nada."""
    wt = crear(repo)
    commitear_archivo(wt, "app.txt")
    cwd = wt / subcarpeta if subcarpeta else wt
    cwd.mkdir(parents=True, exist_ok=True)
    antes = git(repo, "rev-parse", "main").strip()
    proceso = correr(INTEGRAR, cwd, "demo", "T1", "main", "app.txt")
    assert proceso.returncode == 3, texto(proceso.stdout) + texto(proceso.stderr)
    assert "el directorio actual está dentro de" in texto(proceso.stderr)
    assert "salir del worktree antes de integrar" in texto(proceso.stderr)
    assert git(repo, "rev-parse", "main").strip() == antes
    assert not (repo / "app.txt").exists()
    assert wt.exists()
    assert git(repo, "branch", "--list", "demo-T1").strip().endswith("demo-T1")


def test_integrar_aborta_si_cwd_esta_dentro(repo):
    _aborta_con_cwd_en(repo, None)


def test_integrar_aborta_si_cwd_esta_en_subcarpeta_del_worktree(repo):
    _aborta_con_cwd_en(repo, "sub/carpeta")
