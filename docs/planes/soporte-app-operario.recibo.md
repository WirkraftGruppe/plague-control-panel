## 2026-11-14 16:02 — tarea T2 de 2026-11-14-soporte-app-operario.md

- HEAD verificado: 0960b7a
- Contrato: intacto (congelado en 2229493)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_me_empresa_devuelve_nombre_y_logo --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_me_empresa_sin_logo_devuelve_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_logo_propio_lo_ve_un_empleado --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_logo_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_logo_lleva_cabeceras_privadas --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas.tests.test_api.EmpresaApiTests.test_plataforma_da_403 --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T2`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 14.0 s
- Veredicto: PASA

