## 2026-11-14 18:39 — tarea T2 de 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: 113b06f
- Contrato: intacto (congelado en eb1dbda)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_devuelve_usuario_y_empresa --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_sin_nombre_usa_username --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_usuario_sin_empresa_da_200_con_empresa_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_token_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_renovacion_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_ruta_con_token_vigente_y_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_otros_codigos_de_autenticacion_no_traen_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_esquema_de_error_documenta_code --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 31.5 s
- Veredicto: PASA

## 2026-11-14 18:39 — tarea T1 de 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: 113b06f
- Contrato: intacto (congelado en eb1dbda)
- Criterios:
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_item_vencido_ayer_trae_estado_vencida --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_estado_coincide_con_el_resolver_de_qr --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_consultas_iguales_con_5_y_50_items --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.002s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_sitio_trae_contacto_o_null --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_historial_y_cierre_no_traen_contacto --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otro_empleado_da_404 --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otra_empresa_da_404 --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_realizado_da_404 --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 29.8 s
- Veredicto: FALLA

## 2026-11-14 18:42 — tarea T1 de 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: 2ff2fcc
- Contrato: intacto (congelado en eb1dbda)
- Criterios:
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_item_vencido_ayer_trae_estado_vencida --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_estado_coincide_con_el_resolver_de_qr --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_consultas_iguales_con_5_y_50_items --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_sitio_trae_contacto_o_null --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_historial_y_cierre_no_traen_contacto --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otro_empleado_da_404 --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otra_empresa_da_404 --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_realizado_da_404 --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_api_turno_app (unittest.loader._FailedTest.test_api_turno_app)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_api_turno_app
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_api_turno_app'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 24.3 s
- Veredicto: FALLA

## 2026-11-14 18:46 — tarea T1 de 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: cb46ec0
- Contrato: intacto (congelado en eb1dbda)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_item_vencido_ayer_trae_estado_vencida --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_estado_coincide_con_el_resolver_de_qr --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_consultas_iguales_con_5_y_50_items --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_sitio_trae_contacto_o_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_historial_y_cierre_no_traen_contacto --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otro_empleado_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_realizado_da_404 --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 29.3 s
- Veredicto: PASA

## 2026-11-14 18:47 — tarea T3 de 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: f4a09ec
- Contrato: intacto (congelado en eb1dbda)
- Criterios:
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/ajustes-api-app-base | grep -q "T1: integra ajustes-api-app-base-T1"`
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/ajustes-api-app-base | grep -q "T2: integra ajustes-api-app-base-T2"`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_turno_por_url --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_otra_empresa_por_url_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_me_visitas_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] grep -qF "/api/v1/me/visitas/<pk>/" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "empresa_inactiva" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T3`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 13.1 s
- Veredicto: PASA

## 2026-11-14 18:50 — todo 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: c43fa72
- Contrato: intacto (congelado en eb1dbda)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_item_vencido_ayer_trae_estado_vencida --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_estado_coincide_con_el_resolver_de_qr --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_consultas_iguales_con_5_y_50_items --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_sitio_trae_contacto_o_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_historial_y_cierre_no_traen_contacto --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otro_empleado_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_realizado_da_404 --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_devuelve_usuario_y_empresa --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_sin_nombre_usa_username --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_usuario_sin_empresa_da_200_con_empresa_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_token_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_renovacion_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_ruta_con_token_vigente_y_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_otros_codigos_de_autenticacion_no_traen_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_esquema_de_error_documenta_code --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/ajustes-api-app-base | grep -q "T1: integra ajustes-api-app-base-T1"`
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/ajustes-api-app-base | grep -q "T2: integra ajustes-api-app-base-T2"`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_turno_por_url --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_otra_empresa_por_url_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_me_visitas_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] grep -qF "/api/v1/me/visitas/<pk>/" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "empresa_inactiva" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T3`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] ./venv/Scripts/python.exe -m ruff check .`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; modificados y sin seguimiento; se excluyen docs/planes, estado, bitácora, decisiones y metodo)`
- Omitido (no toca .claude/, docs/plantilla-plan.md): `py -3 -m pytest .claude/hooks -q`
- duración: 191.7 s
- Veredicto: PASA

## 2026-11-14 19:26 — tarea T4 de 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: b91399b
- Contrato: modificado y aceptado (997807d, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_contacto_null_con_cliente_dado_de_baja --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_contacto_null_con_sitio_dado_de_baja --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T4`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 7.3 s
- Veredicto: PASA

## 2026-11-14 19:29 — todo 2026-11-14-ajustes-api-app-base.md

- HEAD verificado: ce62e12
- Contrato: modificado y aceptado (997807d, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_item_vencido_ayer_trae_estado_vencida --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_estado_coincide_con_el_resolver_de_qr --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_consultas_iguales_con_5_y_50_items --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_sitio_trae_contacto_o_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_historial_y_cierre_no_traen_contacto --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_propio_da_200_con_la_forma_de_la_lista --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otro_empleado_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_detalle_de_turno_realizado_da_404 --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_devuelve_usuario_y_empresa --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_sin_nombre_usa_username --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.RaizTests.test_usuario_sin_empresa_da_200_con_empresa_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_token_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_renovacion_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_ruta_con_token_vigente_y_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_otros_codigos_de_autenticacion_no_traen_code --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_raiz_y_codigos.CodigoErrorTests.test_esquema_de_error_documenta_code --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/ajustes-api-app-base | grep -q "T1: integra ajustes-api-app-base-T1"`
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/ajustes-api-app-base | grep -q "T2: integra ajustes-api-app-base-T2"`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_turno_por_url --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_detalle_de_otra_empresa_por_url_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajustes_api_app_base.IntegracionAppBaseTests.test_me_visitas_con_empresa_inactiva_trae_code --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] grep -qF "/api/v1/me/visitas/<pk>/" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "empresa_inactiva" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T3`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_contacto_null_con_cliente_dado_de_baja --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app.TurnoAppTests.test_contacto_null_con_sitio_dado_de_baja --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_api_turno_app apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T4`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] ./venv/Scripts/python.exe -m ruff check .`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; modificados y sin seguimiento; se excluyen docs/planes, estado, bitácora, decisiones y metodo)`
- Omitido (no toca .claude/, docs/plantilla-plan.md): `py -3 -m pytest .claude/hooks -q`
- duración: 175.4 s
- Veredicto: PASA

