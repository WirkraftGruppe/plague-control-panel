## 2026-11-18 17:10 — tarea T1 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: c0ff43a
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.DiasAvisoTests.test_dias_aviso_por_frecuencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_7_revisado_hoy_queda_al_dia --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_7_a_dos_dias_queda_proxima --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_14_proxima_a_4_dias_o_menos --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_30_y_90_proxima_a_7_dias_o_menos --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_sin_frecuencia_proxima_a_7_dias_o_menos --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoPuntoTests.test_frecuencia_1_proxima_solo_el_dia_que_vence --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoSitioTests.test_condicion_sql_coincide_con_estado_en_python --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoSitioTests.test_sitio_proximo_por_un_punto_que_no_es_el_mas_cercano --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.EstadoSitioTests.test_mapa_usa_los_dias_de_aviso --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_aviso_proxima.ApiSitiosTests.test_resolver_y_me_puntos_usan_los_dias_de_aviso --keepdb`
  - PASA (exit 1, nuevo: —) `T1 [grep-0] grep -n "Esta semana" apps/sitios/estado.py`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 350 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 34.9 s
- Veredicto: PASA

## 2026-11-18 17:11 — tarea T2 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: c0ff43a
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - PASA (exit 0, nuevo: —) `T2 [cmd] git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T1: integra ficha-sitio-trabajo-hecho-T1"`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 0.6 s
- Veredicto: PASA

## 2026-11-18 17:12 — tarea T3 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: 5b0cb98
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - FALLA (exit 1, nuevo: —) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_estado_aviso.EstadoAvisoApiTests.test_estado_del_punto_del_turno_usa_la_frecuencia --keepdb`
    ```
    E
    ======================================================================
    ERROR: test_estado_aviso (unittest.loader._FailedTest.test_estado_aviso)
    ----------------------------------------------------------------------
    ImportError: Failed to import test module: test_estado_aviso
    Traceback (most recent call last):
      File "C:\Users\Emanuel\AppData\Local\Programs\Python\Python313\Lib\unittest\loader.py", line 141, in loadTestsFromName
        module = __import__(module_name)
    ModuleNotFoundError: No module named 'apps.visitas.tests.test_estado_aviso'
    
    
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s
    
    FAILED (errors=1)
    Found 1 test(s).
    System check identified no issues (0 silenced).
    ```
  - FALLA (exit 1, nuevo: —) `T3 [grep-1] grep -n "frecuencia_dias=punto.frecuencia_dias" apps/visitas/serializers.py`
    ```
    ```
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T3`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 12.9 s
- Veredicto: FALLA

## 2026-11-18 17:15 — tarea T3 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: 0ed4e68
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T3 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_estado_aviso.EstadoAvisoApiTests.test_estado_del_punto_del_turno_usa_la_frecuencia --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [grep-1] grep -n "frecuencia_dias=punto.frecuencia_dias" apps/visitas/serializers.py`
  - PASA (exit 0, nuevo: —) `T3 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T3 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 120 --subtarea T3`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 12.9 s
- Veredicto: PASA

## 2026-11-18 17:15 — tarea T5 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: 98d6a47
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "días de aviso" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "días de aviso" docs/contrato-api.md`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "30 s" docs/02-diseno.md`
  - PASA (exit 1, nuevo: —) `T5 [grep-0] grep -n "dentro de los próximos 7 días" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T5 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T5`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 1.0 s
- Veredicto: PASA

## 2026-11-18 17:18 — tarea T4 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: 4358b54
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.EstadoSitioPanelTests.test_listado_chip_proxima_por_un_punto_que_no_es_el_mas_cercano --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.EstadoSitioPanelTests.test_estado_de_me_puntos_coincide_con_la_ficha --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_muestra_fecha_hora_y_operario_de_la_ultima_revision --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_revision_de_visita_de_administrador_no_cuenta --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_punto_sin_revisiones_dice_sin_revisiones --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.UltimaRevisionTests.test_consultas_iguales_con_5_y_50_puntos --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_turno_abierto_muestra_operario_apertura_y_avance --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_dos_turnos_abiertos_muestran_dos_bloques --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_punto_revisado_en_el_turno_queda_marcado --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_sin_turno_abierto_no_hay_actualizacion_de_30_s --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_avance_tras_cerrar_el_turno_corta_la_actualizacion --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_visita_de_administrador_no_cuenta_como_turno --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_turnos_de_hoy_usan_el_mismo_avance --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_avance_de_sitio_de_otra_empresa_da_404 --keepdb`
  - PASA (exit 0, nuevo: sí) `T4 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios.tests.test_panel_ficha_avance.AvanceTurnoTests.test_avance_pide_administrador --keepdb`
  - PASA (exit 1, nuevo: —) `T4 [grep-0] grep -nw "estado_de_sitio" apps/sitios/panel_views.py`
  - PASA (exit 0, nuevo: —) `T4 [grep-1] grep -rn "every 30s" apps/sitios/templates/sitios/panel/`
  - PASA (exit 0, nuevo: —) `T4 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.sitios --keepdb`
  - PASA (exit 0, nuevo: —) `T4 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 600 --subtarea T4`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 44.1 s
- Veredicto: PASA

## 2026-11-18 17:18 — tarea T6 de 2026-11-18-ficha-sitio-trabajo-hecho.md

- HEAD verificado: 4358b54
- Contrato: intacto (congelado en 3b0bb32)
- Criterios:
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T3: integra ficha-sitio-trabajo-hecho-T3"`
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T4: integra ficha-sitio-trabajo-hecho-T4"`
  - PASA (exit 0, nuevo: —) `T6 [cmd] git log --oneline plan/ficha-sitio-trabajo-hecho | grep -q "T5: integra ficha-sitio-trabajo-hecho-T5"`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 0.7 s
- Veredicto: PASA

