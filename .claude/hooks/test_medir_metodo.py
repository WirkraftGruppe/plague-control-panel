"""Tests de `medir_metodo.py` (T7 de docs/planes/2026-11-13-metodo-v2.md).

    py -3 -m pytest .claude/hooks/test_medir_metodo.py -q

Todo ocurre en directorios y repos git temporales (`tmp_path`): no escriben en
`docs/metodo/` real ni leen el `.claude/settings.json` real del proyecto.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_HOOKS))
import medir_metodo  # noqa: E402

SCRIPT = DIR_HOOKS / "medir_metodo.py"
T0 = 1_700_000_000


def git(repo, *argumentos, fecha=None):
    """Ejecuta git en el repo temporal; `fecha` (epoch) fija la fecha del commit."""
    entorno = dict(os.environ)
    if fecha is not None:
        entorno["GIT_COMMITTER_DATE"] = f"{fecha} +0000"
        entorno["GIT_AUTHOR_DATE"] = f"{fecha} +0000"
    proceso = subprocess.run(["git", "-C", str(repo), *argumentos], capture_output=True, env=entorno, timeout=60)
    assert proceso.returncode == 0, proceso.stderr.decode("utf-8", errors="replace")


def preparar_repo(repo):
    """Inicializa un repo temporal con usuario de prueba."""
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "config", "user.name", "Prueba")
    git(repo, "config", "user.email", "prueba@example.invalid")


def commit(repo, asunto, segundos):
    git(repo, "commit", "-q", "--allow-empty", "-m", asunto, fecha=T0 + segundos)


def correr(raiz, *extra):
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
    entorno.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(raiz), *extra],
                          capture_output=True, env=entorno, timeout=120, stdin=subprocess.DEVNULL)


def test_mide_bytes_de_claude_md_y_de_inyeccion(tmp_path):
    (tmp_path / "CLAUDE.md").write_bytes(b"x" * 123)
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    # El hook de inyección imprime 45 bytes.
    (hooks / "contexto.sh").write_bytes(b"cat >/dev/null\nprintf '%045d' 0\n")
    assert medir_metodo.peso_arranque(tmp_path) == (123, 45)
    assert medir_metodo.peso_arranque(tmp_path / "vacio") == (0, 0)


def test_cuenta_agentes(tmp_path):
    agentes = tmp_path / ".claude" / "agents"
    agentes.mkdir(parents=True)
    for nombre in ("a.md", "b.md", "c.md"):
        (agentes / nombre).write_text("x", encoding="utf-8")
    (agentes / "nota.txt").write_text("x", encoding="utf-8")
    assert medir_metodo.contar_agentes(tmp_path) == 3
    assert medir_metodo.contar_agentes(tmp_path / "otro") == 0


def test_registrar_crea_encabezado_y_agrega_fila(tmp_path):
    preparar_repo(tmp_path)
    commit(tmp_path, "docs(plan): demo", 0)
    commit(tmp_path, "registro: demo T1 hecha", 10)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(cmd.exe:*)", "Bash(git status:*)"]}}), encoding="utf-8")
    destino = tmp_path / "docs" / "metodo" / "metricas.md"
    for _ in range(2):
        proceso = correr(tmp_path, "--registrar", "docs/metodo/metricas.md")
        assert proceso.returncode == 0, proceso.stderr.decode("utf-8", errors="replace")
    lineas = destino.read_text(encoding="utf-8").splitlines()
    assert lineas[0] == "# Métricas del método"
    assert sum(1 for linea in lineas if linea.startswith("| Fecha")) == 1
    assert "| Pendientes |" in next(linea for linea in lineas if linea.startswith("| Fecha"))
    filas = [linea for linea in lineas if linea.startswith("| 20")]
    assert len(filas) == 2
    celdas = [c.strip() for c in filas[0].strip("|").split("|")]
    assert celdas[3:7] == ["0", "2.0", "—", "1"]  # sin agentes; 2 de proceso; sin recibo; 1 comodín
    assert filas[0].rstrip().endswith("| — | — | — |")  # sin plan en disco


def test_marca_alto_lo_que_supera_la_meta(tmp_path):
    assert medir_metodo.METAS["claude_md_bytes"] == 8000
    assert medir_metodo.METAS["inyeccion_bytes"] == 6000
    assert medir_metodo.METAS["agentes"] == 3
    assert medir_metodo.METAS["estado_lineas"] == 25
    assert medir_metodo.METAS["estado_bytes"] == 3000
    assert medir_metodo.marca(3000, 3000) == "OK"
    assert medir_metodo.marca(3001, 3000) == "ALTO"
    assert medir_metodo.marca(None, 3000) == "—"
    (tmp_path / "CLAUDE.md").write_bytes(b"x" * 8001)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "estado.md").write_text("ñ" * 1600 + "\n", encoding="utf-8")  # 3201 B
    salida = correr(tmp_path).stdout.decode("utf-8", errors="replace")
    fila_claude = next(linea for linea in salida.splitlines() if linea.startswith("| CLAUDE.md"))
    fila_estado = next(linea for linea in salida.splitlines() if linea.startswith("| Bytes de docs/estado.md"))
    assert fila_claude.rstrip().endswith("ALTO |")
    assert fila_estado.rstrip().endswith("ALTO |")


def test_lee_revisiones_por_modo(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text(
        "- **ruta**: completo\n\n### T1\n- Leer la tabla\n### Revisiones\nde nuevo, en el texto.\n\n"
        "## Registro de verificación\n\n### Revisiones\n\n| Fecha | Modo | Bloqueantes | Decisiones | Menores |\n"
        "|---|---|---|---|---|\n| 2026-11-02 | plan | 5 | 2 | 3 |\n| 2026-11-02 | plan | 1 | 0 | 2 |\n"
        "| 2026-11-03 | cierre | 0 | 0 | 1 |\n\n### Otra\n| x | cierre | 9 | 9 | 9 |\n", encoding="utf-8")
    assert medir_metodo.leer_revisiones(plan) == ("completo", "6/2/5", "0/0/1")
    assert medir_metodo.leer_revisiones(None) == ("—", "—", "—")
    sin_filas = tmp_path / "sin.md"
    sin_filas.write_text("- **ruta**: ligero\n\n### Revisiones\n\n| Fecha | Modo | b | d | m |\n", encoding="utf-8")
    assert medir_metodo.leer_revisiones(sin_filas) == ("ligero", "—", "—")
    invalido = tmp_path / "invalido.md"
    invalido.write_text("### Revisiones\n\n| 2026-11-02 | plan | x | 2 | 3 |\n", encoding="utf-8")
    assert medir_metodo.leer_revisiones(invalido) == ("—", "—", "—")


def test_verificacion_final_sale_del_recibo_y_cuenta_proceso(tmp_path):
    preparar_repo(tmp_path)
    commit(tmp_path, "registro: antes de su plan", 0)
    commit(tmp_path, "docs(plan): demo", 10)
    commit(tmp_path, "T1: código", 20)
    commit(tmp_path, "cierre: demo", 30)
    planes = tmp_path / "docs" / "planes"
    planes.mkdir(parents=True)
    (planes / "demo.recibo.md").write_text(
        "## 2026-11-13 13:00 — todo 2026-11-13-demo.md\n\n- duración: 90 s\n\n"
        "## 2026-11-13 14:00 — todo 2026-11-13-demo.md\n\n- duración: 1260.5 s\n\n"
        "## 2026-11-13 14:30 — tarea T1 de 2026-11-13-demo.md\n\n- duración: 900.0 s\n", encoding="utf-8")
    (fila,) = medir_metodo.medir_planes(medir_metodo.git_log(tmp_path), tmp_path)
    assert (fila["proceso"], fila["verif_min"]) == (2, 21)


def test_permisos_comodin_solo_de_settings_json(tmp_path):
    carpeta = tmp_path / ".claude"
    carpeta.mkdir()
    (carpeta / "settings.json").write_text(
        json.dumps({"permissions": {"allow": ["Bash(py:*)", "Bash(bash -c *)", "Bash(git status:*)", "Read(*)"]}}),
        encoding="utf-8")
    assert len(medir_metodo.permisos_comodin(tmp_path)) == 2
    (carpeta / "settings.json").write_text("{no", encoding="utf-8")
    assert medir_metodo.permisos_comodin(tmp_path) == ["settings.json: JSON inválido"]
