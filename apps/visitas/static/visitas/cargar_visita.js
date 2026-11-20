/* Cargar visita: en cada producto, la dosis solo se pide si el producto es de dosis
   variable (con la habitual precargada) y el lote viene con el último usado.
   Los datos salen de los `data-*` del <option> elegido. */
(function () {
  "use strict";

  function iniciar(bloque) {
    var selector = bloque.querySelector("select[name$='-producto']");
    var lote = bloque.querySelector("input[name$='-lote']");
    var dosis = bloque.querySelector("input[name$='-dosis']");
    var unidad = bloque.querySelector("input[name$='-unidad_dosis']");
    var campos = bloque.querySelectorAll("[data-dosis-campo]");
    if (!selector) { return; }

    function actualizar(precargar) {
      var opcion = selector.selectedOptions[0];
      var variable = !!opcion && opcion.dataset.dosisVariable === "1";
      campos.forEach(function (campo) { campo.hidden = !variable; });
      if (!precargar || !opcion || !opcion.value) { return; }
      if (lote && !lote.value) { lote.value = opcion.dataset.lote || ""; }
      if (variable && dosis && !dosis.value) { dosis.value = opcion.dataset.dosis || ""; }
      if (variable && unidad && !unidad.value) { unidad.value = opcion.dataset.unidadDosis || ""; }
    }

    selector.addEventListener("change", function () { actualizar(true); });
    actualizar(false);
  }

  function registrar() {
    document.querySelectorAll("[data-producto]").forEach(iniciar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", registrar);
  } else {
    registrar();
  }
})();
