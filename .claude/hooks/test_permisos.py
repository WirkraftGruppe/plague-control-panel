"""Tests de `.claude/hooks/permisos.py` y del bloque `permissions` y los hooks de `settings.json`.

    py -3 -m pytest .claude/hooks/test_permisos.py -q
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import permisos

DIR_HOOKS = Path(__file__).resolve().parent
PRE_PUSH = DIR_HOOKS / "pre-push"
CEROS = "0" * 40

DENY_MINIMO = [
    "Read(**/.env)",
    "Bash(gh pr merge*)",
    "Bash(git push --force*)",
    "Bash(git push *--no-verify*)",
    "Bash(git stash*)",
    "Bash(git -c *)",
    "Bash(railway variables*)",
    "Edit(**/.git/hooks/**)",
    "Edit(.claude/settings.json)",
    "Edit(.claude/settings.local.json)",
    "Edit(.claude/hooks/permisos.py)",
    "Edit(.claude/hooks/guardia_bash.py)",
    "Edit(.claude/hooks/pre-push)",
]


class TestPermisos(unittest.TestCase):
    def test_settings_coincide_con_permisos_py(self):
        actual = json.loads(permisos.SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(actual["permissions"], permisos.generar(actual)["permissions"])

    def test_bash_libre_ask_vacio_y_ediciones_aceptadas(self):
        actual = json.loads(permisos.SETTINGS.read_text(encoding="utf-8"))["permissions"]
        self.assertEqual(actual["allow"], ["Bash"])
        self.assertEqual(actual["ask"], [])
        self.assertEqual(actual["defaultMode"], "acceptEdits")

    def test_deny_protege_merge_historia_secretos_y_permisos(self):
        for regla in DENY_MINIMO:
            with self.subTest(regla=regla):
                self.assertIn(regla, permisos.DENY)

    def test_env_de_ejemplo_queda_legible(self):
        self.assertNotIn("Read(**/.env.*)", permisos.DENY)

    def test_push_de_ramas_y_pr_no_estan_negados(self):
        for regla in permisos.DENY:
            with self.subTest(regla=regla):
                self.assertNotIn(regla, {"Bash(git push*)", "Bash(git push *)", "Bash(gh pr create*)", "Bash(gh *)"})

    def test_limpiar_local_saca_bash_y_conserva_mcp(self):
        local = {"permissions": {"allow": ["Bash(git mv *)", "mcp__railway__whoami", "Skill(use-railway)"]}}
        self.assertEqual(
            permisos.limpiar_local(local)["permissions"]["allow"], ["mcp__railway__whoami", "Skill(use-railway)"]
        )

    def test_generar_conserva_hooks_y_env(self):
        settings = {"env": {"A": "1"}, "hooks": {"Stop": []}, "permissions": {"allow": ["Bash(ls*)"]}}
        generado = permisos.generar(settings)
        self.assertEqual(generado["env"], {"A": "1"})
        self.assertEqual(generado["hooks"], {"Stop": []})
        self.assertNotIn("defaultMode", generado["permissions"])

    def test_settings_registra_la_guardia_y_el_cierre_liviano(self):
        hooks = json.loads(permisos.SETTINGS.read_text(encoding="utf-8"))["hooks"]
        guardia = hooks["PreToolUse"][0]
        self.assertIn("Bash", guardia["matcher"])
        self.assertIn("guardia_bash.py", guardia["hooks"][0]["command"])
        cierre = hooks["Stop"][0]["hooks"][0]
        self.assertIn("verificar_plan.py --aviso", cierre["command"])


def entrada_de_git(lineas):
    """Bytes que git manda por stdin al hook pre-push: las líneas tal cual, con `\n` y sin `\r`."""
    return "".join(lineas).encode("utf-8")


def test_entrada_de_git_no_lleva_retorno_de_carro():
    # Con `text=True` Windows convierte `\n` en `\r\n` y el `\r` queda pegado al último campo.
    entrada = entrada_de_git(["refs/heads/a 1 refs/heads/a 0\n", "refs/heads/b 2 refs/heads/b 0\n"])
    assert isinstance(entrada, bytes)
    assert b"\r" not in entrada
    assert entrada.count(b"\n") == 2


def correr_pre_push(remoto, lineas, repo):
    """Ejecuta el hook pre-push con el remoto y las líneas de refs que le pasaría git."""
    p = subprocess.run(
        ["bash", PRE_PUSH.as_posix(), remoto, "https://example.invalid/repo.git"],
        input=entrada_de_git(lineas), capture_output=True, cwd=repo, timeout=60,
    )
    p.stdout = p.stdout.decode("utf-8", errors="replace")
    p.stderr = p.stderr.decode("utf-8", errors="replace")
    return p


class TestPrePush(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = cls.tmp.name

        def git(*args):
            return subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                cwd=cls.repo, capture_output=True, text=True, check=True,
            ).stdout.strip()

        git("init", "-q")
        git("commit", "-q", "--allow-empty", "-m", "uno")
        cls.uno = git("rev-parse", "HEAD")
        git("commit", "-q", "--allow-empty", "-m", "dos")
        cls.dos = git("rev-parse", "HEAD")
        git("checkout", "-q", "--orphan", "otra")
        git("commit", "-q", "--allow-empty", "-m", "sin relación")
        cls.suelto = git("rev-parse", "HEAD")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_rama_nueva_a_origin_pasa(self):
        p = correr_pre_push("origin", [f"refs/heads/plan/x {self.dos} refs/heads/plan/x {CEROS}\n"], self.repo)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_avance_normal_pasa(self):
        p = correr_pre_push("origin", [f"refs/heads/plan/x {self.dos} refs/heads/plan/x {self.uno}\n"], self.repo)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_push_a_main_se_rechaza(self):
        p = correr_pre_push("origin", [f"refs/heads/plan/x {self.dos} refs/heads/main {self.uno}\n"], self.repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("push directo a 'main'", p.stderr)

    def test_push_forzado_se_rechaza(self):
        p = correr_pre_push("origin", [f"refs/heads/plan/x {self.suelto} refs/heads/plan/x {self.dos}\n"], self.repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("push forzado", p.stderr)

    def test_otro_remoto_se_rechaza(self):
        p = correr_pre_push("macontrol-viejo", [f"refs/heads/plan/x {self.dos} refs/heads/plan/x {CEROS}\n"], self.repo)
        self.assertEqual(p.returncode, 1)
        self.assertIn("Solo se sube a 'origin'", p.stderr)

    def test_borrar_una_rama_que_no_es_main_pasa(self):
        p = correr_pre_push("origin", [f"(delete) {CEROS} refs/heads/plan/vieja {self.uno}\n"], self.repo)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
