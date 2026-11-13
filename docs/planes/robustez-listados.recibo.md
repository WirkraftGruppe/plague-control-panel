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

## 2026-11-13 18:03 — tarea T1 de 2026-11-13-robustez-listados.md

- HEAD verificado: b1f560b
- Contrato: intacto (congelado en ccb6738)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_orden_con_doble_guion_responde_200_en_todos --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_busqueda_con_nul_responde_200_en_todos --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_listados_robustez.ListadosRobustezTests.test_get_busqueda_descarta_nul --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 150 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 121.1 s
- Veredicto: PASA

## 2026-11-13 18:13 — tarea T2 de 2026-11-13-robustez-listados.md

- HEAD verificado: a52a4e0
- Contrato: intacto (congelado en ccb6738)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_plataforma_api.PlataformaApiTests.test_plataforma_no_obtiene_token --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_plataforma_api.PlataformaApiTests.test_plataforma_no_renueva_token --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_non_field_errors_anidado_conserva_ruta --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_all_de_django_va_a_detalle --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_429_del_balde_lleva_retry_after --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_no_encontrado_bajo_api_devuelve_json --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_esquema_robustez.EsquemaRobustezTests.test_sesion_sin_empresa_activa_se_rechaza --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_esquema_robustez.EsquemaRobustezTests.test_postproceso_agrega_401_y_429 --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T2`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 77.2 s
- Veredicto: PASA

## 2026-11-13 18:28 — tarea T3 de 2026-11-13-robustez-listados.md

- HEAD verificado: 7ee5383
- Contrato: intacto (congelado en ccb6738)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_admin_errores.AdminErroresTests.test_padre_de_otra_empresa_da_error_de_formulario --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_admin_errores.AdminErroresTests.test_slug_repetido_en_la_empresa_da_error_de_formulario --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes.tests.test_admin_errores.AdminErroresTests.test_referencia_plataforma_de_solo_lectura_da_error_de_formulario --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.accounts.tests.test_admin_rol_plataforma.RolPlataformaAdminTests.test_plataforma_con_empresa_da_error_que_indica_la_salida --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_admin_logo.EmpresaAdminLogoTests.test_logo_del_admin_se_guarda_procesado --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_admin_logo.EmpresaAdminLogoTests.test_logo_invalido_da_error_de_formulario --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.clientes apps.accounts apps.empresas apps.sitios apps.visitas apps.servicios --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T3`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 368.5 s
- Veredicto: PASA

## 2026-11-13 18:52 — tarea T5 de 2026-11-13-robustez-listados.md

- HEAD verificado: 898c4c7
- Contrato: modificado y aceptado (f2c0d5a, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ProgramacionRobustezTests.test_servicio_desactivado_se_conserva_al_editar_la_fila --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ProgramacionRobustezTests.test_punto_inactivo_no_se_programa --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ProgramacionRobustezTests.test_no_se_asigna_otro_servicio_inactivo --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.GeocodificacionEmpresaTests.test_cache_de_una_empresa_no_responde_a_otra --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_robustez_sitios.ResolverRobustezTests.test_codigo_mal_formado_da_404_json --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T5`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 278.5 s
- Veredicto: PASA

## 2026-11-13 19:03 — tarea T6 de 2026-11-13-robustez-listados.md

- HEAD verificado: 96facef
- Contrato: modificado y aceptado (f2c0d5a, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/robustez-listados | grep -q "T1: integra robustez-listados-T1"`
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/robustez-listados | grep -q "T2: integra robustez-listados-T2"`
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/robustez-listados | grep -q "T3: integra robustez-listados-T3"`
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/robustez-listados | grep -q "T4: integra robustez-listados-T4"`
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/robustez-listados | grep -q "T5: integra robustez-listados-T5"`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_ruta_inexistente_bajo_api_da_404_json --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_esquema_con_sesion_de_plataforma_se_rechaza --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_esquema_con_sesion_de_empresa_inactiva_se_rechaza --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_robustez_listados.IntegracionRobustezTests.test_esquema_con_sesion_de_empresa_activa_responde --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T6`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 541.6 s
- Veredicto: PASA

## 2026-11-13 19:04 — tarea T2 de 2026-11-13-robustez-listados.md

- HEAD verificado: 96facef
- Contrato: modificado y aceptado (f2c0d5a, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_plataforma_api.PlataformaApiTests.test_plataforma_no_obtiene_token --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_plataforma_api.PlataformaApiTests.test_plataforma_no_renueva_token --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_non_field_errors_anidado_conserva_ruta --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_all_de_django_va_a_detalle --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_429_del_balde_lleva_retry_after --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_errores_robustez.ErroresRobustezTests.test_no_encontrado_bajo_api_devuelve_json --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_esquema_robustez.EsquemaRobustezTests.test_sesion_sin_empresa_activa_se_rechaza --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api.tests.test_esquema_robustez.EsquemaRobustezTests.test_postproceso_agrega_401_y_429 --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T2`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 80.3 s
- Veredicto: PASA

