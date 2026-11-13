"""Tests del hook SessionStart `contexto.sh` (método v2; se invoca con bash)."""
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
SCRIPT = DIR_HOOKS / "contexto.sh"
FIXTURE = DIR_HOOKS / "fixtures" / "contexto_v2"

AVISO_IGNORADO = "(Plan activo ignorado: tiene que ser un archivo de docs/planes/)"


def correr_hook(raiz, entrada=None, script=SCRIPT, extra_entorno=None):
    """Ejecuta contexto.sh con CLAUDE_PROJECT_DIR=raiz y devuelve el proceso terminado."""
    entorno = dict(os.environ, CLAUDE_PROJECT_DIR=str(raiz), **(extra_entorno or {}))
    return subprocess.run(
        ["bash", Path(script).as_posix()],
        env=entorno,
        input=entrada if entrada is not None else b"",
        capture_output=True,
        timeout=60,
    )


def texto(proceso):
    """Decodifica stdout como UTF-8."""
    return proceso.stdout.decode("utf-8", errors="replace")


def git(directorio, *args):
    """Corre git en `directorio` con identidad fija; falla el test si git falla."""
    subprocess.run(
        ["git", "-C", str(directorio), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


def crear_raiz(tmp_path, rama="plan/plan-v2"):
    """Copia la fixture v2 en un repo git temporal con un commit, en la rama pedida."""
    raiz = tmp_path / "raiz"
    shutil.copytree(FIXTURE / "docs", raiz / "docs")
    git(raiz, "init", "-q", "-b", rama)
    git(raiz, "add", "docs")
    git(raiz, "commit", "-q", "-m", "primer commit")
    return raiz


def escribir_estado(raiz, contenido):
    (raiz / "docs" / "estado.md").write_text(contenido, encoding="utf-8")


def estado_de(raiz):
    return (raiz / "docs" / "estado.md").read_text(encoding="utf-8")


def test_v2_inyecta_estado_y_no_la_bitacora(tmp_path):
    raiz = crear_raiz(tmp_path)
    proceso = correr_hook(raiz)
    salida = texto(proceso)
    assert proceso.returncode == 0
    marcas = [
        "=== git ===",
        "plan/plan-v2 @",
        "=== worktrees ===",
        "=== docs/estado.md ===",
        "PENDIENTE-DE-JUGUETE",
        "ENCABEZADO-DEL-PLAN",
        "| T1 | pendiente |",
        "DECISION-SEIS",
        "=== pendientes ===",
    ]
    posiciones = [salida.find(m) for m in marcas]
    for marca, pos in zip(marcas, posiciones):
        assert pos != -1, f"falta {marca!r} en la salida:\n{salida}"
    assert posiciones == sorted(posiciones), salida
    # Solo las últimas 5 decisiones; nada del detalle de subtareas ni de corridas ni del registro viejo.
    assert "DECISION-UNO" not in salida
    assert "TEXTO-DE-LA-SUBTAREA" not in salida
    assert "TEXTO-DE-CORRIDAS" not in salida
    assert "TEXTO-DE-LA-BITACORA" not in salida
    assert "Bitácora de juguete" not in salida


def test_v2_salida_recortada_a_6000_bytes(tmp_path):
    raiz = crear_raiz(tmp_path)
    relleno = "".join(f"- ñandú {i} " + "x" * 120 + "\n" for i in range(80))
    escribir_estado(raiz, estado_de(raiz) + relleno)
    git(raiz, "switch", "-q", "-c", "otra/rama")
    proceso = correr_hook(raiz)
    assert proceso.returncode == 0, proceso.stderr
    salida = proceso.stdout.decode("utf-8")  # estricto: no corta un carácter a la mitad
    assert len(proceso.stdout) <= 6000
    assert re.search(r"\(recortado: \d+ bytes; leer docs/estado\.md\)$", salida.rstrip("\n"))
    # Lo importante va primero y sobrevive al recorte.
    assert "DIFERENCIA" in salida
    # Una salida corta no se recorta.
    assert "(recortado" not in texto(correr_hook(crear_raiz(tmp_path / "otro")))


def test_v2_estado_largo_avisa(tmp_path):
    raiz = crear_raiz(tmp_path)
    assert "AVISO" not in texto(correr_hook(raiz))
    escribir_estado(raiz, "# Estado\n" + "".join(f"linea {i}\n" for i in range(30)))
    salida = texto(correr_hook(raiz))
    assert "(AVISO: estado.md tiene 31 líneas; el máximo es 25)" in salida
    assert "bytes; el máximo" not in salida
    escribir_estado(raiz, "# Estado\n" + "".join(f"linea {i} " + "x" * 150 + "\n" for i in range(20)))
    salida = texto(correr_hook(raiz))
    assert re.search(r"AVISO: estado\.md tiene \d+ bytes; el máximo es 3000", salida)
    assert "líneas; el máximo" not in salida


def test_v2_diferencia_de_rama_con_estado(tmp_path):
    raiz = crear_raiz(tmp_path)
    assert "DIFERENCIA" not in texto(correr_hook(raiz))
    # Texto agregado tras el nombre de la rama: solo cuenta el primer token.
    base = estado_de(raiz)
    for agregado in ("plan/plan-v2 (PR #4 abierto)", "plan/plan-v2 en revisión"):
        escribir_estado(raiz, base.replace("| plan/plan-v2 |", f"| {agregado} |"))
        assert "DIFERENCIA" not in texto(correr_hook(raiz))
    escribir_estado(raiz, base)
    git(raiz, "switch", "-q", "-c", "otra/rama")
    salida = texto(correr_hook(raiz))
    assert "DIFERENCIA: estado.md dice 'plan/plan-v2' para plan-v2 y git está en 'otra/rama'" in salida
    assert salida.count("DIFERENCIA") == 1


def test_v2_plan_de_rama_encabezado_y_tabla_v1_y_v2(tmp_path):
    raiz = crear_raiz(tmp_path / "v1", "plan/demo")
    planes = raiz / "docs" / "planes"
    (planes / "2026-01-01-demo.md").write_text(
        "# Plan v1\nPLAN-V1-ENCABEZADO\n\n## Subtareas\n### T1 — x\nCUERPO-V1\n\n"
        "### Estado de subtareas\n\n| Tarea | Estado |\n|---|---|\n| T1 | hecha |\n\n### Otra\nNO-V1\n",
        encoding="utf-8",
    )
    (planes / "2026-01-01-demo-dos.md").write_text("PLAN-PARIENTE\n", encoding="utf-8")
    salida = texto(correr_hook(raiz))
    assert "(por rama plan/demo; encabezado)" in salida
    assert "PLAN-V1-ENCABEZADO" in salida and "### Estado de subtareas" in salida
    assert "| T1 | hecha |" in salida
    for ausente in ("CUERPO-V1", "NO-V1", "PLAN-PARIENTE", "ENCABEZADO-DEL-PLAN"):
        assert ausente not in salida

    # v2 y rama de subtarea <slug>-T<n>: la tabla sale de "## Registro de verificación".
    raiz = crear_raiz(tmp_path / "v2", "demo-T2")
    (raiz / "docs" / "planes" / "2026-01-01-demo.md").write_text(
        "# Plan v2\nPLAN-V2-ENCABEZADO\n\n## Subtareas\nCUERPO-V2\n\n## Registro de verificación\n\n"
        "commit_base: abc\n\n| Tarea | Estado |\n|---|---|\n| T9 | en curso |\n\n### Corridas\nNO-V2\n",
        encoding="utf-8",
    )
    salida = texto(correr_hook(raiz))
    assert "(por rama demo-T2; encabezado)" in salida
    assert "PLAN-V2-ENCABEZADO" in salida and "| T9 | en curso |" in salida
    for ausente in ("CUERPO-V2", "NO-V2", "ENCABEZADO-DEL-PLAN"):
        assert ausente not in salida


def test_v2_plan_activo_como_slug(tmp_path):
    raiz = crear_raiz(tmp_path, "main")
    (raiz / "docs" / "planes" / "2026-01-01-demo.md").write_text("PLAN-POR-SLUG\n", encoding="utf-8")
    escribir_estado(raiz, estado_de(raiz).replace("docs/planes/plan-v2.md", "`demo`"))
    assert "PLAN-POR-SLUG" in texto(correr_hook(raiz))


def test_v2_plan_activo_confinado_a_docs_planes(tmp_path):
    raiz = crear_raiz(tmp_path, "main")
    (tmp_path / "secreto.md").write_text("SECRETO-XYZ\n", encoding="utf-8")
    (raiz / "docs" / "otro.md").write_text("OTRO-SECRETO\n", encoding="utf-8")
    (raiz / "docs" / "planes" / "sub").mkdir()
    (raiz / "docs" / "planes" / "sub" / "x.md").write_text("SUB-SECRETO\n", encoding="utf-8")
    base = estado_de(raiz)
    casos = {
        "docs/planes/../../../secreto.md": "SECRETO-XYZ",
        "docs/planes/../otro.md": "OTRO-SECRETO",
        "docs/planes/sub/x.md": "SUB-SECRETO",
        "docs/otro.md": "OTRO-SECRETO",
        (tmp_path / "secreto.md").as_posix(): "SECRETO-XYZ",
    }
    for valor, marca in casos.items():
        escribir_estado(raiz, base.replace("docs/planes/plan-v2.md", valor))
        salida = texto(correr_hook(raiz))
        assert marca not in salida, valor
        assert "ENCABEZADO-DEL-PLAN" not in salida, valor
        assert AVISO_IGNORADO in salida, valor


def test_v2_plan_activo_symlink_se_ignora(tmp_path):
    raiz = crear_raiz(tmp_path, "main")
    (tmp_path / "secreto.md").write_text("SECRETO-XYZ\n", encoding="utf-8")
    enlace = raiz / "docs" / "planes" / "enlace.md"
    try:
        enlace.symlink_to(tmp_path / "secreto.md")
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("el sistema no permite crear symlinks")
    chequeo = subprocess.run(["bash", "-c", f'[ -L "{enlace.as_posix()}" ]'], capture_output=True)
    if chequeo.returncode != 0:
        import pytest
        pytest.skip("bash no ve el symlink")
    escribir_estado(raiz, estado_de(raiz).replace("docs/planes/plan-v2.md", "docs/planes/enlace.md"))
    salida = texto(correr_hook(raiz))
    assert "SECRETO-XYZ" not in salida
    assert AVISO_IGNORADO in salida


def test_v2_lista_worktrees_con_ruta_relativa(tmp_path):
    raiz = crear_raiz(tmp_path)
    git(raiz, "worktree", "add", "-q", "-b", "demo-T1", str(raiz / "worktrees" / "demo-T1"))
    salida = texto(correr_hook(raiz))
    assert ". [plan/plan-v2]" in salida
    assert "worktrees/demo-T1 [demo-T1]" in salida
    assert raiz.name + "/worktrees" not in salida


def test_v2_llama_recibo_pendiente_inicio_si_existe(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    shutil.copy(SCRIPT, hooks / "contexto.sh")
    shutil.copy(DIR_HOOKS / "pendientes.py", hooks / "pendientes.py")
    registro = tmp_path / "registro.txt"
    # Script falso: anota sus argumentos, la raíz que recibe y lo que llega por stdin.
    (hooks / "recibo_pendiente.py").write_text(
        "import os, sys\n"
        "with open(os.environ['REGISTRO_FALSO'], 'w', encoding='utf-8') as f:\n"
        "    f.write(' '.join(sys.argv[1:]) + '\\n' + os.environ.get('CLAUDE_PROJECT_DIR', '') + '\\n' + sys.stdin.read())\n",
        encoding="utf-8",
    )
    raiz = crear_raiz(tmp_path)
    entorno = {"REGISTRO_FALSO": str(registro)}
    json_hook = b'{"session_id": "sesion-x", "source": "startup"}\n'
    proceso = correr_hook(raiz, entrada=json_hook, script=hooks / "contexto.sh", extra_entorno=entorno)
    assert proceso.returncode == 0, proceso.stderr
    lineas = registro.read_text(encoding="utf-8").splitlines()
    assert lineas[0] == "--inicio"
    assert lineas[1] == str(raiz)
    assert lineas[2] == json_hook.decode().strip()
    assert "sesion-x" not in texto(proceso)  # el registro no imprime nada
    # Sin el script, el hook sigue funcionando y no registra nada.
    (hooks / "recibo_pendiente.py").unlink()
    registro.unlink()
    proceso = correr_hook(raiz, entrada=json_hook, script=hooks / "contexto.sh", extra_entorno=entorno)
    assert proceso.returncode == 0
    assert not registro.exists()


def test_v2_no_se_cuelga_con_stdin_abierto(tmp_path):
    # stdin abierto y sin datos: `read -t 1` debe soltarlo en vez de colgar el hook.
    raiz = crear_raiz(tmp_path)
    entorno = dict(os.environ, CLAUDE_PROJECT_DIR=str(raiz))
    inicio = time.monotonic()
    proceso = subprocess.Popen(
        ["bash", SCRIPT.as_posix()], env=entorno, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        salida = proceso.stdout.read()
        proceso.wait(timeout=20)
    finally:
        proceso.stdin.close()
        proceso.stdout.close()
        proceso.stderr.close()
    assert proceso.returncode == 0
    assert time.monotonic() - inicio < 15
    assert b"=== docs/estado.md ===" in salida


def test_v2_directorio_vacio_sale_con_cero_y_sin_traceback(tmp_path):
    proceso = correr_hook(tmp_path)
    assert proceso.returncode == 0
    assert proceso.stderr == b""
    assert "falta docs/estado.md" in texto(proceso)
    assert "Traceback" not in texto(proceso)


def test_v2_crlf_funciona_igual(tmp_path):
    raiz = crear_raiz(tmp_path)
    for archivo in (raiz / "docs").rglob("*.md"):
        archivo.write_bytes(archivo.read_bytes().replace(b"\n", b"\r\n"))
    salida = texto(correr_hook(raiz))
    assert "ENCABEZADO-DEL-PLAN" in salida
    assert "| T1 | pendiente |" in salida
    assert "\r" not in salida


def test_v2_ruta_estilo_windows_en_claude_project_dir(tmp_path):
    # Claude Code en Windows pasa la raíz como C:\...; el hook la normaliza con cygpath.
    if shutil.which("cygpath") is None and os.name != "nt":
        import pytest
        pytest.skip("sin cygpath ni Windows")
    proceso = correr_hook(str(crear_raiz(tmp_path)))
    assert proceso.returncode == 0
    assert "ENCABEZADO-DEL-PLAN" in texto(proceso)


def test_v2_inyecta_pendientes(tmp_path):
    raiz = crear_raiz(tmp_path)
    (raiz / "docs" / "planes" / "2026-01-01-demo.md").write_text(
        "# Plan\n\n## Registro de verificación\n\n## Pendientes que deja este plan\n\n"
        "### Problemas\n\n- P-demo-1 [importante] PENDIENTE-IMPORTANTE\n- P-demo-2 [menor] PENDIENTE-MENOR\n",
        encoding="utf-8",
    )
    salida = texto(correr_hook(raiz))
    assert "PENDIENTE-IMPORTANTE" in salida and "PENDIENTE-MENOR" not in salida
    assert "Pendientes abiertos: 2 (0 bloqueante, 1 importante, 1 menor, 0 observación)" in salida
