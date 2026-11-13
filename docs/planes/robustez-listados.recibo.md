## 2026-11-13 17:50 — tarea T4 de 2026-11-13-robustez-listados.md

- HEAD verificado: 506b64b
- Contrato: intacto (congelado en ccb6738)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios.tests.test_slug_concurrente.SlugConcurrenteTests.test_choque_de_slug_reintenta_con_sufijo --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidad_bloqueada.UnidadBloqueadaTests.test_modo_unidad_con_movimientos_da_error --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_unidad_bloqueada.UnidadBloqueadaTests.test_admin_unidades_de_solo_lectura_con_movimientos --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.servicios apps.productos --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T4`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 16.5 s
- Veredicto: PASA

## 2026-11-13 17:52 — tarea T1 de 2026-11-13-robustez-listados.md

- HEAD verificado: 506b64b
- Contrato: intacto (congelado en ccb6738)
- Criterios:
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_orden_con_doble_guion_responde_200_en_todos --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_listados_robustez (unittest.loader._FailedTest.test_listados_robustez)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_listados_robustez
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.panel.tests.test_listados_robustez'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_busqueda_con_nul_responde_200_en_todos --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_listados_robustez (unittest.loader._FailedTest.test_listados_robustez)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_listados_robustez
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.panel.tests.test_listados_robustez'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_get_busqueda_descarta_nul --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_listados_robustez (unittest.loader._FailedTest.test_listados_robustez)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_listados_robustez
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.panel.tests.test_listados_robustez'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 119.6 s
- Veredicto: FALLA

