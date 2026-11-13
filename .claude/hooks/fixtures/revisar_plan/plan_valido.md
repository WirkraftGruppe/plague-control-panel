# Plan: ejemplo válido

- **slug**: `ejemplo`
- **ruta**: completo
- **seguridad**: no

## Subtareas

### T1 — Crear algo

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/uno/nuevo.py`, `apps/uno/migrations/0002_x.py`
- **Skill a leer antes**: `.claude/skills/convenciones-proyecto/SKILL.md` § Comandos canónicos
- **Criterios**:
  - `[test]` `PYTHONIOENCODING=utf-8 DJANGO_ENV=development ./venv/Scripts/python.exe manage.py test apps.uno.tests.test_a.PruebaTests.test_nuevo --keepdb`
  - `[test]` `py -3 -m pytest .claude/hooks/test_viejo.py::test_nuevo -q`
  - `[grep-1]` `grep -n hola apps/uno/nuevo.py`
  - `[cmd]` `./venv/Scripts/python.exe manage.py check`

### T2 — Otra cosa

- **Ola**: 1
- **Depende de**: —
- **Puede tocar**: `apps/dos/migrations/0002_y.py`
- **Criterios**:
  - `[existe]` `apps/dos`

### T3 — Integración ola 1 (principal)

- **Ola**: 1
- **Depende de**: T1, T2
- **Criterios**:
  - `[cmd]` `git log --oneline | grep -q "T1: integra"`
