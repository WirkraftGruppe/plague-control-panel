/* Editor del plano: marcadores arrastrables (x, y en fracción 0 a 1); alta y ubicación de puntos con clic dentro de un modo explícito. */
(function () {
  "use strict";

  var contenedor = document.getElementById("plano-editor");
  var origen = document.getElementById("datos-plano");
  if (!contenedor || !origen || typeof L === "undefined") {
    return;
  }
  var datos = JSON.parse(origen.textContent);
  var mensaje = document.getElementById("plano-mensaje");
  var formulario = document.getElementById("plano-alta");
  var ETIQUETAS = {
    al_dia: "Al día",
    proxima: "Próxima",
    vencida: "Vencida",
    sin_programar: "Sin programar",
  };

  var limites = [[0, 0], [datos.alto, datos.ancho]];
  var mapa = L.map(contenedor, {
    crs: L.CRS.Simple,
    minZoom: -4,
    maxZoom: 2,
    attributionControl: false,
  });
  L.imageOverlay(datos.imagen, limites).addTo(mapa);
  mapa.fitBounds(limites);
  mapa.setMaxBounds(L.latLngBounds(limites).pad(0.25));

  function fraccion(valor) {
    return Math.min(1, Math.max(0, valor));
  }

  /* y crece hacia abajo en el plano y hacia arriba en Leaflet. */
  function aLatLng(x, y) {
    return L.latLng(datos.alto * (1 - y), datos.ancho * x);
  }

  function deLatLng(latlng) {
    return { x: fraccion(latlng.lng / datos.ancho), y: fraccion(1 - latlng.lat / datos.alto) };
  }

  function icono(estado, sinPosicion) {
    var clase = "marcador marcador-" + estado + (sinPosicion ? " marcador-sin-posicion" : "");
    return L.divIcon({ className: clase, iconSize: [22, 22] });
  }

  function avisar(texto) {
    mensaje.textContent = texto;
  }

  var marcadores = {};

  /* Un handler propio de htmx.ajax reemplaza al de fábrica: el éxito se lee del estado HTTP. */
  function exito(respuesta) {
    var estado = respuesta && respuesta.xhr ? respuesta.xhr.status : 0;
    return estado >= 200 && estado <= 299;
  }

  /* Modo del clic en el plano: null, {tipo: "alta"} o {tipo: "ubicar", punto}. */
  var modo = null;
  var botonCrear = document.getElementById("plano-crear");
  var textoModo = document.getElementById("plano-modo");
  var provisorio = null;

  function botonesUbicar() {
    return document.querySelectorAll("[data-ubicar]");
  }

  function fijarModo(nuevo) {
    modo = nuevo;
    if (!nuevo && provisorio) {
      provisorio.remove();
      provisorio = null;
    }
    if (!nuevo && formulario) {
      formulario.hidden = true;
    }
    contenedor.classList.toggle("modo-activo", !!nuevo);
    if (botonCrear) {
      botonCrear.setAttribute("aria-pressed", nuevo && nuevo.tipo === "alta" ? "true" : "false");
    }
    botonesUbicar().forEach(function (boton) {
      var activo = nuevo && nuevo.tipo === "ubicar" && String(nuevo.punto.id) === boton.dataset.ubicar;
      boton.setAttribute("aria-pressed", activo ? "true" : "false");
    });
    if (!nuevo) {
      textoModo.textContent = "";
    } else if (nuevo.tipo === "alta") {
      textoModo.textContent = "Modo alta: haga clic en el plano para ubicar el nuevo punto. Escape cancela.";
    } else {
      textoModo.textContent = "Modo ubicar: haga clic en el plano para ubicar " + nuevo.punto.nombre + ". Escape cancela.";
    }
  }

  function ubicar(punto, posicion) {
    htmx.ajax("POST", punto.url, {
      source: contenedor,
      swap: "none",
      values: { plano: datos.plano, x: posicion.x.toFixed(4), y: posicion.y.toFixed(4) },
      handler: function (elemento, respuesta) {
        if (exito(respuesta)) {
          window.location.reload();
        } else {
          avisar("No se pudo ubicar " + punto.nombre + " en el plano.");
        }
      },
    });
  }

  function guardar(marcador, punto) {
    var nueva = deLatLng(marcador.getLatLng());
    htmx.ajax("POST", punto.url, {
      source: contenedor,
      swap: "none",
      values: { x: nueva.x.toFixed(4), y: nueva.y.toFixed(4) },
      handler: function (elemento, respuesta) {
        if (exito(respuesta)) {
          punto.x = nueva.x;
          punto.y = nueva.y;
          marcador.getElement().classList.remove("marcador-sin-posicion");
          avisar("Posición de " + punto.nombre + " guardada.");
        } else {
          marcador.setLatLng(aLatLng(punto.x === null ? 0.5 : punto.x, punto.y === null ? 0.5 : punto.y));
          avisar("No se pudo guardar la posición de " + punto.nombre + ".");
        }
      },
    });
  }

  // El nombre viene de la base de datos: el tooltip se arma con textContent.
  function textoTooltip(punto) {
    var el = document.createElement("span");
    el.textContent = punto.nombre + " · " + (ETIQUETAS[punto.estado] || "");
    return el;
  }

  datos.puntos.forEach(function (punto) {
    var sinPosicion = punto.x === null || punto.y === null;
    var marcador = L.marker(aLatLng(sinPosicion ? 0.5 : punto.x, sinPosicion ? 0.5 : punto.y), {
      draggable: true,
      icon: icono(punto.estado, sinPosicion),
      title: punto.nombre,
    }).addTo(mapa);
    marcador.bindTooltip(textoTooltip(punto));
    marcador.on("dragend", function () {
      guardar(marcador, punto);
    });
    marcador.on("click", function (evento) {
      L.DomEvent.stopPropagation(evento);
    });
    marcadores[punto.id] = marcador;
  });

  if (botonCrear) {
    botonCrear.addEventListener("click", function () {
      fijarModo(modo && modo.tipo === "alta" ? null : { tipo: "alta" });
    });
  }
  botonesUbicar().forEach(function (boton) {
    boton.addEventListener("click", function () {
      var punto = datos.sin_ubicar.filter(function (p) {
        return String(p.id) === boton.dataset.ubicar;
      })[0];
      var mismo = modo && modo.tipo === "ubicar" && modo.punto === punto;
      fijarModo(mismo || !punto ? null : { tipo: "ubicar", punto: punto });
    });
  });
  document.addEventListener("keydown", function (evento) {
    if (evento.key === "Escape" && modo) {
      fijarModo(null);
    }
  });

  mapa.on("click", function (evento) {
    if (!modo) {
      return;
    }
    var posicion = deLatLng(evento.latlng);
    if (modo.tipo === "ubicar") {
      ubicar(modo.punto, posicion);
      return;
    }
    if (!formulario) {
      return;
    }
    document.getElementById("plano-alta-x").value = posicion.x.toFixed(4);
    document.getElementById("plano-alta-y").value = posicion.y.toFixed(4);
    if (provisorio) {
      provisorio.setLatLng(evento.latlng);
    } else {
      provisorio = L.marker(evento.latlng, { icon: icono("sin_programar", true) }).addTo(mapa);
    }
    formulario.hidden = false;
    document.getElementById("plano-alta-nombre").focus();
  });

  /* Contrato con apps/panel: <ul id="estado-puntos"> con un <li data-punto data-estado> por punto. */
  document.addEventListener("htmx:afterSwap", function () {
    var lista = document.getElementById("estado-puntos");
    if (!lista) {
      return;
    }
    lista.querySelectorAll("li[data-punto]").forEach(function (item) {
      var marcador = marcadores[item.dataset.punto];
      if (marcador) {
        var sinPosicion = marcador.getElement().classList.contains("marcador-sin-posicion");
        marcador.setIcon(icono(item.dataset.estado, sinPosicion));
      }
    });
  });
})();
