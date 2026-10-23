/* Plano de solo lectura de la ficha del sitio: puntos numerados y resaltado cruzado con la lista (data-punto). */
(function () {
  "use strict";

  var contenedor = document.getElementById("ficha-plano");
  var origen = document.getElementById("datos-ficha-plano");
  var lista = document.getElementById("ficha-puntos");
  if (!contenedor || !origen || !lista || typeof L === "undefined") {
    return;
  }
  var planos = JSON.parse(origen.textContent);
  var selector = document.getElementById("ficha-plano-selector");
  var mapa = L.map(contenedor, { crs: L.CRS.Simple, minZoom: -4, maxZoom: 2, attributionControl: false });
  var capa = L.layerGroup().addTo(mapa);
  var marcadores = {};

  function fila(id) {
    return lista.querySelector('[data-punto="' + id + '"]');
  }

  function resaltar(id, activo) {
    var item = fila(id);
    if (item) {
      item.classList.toggle("punto-resaltado", activo);
    }
    var marcador = marcadores[id];
    if (marcador && marcador.getElement()) {
      marcador.getElement().classList.toggle("marcador-resaltado", activo);
    }
  }

  function icono(punto, estado) {
    return L.divIcon({
      className: "marcador marcador-" + estado,
      html: String(punto.numero),
      iconSize: [22, 22],
    });
  }

  function mostrar(plano) {
    capa.clearLayers();
    marcadores = {};
    var limites = [[0, 0], [plano.alto, plano.ancho]];
    L.imageOverlay(plano.imagen, limites).addTo(capa);
    mapa.fitBounds(limites);
    mapa.setMaxBounds(L.latLngBounds(limites).pad(0.25));
    plano.puntos.forEach(function (punto) {
      var marcador = L.marker([plano.alto * (1 - punto.y), plano.ancho * punto.x], {
        icon: icono(punto, punto.estado),
        title: punto.nombre + " · " + punto.estado_texto,
        keyboard: false,
      }).addTo(capa);
      marcador.on("mouseover", function () { resaltar(punto.id, true); });
      marcador.on("mouseout", function () { resaltar(punto.id, false); });
      marcadores[punto.id] = marcador;
      marcador.punto = punto;
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

  lista.querySelectorAll("[data-punto]").forEach(function (item) {
    var id = item.dataset.punto;
    item.addEventListener("mouseenter", function () { resaltar(id, true); });
    item.addEventListener("mouseleave", function () { resaltar(id, false); });
    item.addEventListener("focusin", function () { resaltar(id, true); });
    item.addEventListener("focusout", function () { resaltar(id, false); });
  });

  /* Contrato con apps/panel: <ul id="estado-puntos"> con un <li data-punto data-estado> por punto. */
  document.addEventListener("htmx:afterSwap", function () {
    var estados = document.getElementById("estado-puntos");
    if (!estados) {
      return;
    }
    estados.querySelectorAll("li[data-punto]").forEach(function (item) {
      var marcador = marcadores[item.dataset.punto];
      if (marcador) {
        marcador.punto.estado = item.dataset.estado;
        marcador.setIcon(icono(marcador.punto, item.dataset.estado));
      }
      var enLista = fila(item.dataset.punto);
      if (enLista) {
        enLista.dataset.estado = item.dataset.estado;
      }
    });
  });
})();
