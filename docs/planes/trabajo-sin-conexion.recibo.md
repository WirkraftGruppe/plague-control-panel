## 2026-11-18 20:43 — tarea T1 de 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: 2d0311c
- Contrato: intacto (congelado en 89f2a8d)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajuste_atraso_app.AjusteAtrasoAppTests.test_default_72_y_rango_1_a_8760 --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" config/settings/base.py`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" .env.example`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 2.0 s
- Veredicto: PASA

## 2026-11-18 20:50 — tarea T3 de 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: c1a1594
- Contrato: intacto (congelado en 89f2a8d)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_solo_puntos_de_la_empresa --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_excluye_puntos_sitios_y_clientes_inactivos --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_consultas_iguales_con_50_y_500_puntos --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_mismo_etag_responde_304 --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_cache_control_no_store --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_campos_de_punto_y_servicios_activos --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_entrega_qr_hash_y_nunca_qr_codigo --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_datos_sin_conexion.DatosSinConexionTests.test_anonimo_401 --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "datos-sin-conexion" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "atraso_excedido" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "visita_no_abierta" docs/contrato-api.md`
  - PASA (exit 1, nuevo: —) `T3 [grep-0] grep -n "Ningún otro error trae" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios apps.api.tests.test_contrato_doc --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T3`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 32.7 s
- Veredicto: PASA

