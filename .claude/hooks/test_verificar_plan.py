"""Tests del hook Stop `verificar_plan.py` y del verificador de congelado `congelado.sh`.

Se ejecutan con unittest (sin pytest):
    py -3 -m unittest discover -s .claude/hooks -p "test_verificar_plan.py" -v

Los proyectos de prueba se copian de `fixtures/proyecto_con_plan/` a un repo git temporal con el
commit `docs(plan): plan` (el hook exige el plan congelado). Los criterios de los fixtures y de los
tests solo usan `true`, `false`, `test -e`, `grep`, `touch`/`echo` dentro del repo temporal y un
`python` que duerme (test de timeout): nada destructivo fuera del directorio temporal.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

DIR_HOOKS = Path(__file__).resolve().parent
SCRIPT = DIR_HOOKS / "verificar_plan.py"
CONGELADO = DIR_HOOKS / "congelado.sh"
FIXTURE_CON_PLAN = DIR_HOOKS / "fixtures" / "proyecto_con_plan"
FIXTURE_SIN_PLAN = DIR_HOOKS / "fixtures" / "proyecto_sin_plan"

sys.path.insert(0, str(DIR_HOOKS))
import verificar_plan  # noqa: E402

CRITERIO_T1_BASE = "  - `[cmd]` `true`\n"


def correr_hook(raiz, entrada=None, session_id=None, extra_entorno=None):
    """Ejecuta verificar_plan.py con CLAUDE_PROJECT_DIR=raiz y el JSON dado por stdin."""
    if entrada is None:
        entrada = json.dumps({"session_id": session_id or "test", "stop_hook_active": False})
    entorno = dict(os.environ, CLAUDE_PROJECT_DIR=str(raiz))
    entorno.pop("VERIFICAR_PLAN_TIMEOUT", None)
    entorno.update(extra_entorno or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=entrada.encode("utf-8"),
        env=entorno,
        capture_output=True,
        timeout=120,
    )


def texto(bytes_):
    """Decodifica una salida como UTF-8."""
    return bytes_.decode("utf-8", errors="replace")


CRITERIO_MARCADOR = "  - `[cmd]` `touch marcador-ejecutado`"


class ProyectoTemporal(unittest.TestCase):
    """Base: copia el fixture con plan a un repo git temporal y lo congela.

    El hook exige que el plan esté congelado (`congelado.sh`): el fixture se commitea con el
    asunto `docs(plan): plan` y cada cambio del plan hecho por los helpers se re-congela con
    `--amend`, salvo que se pida lo contrario (`congelar=False`).
    """

    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("sin git")
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name) / "proyecto"
        shutil.copytree(FIXTURE_CON_PLAN, self.raiz)
        self.plan = self.raiz / "docs" / "planes" / "plan.md"
        preparar_repo(self.raiz)
        git(self.raiz, "add", "-A")
        git(self.raiz, "commit", "-q", "-m", "docs(plan): plan")

    def tearDown(self):
        self._tmp.cleanup()

    def reemplazar_en_plan(self, viejo, nuevo, congelar=True):
        """Reemplaza un fragmento único del plan del proyecto temporal y lo re-congela."""
        contenido = self.plan.read_text(encoding="utf-8")
        self.assertEqual(contenido.count(viejo), 1, f"fragmento no único: {viejo!r}")
        self.plan.write_text(contenido.replace(viejo, nuevo), encoding="utf-8")
        if congelar:
            git(self.raiz, "commit", "-q", "-a", "--amend", "--no-edit")

    def agregar_criterio_t1(self, linea, congelar=True):
        """Agrega un criterio al bloque Criterios de T1."""
        self.reemplazar_en_plan(CRITERIO_T1_BASE, CRITERIO_T1_BASE + linea + "\n", congelar)

    def fijar_plan_activo(self, valor):
        """Reescribe la línea `Plan activo:` de la bitácora del proyecto temporal."""
        (self.raiz / "docs" / "bitacora.md").write_text(
            f"# Bitácora de juguete\n\n## Estado actual\n\nPlan activo: {valor}\n", encoding="utf-8"
        )

    def copiar_plan_con_marcador(self, destino):
        """Copia el plan del fixture a `destino` con un criterio de T1 que deja un marcador."""
        destino.parent.mkdir(parents=True, exist_ok=True)
        contenido = self.plan.read_text(encoding="utf-8")
        destino.write_text(
            contenido.replace(CRITERIO_T1_BASE, CRITERIO_T1_BASE + CRITERIO_MARCADOR + "\n"), encoding="utf-8"
        )

    def assert_sin_marcador(self, *directorios):
        """Ningún criterio del plan corrió: no quedó el marcador en ninguno de los directorios."""
        for directorio in (self.raiz, *directorios):
            self.assertFalse((directorio / "marcador-ejecutado").exists(), f"se ejecutó un criterio en {directorio}")

    def fijar_modo(self, modo):
        """Escribe `.claude/hooks/modo` en el proyecto temporal."""
        archivo = self.raiz / ".claude" / "hooks" / "modo"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(modo + "\n", encoding="utf-8")


class TestVerificarPlan(ProyectoTemporal):
    def test_fixture_base_pasa_con_exit_cero(self):
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertEqual(proceso.stderr, b"")

    def test_tarea_hecha_con_criterio_que_falla_es_falla(self):
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        proceso = correr_hook(self.raiz)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("T1 [cmd] `false` → FALLA (exit 1)", error)

    def test_tarea_pendiente_con_criterio_que_falla_no_se_ejecuta(self):
        # T2 está pendiente y su único criterio es `false`: el fixture base igual pasa.
        self.assertIn("| T2 | pendiente |", self.plan.read_text(encoding="utf-8"))
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertNotIn("T2", texto(proceso.stderr))

    def test_tarea_en_curso_o_sin_fila_no_se_ejecuta(self):
        self.reemplazar_en_plan("| T2 | pendiente |\n", "")
        self.assertEqual(correr_hook(self.raiz).returncode, 0)
        with self.plan.open("a", encoding="utf-8") as archivo:
            archivo.write("| T2 | en curso |\n")
        self.assertEqual(correr_hook(self.raiz).returncode, 0)

    def test_cmd_falla_con_comando_que_devuelve_cero_es_falla(self):
        self.agregar_criterio_t1("  - `[cmd-falla]` `true`")
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("[cmd-falla] `true` → FALLA (exit 0)", texto(proceso.stderr))

    def test_grep_0_con_coincidencia_es_falla(self):
        self.agregar_criterio_t1('  - `[grep-0]` `grep -n "Plan activo" docs/bitacora.md`')
        proceso = correr_hook(self.raiz)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("[grep-0]", error)
        self.assertIn("Plan activo: docs/planes/plan.md", error)  # la salida del grep

    def test_grep_0_con_error_de_grep_es_falla(self):
        self.agregar_criterio_t1('  - `[grep-0]` `grep -n "x" docs/archivo-inexistente.md`')
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("FALLA (exit 2)", texto(proceso.stderr))

    def test_no_existe_sobre_ruta_existente_es_falla(self):
        self.agregar_criterio_t1("  - `[no-existe]` `docs/bitacora.md`")
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("[no-existe] `docs/bitacora.md` → FALLA", texto(proceso.stderr))

    def test_stop_hook_active_true_sale_con_cero_sin_ejecutar_nada(self):
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        entrada = json.dumps({"session_id": "x", "stop_hook_active": True})
        proceso = correr_hook(self.raiz, entrada=entrada)
        self.assertEqual(proceso.returncode, 0)
        self.assertEqual(proceso.stderr, b"")
        self.assertFalse((self.raiz / ".claude" / ".ultimo-verificado").exists())

    def test_stdin_vacio_o_malformado_sale_con_cero_sin_traceback(self):
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        for entrada in ("", "no es json", "[1, 2]", "{"):
            with self.subTest(entrada=entrada):
                proceso = correr_hook(self.raiz, entrada=entrada)
                self.assertEqual(proceso.returncode, 0)
                self.assertNotIn("Traceback", texto(proceso.stderr))

    def test_modo_aviso_sale_con_uno(self):
        self.fijar_modo("aviso")
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        self.assertEqual(correr_hook(self.raiz).returncode, 1)

    def test_modo_bloqueo_sale_con_dos(self):
        self.fijar_modo("bloqueo")
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        sesion = f"test-{uuid.uuid4().hex}"
        try:
            self.assertEqual(correr_hook(self.raiz, session_id=sesion).returncode, 2)
        finally:
            verificar_plan.reiniciar_intentos(sesion)

    def test_modo_bloqueo_al_cuarto_intento_sale_con_uno_y_revisar_a_mano(self):
        self.fijar_modo("bloqueo")
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        sesion = f"test-{uuid.uuid4().hex}"
        try:
            codigos = [correr_hook(self.raiz, session_id=sesion) for _ in range(4)]
            self.assertEqual([p.returncode for p in codigos], [2, 2, 2, 1])
            self.assertIn("revisar a mano", texto(codigos[-1].stderr))
        finally:
            verificar_plan.reiniciar_intentos(sesion)

    def test_cierre_global_se_ejecuta_solo_con_todas_las_tareas_hechas(self):
        self.reemplazar_en_plan("- `[cmd]` `true`\n\n## Registro", "- `[cmd]` `false`\n\n## Registro")
        self.reemplazar_en_plan("  - `[cmd]` `false`\n\n## Criterios", "  - `[cmd]` `true`\n\n## Criterios")
        # T2 pendiente: el cierre global (que falla) no se ejecuta.
        self.assertEqual(correr_hook(self.raiz).returncode, 0)
        # Con T2 hecha, se ejecuta y falla.
        self.reemplazar_en_plan("| T2 | pendiente |", "| T2 | hecha |")
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("cierre global [cmd] `false`", texto(proceso.stderr))

    def test_plan_con_crlf_se_parsea_igual(self):
        self.agregar_criterio_t1("  - `[cmd]` `false`")
        for archivo in (self.raiz / "docs").rglob("*.md"):
            contenido = archivo.read_bytes().replace(b"\r\n", b"\n")
            archivo.write_bytes(contenido.replace(b"\n", b"\r\n"))
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("T1 [cmd] `false`", texto(proceso.stderr))

    def test_proyecto_sin_plan_sale_con_cero(self):
        proceso = correr_hook(FIXTURE_SIN_PLAN)
        self.assertEqual(proceso.returncode, 0)
        self.assertEqual(proceso.stderr, b"")

    def test_directorio_vacio_sale_con_cero(self):
        with tempfile.TemporaryDirectory() as tmp:
            proceso = correr_hook(tmp)
            self.assertEqual(proceso.returncode, 0)
            self.assertEqual(proceso.stderr, b"")

    def test_cache_en_repo_git_se_escribe_tras_corrida_limpia(self):
        self.assertEqual(correr_hook(self.raiz).returncode, 0)
        cache = self.raiz / ".claude" / ".ultimo-verificado"
        self.assertTrue(cache.is_file())
        self.assertFalse(json.loads(cache.read_text(encoding="utf-8"))["fallas"])
        # Con la firma igual, una segunda corrida sale con 0 sin volver a ejecutar.
        self.assertEqual(correr_hook(self.raiz).returncode, 0)


def borrar_arbol(ruta):
    """Borra un directorio aunque tenga archivos de solo lectura (objetos de git en Windows)."""
    def reintentar(funcion, camino, _error):
        os.chmod(camino, 0o700)
        funcion(camino)

    if sys.version_info >= (3, 12):
        shutil.rmtree(ruta, onexc=reintentar)
    else:
        shutil.rmtree(ruta, onerror=reintentar)


def proceso_vivo(pid):
    """True si el proceso `pid` sigue corriendo (Windows: GetExitCodeProcess == STILL_ACTIVE)."""
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        manejador = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not manejador:
            return False
        try:
            codigo = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(manejador, ctypes.byref(codigo)):
                return False
            return codigo.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(manejador)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class TestContencionDelPlanActivo(ProyectoTemporal):
    """El plan activo solo puede ser un .md de docs/planes/ de la raíz, por ruta relativa."""

    def assert_ignorado(self, proceso, *directorios):
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 0, error)
        self.assertIn("se ignora el plan activo", error)
        self.assert_sin_marcador(*directorios)

    def test_plan_activo_con_puntos_fuera_de_la_raiz_no_se_ejecuta(self):
        fuera = self.raiz.parent / "fuera"
        self.copiar_plan_con_marcador(fuera / "plan.md")
        for valor in ("../fuera/plan.md", "docs/planes/../../../fuera/plan.md", "docs\\planes\\..\\..\\..\\fuera\\plan.md"):
            with self.subTest(valor=valor):
                self.fijar_plan_activo(valor)
                self.assert_ignorado(correr_hook(self.raiz), fuera)
        # Aun con `..` que vuelve adentro de docs/planes, se rechaza.
        self.agregar_criterio_t1(CRITERIO_MARCADOR)
        self.fijar_plan_activo("docs/planes/../planes/plan.md")
        self.assert_ignorado(correr_hook(self.raiz))

    def test_plan_activo_con_ruta_absoluta_no_se_ejecuta(self):
        # El plan apunta al plan congelado real de la raíz, pero por ruta absoluta: se rechaza.
        self.agregar_criterio_t1(CRITERIO_MARCADOR)
        fuera = self.raiz.parent / "fuera"
        self.copiar_plan_con_marcador(fuera / "plan.md")
        for valor in (str(self.plan), self.plan.as_posix(), str(fuera / "plan.md"), "/tmp/plan.md"):
            with self.subTest(valor=valor):
                self.fijar_plan_activo(valor)
                self.assert_ignorado(correr_hook(self.raiz), fuera)

    def test_plan_activo_fuera_de_docs_planes_no_se_ejecuta(self):
        for relativa in ("docs/otro/plan.md", "docs/plan.md", "plan.md", "docs/planes/sub/plan.md"):
            with self.subTest(relativa=relativa):
                self.copiar_plan_con_marcador(self.raiz / relativa)
                self.fijar_plan_activo(relativa)
                self.assert_ignorado(correr_hook(self.raiz))
        # Un archivo de docs/planes/ que no es .md tampoco.
        (self.raiz / "docs" / "planes" / "plan.txt").write_text(self.plan.read_text(encoding="utf-8"), encoding="utf-8")
        self.fijar_plan_activo("docs/planes/plan.txt")
        self.assert_ignorado(correr_hook(self.raiz))


class TestCongeladoPrevio(ProyectoTemporal):
    """Sin contrato congelado e intacto el hook no ejecuta ningún criterio."""

    def test_plan_no_congelado_no_ejecuta_criterios(self):
        # a) Repo sin commit "docs(plan): plan": congelado.sh sale con 2.
        self.agregar_criterio_t1(CRITERIO_MARCADOR)
        git(self.raiz, "commit", "-q", "--amend", "-m", "otra cosa")
        proceso = correr_hook(self.raiz)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("no se ejecuta ningún criterio", error)
        self.assertIn("CONTRATO NO CONGELADO", error)
        self.assert_sin_marcador()
        # b) El proyecto ni siquiera es un repo git.
        borrar_arbol(self.raiz / ".git")
        proceso = correr_hook(self.raiz)
        self.assertEqual(proceso.returncode, 1, texto(proceso.stderr))
        self.assertIn("CONTRATO NO CONGELADO", texto(proceso.stderr))
        self.assert_sin_marcador()

    def test_plan_modificado_arriba_del_corte_no_ejecuta_criterios(self):
        self.agregar_criterio_t1(CRITERIO_MARCADOR, congelar=False)
        proceso = correr_hook(self.raiz)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("no se ejecuta ningún criterio", error)
        self.assertIn("CONTRATO MODIFICADO", error)
        self.assertIn("touch marcador-ejecutado", error)  # el diff de congelado.sh
        self.assert_sin_marcador()
        # En modo bloqueo sale con 2, igual sin ejecutar nada.
        self.fijar_modo("bloqueo")
        sesion = f"test-{uuid.uuid4().hex}"
        try:
            self.assertEqual(correr_hook(self.raiz, session_id=sesion).returncode, 2)
        finally:
            verificar_plan.reiniciar_intentos(sesion)
        self.assert_sin_marcador()


class TestTimeoutYCache(ProyectoTemporal):
    def test_timeout_corta_el_arbol_de_procesos(self):
        # El criterio lanza un nieto (python) que anota su PID y duerme 15 s.
        python = Path(sys.executable).as_posix()
        codigo_nieto = "import os,time; open('.git/pid-nieto','w').write(str(os.getpid())); time.sleep(15)"
        self.agregar_criterio_t1(f'  - `[cmd]` `"{python}" -c "{codigo_nieto}"; echo fin`')
        inicio = time.monotonic()
        proceso = correr_hook(self.raiz, extra_entorno={"VERIFICAR_PLAN_TIMEOUT": "2"})
        transcurrido = time.monotonic() - inicio
        error = texto(proceso.stderr)
        self.assertLess(transcurrido, 8, f"el hook tardó {transcurrido:.1f} s")
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("FALLA (exit timeout/error)", error)
        self.assertIn("timeout de 2 s", error)
        archivo_pid = self.raiz / ".git" / "pid-nieto"
        self.assertTrue(archivo_pid.is_file(), "el nieto no llegó a arrancar")
        pid = int(archivo_pid.read_text(encoding="utf-8"))
        limite = time.monotonic() + 5
        while proceso_vivo(pid) and time.monotonic() < limite:
            time.sleep(0.2)
        self.assertFalse(proceso_vivo(pid), f"el nieto {pid} sigue vivo")

    def test_falla_cacheada_no_reejecuta_criterios(self):
        # Cada ejecución real del criterio suma una línea en .git/contador (fuera del status).
        self.agregar_criterio_t1("  - `[cmd]` `echo x >> .git/contador; false`")
        contador = self.raiz / ".git" / "contador"
        primera = correr_hook(self.raiz)
        self.assertEqual(primera.returncode, 1, texto(primera.stderr))
        self.assertEqual(contador.read_text(encoding="utf-8").count("x"), 1)
        cache = json.loads((self.raiz / ".claude" / ".ultimo-verificado").read_text(encoding="utf-8"))
        self.assertTrue(cache["fallas"])

        segunda = correr_hook(self.raiz)
        error = texto(segunda.stderr)
        self.assertEqual(segunda.returncode, 1, error)
        self.assertIn("(caché)", error)
        self.assertIn("`echo x >> .git/contador; false` → FALLA (exit 1)", error)
        self.assertEqual(contador.read_text(encoding="utf-8").count("x"), 1, "se reejecutó el criterio")

        # Si el repo cambia, la firma cambia y se vuelve a ejecutar.
        (self.raiz / "nuevo.txt").write_text("cambio\n", encoding="utf-8")
        tercera = correr_hook(self.raiz)
        self.assertEqual(tercera.returncode, 1)
        self.assertNotIn("(caché)", texto(tercera.stderr))
        self.assertEqual(contador.read_text(encoding="utf-8").count("x"), 2)


def correr_main(raiz, extra_entorno=None, session_id="test"):
    """Ejecuta `verificar_plan.main` en el mismo proceso (para poder parchear el módulo).

    Devuelve (código, stderr). El entorno no hereda `VERIFICAR_PLAN_TIMEOUT` del proceso.
    """
    entorno = {"CLAUDE_PROJECT_DIR": str(raiz), **(extra_entorno or {})}
    entrada = json.dumps({"session_id": session_id, "stop_hook_active": False})
    errores = io.StringIO()
    with contextlib.redirect_stderr(errores):
        codigo = verificar_plan.main(entrada, entorno)
    return codigo, errores.getvalue()


class TestCommitCongelado(ProyectoTemporal):
    """C: los criterios salen del commit congelado (`git show`), nunca del plan en disco."""

    def congelado_parcheado(self, salida):
        """Reemplaza `correr_congelado` por uno que "aprueba" y devuelve `salida` por stdout.

        Simula la carrera TOCTOU: congelado.sh ya dio el visto bueno y el disco cambia después.
        """
        return mock.patch.object(verificar_plan, "correr_congelado", return_value=(0, salida, ""))

    def test_criterios_se_leen_del_commit_congelado_no_del_disco(self):
        cabeza = git(self.raiz, "rev-parse", "HEAD").strip()
        # a) El disco agrega, arriba del corte, un criterio que falla y deja un marcador: no corre.
        self.agregar_criterio_t1(CRITERIO_MARCADOR + "\n  - `[cmd]` `false`", congelar=False)
        with self.congelado_parcheado(cabeza + "\n"):
            codigo, error = correr_main(self.raiz)
        self.assertEqual(codigo, 0, error)
        self.assert_sin_marcador()

        # b) Al revés: el commit congelado tiene un criterio que falla y el disco lo borró.
        #    Se ejecuta el del commit y falla, aunque el disco "diga" que no existe.
        git(self.raiz, "checkout", "-q", "--", ".")
        self.agregar_criterio_t1("  - `[cmd]` `echo desde-el-commit; false`")
        cabeza = git(self.raiz, "rev-parse", "HEAD").strip()
        self.reemplazar_en_plan("  - `[cmd]` `echo desde-el-commit; false`\n", "", congelar=False)
        self.assertNotIn("desde-el-commit", self.plan.read_text(encoding="utf-8"))
        with self.congelado_parcheado(cabeza + "\n"):
            codigo, error = correr_main(self.raiz)
        self.assertEqual(codigo, 1, error)
        self.assertIn("T1 [cmd] `echo desde-el-commit; false` → FALLA (exit 1)", error)
        self.assertIn("desde-el-commit", error)

        # c) Los estados sí salen del disco (debajo del corte): con T1 pendiente no corre nada.
        self.reemplazar_en_plan("| T1 | hecha |", "| T1 | pendiente |", congelar=False)
        with self.congelado_parcheado(cabeza + "\n"):
            codigo, error = correr_main(self.raiz)
        self.assertEqual(codigo, 0, error)

    def test_hash_invalido_o_ajeno_del_congelado_no_ejecuta_criterios(self):
        self.agregar_criterio_t1(CRITERIO_MARCADOR)
        for salida in ("", "no-es-un-hash\n", "HEAD\n", "a" * 39 + "\n", "0" * 40 + "\n"):
            with self.subTest(salida=salida):
                with self.congelado_parcheado(salida):
                    codigo, error = correr_main(self.raiz)
                self.assertEqual(codigo, 1, error)
                self.assertIn("no se ejecuta ningún criterio", error)
                self.assert_sin_marcador()


class TestFormatoT(ProyectoTemporal):
    """D: un plan con criterios pero sin subtareas `### T<n>` no pasa en silencio."""

    def test_plan_sin_subtareas_t_con_criterios_avisa(self):
        self.agregar_criterio_t1(CRITERIO_MARCADOR, congelar=False)
        self.reemplazar_en_plan("### T1 —", "### Tarea 1 —", congelar=False)
        self.reemplazar_en_plan("### T2 —", "### Tarea 2 —")
        proceso = correr_hook(self.raiz)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("no sigue el formato T<n>", error)
        self.assert_sin_marcador()
        # En modo bloqueo sale con 2.
        self.fijar_modo("bloqueo")
        sesion = f"test-{uuid.uuid4().hex}"
        try:
            proceso = correr_hook(self.raiz, session_id=sesion)
            self.assertEqual(proceso.returncode, 2, texto(proceso.stderr))
            self.assertIn("no sigue el formato T<n>", texto(proceso.stderr))
        finally:
            verificar_plan.reiniciar_intentos(sesion)
        self.assert_sin_marcador()

    def test_plan_solo_con_cierre_global_tambien_avisa(self):
        plan = verificar_plan.parsear_plan("# P\n\n## Criterios de cierre global\n\n- `[cmd]` `true`\n")
        self.assertTrue(verificar_plan.sin_formato_t(plan))
        # Un plan sin criterios de ningún tipo sigue siendo un 0 mudo (nada que ejecutar).
        self.assertFalse(verificar_plan.sin_formato_t(verificar_plan.parsear_plan("# P\n\nnada\n")))


class TestFirmaPorContenido(ProyectoTemporal):
    """E: la firma de la caché cambia con el contenido, no solo con `git status`."""

    def test_cambio_en_archivo_ya_modificado_invalida_la_cache(self):
        self.agregar_criterio_t1('  - `[grep-0]` `grep -n malo datos.txt nuevo.txt backend/b.txt`')
        (self.raiz / "datos.txt").write_text("bien\n", encoding="utf-8")
        git(self.raiz, "add", "datos.txt")
        git(self.raiz, "commit", "-q", "-m", "chore: datos")
        # backend/ es un repo aparte (como en TerritoryOS), con un archivo versionado.
        backend = self.raiz / "backend"
        backend.mkdir()
        preparar_repo(backend)
        (backend / "b.txt").write_text("bien\n", encoding="utf-8")
        git(backend, "add", "b.txt")
        git(backend, "commit", "-q", "-m", "inicial")
        nuevo = self.raiz / "nuevo.txt"
        nuevo.write_text("bien\n", encoding="utf-8")

        casos = (
            (self.raiz / "datos.txt", "versionado ya modificado en la raíz"),
            (nuevo, "sin seguimiento en la raíz"),
            (backend / "b.txt", "versionado ya modificado en backend/"),
        )
        for archivo, descripcion in casos:
            with self.subTest(caso=descripcion):
                # Primer cambio (el archivo queda modificado o sin seguimiento): corrida limpia.
                archivo.write_text("bien 2\n", encoding="utf-8")
                proceso = correr_hook(self.raiz)
                self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
                estado_antes = git(self.raiz, "status", "--porcelain") + git(backend, "status", "--porcelain")
                # Segundo cambio sobre el mismo archivo: `git status` no cambia, la firma sí.
                archivo.write_text("malo\n", encoding="utf-8")
                estado_despues = git(self.raiz, "status", "--porcelain") + git(backend, "status", "--porcelain")
                self.assertEqual(estado_antes, estado_despues)
                proceso = correr_hook(self.raiz)
                error = texto(proceso.stderr)
                self.assertEqual(proceso.returncode, 1, error)
                self.assertNotIn("(caché)", error)
                self.assertIn(archivo.relative_to(self.raiz).as_posix() + ":1:malo", error)
                archivo.write_text("bien\n", encoding="utf-8")

    def test_cambio_en_el_plan_en_disco_invalida_la_cache(self):
        self.assertEqual(correr_hook(self.raiz).returncode, 0)
        firma_antes = verificar_plan.firma(self.raiz, self.plan)
        with self.plan.open("a", encoding="utf-8") as archivo:
            archivo.write("\nnota debajo del corte\n")
        self.assertNotEqual(firma_antes, verificar_plan.firma(self.raiz, self.plan))
        # Escribir la caché no cambia la firma.
        firma_actual = verificar_plan.firma(self.raiz, self.plan)
        verificar_plan.escribir_cache(self.raiz / ".claude" / ".ultimo-verificado", "otra", "x")
        self.assertEqual(firma_actual, verificar_plan.firma(self.raiz, self.plan))


class TestPresupuesto(ProyectoTemporal):
    """F: cada criterio recibe `min(timeout, presupuesto_restante)`."""

    def test_timeout_del_criterio_se_recorta_al_presupuesto(self):
        python = Path(sys.executable).as_posix()
        dormir = f'"{python}" -c "import time; time.sleep(20)"'
        # a) Directo sobre ejecutar_seleccion: presupuesto de 3 s, timeout por criterio de 300 s.
        criterios = [
            verificar_plan.Criterio("T1", "cmd", dormir),
            verificar_plan.Criterio("T1", "cmd", "true"),
        ]
        bash = verificar_plan.buscar_bash()
        inicio = time.monotonic()
        resultados = verificar_plan.ejecutar_seleccion(
            criterios, self.raiz, bash, 300.0, verificar_plan.Presupuesto(3)
        )
        transcurrido = time.monotonic() - inicio
        self.assertLess(transcurrido, 10, f"tardó {transcurrido:.1f} s")
        self.assertGreater(transcurrido, 2)
        self.assertFalse(resultados[0].pasa)
        self.assertIsNone(resultados[0].codigo)
        self.assertRegex(resultados[0].salida, r"timeout de (2\.\d|3) s")
        # El siguiente ya no tiene presupuesto: no se ejecuta.
        self.assertFalse(resultados[1].pasa)
        self.assertIn("presupuesto total de 3 s agotado", resultados[1].salida)

        # b) Por main: el presupuesto cuenta desde el arranque (congelado.sh y git incluidos).
        self.agregar_criterio_t1(f"  - `[cmd]` `{dormir}`")
        with mock.patch.object(verificar_plan, "PRESUPUESTO_TOTAL", 6):
            inicio = time.monotonic()
            codigo, error = correr_main(self.raiz, extra_entorno={"VERIFICAR_PLAN_TIMEOUT": "300"})
            transcurrido = time.monotonic() - inicio
        self.assertEqual(codigo, 1, error)
        self.assertLess(transcurrido, 15, f"tardó {transcurrido:.1f} s")
        self.assertRegex(error, r"timeout de \d+(\.\d)? s|presupuesto total de 6 s agotado")
        self.assertNotIn("timeout de 300 s", error)


class TestTimeoutSuite(ProyectoTemporal):
    """P-catalogo-stock-10: la suite completa o por app tiene un timeout propio (700 s)."""

    PY = "PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test"

    def limites(self, comandos, timeout=300.0, timeout_suite=700.0, presupuesto=780):
        """Ejecuta los comandos con `evaluar` simulado y devuelve (límites recibidos, resultados)."""
        recibidos = []

        def falso(criterio, raiz, bash, limite):
            recibidos.append(limite)
            return verificar_plan.Resultado(criterio, True, 0, "")

        criterios = [verificar_plan.Criterio(f"T{i}", "cmd", c) for i, c in enumerate(comandos, 1)]
        with mock.patch.object(verificar_plan, "evaluar", falso):
            resultados = verificar_plan.ejecutar_seleccion(
                criterios, self.raiz, "bash", timeout, verificar_plan.Presupuesto(presupuesto), timeout_suite
            )
        return recibidos, resultados

    def test_suite_sin_etiquetas_usa_timeout_de_suite(self):
        for comando in (f"{self.PY} --keepdb", self.PY, f"{self.PY} --keepdb -v 2".replace(" -v 2", "")):
            self.assertTrue(verificar_plan.es_suite(comando), comando)
        recibidos, _ = self.limites([f"{self.PY} --keepdb"])
        self.assertEqual(recibidos, [700.0])
        self.assertEqual(verificar_plan.TIMEOUT_SUITE, 700)
        self.assertEqual(verificar_plan.leer_timeout_suite({}), 700.0)
        self.assertEqual(verificar_plan.leer_timeout_suite({"VERIFICAR_PLAN_TIMEOUT_SUITE": "50"}), 50.0)
        for invalido in ("0", "-3", "x", ""):
            self.assertEqual(verificar_plan.leer_timeout_suite({"VERIFICAR_PLAN_TIMEOUT_SUITE": invalido}), 700.0)
        # Siempre recortado por el presupuesto.
        recibidos, _ = self.limites([f"{self.PY} --keepdb"], presupuesto=100)
        self.assertLessEqual(recibidos[0], 100)

    def test_suite_por_app_usa_timeout_de_suite(self):
        for comando in (f"{self.PY} apps.visitas --keepdb", f"{self.PY} apps.visitas apps.sitios"):
            self.assertTrue(verificar_plan.es_suite(comando), comando)
        recibidos, _ = self.limites([f"{self.PY} apps.visitas --keepdb"])
        self.assertEqual(recibidos, [700.0])

    def test_test_nombrado_usa_timeout_comun(self):
        for comando in (
            f"{self.PY} apps.visitas.tests.test_qr --keepdb",
            f"{self.PY} apps.visitas.tests.test_qr.ResolverQRTests.test_x --keepdb",
            f"{self.PY} apps.visitas --keepdb && echo hola",
            "py -3 -m pytest .claude/hooks/test_verificar_plan.py -q",
        ):
            self.assertFalse(verificar_plan.es_suite(comando), comando)
        recibidos, _ = self.limites([f"{self.PY} apps.visitas.tests.test_qr --keepdb"])
        self.assertEqual(recibidos, [300.0])

    def test_criterio_repetido_se_ejecuta_una_vez(self):
        recibidos, resultados = self.limites(["echo a", "echo b", "echo a"])
        self.assertEqual(len(recibidos), 2)
        self.assertEqual([r.criterio.origen for r in resultados], ["T1", "T2", "T3"])
        self.assertEqual([r.criterio.comando for r in resultados], ["echo a", "echo b", "echo a"])

    def test_presupuesto_total_queda_bajo_el_timeout_del_stop(self):
        configuracion = json.loads((DIR_HOOKS.parent / "settings.json").read_text(encoding="utf-8"))
        timeout_stop = configuracion["hooks"]["Stop"][0]["hooks"][0]["timeout"]
        self.assertLess(verificar_plan.PRESUPUESTO_TOTAL, timeout_stop)


class TestParseo(unittest.TestCase):
    def test_bloque_de_codigo_con_numeral_no_corta_la_subtarea(self):
        plan = verificar_plan.parsear_plan(FIXTURE_CON_PLAN.joinpath("docs", "planes", "plan.md").read_text(encoding="utf-8"))
        self.assertEqual(len(plan.criterios[1]), 7)
        self.assertEqual([c.tipo for c in plan.criterios[1]][:2], ["cmd", "cmd-falla"])
        self.assertEqual(plan.estados, {1: "hecha", 2: "pendiente"})
        self.assertEqual([c.comando for c in plan.cierre_global], ["true"])

    def test_criterios_debajo_del_corte_se_ignoran(self):
        texto_plan = (
            "### T1 — x\n- **Criterios**:\n  - `[cmd]` `true`\n\n"
            "## Registro de verificación\n\n### T9 — no\n- **Criterios**:\n  - `[cmd]` `false`\n"
        )
        plan = verificar_plan.parsear_plan(texto_plan)
        self.assertEqual(list(plan.criterios), [1])


# ---------------------------------------------------------------------------
# congelado.sh sobre repos temporales creados por el test
# ---------------------------------------------------------------------------

def git(repo, *argumentos):
    """Ejecuta git en el repo temporal y falla el test si git falla."""
    proceso = subprocess.run(["git", "-C", str(repo), *argumentos], capture_output=True, timeout=60)
    if proceso.returncode != 0:
        raise AssertionError(f"git {argumentos} falló: {texto(proceso.stderr)}")
    return texto(proceso.stdout)


def preparar_repo(repo):
    """Inicializa un repo temporal con config local (sin autocrlf) y usuario de prueba."""
    git(repo, "init", "-q")
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "commit.gpgsign", "false")


PLAN_CONGELADO = (
    "# Plan: demo\n\n### T1 — algo\n\n- **Criterios**:\n  - `[cmd]` `true`\n\n"
    "## Registro de verificación\n\n### Estado de subtareas\n\n| T1 | pendiente |\n"
)


def correr_congelado(plan, slug, cwd):
    """Ejecuta congelado.sh con bash."""
    return subprocess.run(
        ["bash", CONGELADO.as_posix(), str(plan), slug],
        cwd=str(cwd),
        capture_output=True,
        timeout=60,
    )


class TestCongelado(unittest.TestCase):
    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("sin git")
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        preparar_repo(self.repo)
        self.plan = self.repo / "docs" / "planes" / "p.md"
        self.plan.parent.mkdir(parents=True)
        self.plan.write_bytes(PLAN_CONGELADO.encode("utf-8"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "docs(plan): demo")
        self.ruta = "docs/planes/p.md"

    def tearDown(self):
        self._tmp.cleanup()

    def test_plan_identico_sale_con_cero(self):
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))

    def test_plan_alterado_arriba_del_corte_sale_con_uno_y_diff(self):
        self.plan.write_bytes(PLAN_CONGELADO.replace("`true`", "`false`").encode("utf-8"))
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("CONTRATO MODIFICADO", error)
        self.assertIn("`false`", error)

    def test_plan_alterado_solo_debajo_del_corte_sale_con_cero(self):
        self.plan.write_bytes(PLAN_CONGELADO.replace("| T1 | pendiente |", "| T1 | hecha |").encode("utf-8"))
        git(self.repo, "commit", "-q", "-am", "registro: T1 hecha")
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))

    def test_slug_sin_commit_sale_con_dos(self):
        proceso = correr_congelado(self.ruta, "otro-slug", self.repo)
        self.assertEqual(proceso.returncode, 2)
        self.assertIn("CONTRATO NO CONGELADO", texto(proceso.stderr))

    def test_plan_en_disco_con_crlf_y_contenido_igual_sale_con_cero(self):
        self.plan.write_bytes(PLAN_CONGELADO.replace("\n", "\r\n").encode("utf-8"))
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))

    def test_mas_de_un_commit_docs_plan_sale_con_uno(self):
        # Un contrato recongelado no se ejecuta: con dos commits de congelado sale con 1 aunque
        # el plan en disco coincida con el más reciente, y lista los dos por stderr.
        self.plan.write_bytes(PLAN_CONGELADO.replace("algo", "otra cosa").encode("utf-8"))
        git(self.repo, "commit", "-q", "-am", "docs(plan): demo — modificado: recongelado")
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        error = texto(proceso.stderr)
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("CONTRATO MODIFICADO: 2 commits docs(plan): revisar a mano", error)
        self.assertIn("docs(plan): demo — modificado: recongelado", error)
        self.assertIn(git(self.repo, "rev-parse", "HEAD~1").strip(), error)
        self.assertEqual(proceso.stdout, b"")

    def test_commit_con_docs_plan_en_el_cuerpo_no_recongela(self):
        # "docs(plan): <slug>" en el cuerpo (en cualquier línea) no cuenta: solo el asunto.
        self.plan.write_bytes(PLAN_CONGELADO.replace("`true`", "`false`").encode("utf-8"))
        git(self.repo, "commit", "-q", "-am", "fix: x", "-m", "docs(plan): demo")
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        error = texto(proceso.stderr)
        # Se compara contra el congelado original: el plan cambió → 1 por diff, no por conteo.
        self.assertEqual(proceso.returncode, 1, error)
        self.assertIn("`false`", error)
        self.assertNotIn("commits docs(plan)", error)
        self.assertEqual(proceso.stdout, b"")
        # Un slug que solo aparece en el cuerpo de un commit no está congelado.
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore: y", "-m", "docs(plan): otro\nmas texto")
        proceso = correr_congelado(self.ruta, "otro", self.repo)
        self.assertEqual(proceso.returncode, 2, texto(proceso.stderr))
        self.assertIn("CONTRATO NO CONGELADO", texto(proceso.stderr))

    def test_congelado_imprime_el_hash_por_stdout(self):
        esperado = git(self.repo, "rev-parse", "HEAD").strip()
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertEqual(texto(proceso.stdout), esperado + "\n")
        # Sigue siendo el commit congelado aunque después haya commits que solo tocan el registro.
        self.plan.write_bytes(PLAN_CONGELADO.replace("| T1 | pendiente |", "| T1 | hecha |").encode("utf-8"))
        git(self.repo, "commit", "-q", "-am", "registro: T1 hecha")
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertEqual(texto(proceso.stdout), esperado + "\n")
        # Sin exit 0 no se imprime nada por stdout.
        self.assertEqual(correr_congelado(self.ruta, "otro-slug", self.repo).stdout, b"")

    def test_slug_que_es_prefijo_de_otro_no_coincide(self):
        # Un plan congelado como "esquema-agentes" no cuenta como congelado para "esquema".
        plan = self.repo / "docs" / "planes" / "2026-09-23-esquema-agentes.md"
        plan.write_bytes(PLAN_CONGELADO.encode("utf-8"))
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "docs(plan): esquema-agentes")
        ruta = "docs/planes/2026-09-23-esquema-agentes.md"
        proceso = correr_congelado(ruta, "esquema", self.repo)
        self.assertEqual(proceso.returncode, 2, texto(proceso.stderr))
        self.assertIn("CONTRATO NO CONGELADO", texto(proceso.stderr))
        self.assertEqual(correr_congelado(ruta, "esquema-agentes", self.repo).returncode, 0)
        # Tampoco coincide un asunto con texto pegado después del slug sin " — ".
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "docs(plan): esquemaX")
        self.assertEqual(correr_congelado(ruta, "esquema", self.repo).returncode, 2)

    def test_asunto_con_motivo_de_modificacion_sigue_contando(self):
        # Un único commit cuyo asunto es "docs(plan): <slug> — <motivo>" es el congelado vigente.
        self.plan.write_bytes(PLAN_CONGELADO.replace("algo", "otra cosa").encode("utf-8"))
        git(self.repo, "commit", "-q", "-a", "--amend", "-m", "docs(plan): demo — modificado: se corrige un criterio")
        proceso = correr_congelado(self.ruta, "demo", self.repo)
        self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))
        self.assertEqual(texto(proceso.stdout).strip(), git(self.repo, "rev-parse", "HEAD").strip())
        # Sin el espacio y el em dash exactos no cuenta como congelado de "demo".
        git(self.repo, "commit", "-q", "--amend", "-m", "docs(plan): demo - modificado: guion simple")
        self.assertEqual(correr_congelado(self.ruta, "demo", self.repo).returncode, 2)

    def test_slug_con_metacaracteres_de_regex_sale_con_dos(self):
        for slug in ("de.o", "demo|x", "-demo", "Demo", "dem.*"):
            with self.subTest(slug=slug):
                proceso = correr_congelado(self.ruta, slug, self.repo)
                self.assertEqual(proceso.returncode, 2, texto(proceso.stderr))

    def test_funciona_desde_otro_cwd_con_ruta_absoluta(self):
        with tempfile.TemporaryDirectory() as otro:
            proceso = correr_congelado(self.plan.as_posix(), "demo", otro)
            self.assertEqual(proceso.returncode, 0, texto(proceso.stderr))


# ---------------------------------------------------------------------------
# Plan derivado de la rama (estilo pytest)
# ---------------------------------------------------------------------------

def repo_con_plan_de_rama(raiz, slug, rama):
    """Repo temporal con `docs/planes/2026-01-01-<slug>.md` congelado y la rama pedida.

    El criterio de T1 del plan deja `marcador-ejecutado`; la bitácora dice `Plan activo: (ninguno)`.
    """
    (raiz / "docs" / "planes").mkdir(parents=True)
    (raiz / "docs" / "bitacora.md").write_text("# Bitácora\n\nPlan activo: (ninguno)\n", encoding="utf-8")
    plan = PLAN_CONGELADO.replace("`[cmd]` `true`", "`[cmd]` `touch marcador-ejecutado`").replace(
        "| T1 | pendiente |", "| T1 | hecha |"
    )
    (raiz / "docs" / "planes" / f"2026-01-01-{slug}.md").write_text(plan, encoding="utf-8")
    git(raiz, "init", "-q", "-b", "main")
    for clave, valor in (("core.autocrlf", "false"), ("user.name", "Test"),
                         ("user.email", "t@example.invalid"), ("commit.gpgsign", "false")):
        git(raiz, "config", clave, valor)
    git(raiz, "add", "-A")
    git(raiz, "commit", "-q", "-m", f"docs(plan): {slug}")
    git(raiz, "switch", "-q", "-c", rama)
    return raiz


def test_plan_se_deriva_de_rama_plan_slug(tmp_path):
    raiz = repo_con_plan_de_rama(tmp_path, "demo", "plan/demo")
    correr_hook(raiz)
    assert (raiz / "marcador-ejecutado").exists()


def test_plan_se_deriva_de_rama_de_subtarea(tmp_path):
    for rama in ("demo-T3", "demo-T5a"):
        raiz = repo_con_plan_de_rama(tmp_path / rama, "demo", rama)
        correr_hook(raiz)
        assert (raiz / "marcador-ejecutado").exists(), rama


def test_rama_sin_plan_cae_en_bitacora(tmp_path):
    # Rama sin plan correspondiente: se usa `Plan activo:` de la bitácora.
    raiz = repo_con_plan_de_rama(tmp_path, "demo", "otra-rama")
    assert verificar_plan.plan_de_rama(raiz) is None
    correr_hook(raiz)
    assert not (raiz / "marcador-ejecutado").exists()
    (raiz / "docs" / "bitacora.md").write_text(
        "# Bitácora\n\nPlan activo: docs/planes/2026-01-01-demo.md\n", encoding="utf-8"
    )
    correr_hook(raiz)
    assert (raiz / "marcador-ejecutado").exists()


def test_rama_con_slug_invalido_no_ejecuta_plan_ajeno(tmp_path):
    raiz = repo_con_plan_de_rama(tmp_path, "demo", "plan/demo")
    # `demo` no debe tomar `2026-01-01-demo-dos.md`; slugs inválidos o prefijos no ejecutan nada.
    (raiz / "docs" / "planes" / "2026-01-01-demo-dos.md").write_text(
        PLAN_CONGELADO.replace("`[cmd]` `true`", "`[cmd]` `touch marcador-ajeno`").replace(
            "| T1 | pendiente |", "| T1 | hecha |"
        ),
        encoding="utf-8"
    )
    # Control positivo: con la rama válida el hook sí ejecuta el criterio (el resto no es vacuo).
    correr_hook(raiz)
    assert (raiz / "marcador-ejecutado").exists()
    (raiz / "marcador-ejecutado").unlink()
    for rama in ("plan/Demo", "plan/demo_x", "plan/-demo", "plan/de", "x/demo-T1"):
        git(raiz, "switch", "-q", "-C", rama)
        proceso = correr_hook(raiz)
        assert not (raiz / "marcador-ejecutado").exists(), rama
        assert not (raiz / "marcador-ajeno").exists(), rama
        assert proceso.returncode == 0, rama


def test_plantilla_integracion_es_subtarea_numerada():
    # La integración de cada ola es una subtarea `### T<n> — Integración (principal)`: el hook la
    # ve como tarea con sus criterios, y la última tarea numerada es la integración de la última ola.
    texto_plantilla = (DIR_HOOKS.parent.parent / "docs" / "plantilla-plan.md").read_text(
        encoding="utf-8"
    )
    assert "Trabajo del principal" not in texto_plantilla
    plan = verificar_plan.parsear_plan(texto_plantilla)
    integraciones = [
        n for n, lista in plan.criterios.items() if any("integra <slug>" in c.comando for c in lista)
    ]
    assert integraciones
    assert any(
        c.comando.endswith('grep -q "T1: integra <slug>-T1"')
        for n in integraciones
        for c in plan.criterios[n]
    )
    assert max(plan.criterios) in integraciones
    assert len(plan.cierre_global) == 6


# ---------------------------------------------------------------------------
# commit_base desde el Registro (T3 de docs/planes/2026-10-03-limites-ingreso.md)
# ---------------------------------------------------------------------------

def repo_con_registro(raiz, criterios, slug="demo"):
    """Repo temporal con el plan `docs(plan): <slug>` congelado, en la rama `plan/<slug>`.

    `criterios` son las líneas del bloque Criterios de T1. El Registro queda sin `commit_base:`;
    devuelve el hash completo del commit congelado.
    """
    (raiz / "docs" / "planes").mkdir(parents=True)
    (raiz / "docs" / "bitacora.md").write_text("# Bitácora\n\nPlan activo: (ninguno)\n", encoding="utf-8")
    plan = (
        "# Plan: demo\n\n### T1 — algo\n\n- **Criterios**:\n" + criterios + "\n"
        "## Registro de verificación\n\n### Estado de subtareas\n\n| T1 | hecha |\n"
    )
    (raiz / "docs" / "planes" / f"2026-01-01-{slug}.md").write_text(plan, encoding="utf-8")
    git(raiz, "init", "-q", "-b", "main")
    for clave, valor in (("core.autocrlf", "false"), ("user.name", "Test"),
                         ("user.email", "t@example.invalid"), ("commit.gpgsign", "false")):
        git(raiz, "config", clave, valor)
    git(raiz, "add", "-A")
    git(raiz, "commit", "-q", "-m", f"docs(plan): {slug}")
    git(raiz, "switch", "-q", "-c", f"plan/{slug}")
    return git(raiz, "rev-parse", "HEAD").strip()


def anotar_commit_base(raiz, valor, slug="demo"):
    """Escribe `commit_base: <valor>` debajo del corte, en el plan en disco (no congelado)."""
    plan = raiz / "docs" / "planes" / f"2026-01-01-{slug}.md"
    corte = "## Registro de verificación\n\n"
    plan.write_text(plan.read_text(encoding="utf-8").replace(corte, f"{corte}commit_base: {valor}\n\n"), encoding="utf-8")


def registro_con(valor):
    """Texto de un plan en disco cuyo Registro lleva `commit_base: <valor>`."""
    return f"## Registro de verificación\n\ncommit_base: {valor}\n"


def test_commit_base_faltante_falla_con_mensaje(tmp_path):
    repo_con_registro(
        tmp_path, "  - `[cmd]` `touch con-marcador '<commit_base>'`\n  - `[cmd]` `touch sin-marcador`\n"
    )
    proceso = correr_hook(tmp_path)
    error = texto(proceso.stderr)
    assert proceso.returncode == 1, error
    assert "commit_base sin resolver en 2026-01-01-demo.md:" in error
    assert not (tmp_path / "con-marcador").exists()  # el criterio con marcador no se ejecutó
    assert (tmp_path / "sin-marcador").exists()  # los demás sí


def test_marcador_se_reemplaza_antes_de_ejecutar(tmp_path):
    base = repo_con_registro(
        tmp_path,
        "  - `[cmd]` `echo '<commit_base>' > con-comillas`\n  - `[cmd]` `echo <commit_base> > sin-comillas`\n",
    )
    anotar_commit_base(tmp_path, base[:10])  # abreviado: el criterio recibe el hash completo
    proceso = correr_hook(tmp_path)
    assert proceso.returncode == 0, texto(proceso.stderr)
    for nombre in ("con-comillas", "sin-comillas"):
        assert (tmp_path / nombre).read_text(encoding="utf-8").strip() == base


def test_commit_base_que_no_es_docs_plan_se_rechaza(tmp_path):
    base = repo_con_registro(tmp_path, "  - `[cmd]` `touch con-marcador '<commit_base>'`\n")
    (tmp_path / "otro.txt").write_text("x\n", encoding="utf-8")
    git(tmp_path, "add", "otro.txt")
    git(tmp_path, "commit", "-q", "-m", "T1: otra cosa")
    ajeno = git(tmp_path, "rev-parse", "HEAD").strip()
    anotar_commit_base(tmp_path, ajeno)
    disco = (tmp_path / "docs" / "planes" / "2026-01-01-demo.md").read_text(encoding="utf-8")
    resuelto, motivo = verificar_plan.commit_base_del_registro(disco, tmp_path, "demo")
    assert resuelto is None and "docs(plan): demo" in motivo
    proceso = correr_hook(tmp_path)
    assert proceso.returncode == 1 and "commit_base sin resolver" in texto(proceso.stderr)
    assert not (tmp_path / "con-marcador").exists()
    # Controles positivos: el commit congelado y el modificado (` — modificado: …`) se aceptan.
    assert verificar_plan.commit_base_del_registro(registro_con(base), tmp_path, "demo") == (base, None)
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "docs(plan): demo — modificado: motivo")
    modificado = git(tmp_path, "rev-parse", "HEAD").strip()
    assert verificar_plan.commit_base_del_registro(registro_con(modificado), tmp_path, "demo") == (modificado, None)
    # Un asunto que solo empieza igual (`docs(plan): demo2`) no vale.
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "docs(plan): demo2")
    parecido = git(tmp_path, "rev-parse", "HEAD").strip()
    assert verificar_plan.commit_base_del_registro(registro_con(parecido), tmp_path, "demo")[0] is None


def test_cli_commit_base_imprime_hash_sin_leer_stdin(tmp_path):
    base = repo_con_registro(tmp_path, "  - `[cmd]` `true`\n")
    anotar_commit_base(tmp_path, base)
    entorno = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path))
    ok = subprocess.run([sys.executable, str(SCRIPT), "--commit-base"], env=entorno,
                        stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    assert ok.returncode == 0 and texto(ok.stdout).strip() == base
    anotar_commit_base(tmp_path, "0000000")
    mal = subprocess.run([sys.executable, str(SCRIPT), "--commit-base"], env=entorno,
                         stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    assert mal.returncode == 2 and mal.stdout == b"" and "commit_base sin resolver" in texto(mal.stderr)


if __name__ == "__main__":
    unittest.main()
