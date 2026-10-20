/* Nuevo turno: atajos de selección y plano sincronizado con la lista de puntos. */
(function () {
  "use strict";

  var filas = Array.prototype.slice.call(document.querySelectorAll("tr[data-punto]"));
  var porPunto = {};
  filas.forEach(function (fila) {
    porPunto[fila.dataset.punto] = {
      fila: fila,
      casilla: fila.querySelector("input[type=checkbox]"),
      marcadores: [],
    };
  });

  function sincronizar(id) {
    var entrada = porPunto[id];
    var elegido = entrada.casilla.checked;
    entrada.fila.classList.toggle("fila-elegida", elegido);
    entrada.marcadores.forEach(function (marcador) {
      var elemento = marcador.getElement();
      if (elemento) {
        elemento.classList.toggle("marcador-elegido", elegido);
      }
    });
  }

  function marcar(id, valor) {
    porPunto[id].casilla.checked = valor;
    sincronizar(id);
  }

  Object.keys(porPunto).forEach(function (id) {
    porPunto[id].casilla.addEventListener("change", function () {
      sincronizar(id);
    });
  });

  var ATAJOS = {
    todos: function () { return true; },
    vencidos: function (fila) { return fila.dataset.estado === "vencida" || fila.dataset.estado === "proxima"; },
    ninguno: function () { return false; },
  };
  document.querySelectorAll("[data-atajo]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      var criterio = ATAJOS[boton.dataset.atajo];
      filas.forEach(function (fila) {
        marcar(fila.dataset.punto, criterio(fila));
      });
    });
  });

  var contenedor = document.getElementById("turno-plano");
  var origen = document.getElementById("datos-turno-plano");
  if (contenedor && origen && typeof L !== "undefined") {
    iniciarPlano(contenedor, JSON.parse(origen.textContent));
  }
  filas.forEach(function (fila) { sincronizar(fila.dataset.punto); });

  function iniciarPlano(contenedor, planos) {
    var selector = document.getElementById("turno-plano-selector");
    var mapa = L.map(contenedor, { crs: L.CRS.Simple, minZoom: -4, maxZoom: 2, attributionControl: false });
    var capa = L.layerGroup().addTo(mapa);

    function mostrar(plano) {
      capa.clearLayers();
      Object.keys(porPunto).forEach(function (id) { porPunto[id].marcadores = []; });
      var limites = [[0, 0], [plano.alto, plano.ancho]];
      L.imageOverlay(plano.imagen, limites).addTo(capa);
      mapa.fitBounds(limites);
      mapa.setMaxBounds(L.latLngBounds(limites).pad(0.25));
      plano.puntos.forEach(function (punto) {
        var entrada = porPunto[String(punto.id)];
        if (!entrada) { return; }
        var icono = L.divIcon({ className: "marcador marcador-" + punto.estado, iconSize: [22, 22] });
        var marcador = L.marker([plano.alto * (1 - punto.y), plano.ancho * punto.x], {
          icon: icono,
          title: punto.nombre + " · " + punto.estado_texto,
          keyboard: false,
        }).addTo(capa);
        marcador.on("click", function () {
          marcar(String(punto.id), !entrada.casilla.checked);
        });
        marcador.on("mouseover", function () { entrada.fila.classList.add("fila-resaltada"); });
        marcador.on("mouseout", function () { entrada.fila.classList.remove("fila-resaltada"); });
        entrada.marcadores.push(marcador);
        sincronizar(String(punto.id));
      });
    }

    function elegido() {
      var id = selector ? selector.value : String(planos[0].id);
      return planos.filter(function (p) { return String(p.id) === id; })[0] || planos[0];
    }
    if (selector) {
      selector.addEventListener("change", function () { mostrar(elegido()); });
    }
    mostrar(elegido());
  }
})();
