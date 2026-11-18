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

