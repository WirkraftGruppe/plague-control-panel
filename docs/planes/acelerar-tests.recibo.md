## 2026-11-14 09:56 — tarea T1 de 2026-11-14-acelerar-tests.md

- HEAD verificado: 3f28d9e
- Contrato: intacto (congelado en 49cfb0b)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T1 [test] py -3 -m pytest .claude/hooks/test_revisar_plan.py::test_avisa_criterio_que_corre_la_suite_completa -q`
  - PASA (exit 0, nuevo: sí) `T1 [test] py -3 -m pytest .claude/hooks/test_revisar_plan.py::test_no_avisa_criterio_con_apps_nombradas -q`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "suite completa" docs/plantilla-plan.md`
  - PASA (exit 0, nuevo: —) `T1 [grep-1] grep -n "suite completa" .claude/skills/convenciones-proyecto/SKILL.md`
  - PASA (exit 0, nuevo: —) `T1 [cmd] py -3 -m pytest .claude/hooks/test_revisar_plan.py .claude/hooks/test_verificar_plan.py -q`
  - PASA (exit 0, nuevo: —) `T1 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T1`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 75.0 s
- Veredicto: PASA

## 2026-11-14 10:00 — tarea T2 de 2026-11-14-acelerar-tests.md

- HEAD verificado: e0df0d4
- Contrato: intacto (congelado en 49cfb0b)
- Criterios:
  - PASA (exit 0, nuevo: sí) `T2 [test] py -3 -m pytest .claude/hooks/test_verificar.py::test_todo_omite_pytest_de_hooks_si_el_plan_no_toca_el_metodo -q`
  - PASA (exit 0, nuevo: sí) `T2 [test] py -3 -m pytest .claude/hooks/test_verificar.py::test_todo_corre_pytest_de_hooks_si_el_plan_toca_settings_json -q`
  - PASA (exit 0, nuevo: sí) `T2 [test] py -3 -m pytest .claude/hooks/test_verificar.py::test_cierre_sin_plan_corre_los_comandos_con_si_toca -q`
  - PASA (exit 0, nuevo: sí) `T2 [test] py -3 -m pytest .claude/hooks/test_verificar.py::test_todo_corre_pytest_de_hooks_sin_base_resoluble -q`
  - PASA (exit 0, nuevo: —) `T2 [grep-1] grep -n "si_toca" .claude/hooks/cierre_global.json`
  - PASA (exit 0, nuevo: —) `T2 [cmd] py -3 -m pytest .claude/hooks/test_verificar.py .claude/hooks/test_verificar_plan.py -q`
  - PASA (exit 0, nuevo: —) `T2 [cmd] bash .claude/hooks/presupuesto.sh . '<commit_base>' 400 --subtarea T2`
  - PASA (exit 0, nuevo: —) `versionados limpios (sin cambios versionados; solo las rutas de Puede tocar; plan y recibo excluidos)`
  - PASA (exit 0, nuevo: —) `commits de la tarea dentro de Puede tocar`
- duración: 117.2 s
- Veredicto: PASA

