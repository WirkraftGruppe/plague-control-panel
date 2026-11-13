"""Tests de los agentes de `.claude/agents/` (T3 de docs/planes/2026-10-04-herramientas-plan.md).

Se ejecutan con pytest:
    py -3 -m pytest .claude/hooks/test_agentes.py -q
"""
from pathlib import Path

import pytest
import yaml

DIR_AGENTES = Path(__file__).resolve().parent.parent / "agents"
ARCHIVOS = sorted(DIR_AGENTES.glob("*.md"))


def leer_frontmatter(ruta):
    """Devuelve el texto YAML entre los dos `---` iniciales del archivo."""
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    assert lineas and lineas[0] == "---", f"{ruta.name}: no empieza con ---"
    fin = lineas.index("---", 1)
    return "\n".join(lineas[1:fin])


def test_hay_agentes():
    assert ARCHIVOS, "no hay agentes en .claude/agents"


@pytest.mark.parametrize("ruta", ARCHIVOS, ids=lambda r: r.name)
def test_frontmatter_de_agentes_es_yaml_valido(ruta):
    datos = yaml.safe_load(leer_frontmatter(ruta))
    assert isinstance(datos, dict), f"{ruta.name}: el frontmatter no es un mapa"
    assert datos.get("name") == ruta.stem, f"{ruta.name}: name no coincide con el archivo"
    descripcion = datos.get("description")
    assert isinstance(descripcion, str) and descripcion.strip(), (
        f"{ruta.name}: description vacía"
    )


def frontmatter(nombre):
    """Frontmatter YAML ya parseado del agente `nombre`."""
    return yaml.safe_load(leer_frontmatter(DIR_AGENTES / f"{nombre}.md"))


def herramientas(datos, clave):
    """Lista de nombres de una clave tipo `Read, Grep` del frontmatter."""
    return [p.strip() for p in str(datos.get(clave, "")).split(",") if p.strip()]


def test_hay_exactamente_tres_agentes():
    nombres = sorted(r.stem for r in ARCHIVOS)
    assert nombres == ["auditor-seguridad", "implementador", "revisor"]


@pytest.mark.parametrize("ruta", ARCHIVOS, ids=lambda r: r.name)
def test_cada_agente_fija_model_effort_y_max_turns(ruta):
    datos = yaml.safe_load(leer_frontmatter(ruta))
    for campo in ("model", "effort", "maxTurns"):
        assert datos.get(campo), f"{ruta.name}: falta {campo}"
    assert isinstance(datos["maxTurns"], int), f"{ruta.name}: maxTurns debe ser entero"


@pytest.mark.parametrize("nombre", ["revisor", "auditor-seguridad"])
def test_revisor_y_auditor_no_editan(nombre):
    datos = frontmatter(nombre)
    declaradas = herramientas(datos, "tools")
    assert declaradas, f"{nombre}: sin tools"
    assert "Edit" not in declaradas and "Write" not in declaradas
    if nombre == "auditor-seguridad":
        assert herramientas(datos, "disallowedTools") == ["Edit", "Write"]


def test_revisor_cita_revisar_plan_py():
    texto = (DIR_AGENTES / "revisor.md").read_text(encoding="utf-8")
    assert "py -3 .claude/hooks/revisar_plan.py" in texto
    assert "verificar.py revisar-plan" not in texto


def test_implementador_nombra_verificar_py_tarea():
    texto = (DIR_AGENTES / "implementador.md").read_text(encoding="utf-8")
    assert "verificar.py tarea" in texto
    assert "Trabajo en un worktree" in texto
