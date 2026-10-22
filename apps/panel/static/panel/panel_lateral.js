/* Panel lateral: se abre tras un swap de HTMX iniciado por [data-abre-panel]. */
(function () {
  "use strict";

  var contenedor = document.getElementById("panel-lateral");
  if (!contenedor) {
    return;
  }
  var origen = null;
  var FOCALIZABLES =
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
    'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function controles() {
    return Array.from(contenedor.querySelectorAll(FOCALIZABLES));
  }

  function cerrar() {
    contenedor.replaceChildren();
    contenedor.hidden = true;
    if (origen && origen.isConnected) {
      origen.focus();
    }
    origen = null;
  }

  // Recuerda qué elemento pidió el panel, para devolverle el foco al cerrar.
  document.body.addEventListener("htmx:beforeRequest", function (evento) {
    var disparador = evento.detail.elt && evento.detail.elt.closest("[data-abre-panel]");
    if (disparador) {
      origen = disparador;
    }
  });

  document.body.addEventListener("htmx:afterSwap", function (evento) {
    if (evento.detail.target !== contenedor || !origen) {
      return;
    }
    contenedor.hidden = false;
    var primero = controles()[0];
    if (primero) {
      primero.focus();
    }
  });

  document.addEventListener("click", function (evento) {
    if (evento.target.closest("[data-cierra-panel]")) {
      evento.preventDefault();
      cerrar();
    }
  });

  document.addEventListener("keydown", function (evento) {
    if (contenedor.hidden) {
      return;
    }
    if (evento.key === "Escape") {
      cerrar();
      return;
    }
    // El foco no sale del panel mientras está abierto (aria-modal).
    if (evento.key === "Tab") {
      var lista = controles();
      if (!lista.length) {
        return;
      }
      var primero = lista[0];
      var ultimo = lista[lista.length - 1];
      if (evento.shiftKey && document.activeElement === primero) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primero.focus();
      }
    }
  });
})();
