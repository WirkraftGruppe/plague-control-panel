# Plan: demo v1

- **slug**: `demo`
- **fecha**: 2026-10-26
- **commit_base**: el commit cuyo asunto empieza con `docs(plan): demo`. No se escribe acá: el hash se anota en `## Registro de verificación`.

## Subtareas

### T1 — primera tarea

- **Puede tocar**: `a.py`
- **Criterios**:
  - `[cmd]` `echo uno >> marca1.txt`
  - `[cmd]` `echo '<commit_base>' > base_usada.txt`

### T2 — segunda tarea

- **Puede tocar**: `b.py`
- **Criterios**:
  - `[cmd]` `echo dos >> marca2.txt`

## Criterios de cierre global

- `[cmd]` `echo cierre_v1 >> cierre_v1.txt`

## Registro de verificación

commit_base: {{BASE}}

### Estado de subtareas

| Tarea | Estado |
|---|---|
| T1 | hecha |
| T2 | en curso |
