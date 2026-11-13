# Parche de settings — metodo-v2

Claude no puede editar `.claude/settings.json`, `permisos.py`, `guardia_bash.py` ni `pre-push`, ni
instalar hooks de git (`Edit(**/.git/hooks/**)` está en el deny). Lo que sigue lo aplicas tú, en
este orden, con PowerShell 5.1, una vez integrado el plan `metodo-v2` (los archivos nuevos solo
existen después de la integración de la ola 2). Cierra P-metodo-v2-2.

Dónde correr: en `worktrees\metodo-v2` (rama `plan/metodo-v2`) o en la raíz si ya tiene el merge.
La raíz sigue en `plan/multiempresa` y todavía no tiene `commit_msg.py`; sin él `commit-msg` sale
con 0 y no hace nada, así que instalarlo antes no estorba.

## 1. Cambiar el hook `Stop`

`permisos.py` solo genera el bloque `permissions` y conserva `hooks` tal cual; por eso este
cambio se hace a mano en `.claude/settings.json`. Reemplaza el comando del hook `Stop`:

```json
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "py -3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/recibo_pendiente.py",
            "timeout": 30
          }
        ]
      }
    ]
```

Antes decía `verificar_plan.py --aviso` con `timeout` 900. `recibo_pendiente.py` no ejecuta
criterios: pide el recibo (`verificar.py todo` o `cierre`) una vez por sesión y HEAD si la sesión
hizo commits y el HEAD no tiene recibo. `SessionStart` no cambia: `contexto.sh` ya le pasa el
stdin a `recibo_pendiente.py --inicio`.

El test `test_settings_registra_la_guardia_y_el_cierre_liviano` de `.claude/hooks/test_permisos.py`
(línea 77) afirma que el comando de `Stop` contiene `verificar_plan.py --aviso`; con este cambio
falla. Cámbialo por `recibo_pendiente.py`:

```python
        self.assertIn("recibo_pendiente.py", cierre["command"])
```

Después:

```powershell
py -3 .claude\hooks\permisos.py --comprobar
py -3 -m pytest .claude\hooks\test_permisos.py -q
```

`permisos.py --comprobar` debe decir que coincide (no toca `hooks`). `verificar_plan.py` se
queda: `verificar.py` lo importa.

## 2. Instalar `commit-msg` y `pre-push` en `.git/hooks/`

Los worktrees comparten la carpeta `hooks` del repositorio común, así que se instala una vez.
Ambos archivos tienen que quedar con LF (`.gitattributes` fija `eol=lf` para los dos).

```powershell
$hooks = Join-Path (Resolve-Path (git rev-parse --git-common-dir)) 'hooks'
Copy-Item .claude\hooks\commit-msg "$hooks\commit-msg" -Force
Copy-Item .claude\hooks\pre-push   "$hooks\pre-push"   -Force
[IO.File]::ReadAllText("$hooks\commit-msg").Contains("`r")   # debe imprimir False
[IO.File]::ReadAllText("$hooks\pre-push").Contains("`r")     # debe imprimir False
```

No uses `core.hooksPath`: está en el deny y, apuntado a `.claude/hooks/`, ejecutaría los scripts
de esa carpeta como hooks.

### Comprobación de `commit-msg`

Un `cierre:` sin recibo tiene que rechazarse sin crear el commit, y un mensaje común tiene que pasar:

```powershell
$h = $hooks -replace '\\', '/'
$m = [IO.Path]::GetTempFileName()
Set-Content -Path $m -Value 'cierre: humo-sin-plan' -Encoding Ascii
bash "$h/commit-msg" $m; $LASTEXITCODE                        # 1: no hay plan ni recibo
Set-Content -Path $m -Value 'docs: mensaje comun' -Encoding Ascii
bash "$h/commit-msg" $m; $LASTEXITCODE                        # 0
git log -1 --oneline                                          # sin commits nuevos
git commit --allow-empty -m "cierre: humo-sin-plan"           # debe fallar; no queda commit
git log -1 --oneline                                          # el mismo commit de antes
```

### Comprobación de `pre-push`

Git manda la entrada con `\n`; PowerShell 5.1 agregaría `\r\n` al canalizar, así que la prueba se
hace dentro de `bash`:

```powershell
bash -c "printf 'refs/heads/x 1 refs/heads/main 0\n' | bash '$h/pre-push' origin"; $LASTEXITCODE   # 1: push a main
bash -c "printf 'refs/heads/x 1 refs/heads/x 0\n'    | bash '$h/pre-push' origin"; $LASTEXITCODE   # 0: rama nueva
```

## 3. Lo que informó T9: nada que cambiar en `pre-push` ni en `guardia_bash.py`

Los dos tests de `TestPrePush` que fallaban en la base (`test_avance_normal_pasa` y
`test_rama_nueva_a_origin_pasa`) eran un defecto del test: `subprocess.run(..., text=True)` en
Windows manda `\r\n` al stdin del hook y el `\r` queda pegado al último campo, mientras que git
real manda `\n`. T9 lo corrigió en `test_permisos.py` (`entrada_de_git`, entrada en bytes). El
`pre-push` y la guardia no se tocaron y no hace falta tocarlos.

## 4. Opcional: proteger la copia versionada de `commit-msg`

`Edit(**/.git/hooks/**)` ya protege la copia instalada, pero no la versionada
(`.claude/hooks/commit-msg`, `.claude/hooks/commit_msg.py`). Si quieres el mismo trato que
`pre-push`, suma esas dos rutas a `DENY` de `permisos.py` como `Edit(.claude/hooks/commit-msg)` y
`Edit(.claude/hooks/commit_msg.py)` y corre `py -3 .claude\hooks\permisos.py`. Hazlo después de
cerrar el plan: un plan posterior que cambie el hook necesitaría que lo quites.
