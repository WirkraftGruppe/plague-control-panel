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

## 2026-11-18 20:58 — tarea T2,T4 de 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: 0734e41
- Contrato: intacto (congelado en 89f2a8d)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_71_horas_se_guarda --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_73_horas_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_manual_sigue_con_168_horas --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_reintento_73_horas_mismo_uuid_es_duplicada --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_pendiente_con_abierta_en_de_ayer --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_futura_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abierta_en_futura_tolerada_cuenta_revisiones_al_cerrar --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_no_toma_pendiente_de_dia_posterior --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cerrada_en_anterior_a_abierta_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_reporte_guarda_reportado_en --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cierre_por_sistema_usa_reportado_en --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_revision_en_visita_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_reporte_en_visita_cancelada --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_cierre_de_visita_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_distinto_guarda_servicio_e_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_igual_sin_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_inactivo_o_de_otra_empresa_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_valida_contra_la_planilla_del_servicio_enviado --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_visita_nueva_compara_con_servicio_del_punto --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.IncidenciaServicioTests.test_cuenta_sin_revisar_y_marcar_revisada_la_saca --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_no_cierra_visita_con_actividad_reciente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_cierra_visita_vieja_sin_actividad --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 800 --subtarea T2`
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T2: integra trabajo-sin-conexion-T2"`
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T3: integra trabajo-sin-conexion-T3"`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - FALLA (exit 1, nuevo: —) `commits de la tarea dentro de Puede tocar`
    ```
    T4: test_vencimiento usa 2 días de atraso, dentro de ATRASO_MAXIMO_APP_HORAS (72) -> apps/visitas/tests/test_vencimiento.py
    ```
- duración: 53.2 s
- Veredicto: FALLA

## 2026-11-18 21:26 — tarea T4 de 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: b2b59bf
- Contrato: modificado y aceptado (3d9aa29, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T2: integra trabajo-sin-conexion-T2"`
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T3: integra trabajo-sin-conexion-T3"`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 0.6 s
- Veredicto: PASA

## 2026-11-18 21:29 — tarea T5 de 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: 35a0340
- Contrato: modificado y aceptado (3d9aa29, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_71_horas_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_73_horas_400_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_reporte_73_horas_400_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_abierta_en_de_ayer_abre_el_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_hora_futura_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cancelado_por_cierre_nocturno_abrir_y_revisiones_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_realizada_por_sistema_revision_409_y_abrir_crea_visita_nueva --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_reporte_y_cierre_en_visita_no_abierta_409 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_dos_veces_200 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_con_cerrada_en_del_cliente --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_distinto_201_con_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_inactivo_o_de_otra_empresa_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_revision --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_reporte --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_reintento_73_horas_mismo_uuid_409 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cierre_de_visita_cerrada_por_sistema_409_visita_ya_cerrada --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.EsquemaTests.test_enum_code_coincide_con_codigos_publicos --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "visita_no_abierta" docs/api/openapi-v1.yaml`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "reportado_en" docs/api/openapi-v1.yaml`
  - PASA (exit 0, nuevo: —) `T5 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T5 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T5`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 44.5 s
- Veredicto: PASA

## 2026-11-18 21:31 — tarea T6,T7 de 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: 2c63d63
- Contrato: modificado y aceptado (3d9aa29, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_servicio_distinto --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_llegada_si_difiere_mas_de_10_minutos --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_no_muestra_llegada_si_difiere_10_minutos_o_menos --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_boton_marcar_revisada_con_incidencia_de_servicio --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_menu_cuenta_incidencia_de_servicio --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "incidencia_servicio" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T6`
  - PASA (exit 0, nuevo: —) `T7 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T5: integra trabajo-sin-conexion-T5"`
  - PASA (exit 0, nuevo: —) `T7 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T6: integra trabajo-sin-conexion-T6"`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 21.3 s
- Veredicto: PASA

## 2026-11-18 21:42 — todo 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: ab6cf72
- Contrato: modificado y aceptado (3d9aa29, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajuste_atraso_app.AjusteAtrasoAppTests.test_default_72_y_rango_1_a_8760 --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" config/settings/base.py`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" .env.example`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T1`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_71_horas_se_guarda --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_73_horas_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_manual_sigue_con_168_horas --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_reintento_73_horas_mismo_uuid_es_duplicada --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_pendiente_con_abierta_en_de_ayer --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_futura_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abierta_en_futura_tolerada_cuenta_revisiones_al_cerrar --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_no_toma_pendiente_de_dia_posterior --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cerrada_en_anterior_a_abierta_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_reporte_guarda_reportado_en --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cierre_por_sistema_usa_reportado_en --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_revision_en_visita_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_reporte_en_visita_cancelada --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_cierre_de_visita_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_distinto_guarda_servicio_e_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_igual_sin_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_inactivo_o_de_otra_empresa_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_valida_contra_la_planilla_del_servicio_enviado --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_visita_nueva_compara_con_servicio_del_punto --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.IncidenciaServicioTests.test_cuenta_sin_revisar_y_marcar_revisada_la_saca --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_no_cierra_visita_con_actividad_reciente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_cierra_visita_vieja_sin_actividad --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 800 --subtarea T2`
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
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T2: integra trabajo-sin-conexion-T2"`
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T3: integra trabajo-sin-conexion-T3"`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_71_horas_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_73_horas_400_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_reporte_73_horas_400_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_abierta_en_de_ayer_abre_el_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_hora_futura_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cancelado_por_cierre_nocturno_abrir_y_revisiones_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_realizada_por_sistema_revision_409_y_abrir_crea_visita_nueva --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_reporte_y_cierre_en_visita_no_abierta_409 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_dos_veces_200 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_con_cerrada_en_del_cliente --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_distinto_201_con_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_inactivo_o_de_otra_empresa_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_revision --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_reporte --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_reintento_73_horas_mismo_uuid_409 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cierre_de_visita_cerrada_por_sistema_409_visita_ya_cerrada --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.EsquemaTests.test_enum_code_coincide_con_codigos_publicos --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "visita_no_abierta" docs/api/openapi-v1.yaml`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "reportado_en" docs/api/openapi-v1.yaml`
  - PASA (exit 0, nuevo: —) `T5 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T5 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T5`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_servicio_distinto --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_llegada_si_difiere_mas_de_10_minutos --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_no_muestra_llegada_si_difiere_10_minutos_o_menos --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_boton_marcar_revisada_con_incidencia_de_servicio --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_menu_cuenta_incidencia_de_servicio --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "incidencia_servicio" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T6`
  - PASA (exit 0, nuevo: —) `T7 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T5: integra trabajo-sin-conexion-T5"`
  - PASA (exit 0, nuevo: —) `T7 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T6: integra trabajo-sin-conexion-T6"`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - FALLA (exit 1, nuevo: —) `cierre global [cmd] ./venv/Scripts/python.exe -m ruff check .`
    ```
    E501 Line too long (90 > 88)
     --> config\tests\test_ajuste_atraso_app.py:1:89
      |
    1 | """Ajuste `ATRASO_MAXIMO_APP_HORAS`: atraso máximo de lo que manda la app sin conexión."""
      |                                                                                         ^^
    2 |
    3 | import os
      |
    
    Found 1 error.
    ```
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; modificados y sin seguimiento; se excluyen docs/planes, estado, bitácora, decisiones y metodo)`
- Omitido (no toca .claude/, docs/plantilla-plan.md): `py -3 -m pytest .claude/hooks -q`
- duración: 260.1 s
- Veredicto: FALLA

## 2026-11-18 21:47 — todo 2026-11-18-trabajo-sin-conexion.md

- HEAD verificado: 0f65929
- Contrato: modificado y aceptado (3d9aa29, decisión del usuario)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test config.tests.test_ajuste_atraso_app.AjusteAtrasoAppTests.test_default_72_y_rango_1_a_8760 --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" config/settings/base.py`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" .env.example`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 80 --subtarea T1`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_71_horas_se_guarda --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_revision_73_horas_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_manual_sigue_con_168_horas --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.AtrasoAppTests.test_reintento_73_horas_mismo_uuid_es_duplicada --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_pendiente_con_abierta_en_de_ayer --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_futura_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abierta_en_futura_tolerada_cuenta_revisiones_al_cerrar --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_abrir_con_abierta_en_no_toma_pendiente_de_dia_posterior --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cerrada_en_anterior_a_abierta_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_reporte_guarda_reportado_en --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.HoraClienteTests.test_cierre_por_sistema_usa_reportado_en --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_revision_en_visita_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_reporte_en_visita_cancelada --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.VisitaNoAbiertaTests.test_cierre_de_visita_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_distinto_guarda_servicio_e_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_igual_sin_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_servicio_inactivo_o_de_otra_empresa_falla --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_valida_contra_la_planilla_del_servicio_enviado --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.ServicioEnviadoTests.test_visita_nueva_compara_con_servicio_del_punto --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.IncidenciaServicioTests.test_cuenta_sin_revisar_y_marcar_revisada_la_saca --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_no_cierra_visita_con_actividad_reciente --keepdb`
  - PASA (exit 0, nuevo: sí) `T2 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion_servicios.CierreNocturnoTests.test_cierra_visita_vieja_sin_actividad --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `T2 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 800 --subtarea T2`
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
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T2: integra trabajo-sin-conexion-T2"`
  - PASA (exit 0, nuevo: —) `T4 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T3: integra trabajo-sin-conexion-T3"`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_71_horas_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_revision_73_horas_400_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AtrasoApiTests.test_reporte_73_horas_400_atraso_excedido --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_abierta_en_de_ayer_abre_el_pendiente --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_abrir_con_hora_futura_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cancelado_por_cierre_nocturno_abrir_y_revisiones_201 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_realizada_por_sistema_revision_409_y_abrir_crea_visita_nueva --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_reporte_y_cierre_en_visita_no_abierta_409 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_dos_veces_200 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cerrar_con_cerrada_en_del_cliente --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_distinto_201_con_incidencia --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.ServicioApiTests.test_servicio_inactivo_o_de_otra_empresa_400 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_revision --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_mismo_uuid_no_duplica_reporte --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.IdempotenciaApiTests.test_reintento_73_horas_mismo_uuid_409 --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.AbrirCerrarApiTests.test_cierre_de_visita_cerrada_por_sistema_409_visita_ya_cerrada --keepdb`
  - PASA (exit 0, nuevo: sí) `T5 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_sin_conexion.EsquemaTests.test_enum_code_coincide_con_codigos_publicos --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "visita_no_abierta" docs/api/openapi-v1.yaml`
  - PASA (exit 0, nuevo: —) `T5 [grep-1] grep -n "reportado_en" docs/api/openapi-v1.yaml`
  - PASA (exit 0, nuevo: —) `T5 [cmd] T=$(mktemp) && PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py spectacular --validate --file "$(cygpath -w "$T")" && diff -q --strip-trailing-cr "$T" docs/api/openapi-v1.yaml; r=$?; rm -f "$T"; exit $r`
  - PASA (exit 0, nuevo: —) `T5 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas apps.api --keepdb`
  - PASA (exit 0, nuevo: —) `T5 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 650 --subtarea T5`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_servicio_distinto --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_muestra_llegada_si_difiere_mas_de_10_minutos --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_ficha_no_muestra_llegada_si_difiere_10_minutos_o_menos --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_boton_marcar_revisada_con_incidencia_de_servicio --keepdb`
  - PASA (exit 0, nuevo: sí) `T6 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas.tests.test_panel_sin_conexion.FichaSinConexionTests.test_menu_cuenta_incidencia_de_servicio --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "incidencia_servicio" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [grep-1] grep -n "ATRASO_MAXIMO_APP_HORAS" docs/01-modelo-y-arquitectura.md`
  - PASA (exit 0, nuevo: —) `T6 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.visitas --keepdb`
  - PASA (exit 0, nuevo: —) `T6 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 300 --subtarea T6`
  - PASA (exit 0, nuevo: —) `T7 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T5: integra trabajo-sin-conexion-T5"`
  - PASA (exit 0, nuevo: —) `T7 [cmd] git log --oneline plan/trabajo-sin-conexion | grep -q "T6: integra trabajo-sin-conexion-T6"`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py check`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test --keepdb`
  - PASA (exit 0, nuevo: —) `cierre global [cmd] ./venv/Scripts/python.exe -m ruff check .`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; modificados y sin seguimiento; se excluyen docs/planes, estado, bitácora, decisiones y metodo)`
- Omitido (no toca .claude/, docs/plantilla-plan.md): `py -3 -m pytest .claude/hooks -q`
- duración: 262.3 s
- Veredicto: PASA

