"""Tests de `pendientes.py` (consolidado de pendientes por plan)."""
import json
import subprocess
import sys
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
SCRIPT = DIR_HOOKS / "pendientes.py"

CORTE = "## Registro de verificación\n\n(vacío)\n\n## Pendientes que deja este plan\n\n"


def plan(raiz, nombre, problemas="", decisiones="", cierra="", arriba="", etiquetas=""):
    """Escribe docs/planes/<nombre>.md con la sección de pendientes debajo del corte.

    `etiquetas` agrega la subsección `### Etiquetas` (solo si no está vacío).
    """
    carpeta = Path(raiz) / "docs" / "planes"
    carpeta.mkdir(parents=True, exist_ok=True)
    cuerpo = (
        f"# Plan\n\n{arriba}\n{CORTE}"
        f"### Problemas\n\n{problemas}\n### Decisiones\n\n{decisiones}\n### Cierra\n\n{cierra}\n"
    )
    if etiquetas:
        cuerpo += f"### Etiquetas\n\n{etiquetas}\n"
    (carpeta / f"{nombre}.md").write_text(cuerpo, encoding="utf-8")


def correr(raiz, *args, env=None):
    """Ejecuta pendientes.py con --raiz y devuelve el proceso (stdout en bytes)."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--raiz", str(raiz), *args],
        capture_output=True,
        timeout=60,
        env=env,
    )


def como_json(raiz):
    proceso = correr(raiz, "--json")
    assert proceso.returncode == 0, proceso.stderr
    return json.loads(proceso.stdout.decode("utf-8"))


def test_abiertos_son_abiertos_menos_cerrados(tmp_path):
    plan(
        tmp_path,
        "2026-01-01-uno",
        problemas="- P-uno-1 [menor] primero\n- P-uno-2 [importante] segundo\n  sub-viñeta larga\n",
    )
    plan(tmp_path, "2026-01-02-dos", cierra="- cierra: P-uno-1 — se corrigió\n")
    datos = como_json(tmp_path)
    assert [p["id"] for p in datos["abiertos"]] == ["P-uno-2"]
    assert datos["abiertos"][0]["severidad"] == "importante"
    assert "sub-viñeta larga" in datos["abiertos"][0]["texto"]
    assert datos["avisos"] == []


def test_id_duplicado_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [menor] a\n- P-uno-1 [menor] b\n")
    datos = como_json(tmp_path)
    assert any("duplicado" in a and "P-uno-1" in a for a in datos["avisos"])


def test_cierre_de_id_inexistente_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", cierra="- cierra: P-uno-9 — nada\n")
    datos = como_json(tmp_path)
    assert any("inexistente" in a and "P-uno-9" in a for a in datos["avisos"])


def test_id_con_slug_ajeno_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-otro-1 [menor] x\n")
    datos = como_json(tmp_path)
    assert any("slug" in a and "P-otro-1" in a for a in datos["avisos"])


def test_severidad_y_forma_invalida_avisan_con_archivo_y_linea(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [grave] x\nlinea suelta\n")
    datos = como_json(tmp_path)
    assert any("severidad" in a for a in datos["avisos"])
    assert any("2026-01-01-uno.md:" in a and "forma" in a for a in datos["avisos"])


def test_seccion_arriba_del_corte_se_ignora(tmp_path):
    arriba = "## Pendientes que deja este plan\n\n### Problemas\n\n- P-uno-7 [menor] de ejemplo\n"
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [menor] real\n", arriba=arriba)
    datos = como_json(tmp_path)
    assert [p["id"] for p in datos["abiertos"]] == ["P-uno-1"]


def test_sin_planes_sale_con_cero(tmp_path):
    proceso = correr(tmp_path)
    assert proceso.returncode == 0
    assert json.loads(correr(tmp_path, "--json").stdout) == {"abiertos": [], "avisos": []}


def test_json_trae_el_slug_del_plan(tmp_path):
    plan(tmp_path, "2026-10-03-pendientes-heredados", problemas="- P-pendientes-heredados-1 [menor] x\n")
    assert como_json(tmp_path)["abiertos"][0]["plan"] == "pendientes-heredados"


def test_salida_utf8_con_caracteres_fuera_de_cp1252(tmp_path):
    plan(tmp_path, "2026-01-01-uno", problemas="- P-uno-1 [menor] ａｄｍ\n")
    entorno = {"PYTHONIOENCODING": "cp1252", "SYSTEMROOT": r"C:\Windows"}
    proceso = correr(tmp_path, env=entorno)
    assert proceso.returncode == 0
    assert "ａｄｍ" in proceso.stdout.decode("utf-8")


def test_salida_de_texto_agrupa_por_severidad_y_avisos_al_final(tmp_path):
    plan(
        tmp_path,
        "2026-01-01-uno",
        problemas="- P-uno-1 [menor] m\n- P-uno-2 [bloqueante] b\n- P-uno-2 [menor] dup\n",
    )
    salida = correr(tmp_path).stdout.decode("utf-8")
    assert salida.index("P-uno-2") < salida.index("P-uno-1") < salida.index("duplicado")


def test_etiqueta_se_muestra_y_filtra(tmp_path):
    plan(
        tmp_path,
        "2026-01-01-uno",
        problemas="- P-uno-1 [menor] a\n- P-uno-2 [menor] b\n- P-uno-3 [menor] c\n",
    )
    # las etiquetas valen desde cualquier plan, y se aceptan varias por id
    plan(
        tmp_path,
        "2026-01-02-dos",
        etiquetas=(
            "- etiqueta: P-uno-1 → saneamiento\n"
            "- etiqueta: P-uno-1 → despliegue — nota opcional\n"
            "- etiqueta: P-uno-2 → despliegue\n"
        ),
    )
    datos = como_json(tmp_path)
    assert datos["avisos"] == []
    por_id = {p["id"]: p["etiquetas"] for p in datos["abiertos"]}
    assert por_id == {"P-uno-1": ["despliegue", "saneamiento"], "P-uno-2": ["despliegue"], "P-uno-3": []}
    texto = correr(tmp_path).stdout.decode("utf-8")
    assert "- P-uno-1 (uno) [despliegue, saneamiento] a" in texto
    assert "- P-uno-3 (uno) c" in texto
    filtrado = json.loads(correr(tmp_path, "--json", "--etiqueta", "despliegue").stdout.decode("utf-8"))
    assert [p["id"] for p in filtrado["abiertos"]] == ["P-uno-1", "P-uno-2"]
    filtrado_texto = correr(tmp_path, "--etiqueta", "saneamiento").stdout.decode("utf-8")
    assert "P-uno-1" in filtrado_texto and "P-uno-2" not in filtrado_texto


def test_etiqueta_de_id_inexistente_avisa(tmp_path):
    plan(tmp_path, "2026-01-01-uno", etiquetas="- etiqueta: P-uno-9 → despliegue\n")
    datos = como_json(tmp_path)
    assert any(
        "etiqueta de un id inexistente" in a and "P-uno-9" in a and "2026-01-01-uno.md:" in a
        for a in datos["avisos"]
    )


def test_etiqueta_con_forma_invalida_o_destino_repetido_avisa(tmp_path):
    plan(
        tmp_path,
        "2026-01-01-uno",
        problemas="- P-uno-1 [menor] a\n",
        etiquetas=(
            "- etiqueta: P-uno-1 → Despliegue\n"
            "- etiqueta: P-uno-1 despliegue\n"
            "- etiqueta: P-uno-1 → despliegue\n"
            "- etiqueta: P-uno-1 → despliegue — otra vez\n"
        ),
    )
    datos = como_json(tmp_path)
    forma = [a for a in datos["avisos"] if "forma inválida en Etiquetas" in a]
    assert len(forma) == 2 and all("2026-01-01-uno.md:" in a for a in forma)
    assert any("repetid" in a and "P-uno-1" in a and "despliegue" in a for a in datos["avisos"])
    assert datos["abiertos"][0]["etiquetas"] == ["despliegue"]


def test_resumen_cuenta_todo_y_lista_solo_bloqueantes_e_importantes(tmp_path):
    largo = "x" * 400
    plan(
        tmp_path,
        "2026-01-01-demo",
        problemas=(
            "- P-demo-1 [menor] MENOR-DE-JUGUETE\n"
            f"- P-demo-2 [importante] IMPORTANTE {largo}\n"
            "- P-demo-3 [bloqueante] BLOQUEANTE-DE-JUGUETE\n"
            "- P-demo-4 [observación] OBSERVACION-DE-JUGUETE\n"
        ),
    )
    salida = correr(tmp_path, "--resumen").stdout.decode("utf-8")
    lineas = salida.splitlines()
    assert lineas[0] == "Pendientes abiertos: 4 (1 bloqueante, 1 importante, 1 menor, 1 observación)"
    assert lineas[1].startswith("- P-demo-3 [bloqueante] BLOQUEANTE-DE-JUGUETE")
    assert lineas[2].startswith("- P-demo-2 [importante] IMPORTANTE")
    assert lineas[2].endswith("…") and len(lineas[2]) < 200
    assert "MENOR-DE-JUGUETE" not in salida and "OBSERVACION-DE-JUGUETE" not in salida
    assert "Lista completa: py -3 .claude/hooks/pendientes.py" in salida


def test_resumen_corta_la_lista_larga(tmp_path):
    problemas = "".join(f"- P-demo-{n} [importante] texto {n}\n" for n in range(1, 31))
    plan(tmp_path, "2026-01-01-demo", problemas=problemas)
    salida = correr(tmp_path, "--resumen").stdout.decode("utf-8")
    assert salida.count("[importante]") == 10
    assert "… y 20 más entre bloqueantes e importantes" in salida
