"""Tests de `revisar_plan.py` (T3 de docs/planes/2026-11-13-metodo-v2.md).

Se ejecutan con pytest: py -3 -m pytest .claude/hooks/test_revisar_plan.py -q
Cada test arma un repo git temporal con un plan y llama a `revisar_plan.main`.
"""
import contextlib
import io
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

DIR_HOOKS = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR_HOOKS))

import revisar_plan  # noqa: E402

FIXTURE = DIR_HOOKS / "fixtures" / "revisar_plan" / "plan_valido.md"
DJANGO = "PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test {} --keepdb"
PYTEST = "py -3 -m pytest .claude/hooks/test_viejo.py::{} -q"
COMPLETO = "- **ruta**: completo\n\n"
LIGERO = "- **ruta**: ligero\n- **seguridad**: no\n\n"


def git(raiz, *args):
    """Corre git en el repo temporal."""
    subprocess.run(["git", "-C", str(raiz), *args], check=True, capture_output=True)


def tarea(numero, puede_tocar="`a.txt`", criterios=("`[cmd]` `true`",), skill=None, depende="—", ola=None, titulo="tarea"):
    """Texto de una subtarea de plan."""
    lineas = [f"### T{numero} — {titulo}", ""]
    if ola is not None:
        lineas += [f"- **Ola**: {ola}", f"- **Depende de**: {depende}"]
    if puede_tocar is not None:
        lineas.append(f"- **Puede tocar**: {puede_tocar}")
    if skill:
        lineas.append(f"- **Skill a leer antes**: {skill}")
    lineas.append("- **Criterios**:")
    lineas += [f"  - {c}" for c in criterios]
    return "\n".join(lineas) + "\n\n"


@pytest.fixture
def raiz(tmp_path):
    """Repo git temporal con tests viejos commiteados."""
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks" / "test_viejo.py").write_text(
        "def test_ya_existia():\n    pass\n\n\nclass Clase:\n    def test_metodo_viejo(self):\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "apps" / "uno" / "tests").mkdir(parents=True)
    (tmp_path / "apps" / "uno" / "tests" / "test_a.py").write_text(
        "class PruebaTests:\n    def test_viejo(self):\n        pass\n", encoding="utf-8"
    )
    (tmp_path / "carpeta").mkdir()
    (tmp_path / "carpeta" / "x.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "presente.txt").write_text("hola\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return tmp_path


def revisar(raiz, cuerpo, encabezado=COMPLETO):
    """Escribe el plan y devuelve (código, salida)."""
    plan = raiz / "plan.md"
    plan.write_text("# Plan: x\n\n" + encabezado + "## Subtareas\n\n" + cuerpo, encoding="utf-8")
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = revisar_plan.main([str(plan), "--raiz", str(raiz)])
    return codigo, salida.getvalue()


def test_tipo_desconocido_es_error(raiz):
    codigo, salida = revisar(raiz, tarea(1, criterios=("`[cmd]` `true`", "`[magia]` `true`")))
    assert codigo == 1
    assert "tipo de criterio desconocido [magia]" in salida


def test_tarea_sin_criterios_es_error(raiz):
    codigo, salida = revisar(raiz, tarea(1, criterios=()))
    assert codigo == 1
    assert "T1: no tiene criterios" in salida


def test_misma_ruta_en_dos_tareas_es_error(raiz):
    codigo, salida = revisar(raiz, tarea(1, "`x/a.py`") + tarea(2, "`x/a.py`"))
    assert codigo == 1
    assert "T1 y T2 se pisan" in salida
    codigo, salida = revisar(raiz, tarea(1, "`x/`") + tarea(2, "`x/sub/a.py`"))
    assert codigo == 1
    assert "x/sub/a.py" in salida
    codigo, _ = revisar(raiz, tarea(1, "`x/a.py`") + tarea(2, "`x/ab.py`"))
    assert codigo == 0


def test_test_preexistente_es_error(raiz):
    viejos = (
        DJANGO.format("apps.uno.tests.test_a.PruebaTests.test_viejo"),
        PYTEST.format("test_ya_existia"),
        PYTEST.format("Clase::test_metodo_viejo"),
    )
    for comando in viejos:
        codigo, salida = revisar(raiz, tarea(1, criterios=(f"`[test]` `{comando}`",)))
        assert codigo == 1, comando
        assert "ya existe en HEAD" in salida
    nuevos = (
        DJANGO.format("apps.uno.tests.test_a.PruebaTests.test_nuevo"),
        DJANGO.format("apps.otra.tests.test_b.Clase.test_x"),
        PYTEST.format("test_nuevo"),
    )
    for comando in nuevos:
        codigo, salida = revisar(raiz, tarea(1, criterios=(f"`[test]` `{comando}`",)))
        assert codigo == 0, salida


def test_test_sin_forma_canonica_es_error(raiz):
    for comando in ("py -3 -m pytest .claude/hooks/test_viejo.py -q", "manage.py test apps.uno"):
        codigo, salida = revisar(raiz, tarea(1, criterios=(f"`[test]` `{comando}`",)))
        assert codigo == 1
        assert "forma canónica" in salida


def test_manage_py_sin_venv_es_error(raiz):
    for comando in ("py -3 manage.py check", "python manage.py check", "cd carpeta && python3 manage.py test"):
        for tipo in ("cmd", "cmd-falla"):
            codigo, salida = revisar(raiz, tarea(1, criterios=(f"`[{tipo}]` `{comando}`",)))
            assert codigo == 1, comando
            assert "manage.py" in salida
    codigo, salida = revisar(raiz, tarea(1, criterios=("`[cmd]` `./venv/Scripts/python.exe manage.py check`",)))
    assert codigo == 0, salida


def test_ligero_con_seguridad_o_mas_de_10_rutas_es_error(raiz):
    rutas = ", ".join(f"`x/a{i}.py`" for i in range(11))
    codigo, salida = revisar(raiz, tarea(1, rutas), LIGERO)
    assert codigo == 1
    assert "11 rutas" in salida
    codigo, salida = revisar(raiz, tarea(1), "- **ruta**: ligero\n- **seguridad**: sí — toca auth\n\n")
    assert codigo == 1
    assert "seguridad" in salida
    for puede_tocar in ("`x/`", "`x/*.py`", "`carpeta`", "`apps/a/migrations/0002_x.py`"):
        codigo, salida = revisar(raiz, tarea(1, puede_tocar), LIGERO)
        assert codigo == 1, puede_tocar
        assert "ruta ligero" in salida
    codigo, salida = revisar(raiz, tarea(1, ", ".join(f"`x/a{i}.py`" for i in range(10))), LIGERO)
    assert codigo == 0, salida


def test_ruta_directo_o_invalida_es_error(raiz):
    for valor in ("directo", "rapido"):
        codigo, salida = revisar(raiz, tarea(1), f"- **ruta**: {valor}\n\n")
        assert codigo == 1
        assert valor in salida
    codigo, salida = revisar(raiz, tarea(1), "")
    assert codigo == 0
    assert "AVISO: el plan no declara `ruta`" in salida


def test_misma_ola_con_migraciones_de_la_misma_app_es_error(raiz):
    codigo, salida = revisar(
        raiz,
        tarea(1, "`apps/visitas/migrations/0002_a.py`", ola=1) + tarea(2, "`apps/visitas/migrations/0003_b.py`", ola=1),
    )
    assert codigo == 1
    assert "migraciones de la app `visitas`" in salida
    codigo, salida = revisar(
        raiz, tarea(1, "`apps/visitas/`", ola=1) + tarea(2, "`apps/*/migrations/0003_b.py`", ola=1)
    )
    assert codigo == 1
    codigo, salida = revisar(
        raiz,
        tarea(1, "`apps/visitas/migrations/0002_a.py`", ola=1) + tarea(2, "`apps/sitios/migrations/0003_b.py`", ola=1),
    )
    assert codigo == 0, salida
    codigo, salida = revisar(raiz, tarea(1, "`a.py`", ola=1) + tarea(2, "`b.py`", ola=1, depende="T1"))
    assert codigo == 1
    assert "T2 depende de T1 pero están en la misma ola (1)" in salida


def test_integracion_del_principal_no_es_error(raiz):
    codigo, salida = revisar(
        raiz,
        tarea(1, "`a.py`", ola=1) + tarea(2, None, ola=1, depende="T1", titulo="Integración ola 1 (principal)"),
    )
    assert codigo == 0, salida


def test_grep_sobre_archivo_inexistente_no_cubierto_es_error(raiz):
    codigo, salida = revisar(raiz, tarea(1, criterios=("`[grep-1]` `grep -n hola nada/no_existe.py`",)))
    assert codigo == 1
    assert "nada/no_existe.py" in salida
    codigo, salida = revisar(
        raiz,
        tarea(1, "`nuevo/creado.py`", ("`[grep-1]` `grep -n hola nuevo/creado.py`",))
        + tarea(2, "`dir/`", ("`[grep-0]` `grep -n hola dir/otro.py`",)),
    )
    assert codigo == 0, salida


def test_skill_inexistente_es_error(raiz):
    codigo, salida = revisar(raiz, tarea(1, skill="`.agents/skills/no-hay/SKILL.md` § X"))
    assert codigo == 1
    assert "no-hay" in salida
    skill = raiz / ".claude" / "skills" / "conv" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("x\n", encoding="utf-8")
    codigo, salida = revisar(raiz, tarea(1, skill="`.agents/skills/conv/SKILL.md`"))
    assert codigo == 1
    assert ".claude/skills/conv/SKILL.md" in salida
    for valida in ("`.claude/skills/conv/SKILL.md` § Y", "—"):
        codigo, salida = revisar(raiz, tarea(1, skill=valida))
        assert codigo == 0, salida


def test_avisos_de_criterios_que_ya_pasan(raiz):
    codigo, salida = revisar(
        raiz,
        tarea(
            1,
            criterios=(
                "`[grep-1]` `grep -q hola presente.txt`",
                "`[existe]` `presente.txt`",
                "`[no-existe]` `ausente.txt`",
                "`[grep-0]` `grep -q zzz presente.txt`",
            ),
        ),
    )
    assert codigo == 0
    assert salida.count("AVISO") == 4


def test_grep_con_metacaracteres_no_se_ejecuta(raiz):
    codigo, salida = revisar(raiz, tarea(1, criterios=("`[grep-1]` `grep hola presente.txt; touch marca.txt`",)))
    assert codigo == 0
    assert not (raiz / "marca.txt").exists()
    assert "no se ejecuta" in salida
    codigo, salida = revisar(raiz, tarea(1, criterios=("`[grep-1]` `rg --pre=sh x presente.txt`",)))
    assert "no se ejecuta" in salida


def test_no_ejecuta_criterios_cmd(raiz):
    comando_test = PYTEST.format("test_nuevo")
    codigo, _ = revisar(
        raiz,
        tarea(
            1,
            criterios=(
                "`[cmd]` `touch marca.txt`",
                "`[cmd-falla]` `touch marca.txt`",
                f"`[test]` `{comando_test} && touch marca.txt`",
                f"`[test]` `{comando_test}`",
            ),
        ),
    )
    assert codigo == 1  # el [test] con `&&` no es canónico, pero nada se ejecutó
    assert not (raiz / "marca.txt").exists()


def test_plan_valido_sale_0(raiz):
    skill = raiz / ".claude" / "skills" / "convenciones-proyecto" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("x\n", encoding="utf-8")
    (raiz / "apps" / "dos").mkdir(parents=True)
    plan = raiz / "plan.md"
    shutil.copy(FIXTURE, plan)
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida):
        codigo = revisar_plan.main([str(plan), "--raiz", str(raiz)])
    assert codigo == 0, salida.getvalue()
    assert "ERROR" not in salida.getvalue()


def test_uso_invalido_sale_2(raiz):
    assert revisar_plan.main([]) == 2
    assert revisar_plan.main([str(raiz / "no_hay.md")]) == 2
    assert revisar_plan.main(["plan.md", "--raiz"]) == 2


def test_archivos_de_grep():
    assert revisar_plan.archivos_de_grep('grep -n "foo bar" apps/a.py') == ["apps/a.py"]
    assert revisar_plan.archivos_de_grep("grep -e uno -e dos a.py") == ["a.py"]
    assert revisar_plan.archivos_de_grep("grep -n x src/*.py") == []
    assert revisar_plan.archivos_de_grep("grep -n x a.py | wc -l") == []
    assert revisar_plan.archivos_de_grep("echo hola") == []


def test_avisa_criterio_que_corre_la_suite_completa(raiz):
    for flags in ("", " --keepdb", " --keepdb --parallel", " -v 2 --noinput --keepdb"):
        comando = f"PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test{flags}"
        codigo, salida = revisar(raiz, tarea(1, criterios=(f"`[cmd]` `{comando}`",)))
        assert codigo == 0, salida
        assert "AVISO: T1: corre la suite completa; usa sus tests nombrados o las apps que toca" in salida, flags


def test_no_avisa_criterio_con_apps_nombradas(raiz):
    for etiquetas in ("apps.uno --keepdb", "--keepdb apps.uno apps.dos", "apps.uno.tests.test_a --keepdb -v 2"):
        comando = f"PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test {etiquetas}"
        codigo, salida = revisar(raiz, tarea(1, criterios=(f"`[cmd]` `{comando}`",)))
        assert codigo == 0, salida
        assert "suite completa" not in salida, etiquetas
    codigo, salida = revisar(raiz, tarea(1, criterios=("`[cmd]` `echo hola`",)))
    assert "suite completa" not in salida
