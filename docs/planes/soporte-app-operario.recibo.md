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

## 2026-11-14 16:08 — tarea T3 de 2026-11-14-soporte-app-operario.md

- HEAD verificado: 0e588c8
- Contrato: intacto (congelado en 2229493)
- Criterios:
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/soporte-app-operario | grep -q "T1: integra soporte-app-operario-T1"`
  - PASA (exit 0, nuevo: —) `T3 [cmd] git log --oneline plan/soporte-app-operario | grep -q "T2: integra soporte-app-operario-T2"`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_soporte_app_operario.IntegracionSoporteAppTests.test_reporte_no_revisado_por_url_da_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_soporte_app_operario.IntegracionSoporteAppTests.test_me_empresa_por_url --keepdb`
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_soporte_app_operario.IntegracionSoporteAppTests.test_logo_de_otra_empresa_por_url_da_404 --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "no-revisados" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "me/empresa" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.api apps.empresas apps.visitas config --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 250 --subtarea T3`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 31.8 s
- Veredicto: PASA

## 2026-11-14 16:11 — tarea T6 de 2026-11-14-soporte-app-operario.md

- HEAD verificado: ef96b26
- Contrato: intacto (congelado en 2229493)
- Criterios:
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "PuntoNoRevisado" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T6 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T6`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 2.1 s
- Veredicto: PASA

## 2026-11-14 16:16 — tarea T4 de 2026-11-14-soporte-app-operario.md

- HEAD verificado: ca48f79
- Contrato: intacto (congelado en 2229493)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_doce_puntos_desde_cinco_con_servicio_y_frecuencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_ciento_uno_da_error_de_formulario --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_servicio_de_otra_empresa_no_se_acepta --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_sitio_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_alta_multiple.AltaMultiplePuntosTests.test_puntos_siguen_el_orden_de_los_existentes --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_filtra_por_sector --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_filtra_sin_imprimir --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_marcar_impresos_fija_la_fecha_solo_en_los_filtrados --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_sitio_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_hoja_qr.HojaQRTests.test_marcar_impresos_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_no_revisados_sitio.NoRevisadosSitioTests.test_ficha_del_sitio_lista_los_reportes --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_no_revisados_sitio.NoRevisadosSitioTests.test_inicio_lista_la_visita_en_incidencias --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T4`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 36.3 s
- Veredicto: PASA

## 2026-11-14 16:19 — tarea T5 de 2026-11-14-soporte-app-operario.md

- HEAD verificado: 8743e93
- Contrato: intacto (congelado en 2229493)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_contador_cuenta_visita_realizada_con_reporte --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_visita_abierta_con_reporte_no_cuenta --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_marcar_revisada_la_saca_del_contador --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_ficha_del_turno_lista_los_reportes --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_foto_de_reporte_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_no_revisados.NoRevisadosPanelTests.test_empleado_no_ve_la_foto --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T5`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 20.9 s
- Veredicto: PASA

