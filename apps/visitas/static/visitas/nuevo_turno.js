/* Nuevo turno: atajos, plano sincronizado con la lista y resumen en vivo.
   Se inicializa al cargar el documento y en los eventos de htmx: sirve para el panel
   lateral (contenido insertado) y para la página completa. */
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
      // Los puntos con `data-asignado` (turno de otro empleado) no entran en este atajo.
      vencidos: function (fila) { return !fila.dataset.asignado && fila.dataset.estado === "vencida" || fila.dataset.estado === "proxima"; },
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
    iniciarTirador(raiz);
  }

  // Ancho del panel lateral: un tirador en el borde izquierdo, con puntero o flechas.
  // Solo cambia el ancho; el valor vive en --ancho-nuevo-turno de #panel-lateral, que
  // solo se aplica mientras contiene un nuevo turno (los demás paneles siguen en 520 px).
  var ANCHO_MINIMO = 420;
  var PASO_TECLADO = 32;

  function iniciarTirador(raiz) {
    var panel = raiz.closest("#panel-lateral");
    if (!panel) { return; }
    var tirador = document.createElement("div");
    tirador.className = "tirador-ancho";
    tirador.setAttribute("role", "separator");
    tirador.setAttribute("aria-orientation", "vertical");
    tirador.setAttribute("aria-label", "Ancho del panel");
    tirador.tabIndex = 0;
    raiz.prepend(tirador);

    function fijar(ancho) {
      var maximo = Math.max(ANCHO_MINIMO, window.innerWidth - 120);
      var valor = Math.round(Math.min(Math.max(ancho, ANCHO_MINIMO), maximo));
      panel.style.setProperty("--ancho-nuevo-turno", valor + "px");
      tirador.setAttribute("aria-valuenow", String(valor));
    }

    tirador.addEventListener("pointerdown", function (evento) {
      evento.preventDefault();
      tirador.setPointerCapture(evento.pointerId);
      panel.classList.add("redimensionando");
    });
    tirador.addEventListener("pointermove", function (evento) {
      if (tirador.hasPointerCapture(evento.pointerId)) { fijar(window.innerWidth - evento.clientX); }
    });
    function soltar() { panel.classList.remove("redimensionando"); }
    tirador.addEventListener("pointerup", soltar);
    tirador.addEventListener("pointercancel", soltar);
    tirador.addEventListener("keydown", function (evento) {
      var delta = { ArrowLeft: PASO_TECLADO, ArrowRight: -PASO_TECLADO }[evento.key];
      if (!delta) { return; }
      evento.preventDefault();
      fijar(panel.getBoundingClientRect().width + delta);
    });
  }

  function iniciarPlano(contenedor, planos, raiz, porPunto, marcar, sincronizar) {
    var selector = raiz.querySelector("#turno-plano-selector");
    var mapa = L.map(contenedor, { crs: L.CRS.Simple, minZoom: -4, maxZoom: 2, attributionControl: false, keyboard: false });
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
    // Al cambiar el ancho del panel, el mapa recalcula su tamaño.
    if (typeof ResizeObserver !== "undefined") {
      new ResizeObserver(function () { mapa.invalidateSize(); }).observe(contenedor);
    }
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

  function registrar() { buscar(document); }

  // No se usa el registro de htmx, que depende del orden de carga. htmx:load sube hasta
  // document cuando htmx inserta contenido (panel lateral); iniciar es idempotente.
  document.addEventListener("htmx:load", function (evento) { buscar(evento.target); });
  document.addEventListener("htmx:afterSwap", function (evento) { buscar(evento.target); });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", registrar);
  } else {
    registrar();
  }
})();
