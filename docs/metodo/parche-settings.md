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
# Respaldo de lo que hubiera instalado antes (H11 de la auditoría): -Force no avisa.
if (Test-Path "$hooks\commit-msg") { Copy-Item "$hooks\commit-msg" "$hooks\commit-msg.bak" -Force }
if (Test-Path "$hooks\pre-push")   { Copy-Item "$hooks\pre-push"   "$hooks\pre-push.bak"   -Force }
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
Remove-Item $m
```

La prueba invoca el hook directamente y no crea commits: un `git commit --allow-empty` de prueba
dejaría un commit `cierre:` basura si el hook quedara mal instalado (CRLF, sin `py`) o si se
corriera en una rama sin `commit_msg.py`.

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

## 4. Obligatorio: proteger el control de `cierre:` (H4 de la auditoría)

`Edit(**/.git/hooks/**)` protege la copia instalada, pero el control depende de archivos que hoy
el agente puede escribir: borrar `commit_msg.py` o escribir un hash en `.claude/.recibos.json`
deja pasar un `cierre:` sin recibo, y la guardia no lo frena (`echo … > .claude/.recibos.json`
pasa). T14 ya cierra el atajo del archivo faltante y de las entradas que no son hash; esto cierra
la escritura directa.

En `permisos.py`, suma a `DENY`:

```python
    "Edit(.claude/.recibos.json)",
    "Edit(.claude/hooks/recibo.py)",
    "Edit(.claude/hooks/commit-msg)",
    "Edit(.claude/hooks/commit_msg.py)",
```

En `guardia_bash.py`, amplía `RUTAS_PROTEGIDAS` (línea 45) para que la guardia bloquee también las
escrituras por Bash (`cp`, `mv`, `rm`, `sed -i`, redirecciones) sobre esas rutas:

```python
RUTAS_PROTEGIDAS = (
    ".git/hooks", ".claude/settings.json", ".claude/settings.local.json",
    ".claude/.recibos.json", ".claude/hooks/recibo.py",
    ".claude/hooks/commit-msg", ".claude/hooks/commit_msg.py",
)
```

`verificar.py` sigue escribiendo `.recibos.json` desde Python, que no pasa por la guardia. Corre
`py -3 .claude\hooks\permisos.py` y después `py -3 -m pytest .claude\hooks -q`. Un plan posterior
que cambie esos archivos necesita que quites las reglas mientras dura (decisión tuya).

## 5. Abreviaturas de opciones largas en la guardia (H2 de la auditoría)

Git acepta cualquier prefijo único de una opción larga: `--no-verif` es `--no-verify`, `--amen` es
`--amend`, `--forc` es `--force`. La guardia compara la opción completa y el deny busca el texto
`--no-verify`, así que `git commit --no-verif -m "cierre: x"` y `git push --no-verif origin HEAD`
pasan las dos capas y saltean `commit-msg` y `pre-push`. El auditor lo reprodujo en un repo
descartable; ya estaba en `metodo/autonomia-github`.

En `guardia_bash.py`, agrega junto a `grupo_corto`:

```python
def es_prefijo(a: str, *largas: str) -> bool:
    """True si `a` es una opción larga o una abreviatura de alguna (git acepta prefijos únicos)."""
    if not a.startswith("--") or len(a) < 4:
        return False
    nombre = a.split("=", 1)[0]
    return any(larga.startswith(nombre) for larga in largas)
```

y usa la función en `regla_git` (rama `commit`) y en `regla_push`:

```python
            if es_prefijo(a, "--amend", "--all", "--no-verify") or grupo_corto(a, "a") or grupo_corto(a, "n"):
                return "`git commit` sin `--amend`, `-a`/`--all` ni `--no-verify`"
```

```python
        if es_prefijo(a, "--force", "--force-with-lease", "--force-if-includes", "--mirror", "--all", "--prune", "--no-verify") or grupo_corto(a, "f"):
            return f"`git push {a}`: sin forzar, sin `--no-verify` y sin subir todas las ramas"
```

`--al` y `--no` tienen menos de 4 caracteres y no cuentan: git los rechaza por ambiguos.

En `permisos.py`, suma a `DENY` las formas abreviadas:

```python
    "Bash(git commit *--no-v*)",
    "Bash(git push *--no-v*)",
    "Bash(git commit *--am*)",
    "Bash(git push *--forc*)",
```

En `test_guardia_bash.py`, agrega a `BLOQUEADOS`:

```python
    'git commit --no-verif -m "cierre: x"',
    "git commit --amen --no-edit",
    "git push --no-verif origin HEAD",
    "git push --forc origin plan/x",
    "git push --mirr origin",
```

y a `PERMITIDOS` (no deben confundirse con abreviaturas):

```python
    "git commit -m 'T1: algo'",
    "git push -u origin plan/x",
```

Después: `py -3 .claude\hooks\permisos.py`, `py -3 .claude\hooks\permisos.py --comprobar` y
`py -3 -m pytest .claude\hooks\test_guardia_bash.py .claude\hooks\test_permisos.py -q`.

---

# Parche — guarda del `cd` a los worktrees (2026-11-14)

Autorizado por el usuario el 2026-11-14 (`docs/decisiones.md`). Claude no pudo editar
`.claude/hooks/guardia_bash.py`: la lista `deny` de los permisos lo rechaza. El parche está en
`docs/metodo/guarda-cd-worktrees.patch` y cambia dos archivos a la vez:

- `guardia_bash.py`: `cd` y `pushd` hacia una ruta con una carpeta `worktrees` (relativa o absoluta,
  con `/` o `\`, también dentro de `( … )`, `bash -c` o con envoltorios) salen con 2 y el mensaje
  "usa `git -C worktrees/<w>` para git, rutas absolutas para leer y escribir, y
  `verificar.py --raiz worktrees/<w>` para verificar", sin el texto de "queda en manos del usuario".
  `cd mis-worktrees-viejos`, `cd docs` y `git -C worktrees/<w> …` siguen pasando.
- `test_guardia_bash.py`: 3 tests nuevos (`test_bloquea_cd_y_pushd_hacia_worktrees`,
  `test_deja_pasar_cd_fuera_de_worktrees`, `test_main_explica_la_alternativa_al_cd_sin_derivar_al_usuario`).

Probado sobre una copia fuera del repo: `test_guardia_bash.py` da 9 passed, 176 subtests passed, y
`git apply --check` pasa sobre `main` @ 7f785a8. Desde la raíz, en la rama `guardia-cd-worktrees` o
en `main` ya fusionada:

```powershell
git apply docs/metodo/guarda-cd-worktrees.patch
py -3 -m pytest .claude/hooks/test_guardia_bash.py -q
git add .claude/hooks/guardia_bash.py .claude/hooks/test_guardia_bash.py
git commit -m "metodo: guardia_bash bloquea cd y pushd a los worktrees"
```

No hace falta tocar `.claude/settings.json`: el hook PreToolUse ya invoca `guardia_bash.py`.
