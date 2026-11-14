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

## 2026-11-14 16:06 — tarea T1 de 2026-11-14-soporte-app-operario.md

- HEAD verificado: 5436ebc
- Contrato: intacto (congelado en 2229493)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_reporte_en_visita_abierta_propia_da_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_ajena_inexistente_o_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_de_otra_empresa_con_cuerpo_vacio_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_propia_cerrada_da_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_punto_de_otro_sitio_da_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_punto_inactivo_o_ya_reportado_da_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_respuesta_sin_coordenadas_ni_foto --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_reporte_no_crea_revision_ni_cambia_vencimiento --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_visita_solo_con_reportes_no_se_cierra --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_mismo_cliente_uuid_no_duplica --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_409_no_expone_datos_de_otro_empleado --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_foto_se_procesa_y_respeta_el_limite --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.NoRevisadosApiTests.test_mis_visitas_trae_no_revisado --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.IncidenciaNoRevisadoTests.test_condicion_cuenta_solo_visitas_realizadas_con_reporte --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_no_revisados.IncidenciaNoRevisadoTests.test_marcar_revisada_acepta_visita_solo_con_reportes --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.empresas --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 750 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 37.0 s
- Veredicto: PASA

