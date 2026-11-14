# Métricas del método

## Tiempos de la suite

Suite de Django, `manage.py test --keepdb`, en la máquina de desarrollo (acelerar-tests):

| Fecha | Cambio | Tests | Tiempo de la suite (s) |
|---|---|---|---|
| 2026-11-14 | antes (PBKDF2) | 977 | 551 |
| 2026-11-14 | después (MD5 solo en tests) | 981 | 101 |

`verificar.py todo`: 2788 s en robustez-listados (criterios de subtarea con la suite entera); 528 s en acelerar-tests (con `pytest .claude/hooks`, porque el plan toca el método).

## Por plan

| Fecha | CLAUDE.md (B) | Inyección (B) | Agentes | Proceso/plan | Verif. final (min) | Comodines | Pendientes | Ruta | Rev. plan (b/d/m) | Rev. cierre (b/d/m) |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-13 | 20714 | 6716 | 6 | 5.4 | — | 0 | 111 | completo | — | — |
| 2026-11-13 | 8046 | 5517 | 3 | 9.7 | 46 | 0 | 133 | completo | 4/0/8 | 4/0/4 |
| 2026-11-14 | 8046 | 5252 | 3 | 10.2 | 27 | 0 | 136 | completo | 3/0/6 | 0/0/4 |
| 2026-11-14 | 8046 | 5862 | 3 | 10.8 | 19 | 0 | 147 | completo | 5/1/4 | 2/1/5 |
| 2026-11-14 | 8046 | 5999 | 3 | 11.4 | 19 | 0 | 151 | completo | 5/1/4 | 2/1/5 |
