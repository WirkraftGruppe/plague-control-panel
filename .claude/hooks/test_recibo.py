"""Tests de `recibo.py`: HEAD, test nuevo, recibo por secciones e índice de HEAD.

    py -3 -m pytest .claude/hooks/test_recibo.py -q

Todo corre en directorios y repos git temporales (`tmp_path`).
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recibo  # noqa: E402


def git(directorio, *args):
    """Corre git en `directorio` y devuelve su stdout."""
    return subprocess.run(
        ["git", "-C", str(directorio), *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def repo_con(directorio, archivos: dict):
    """Crea un repo con `archivos` (ruta → texto) commiteados; devuelve el hash completo."""
    directorio.mkdir(parents=True, exist_ok=True)
    git(directorio, "init", "-q")
    git(directorio, "config", "user.email", "t@t")
    git(directorio, "config", "user.name", "t")
    git(directorio, "config", "commit.gpgsign", "false")
    for ruta, texto in archivos.items():
        escribir(directorio / ruta, texto)
    return commitear(directorio)


def commitear(directorio):
    """Agrega todo y commitea; devuelve el hash completo."""
    git(directorio, "add", "-A")
    git(directorio, "commit", "-q", "-m", "c")
    return git(directorio, "rev-parse", "HEAD")


def escribir(ruta, texto):
    """Escribe `texto` en `ruta` creando los padres."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")


VIEJO = "class T:\n    def test_viejo(self):\n        pass\n"
NUEVO = VIEJO + "    def test_nuevo(self):\n        pass\n"
CMD_DJANGO = (
    "PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe "
    "manage.py test apps.x.tests.test_a.T.{} --keepdb"
)


def test_head_devuelve_hash_corto_del_toplevel(tmp_path):
    completo = repo_con(tmp_path, {"a.txt": "a"})
    (tmp_path / "sub").mkdir()
    resultado = recibo.head(tmp_path / "sub")
    assert 4 <= len(resultado) < len(completo)
    assert completo.startswith(resultado)
    assert recibo.head(tmp_path / "no_existe") is None


def test_es_nuevo_django_sin_def_en_base(tmp_path):
    base = repo_con(tmp_path, {"apps/x/tests/test_a.py": VIEJO})
    escribir(tmp_path / "apps/x/tests/test_a.py", NUEVO)
    assert recibo.test_es_nuevo(tmp_path, base, CMD_DJANGO.format("test_nuevo")) is True
    # Un archivo que no existía en la base también es nuevo.
    escribir(tmp_path / "apps/x/tests/test_b.py", "def test_z(): pass\n")
    assert recibo.test_es_nuevo(tmp_path, base, "manage.py test apps.x.tests.test_b.test_z") is True
    assert recibo.test_es_nuevo(tmp_path, base, "echo hola") is None


def test_es_nuevo_django_con_def_en_base_es_falso(tmp_path):
    base = repo_con(tmp_path, {"apps/x/tests/test_a.py": VIEJO})
    assert recibo.test_es_nuevo(tmp_path, base, CMD_DJANGO.format("test_viejo")) is False


def test_es_nuevo_pytest_funcion_nueva(tmp_path):
    base = repo_con(tmp_path, {".claude/hooks/test_h.py": "def test_h_viejo(): pass\n"})
    escribir(tmp_path / ".claude/hooks/test_h.py", "def test_h_viejo(): pass\ndef test_h_nuevo(): pass\n")
    comando = "py -3 -m pytest .claude/hooks/test_h.py::test_h_nuevo -q"
    assert recibo.test_es_nuevo(tmp_path, base, comando) is True
    con_clase = "pytest .claude/hooks/test_h.py::Clase::test_otro"
    assert recibo.test_es_nuevo(tmp_path, base, con_clase) is True


def test_es_nuevo_pytest_funcion_preexistente_es_falso(tmp_path):
    base = repo_con(tmp_path, {".claude/hooks/test_h.py": "class C:\n    def test_h_viejo(self): pass\n"})
    comando = "py -3 -m pytest .claude/hooks/test_h.py::C::test_h_viejo -q"
    assert recibo.test_es_nuevo(tmp_path, base, comando) is False


def test_escribir_y_leer_recibo_por_secciones(tmp_path):
    ruta = tmp_path / "docs" / "planes" / "p.recibo.md"
    assert recibo.leer_recibo(ruta) == []
    seccion = {
        "fecha": "2026-11-13 10:00",
        "alcance": "T1",
        "head": "abc1234",
        "contrato": "intacto",
        "criterios": [
            {"comando": "true", "pasa": True, "exit": 0, "nuevo": None, "salida": ""},
            {"comando": "false", "pasa": False, "exit": 1, "nuevo": True,
             "salida": "\n".join(f"linea {i}" for i in range(40))},
            {"comando": "otro", "pasa": True, "previo": "2026-11-01 09:00"},
        ],
        "duracion": 3.5,
        "veredicto": "FALLA",
    }
    recibo.escribir_recibo(ruta, seccion)
    recibo.escribir_recibo(ruta, dict(seccion, alcance="T2", veredicto="PASA"))
    texto = ruta.read_text(encoding="utf-8")
    assert "linea 39" in texto and "linea 10" in texto and "linea 9\n" not in texto
    secciones = recibo.leer_recibo(ruta)
    assert [s["alcance"] for s in secciones] == ["T1", "T2"]
    assert secciones[0]["head"] == "abc1234"
    assert secciones[0]["contrato"] == "intacto"
    # La salida de la FALLA está en un bloque de código y no aparece como línea de criterio.
    assert secciones[0]["lineas"] == [
        {"pasa": True, "previo": None, "comando": "true"},
        {"pasa": False, "previo": None, "comando": "false"},
        {"pasa": True, "previo": "2026-11-01 09:00", "comando": "otro"},
    ]


def test_indice_registra_head_y_conserva_50(tmp_path):
    for i in range(60):
        recibo.registrar_head(tmp_path, f"h{i}")
    datos = json.loads((tmp_path / ".claude" / ".recibos.json").read_text(encoding="utf-8"))
    assert len(datos) == 50
    assert datos[-1] == "h59" and datos[0] == "h10"
    assert recibo.head_tiene_recibo(tmp_path, "h59")
    assert not recibo.head_tiene_recibo(tmp_path, "h0")
    # Registrar de nuevo un HEAD no lo duplica.
    recibo.registrar_head(tmp_path, "h59")
    assert len(recibo._leer_indice(tmp_path)) == 50


def test_head_sin_registrar_no_tiene_recibo(tmp_path):
    assert not recibo.head_tiene_recibo(tmp_path, "aaa1234")
    recibo.registrar_head(tmp_path, "aaa1234567")
    assert recibo.head_tiene_recibo(tmp_path, "aaa1234")  # prefijo
    assert not recibo.head_tiene_recibo(tmp_path, "bbb1234")
    assert not recibo.head_tiene_recibo(tmp_path, "")
