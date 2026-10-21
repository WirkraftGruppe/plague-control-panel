# Protocolo de decisiones

Cómo decide el principal cuando aparece una disyuntiva de diseño o de implementación: cuáles decide solo y deja registradas, cuáles escala al usuario y qué hace mientras el usuario no responde. No repite `CLAUDE.md`: el contrato congelado y el contrato modificado están en su § 4.

Una disyuntiva es un punto donde el plan, los criterios y `convenciones-proyecto` admiten dos o más caminos válidos. Lo que el plan ya fija no es disyuntiva.

## 1. Clasificación

Toda disyuntiva se clasifica antes de actuar. Ante la duda, escalable.

**Autónoma**: se cumplen las tres condiciones a la vez.

- Es reversible.
- Cae dentro del «Puede tocar» de la subtarea.
- No toca datos existentes, contratos de `/api/v1/` ni costos.

Agregar campos, modelos, índices o migraciones aditivas dentro del alcance es autónomo. Las migraciones aditivas solo crean; no alteran ni borran lo que ya existe.

**Escalable**: basta una de estas condiciones.

- Es irreversible.
- Borra, renombra o cambia el tipo de un campo o de una tabla con datos.
- Toca producción o los settings de producción.
- Cambia `/api/v1/`.
- Agrega una dependencia con costo o licencia.
- Toca un modelo fuera del «Puede tocar».
- Contradice `docs/decisiones.md`.
- Es una decisión de producto o de negocio.
- Cambia la arquitectura general.
- Borra apps o pantallas enteras.
- Es el merge a `main`.

Alterar el alcance del plan no es una decisión: es contrato modificado (§ 4 de `CLAUDE.md`) y lo resuelve el usuario.

## 2. Criterios de elección

Entre las opciones válidas se elige aplicando estos criterios en este orden; el primero que distingue a una opción decide.

1. Cumple los criterios congelados del plan.
2. Es consistente con el código existente y con `convenciones-proyecto`.
3. Es reversible.
4. Es simple.

## 3. Registro

Cada decisión autónoma se anota en `### Decisiones del plan`, bajo `## Registro de verificación`, con este formato de una línea:

`- T<n> — disyuntiva — opciones — elección — motivo (una línea) — autónoma — cómo revertir — decidida por Claude, revisable`

- Las decisiones se presentan juntas al usuario al cierre de cada ola.
- Más de cinco decisiones en una subtarea se reportan al cierre de la ola como señal de un plan mal especificado.
- Una decisión autónoma nunca modifica criterios ni el «no incluye» del plan.
- Al fusionar, las decisiones que el usuario acepta se copian a `docs/decisiones.md` con el formato fechado de esa sección.

## 4. Escalamiento

El mensaje al usuario lleva cuatro partes:

1. La disyuntiva, con sus opciones.
2. La opción recomendada, ya evaluada con los criterios del § 2.
3. El motivo de la escalada: qué condición del § 1 la vuelve escalable.
4. La conducta por defecto, es decir, qué ocurre mientras no haya respuesta.

Conducta por defecto, la misma para toda escalada:

- La subtarea bloqueada pasa a «pendiente de decisión» en `### Estado de subtareas`, con la pregunta copiada en el plan.
- El principal sigue con las subtareas que no dependen de ella.
- La pregunta se repite al cierre de la ola.

Nunca se asume la respuesta.

## Ejemplo: decisión autónoma (limpieza de `precision_m` sin pasar por `services`)

Contexto: en `robustez-panel`, ola 1, T1 hacía que corregir las coordenadas de un punto a mano borrara quién y cuándo fijó la ubicación. El panel y el admin guardan el punto con un formulario; la regla del dominio vive en `services.fijar_ubicacion`.

Disyuntiva: limpiar `ubicacion_fijada_por`, `ubicacion_fijada_en` y `precision_m` dentro del formulario, o llamar a `services.fijar_ubicacion` desde la vista y el admin.

Clasificación (§ 1):

- Es reversible: son tres asignaciones en el formulario.
- Cae dentro del «Puede tocar» de T1: los formularios del panel y del admin.
- No toca datos existentes, `/api/v1/` ni costos.
- Resultado: autónoma.

Elección (§ 2): el primer criterio no distingue, porque ambas opciones cumplen los criterios congelados. El segundo sí: el formulario ya guarda los demás campos en un solo `save`, y llamar al servicio habría agregado un segundo guardado sobre el mismo objeto. Se eligió limpiar en el formulario.

Línea de registro (§ 3):

`- T1 — limpieza de la ubicación fijada al corregir coordenadas a mano — formulario del panel y del admin, o llamar a services.fijar_ubicacion — limpiar en el formulario — el formulario guarda los demás campos en un solo save — autónoma — llamar a services.fijar_ubicacion desde la vista y el admin y quitar la limpieza del formulario — decidida por Claude, revisable`

Resultado real: el auditor de seguridad observó después que `precision_m` también debía limpiarse. Eso ya no era una disyuntiva sino una decisión del usuario sobre el alcance, y se trató como tal.

## Ejemplo: decisión escalada (regresión del admin en T1)

Contexto: en `robustez-panel`, T1 pasó sus criterios con los dos verificadores, pero el auditor de seguridad encontró una regresión: el alta de un punto en el admin quedaba rechazada.

Disyuntiva: corregir la regresión en T1 antes de integrar, o integrar T1 tal como está y registrar un pendiente para corregirla después.

Clasificación (§ 1): escalable. Ninguna de las dos opciones es autónoma, por estas razones:

- Dejar el defecto y registrar un pendiente integra en la rama una pantalla existente que ya no cumple su función. Eso altera lo que el plan prometía entregar, y alterar el alcance es contrato modificado, no decisión.
- Corregir exige reabrir una subtarea ya verificada y puede requerir tocar archivos fuera de su «Puede tocar».
- Ninguna de las dos opciones se puede deshacer sin reabrir la subtarea o dejar la regresión en la rama de integración.

Con esas condiciones y la regla de «ante la duda, escalable», la decisión es del usuario.

Mensaje al usuario, como debió escribirse:

> T1 de `robustez-panel` pasó sus 11 criterios con los dos verificadores, pero el auditor de seguridad encontró una regresión: desde T1, el admin rechaza el alta de un punto de control. Hay que decidir antes de integrar.
>
> **Opción A (recomendada)**: corregir en T1 antes de integrar. Cumple los criterios congelados y no deja ninguna pantalla rota en la rama; es reversible, porque la corrección es un commit nuevo `T1: …` que se puede revertir solo. Cuesta una ronda más de verificación.
>
> **Opción B**: integrar T1 y anotar un pendiente `[importante]`. Ahorra la ronda, pero el alta en el admin queda rota hasta que otro plan la corrija, y el pendiente no tiene dueño ni fecha.
>
> **Por qué te lo pregunto**: dejar una regresión en una pantalla existente cambia lo que el plan entrega, es decir, modifica el alcance. Eso no lo decido yo (§ 4 de `CLAUDE.md`).
>
> **Si no respondes**: T1 pasa a «pendiente de decisión» con esta pregunta copiada en el plan; no integro T1 y sigo con T2 y las demás subtareas que no dependen de ella; te repito la pregunta al cierre de la ola. No asumo la opción A.

Qué ocurrió en la realidad: el usuario decidió corregir en T1 antes de integrar (opción A). La ronda 2 de T1 cerró los hallazgos y los dos verificadores volvieron a pasar.
