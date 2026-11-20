## 2026-11-20 11:04 — tarea T1,T2 de 2026-11-20-coordinacion-operarios.md

- HEAD verificado: b018b02
- Contrato: intacto (congelado en 794af57)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.DosisHabitualTests.test_dosis_sin_unidad_no_valida --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.DosisHabitualTests.test_sin_dosis_habitual_ni_variable_no_valida --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.DosisHabitualTests.test_panel_edita_dosis_habitual_y_variable --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "update.dosis_variable=True" apps/productos/migrations/0002_dosis_habitual.py`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_catalogo_trae_dosis_y_ultimo_lote_null --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_ultimo_lote_L2291_y_etag_cambia --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_ultimo_lote_no_cruza_empresas --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos.tests.test_dosis_habitual.CatalogoDosisTests.test_consultas_iguales_con_5_y_50_productos --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoCoordinacionTests.test_dos_operarios_comparten_un_punto --keepdb`
  - PASA (exit 0, nuevo: sí) `T1 [test] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.panel.tests.test_cargar_demo.CargarDemoCoordinacionTests.test_productos_con_y_sin_dosis_y_uno_variable --keepdb`
  - PASA (exit 1, nuevo: —) `T1 [grep-0] grep -n "unidad_dosis_por_defecto" apps/productos/models.py apps/productos/serializers.py apps/productos/panel_forms.py apps/panel/demo_historia.py apps/panel/management/commands/cargar_demo.py`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
  - PASA (exit 0, nuevo: —) `T1 [cmd] PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.productos apps.panel --keepdb`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 550 --subtarea T1`
  - PASA (exit 0, nuevo: —) `T2 [cmd] git log --oneline plan/coordinacion-operarios | grep -q "T1: integra coordinacion-operarios-T1"`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 96.1 s
- Veredicto: PASA

