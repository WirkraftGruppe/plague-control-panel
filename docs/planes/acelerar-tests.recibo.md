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

