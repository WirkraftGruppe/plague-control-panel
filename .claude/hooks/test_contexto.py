"""Tests del hook SessionStart `contexto.sh` (se invoca con bash)."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

DIR_HOOKS = Path(__file__).resolve().parent
SCRIPT = DIR_HOOKS / "contexto.sh"
FIXTURE = DIR_HOOKS / "fixtures" / "contexto"


def correr_hook(raiz):
    """Ejecuta contexto.sh con CLAUDE_PROJECT_DIR=raiz y devuelve el proceso terminado."""
    entorno = dict(os.environ, CLAUDE_PROJECT_DIR=str(raiz))
    return subprocess.run(
        ["bash", SCRIPT.as_posix()],
        env=entorno,
        capture_output=True,
        timeout=60,
    )


def texto(proceso):
    """Decodifica stdout como UTF-8."""
    return proceso.stdout.decode("utf-8", errors="replace")


class TestContextoHook(unittest.TestCase):
    def test_fixture_completo_imprime_bitacora_plan_estado_y_decisiones_en_orden(self):
        proceso = correr_hook(FIXTURE)
        salida = texto(proceso)
        self.assertEqual(proceso.returncode, 0)
        marcas = [
            "# Bitácora de juguete",
            "ENCABEZADO-DEL-PLAN",
            "### Estado de subtareas",
            "| T1 | pendiente |",
            "DECISION-DE-JUGUETE",
        ]
        posiciones = [salida.find(m) for m in marcas]
        for marca, pos in zip(marcas, posiciones):
            self.assertNotEqual(pos, -1, f"falta {marca!r} en la salida:\n{salida}")
        self.assertEqual(posiciones, sorted(posiciones), salida)
        # Las subtareas y lo posterior a la tabla de estado no se imprimen.
        self.assertNotIn("### T1", salida)
        self.assertNotIn("TEXTO-DE-LA-SUBTAREA", salida)
        self.assertNotIn("TEXTO-DE-CORRIDAS", salida)

    def test_plan_activo_ninguno_no_imprime_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            shutil.copytree(FIXTURE / "docs", raiz / "docs")
            (raiz / "docs" / "bitacora.md").write_text(
                "# Bitácora\n\n## Estado actual\nPlan activo: (ninguno)\n",
                encoding="utf-8",
            )
            proceso = correr_hook(raiz)
            salida = texto(proceso)
            self.assertEqual(proceso.returncode, 0)
            self.assertIn("Plan activo: (ninguno)", salida)
            self.assertNotIn("ENCABEZADO-DEL-PLAN", salida)
            self.assertNotIn("Estado de subtareas", salida)
            self.assertIn("DECISION-DE-JUGUETE", salida)

    def test_directorio_vacio_sale_con_cero_y_sin_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            proceso = correr_hook(tmp)
            self.assertEqual(proceso.returncode, 0)
            self.assertEqual(proceso.stderr, b"")
            self.assertNotIn("Traceback", texto(proceso))

    def test_bitacora_y_plan_con_crlf_funcionan_igual(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            shutil.copytree(FIXTURE / "docs", raiz / "docs")
            for archivo in (raiz / "docs").rglob("*.md"):
                contenido = archivo.read_bytes().replace(b"\r\n", b"\n")
                archivo.write_bytes(contenido.replace(b"\n", b"\r\n"))
            proceso = correr_hook(raiz)
            salida = texto(proceso)
            self.assertEqual(proceso.returncode, 0)
            self.assertIn("ENCABEZADO-DEL-PLAN", salida)
            self.assertIn("| T1 | pendiente |", salida)
            self.assertNotIn("TEXTO-DE-LA-SUBTAREA", salida)
            self.assertNotIn("\r", salida)

    def test_ruta_estilo_windows_en_claude_project_dir(self):
        # Claude Code en Windows pasa la raíz como C:\...; el hook la normaliza con cygpath.
        if shutil.which("cygpath") is None and os.name != "nt":
            self.skipTest("sin cygpath ni Windows")
        proceso = correr_hook(str(FIXTURE))  # en Windows, str() da la forma C:\...
        salida = texto(proceso)
        self.assertEqual(proceso.returncode, 0)
        self.assertIn("ENCABEZADO-DEL-PLAN", salida)
        self.assertIn("DECISION-DE-JUGUETE", salida)


AVISO_IGNORADO = "(Plan activo ignorado: fuera de docs/planes/)"


class TestPlanActivoConfinado(unittest.TestCase):
    """El valor de `Plan activo:` solo se usa si apunta a docs/planes/*.md de la raíz."""

    def setUp(self):
        # Árbol temporal propio: <tmp>/raiz es la raíz del proyecto y <tmp>/secreto.md
        # queda fuera de ella. No se toca fixtures/contexto/.
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.raiz = self.base / "raiz"
        (self.raiz / "docs" / "planes").mkdir(parents=True)
        (self.base / "secreto.md").write_text("SECRETO-XYZ\n", encoding="utf-8")
        (self.raiz / "docs" / "otro.md").write_text("OTRO-SECRETO\n", encoding="utf-8")
        (self.raiz / "docs" / "planes" / "bueno.md").write_text(
            "PLAN-BUENO\n\n### Estado de subtareas\n| T1 | pendiente |\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def correr_con_plan(self, valor):
        """Escribe la bitácora con `Plan activo: valor` y corre el hook."""
        (self.raiz / "docs" / "bitacora.md").write_text(
            f"# Bitácora\n\nPlan activo: {valor}\n", encoding="utf-8"
        )
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 0)
        return texto(proceso)

    def assert_ignorado(self, salida, marca):
        self.assertNotIn(marca, salida)
        self.assertNotIn("=== Plan activo:", salida)
        self.assertIn(AVISO_IGNORADO, salida)

    def test_plan_activo_con_puntos_no_imprime_el_archivo(self):
        for valor in ("../secreto.md", "docs/planes/../../secreto.md", "`../secreto.md`"):
            with self.subTest(valor=valor):
                self.assert_ignorado(self.correr_con_plan(valor), "SECRETO-XYZ")

    def test_plan_activo_fuera_de_docs_planes_no_se_imprime(self):
        # Subcarpeta dentro de docs/planes/: tampoco se acepta.
        (self.raiz / "docs" / "planes" / "sub").mkdir()
        (self.raiz / "docs" / "planes" / "sub" / "x.md").write_text(
            "SUB-SECRETO\n", encoding="utf-8"
        )
        casos = {
            "docs/otro.md": "OTRO-SECRETO",
            "docs/planes/sub/x.md": "SUB-SECRETO",
            "docs\\planes\\bueno.md": "PLAN-BUENO",
            "docs/planes/bueno.txt": "PLAN-BUENO",
        }
        for valor, marca in casos.items():
            with self.subTest(valor=valor):
                self.assert_ignorado(self.correr_con_plan(valor), marca)

    def test_plan_activo_con_ruta_absoluta_no_se_imprime(self):
        secreto = self.base / "secreto.md"
        posix = secreto.as_posix()  # C:/... en Windows, /tmp/... en Unix
        valores = [posix, str(secreto)]
        if len(posix) > 1 and posix[1] == ":":
            valores.append("/" + posix[0].lower() + posix[2:])  # forma /c/...
        valores.append("\\\\servidor\\recurso\\secreto.md")
        for valor in valores:
            with self.subTest(valor=valor):
                self.assert_ignorado(self.correr_con_plan(valor), "SECRETO-XYZ")

    def test_plan_activo_symlink_en_docs_planes_no_se_imprime(self):
        enlace = self.raiz / "docs" / "planes" / "enlace.md"
        try:
            enlace.symlink_to(self.base / "secreto.md")
        except (OSError, NotImplementedError):
            self.skipTest("el sistema no permite crear symlinks")
        # Git Bash sin symlinks nativos puede copiar en vez de enlazar; solo vale si bash lo ve.
        chequeo = subprocess.run(
            ["bash", "-c", f'[ -L "{enlace.as_posix()}" ]'], capture_output=True
        )
        if chequeo.returncode != 0:
            self.skipTest("bash no ve el symlink")
        self.assert_ignorado(self.correr_con_plan("docs/planes/enlace.md"), "SECRETO-XYZ")

    def test_plan_activo_valido_se_imprime_sin_aviso(self):
        salida = self.correr_con_plan("docs/planes/bueno.md")
        self.assertIn("PLAN-BUENO", salida)
        self.assertIn("| T1 | pendiente |", salida)
        self.assertNotIn(AVISO_IGNORADO, salida)

    def test_plan_activo_ninguno_no_muestra_aviso(self):
        self.assertNotIn(AVISO_IGNORADO, self.correr_con_plan("(ninguno)"))


def repo_con_plan_de_rama(raiz, rama):
    """Repo temporal con un plan fechado `demo` y la rama pedida; la bitácora apunta a otro plan."""
    shutil.copytree(FIXTURE / "docs", raiz / "docs")
    planes = raiz / "docs" / "planes"
    (planes / "2026-01-01-demo.md").write_text(
        "PLAN-DE-RAMA\n\n### Estado de subtareas\n| T1 | pendiente |\n", encoding="utf-8"
    )
    (planes / "2026-01-01-demo-dos.md").write_text("PLAN-PARIENTE\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(raiz), "init", "-q", "-b", "main"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(raiz), "switch", "-q", "-c", rama], check=True, capture_output=True)
    return raiz


def test_contexto_elige_plan_por_rama(tmp_path):
    for rama in ("plan/demo", "demo-T2"):
        raiz = repo_con_plan_de_rama(tmp_path / rama.replace("/", "_"), rama)
        salida = texto(correr_hook(raiz))
        assert f"=== Plan activo (por rama {rama}): docs/planes/2026-01-01-demo.md" in salida
        assert "PLAN-DE-RAMA" in salida
        assert "PLAN-PARIENTE" not in salida
        assert "ENCABEZADO-DEL-PLAN" not in salida


def test_contexto_sin_plan_de_rama_usa_bitacora(tmp_path):
    raiz = repo_con_plan_de_rama(tmp_path, "plan/otro")
    salida = texto(correr_hook(raiz))
    assert "=== Plan activo (por bitácora): docs/planes/plan.md" in salida
    assert "ENCABEZADO-DEL-PLAN" in salida
    assert "PLAN-DE-RAMA" not in salida


def test_contexto_inyecta_pendientes(tmp_path):
    planes = tmp_path / "docs" / "planes"
    planes.mkdir(parents=True)
    (planes / "2026-01-01-demo.md").write_text(
        "# Plan\n\n## Registro de verificación\n\n## Pendientes que deja este plan\n\n"
        "### Problemas\n\n- P-demo-1 [importante] PENDIENTE-DE-JUGUETE\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "bitacora.md").write_text("# Bitácora\n", encoding="utf-8")
    proceso = correr_hook(tmp_path)
    salida = texto(proceso)
    assert proceso.returncode == 0
    assert "=== Pendientes abiertos (pendientes.py) ===" in salida
    assert "PENDIENTE-DE-JUGUETE" in salida
    assert salida.index("# Bitácora") < salida.index("=== Pendientes abiertos")


def test_contexto_recorta_lineas_largas_entradas_viejas_y_pendientes_menores(tmp_path):
    planes = tmp_path / "docs" / "planes"
    planes.mkdir(parents=True)
    menores = "".join(f"- P-demo-{n} [menor] MENOR-{n} {'m' * 300}\n" for n in range(1, 41))
    (planes / "2026-01-01-demo.md").write_text(
        "# Plan\n\n" + "".join(f"linea {n} del encabezado\n" for n in range(1, 61)) + "\n### T1 — x\n\n"
        "## Registro de verificación\n\n## Pendientes que deja este plan\n\n### Problemas\n\n"
        + menores + "- P-demo-99 [importante] IMPORTANTE-DE-JUGUETE\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "bitacora.md").write_text(
        "# Bitácora\n\n## Estado actual\nPlan activo: docs/planes/2026-01-01-demo.md\n"
        "Pendiente inmediato: " + "ñ" * 900 + "FIN-DE-LINEA-LARGA\n\n## Entradas (la más reciente arriba)\n\n"
        "### 2026-01-02 — ENTRADA-RECIENTE\n" + "".join(f"- detalle {n}\n" for n in range(1, 31))
        + "\n### 2026-01-01 — ENTRADA-VIEJA\n- algo\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "decisiones.md").write_text(
        "".join(f"- 2026-01-{n:02d} — DECISION-{n} — motivo — reemplaza a: (nada)\n" for n in range(1, 21)),
        encoding="utf-8",
    )
    proceso = correr_hook(tmp_path)
    salida = texto(proceso)
    assert proceso.returncode == 0
    assert "\ufffd" not in salida  # ningún carácter partido al recortar
    assert "ENTRADA-RECIENTE" in salida and "ENTRADA-VIEJA" not in salida
    assert "detalle 11" in salida and "detalle 12" not in salida
    assert "FIN-DE-LINEA-LARGA" not in salida
    assert "linea 14 del encabezado" in salida and "linea 15 del encabezado" not in salida
    assert "líneas más del encabezado en el plan" in salida
    assert "DECISION-20" in salida and "DECISION-16" in salida and "DECISION-15 " not in salida
    assert "IMPORTANTE-DE-JUGUETE" in salida and "MENOR-1 " not in salida
    assert "Pendientes abiertos: 41 (0 bloqueante, 1 importante, 40 menor, 0 observación)" in salida
    assert len(proceso.stdout) < 8000


if __name__ == "__main__":
    unittest.main()
