"""Tests de recibo_pendiente.py (hook Stop liviano, T4 de metodo-v2).

Usan repos git y directorios temporales: nunca leen el docs/estado.md ni el .claude/.recibos.json reales.
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import recibo  # noqa: E402
import recibo_pendiente as rp  # noqa: E402

PLAN = "docs/planes/2026-01-01-demo.md"
SESION = "sesion-1"


def _git(directorio, *args):
    subprocess.run(
        ["git", "-C", str(directorio), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True, capture_output=True,
    )


def _commit(raiz, nombre="a.txt", texto="x"):
    (raiz / nombre).write_text(texto, encoding="utf-8")
    _git(raiz, "add", nombre)
    _git(raiz, "commit", "-m", f"cambio {nombre}")


def _plan(estados, ruta=None):
    filas = "\n".join(f"| T{i} | {e} |" for i, e in enumerate(estados, 1))
    linea_ruta = f"- **ruta**: {ruta}\n" if ruta else ""
    return (f"# Demo\n\n{linea_ruta}\n## Registro de verificación\n\n### Estado de subtareas\n\n"
            f"| Tarea | Estado |\n|---|---|\n{filas}\n")


@pytest.fixture
def entorno(tmp_path):
    """Repo con un commit inicial, directorio de marcas propio y `docs/estado.md` apuntando al plan."""
    raiz = tmp_path / "repo"
    raiz.mkdir()
    _git(raiz, "init", "-b", "main")
    _commit(raiz)
    marcas = tmp_path / "marcas"
    marcas.mkdir()
    (raiz / "docs" / "planes").mkdir(parents=True)
    (raiz / "docs" / "estado.md").write_text(f"Plan activo: {PLAN}\n", encoding="utf-8")
    return raiz, marcas


def _inicio(raiz, marcas, sesion=SESION):
    return rp.registrar_inicio(json.dumps({"session_id": sesion}), raiz, marcas)


def _stop(raiz, marcas, sesion=SESION, **extra):
    err = io.StringIO()
    codigo = rp.ejecutar(json.dumps({"session_id": sesion, **extra}), raiz, marcas, err=err)
    return codigo, err.getvalue()


def _con_plan(raiz, texto):
    (raiz / PLAN).write_text(texto, encoding="utf-8")


def test_inicio_guarda_head_por_sesion_sin_pisar(entorno):
    raiz, marcas = entorno
    inicial = recibo.head(raiz)
    assert _inicio(raiz, marcas) == 0
    archivo = marcas / f"heads_inicio_{SESION}.json"
    assert json.loads(archivo.read_text(encoding="utf-8")) == {"head": inicial}
    _commit(raiz, "b.txt")
    assert _inicio(raiz, marcas) == 0
    assert json.loads(archivo.read_text(encoding="utf-8")) == {"head": inicial}
    assert _inicio(raiz, marcas, sesion="") == 0
    assert len(list(marcas.iterdir())) == 1


def test_sin_commits_en_la_sesion_no_pide_nada(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha"]))
    _inicio(raiz, marcas)
    assert _stop(raiz, marcas) == (0, "")


def test_plan_completo_todas_hechas_sin_recibo_pide_todo(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha", "PASA"], ruta="completo"))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    codigo, err = _stop(raiz, marcas)
    assert codigo == 2
    assert err.startswith("Falta el recibo de verificación: ")
    assert f"verificar.py todo {PLAN}" in err


def test_plan_con_tareas_pendientes_no_pide(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha", "pendiente"], ruta="completo"))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    assert _stop(raiz, marcas) == (0, "")


def test_sin_plan_con_commits_pide_cierre(entorno):
    raiz, marcas = entorno
    (raiz / "docs" / "estado.md").write_text("Plan activo: ninguno\n", encoding="utf-8")
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    codigo, err = _stop(raiz, marcas)
    assert codigo == 2
    assert "verificar.py cierre" in err


def test_plan_ligero_con_commits_pide_cierre(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["pendiente"], ruta="ligero"))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    codigo, err = _stop(raiz, marcas)
    assert codigo == 2
    assert "verificar.py cierre" in err


def test_head_con_recibo_no_pide(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha"]))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    recibo.registrar_head(raiz, recibo.head(raiz))
    assert _stop(raiz, marcas) == (0, "")


def test_avisa_una_vez_por_sesion_y_head(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha"]))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    assert _stop(raiz, marcas)[0] == 2
    assert _stop(raiz, marcas) == (0, "")
    _commit(raiz, "c.txt")
    assert _stop(raiz, marcas)[0] == 2


def test_verificando_reciente_no_pide(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha"]))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    marca = raiz / ".claude" / ".verificando"
    marca.parent.mkdir(exist_ok=True)
    marca.write_text("1", encoding="utf-8")
    assert _stop(raiz, marcas) == (0, "")
    # Un archivo huérfano (más de 2 horas) se ignora.
    viejo = marca.stat().st_mtime - 3 * 3600
    os.utime(marca, (viejo, viejo))
    assert _stop(raiz, marcas)[0] == 2


def test_stop_hook_active_sale_0(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha"]))
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    assert _stop(raiz, marcas, stop_hook_active=True) == (0, "")
    assert rp.ejecutar("no es json", raiz, marcas, err=io.StringIO()) == 0


def test_tabla_v2_de_cuatro_columnas(entorno):
    raiz, marcas = entorno
    texto = ("# Demo\n\n- **ruta**: completo\n\n## Registro de verificación\n\n"
             "| Tarea | Fecha | HEAD | Veredicto |\n|---|---|---|---|\n"
             "| T1 | 2026-01-01 | abc1234 | PASA |\n| T2 | 2026-01-02 | abc1235 | PASA |\n")
    assert rp.todas_hechas(texto)
    assert not rp.todas_hechas(texto.replace("| T2 | 2026-01-02 | abc1235 | PASA |", "| T2 | — | — | FALLA |"))
    _con_plan(raiz, texto)
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    assert _stop(raiz, marcas)[0] == 2


def test_plan_de_la_rama_tiene_prioridad(entorno):
    raiz, marcas = entorno
    (raiz / "docs" / "estado.md").write_text("Plan activo: ninguno\n", encoding="utf-8")
    _con_plan(raiz, _plan(["pendiente"], ruta="completo"))
    _git(raiz, "checkout", "-b", "plan/demo")
    _inicio(raiz, marcas)
    _commit(raiz, "b.txt")
    assert rp.plan_activo(raiz) == PLAN
    assert _stop(raiz, marcas) == (0, "")


def _commit_en(raiz, ruta, texto="x"):
    """Commitea `ruta` (con sus carpetas) y devuelve el HEAD."""
    archivo = raiz / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(texto, encoding="utf-8")
    _git(raiz, "add", ruta)
    _git(raiz, "commit", "-m", f"cambio {ruta}")
    return recibo.head(raiz)


def _codigo_con_recibo(raiz, marcas):
    """Plan completo con todo hecho, sesión iniciada, un commit de código y su recibo en PASA."""
    _con_plan(raiz, _plan(["hecha"], ruta="completo"))
    _inicio(raiz, marcas)
    recibo.registrar_head(raiz, _commit_en(raiz, "apps/a.py"), f"todo {PLAN}")


def test_cierre_solo_con_documentos_tras_un_recibo_no_pide(entorno):
    raiz, marcas = entorno
    _codigo_con_recibo(raiz, marcas)
    for ruta in ("docs/estado.md", "docs/decisiones.md", "docs/bitacora.md",
                 "docs/metodo/metricas.md", "docs/planes/demo.recibo.md"):
        _commit_en(raiz, ruta, f"Plan activo: {PLAN}\ncierre\n")
    assert _stop(raiz, marcas) == (0, "")


def test_codigo_despues_del_recibo_pide(entorno):
    raiz, marcas = entorno
    _codigo_con_recibo(raiz, marcas)
    _commit_en(raiz, "docs/estado.md", f"Plan activo: {PLAN}\nActualizado: cierre\n")
    _commit_en(raiz, "apps/b.py")
    codigo, err = _stop(raiz, marcas)
    assert codigo == 2
    assert f"verificar.py todo {PLAN}" in err


def test_solo_documentos_sin_recibo_previo_pide(entorno):
    raiz, marcas = entorno
    _con_plan(raiz, _plan(["hecha"], ruta="completo"))
    _inicio(raiz, marcas)
    _commit_en(raiz, "docs/estado.md", f"Plan activo: {PLAN}\nActualizado: cierre\n")
    codigo, err = _stop(raiz, marcas)
    assert codigo == 2
    assert f"verificar.py todo {PLAN}" in err


def test_renombre_desde_fuera_de_proceso_pide(entorno):
    raiz, marcas = entorno
    _codigo_con_recibo(raiz, marcas)
    (raiz / "docs" / "metodo").mkdir(parents=True, exist_ok=True)
    _git(raiz, "mv", "apps/a.py", "docs/metodo/a.py")
    _git(raiz, "commit", "-m", "mueve a.py a docs/metodo")
    codigo, err = _stop(raiz, marcas)
    assert codigo == 2
    assert f"verificar.py todo {PLAN}" in err
