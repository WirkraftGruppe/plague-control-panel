/* Nuevo turno: atajos, plano sincronizado con la lista y resumen en vivo.
   Se inicializa con htmx.onLoad: sirve para el panel lateral (contenido insertado)
   y para la página completa. */
(function () {
  "use strict";

  function iniciar(raiz) {
    if (raiz.dataset.iniciado) { return; }
    raiz.dataset.iniciado = "1";

    var filas = Array.prototype.slice.call(raiz.querySelectorAll("tr[data-punto]"));
    var porPunto = {};
    filas.forEach(function (fila) {
      porPunto[fila.dataset.punto] = {
        fila: fila,
        casilla: fila.querySelector("input[type=checkbox]"),
        servicio: fila.querySelector("select"),
        marcadores: [],
      };
    });
    var resumen = raiz.querySelector("[data-resumen]");
    var crear = raiz.querySelector("[data-crear]");

    function textoServicio(entrada) {
      var opcion = entrada.servicio && entrada.servicio.selectedOptions[0];
      return opcion && opcion.value ? opcion.textContent : "Sin servicio";
    }

    function actualizarResumen() {
      var elegidos = filas.filter(function (fila) { return porPunto[fila.dataset.punto].casilla.checked; });
      var vencidos = elegidos.filter(function (fila) { return fila.dataset.estado === "vencida"; }).length;
      var porServicio = {};
      elegidos.forEach(function (fila) {
        var nombre = textoServicio(porPunto[fila.dataset.punto]);
        porServicio[nombre] = (porServicio[nombre] || 0) + 1;
      });
      if (resumen) {
        var partes = [elegidos.length + (elegidos.length === 1 ? " punto" : " puntos")];
        partes.push(vencidos + (vencidos === 1 ? " vencido" : " vencidos"));
        Object.keys(porServicio).sort().forEach(function (nombre) {
          partes.push(nombre + ": " + porServicio[nombre]);
        });
        resumen.textContent = elegidos.length ? partes.join(" · ") : "Ningún punto elegido.";
      }
      // Sin puntos en el sitio el HTML ya lo trae deshabilitado; aquí se sigue la elección.
      if (crear && filas.length) { crear.disabled = elegidos.length === 0; }
    }

    function sincronizar(id) {
      var entrada = porPunto[id];
      var elegido = entrada.casilla.checked;
      entrada.fila.classList.toggle("fila-elegida", elegido);
      entrada.marcadores.forEach(function (marcador) {
        var elemento = marcador.getElement();
        if (elemento) { elemento.classList.toggle("marcador-elegido", elegido); }
      });
      actualizarResumen();
    }

    function marcar(id, valor) {
      porPunto[id].casilla.checked = valor;
      sincronizar(id);
    }

    Object.keys(porPunto).forEach(function (id) {
      porPunto[id].casilla.addEventListener("change", function () { sincronizar(id); });
      if (porPunto[id].servicio) {
        porPunto[id].servicio.addEventListener("change", actualizarResumen);
      }
    });

    var ATAJOS = {
      todos: function () { return true; },
      vencidos: function (fila) { return fila.dataset.estado === "vencida" || fila.dataset.estado === "proxima"; },
      ninguno: function () { return false; },
    };
    raiz.querySelectorAll("[data-atajo]").forEach(function (boton) {
      boton.addEventListener("click", function () {
        var criterio = ATAJOS[boton.dataset.atajo];
        filas.forEach(function (fila) { marcar(fila.dataset.punto, criterio(fila)); });
      });
    });

    var contenedor = raiz.querySelector("#turno-plano");
    var origen = raiz.querySelector("#datos-turno-plano");
    if (contenedor && origen && typeof L !== "undefined") {
      iniciarPlano(contenedor, JSON.parse(origen.textContent), raiz, porPunto, marcar, sincronizar);
    }
    filas.forEach(function (fila) { sincronizar(fila.dataset.punto); });
    actualizarResumen();
  }

  function iniciarPlano(contenedor, planos, raiz, porPunto, marcar, sincronizar) {
    var selector = raiz.querySelector("#turno-plano-selector");
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
        marcador.on("click", function () { marcar(String(punto.id), !entrada.casilla.checked); });
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
    // El panel lateral se muestra justo después de insertar el contenido.
    setTimeout(function () { mapa.invalidateSize(); mapa.fitBounds([[0, 0], [elegido().alto, elegido().ancho]]); }, 50);
  }

  function buscar(elemento) {
    if (elemento.matches && elemento.matches("[data-nuevo-turno]")) {
      iniciar(elemento);
    } else if (elemento.querySelectorAll) {
      elemento.querySelectorAll("[data-nuevo-turno]").forEach(iniciar);
    }
  }

  function registrar() {
    if (typeof htmx !== "undefined") { htmx.onLoad(buscar); }
    buscar(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", registrar);
  } else {
    registrar();
  }
})();
