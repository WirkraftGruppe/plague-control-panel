/* Hoja de QR: el botón Imprimir abre el diálogo de impresión del navegador. */
(function () {
  "use strict";

  var boton = document.getElementById("imprimir-hoja");
  if (boton) {
    boton.addEventListener("click", function () {
      window.print();
    });
  }
})();
