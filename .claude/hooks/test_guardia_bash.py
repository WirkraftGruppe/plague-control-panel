"""Tests de `.claude/hooks/guardia_bash.py`, el hook PreToolUse de Bash.

    py -3 -m pytest .claude/hooks/test_guardia_bash.py -q
"""
import io
import json
import unittest

import guardia_bash

BLOQUEADOS = [
    # fusionar y aprobar
    "gh pr merge 12 --squash",
    "gh -R WirkraftGruppe/plague-control-panel pr merge 12",
    "gh pr review 12 --approve",
    "gh pr review 12 -a -b 'ok'",
    "gh api -X PUT repos/o/r/pulls/12/merge",
    "gh api repos/o/r/pulls/12/merge --method=PUT",
    "gh api repos/o/r/issues -f title=x",
    "gh api graphql -f query='mutation { x }'",
    # push
    "git push --force origin plan/x",
    "git push -f",
    "git push --force-with-lease origin plan/x",
    "git push origin +plan/x",
    "git push origin main",
    "git push origin HEAD:main",
    "git push origin plan/x:refs/heads/master",
    "git push origin --delete main",
    "git push origin :main",
    "git push --no-verify origin plan/x",
    "git push macontrol-viejo plan/x",
    "git push https://github.com/otro/repo.git plan/x",
    "git push --all origin",
    "git -C worktrees/x-T1 push --force origin x-T1",
    # perder o reescribir trabajo
    "git stash",
    "git -C worktrees/x-T1 stash pop",
    "git clean -fd",
    "git reset --hard HEAD~1",
    "git commit --amend -m x",
    "git commit -am 'T1: algo'",
    "git commit --no-verify -m x",
    "git add -A",
    "git add .",
    "git add --all",
    "git branch -D plan/x",
    "git switch -f main",
    "git checkout -f main",
    "git checkout .",
    "git restore .",
    # saltear controles
    "git -c core.hooksPath=/dev/null push origin plan/x",
    "git config core.hooksPath otra",
    "git config --global user.name x",
    "git remote set-url origin https://github.com/otro/repo.git",
    "git remote add otro https://github.com/otro/repo.git",
    "cp x .git/hooks/pre-push",
    "rm .git/hooks/pre-push",
    "sed -i 's/deny/allow/' .claude/settings.json",
    "echo '{}' > .claude/settings.json",
    "py -3 .claude/hooks/permisos.py",
    "python3 .claude/hooks/permisos.py",
    # administración de GitHub
    "gh repo delete o/r --yes",
    "gh repo edit --visibility public",
    "gh secret set X",
    "gh release create v1",
    "gh workflow run deploy.yml",
    "gh auth token",
    # producción
    "railway variables",
    "railway run python manage.py migrate",
    "railway.exe ssh",
    "railway up",
    # secretos
    "cat .env",
    "cat config/.env.production",
    "grep SECRET .env",
    "git add .env",
    "cp .env /tmp/x",
    "cat claves/servidor.pem",
    "docker run --env-file=.env x",
    "cat credenciales-demo.txt",
    # formas indirectas
    "cd backend && git stash",
    "ls; git stash",
    "bash -c 'git stash'",
    "bash -lc \"gh pr merge 3\"",
    "echo \"$(git stash)\"",
    "echo `git clean -f`",
    "env FOO=1 git stash",
    "FOO=1 git stash",
    "timeout 30 git clean -f",
    "/usr/bin/git stash",
    "\"C:/Program Files/Git/bin/git.exe\" stash",
    "echo plan/x | xargs git push --force origin",
    "eval 'git stash'",
    "python -c \"import os; os.system('git stash')\"",
    "if true; then git stash; fi",
    "for r in a b; do gh pr merge $r; done",
    "ls\ngit stash",
    "cat <<EOF\ntexto\nEOF\ngit stash",
    "cat <<EOF && git stash\ntexto\nEOF",
    'git commit --no-verif -m "cierre: x"',
    "git commit --amen --no-edit",
    "git push --no-verif origin HEAD",
    "git push --forc origin plan/x",
    "git push --mirr origin",
]

PERMITIDOS = [
    "git status",
    "git add apps/sitios/models.py docs/planes/x.md",
    "git commit -m 'T1: agrega el modelo'",
    "git commit -m \"docs: no usar git stash ni gh pr merge\"",
    "git push",
    "git push -u origin plan/multiempresa",
    "git push origin plan/x",
    "git push origin HEAD",
    "git push origin --delete plan/vieja",
    "git -C worktrees/x-T1 push -u origin x-T1",
    "git fetch origin && git rebase origin/main",
    "git switch -c plan/x",
    "git checkout main",
    "git checkout -b plan/x",
    "git checkout -- apps/sitios/models.py",
    "git restore --staged .",
    "git branch -d plan/fusionada",
    "git reset HEAD~1",
    "git merge --no-ff x-T1",
    "git config user.name",
    "git remote -v",
    "git check-ignore .env",
    "gh pr create --title 'x' --body 'y' --base main",
    "gh pr view 12 --json state,mergeable",
    "gh pr checks 12 --watch",
    "gh pr comment 12 --body 'listo'",
    "gh pr review 12 --comment -b 'ver línea 3'",
    "gh pr edit 12 --add-label metodo",
    "gh pr list",
    "gh run view 123 --log-failed",
    "gh run rerun 123",
    "gh issue create --title x --body y",
    "gh api repos/o/r/pulls/12/comments",
    "gh api -X GET repos/o/r/branches/main/protection",
    "gh repo view --json name",
    "gh auth status",
    "railway status",
    "railway logs",
    "cat .env.example",
    "test -f .env",
    "ls -la .env",
    "grep -n 'env' .gitignore",
    "py -3 .claude/hooks/permisos.py --comprobar",
    "cat .claude/settings.json",
    "sed -n 1,20p .claude/settings.json",
    "cmp .claude/hooks/pre-push .git/hooks/pre-push",
    "PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb",
    "./venv/Scripts/python.exe -m ruff check .",
    "bash .claude/hooks/worktree-crear.sh x T1",
    "git commit -m \"$(cat <<'EOF'\nT1: agrega el modelo\n\nCo-Authored-By: Claude <noreply@anthropic.com>\nEOF\n)\"",
    "echo 'texto con comilla \" suelta'",
    "gh pr create --title x --body \"$(cat <<'EOF'\nNo se usa `git stash` ni gh pr merge; don't.\nEOF\n)\"",
    "cat <<EOF | grep x\ngit stash\nEOF",
    "git commit -m 'T1: algo'",
    "git push -u origin plan/x",
]


class TestGuardiaBash(unittest.TestCase):
    def test_bloquea_lo_que_queda_en_manos_del_usuario(self):
        for comando in BLOQUEADOS:
            with self.subTest(comando=comando):
                self.assertIsNotNone(guardia_bash.revisar(comando))

    def test_deja_pasar_el_trabajo_normal(self):
        for comando in PERMITIDOS:
            with self.subTest(comando=comando):
                self.assertIsNone(guardia_bash.revisar(comando))

    def test_main_bloquea_con_exit_2_y_motivo(self):
        err = io.StringIO()
        entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": "gh pr merge 3"}})
        self.assertEqual(guardia_bash.main(entrada, err), 2)
        self.assertIn("el merge de un PR lo hace el usuario", err.getvalue())

    def test_main_deja_pasar_con_exit_0(self):
        entrada = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push -u origin plan/x"}})
        self.assertEqual(guardia_bash.main(entrada, io.StringIO()), 0)

    def test_main_con_entrada_invalida_no_corta_la_sesion(self):
        for entrada in ("", "no es json", "[]", json.dumps({"tool_input": {}}), json.dumps({"tool_input": {"command": 3}})):
            with self.subTest(entrada=entrada):
                self.assertEqual(guardia_bash.main(entrada, io.StringIO()), 0)

    def test_comillas_sin_cerrar_caen_en_la_busqueda_por_patron(self):
        self.assertIsNotNone(guardia_bash.revisar("git stash 'sin cerrar"))
        self.assertIsNone(guardia_bash.revisar("echo 'sin cerrar"))


if __name__ == "__main__":
    unittest.main()
