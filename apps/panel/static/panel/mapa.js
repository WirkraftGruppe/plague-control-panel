/* Mapa de sitios: marcadores con los colores del semáforo (tokens de templates/base.html). */
(function () {
  "use strict";

  var COLORES = {
    vencida: "#D92D20",
    proxima: "#E0A100",
    al_dia: "#2E9E5B",
    sin_programar: "#9AA1A9",
  };
  var ETIQUETAS = {
    vencida: "Vencida",
    proxima: "Próxima a vencer",
    al_dia: "Al día",
    sin_programar: "Sin programar",
  };

  var contenedor = document.getElementById("mapa");
  var filtros = document.getElementById("mapa-filtros");
  if (!contenedor) {
    return;
  }

  var mapa = L.map(contenedor).setView([-36.1, -57.8], 8);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    referrerPolicy: "strict-origin-when-cross-origin",
    attribution: "&copy; colaboradores de OpenStreetMap",
  }).addTo(mapa);
  var capa = L.layerGroup().addTo(mapa);

  function fecha(iso) {
    if (!iso) {
      return "sin programar";
    }
    var d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("es-AR");
  }

  function elemento(etiqueta, texto) {
    var el = document.createElement(etiqueta);
    el.textContent = texto;
    return el;
  }

  // El popup se arma con textContent: los nombres vienen de la base de datos.
  function popup(sitio) {
    var caja = document.createElement("div");
    caja.className = "mapa-popup";
    caja.appendChild(elemento("h3", sitio.nombre));
    caja.appendChild(elemento("div", sitio.cliente));
    caja.appendChild(elemento("div", ETIQUETAS[sitio.estado]));
    caja.appendChild(
      elemento("div", "Próximo vencimiento: " + fecha(sitio.vencimiento))
    );
    if (sitio.url_ficha) {
      var enlace = elemento("a", "Ver ficha del sitio");
      enlace.href = sitio.url_ficha;
      caja.appendChild(enlace);
    }
    if (sitio.url_nuevo_turno) {
      var turno = elemento("a", "Nuevo turno");
      turno.href = sitio.url_nuevo_turno;
      caja.appendChild(turno);
    }
    return caja;
  }

  function cargar() {
    var parametros = new URLSearchParams(new FormData(filtros));
    for (var clave of Array.from(parametros.keys())) {
      if (!parametros.get(clave)) {
        parametros.delete(clave);
      }
    }
    fetch(contenedor.dataset.url + "?" + parametros.toString(), {
      credentials: "same-origin",
    })
      .then(function (respuesta) {
        return respuesta.json();
      })
      .then(function (datos) {
        capa.clearLayers();
        var puntos = [];
        datos.sitios.forEach(function (sitio) {
          var color = COLORES[sitio.estado] || COLORES.sin_programar;
          L.circleMarker([sitio.lat, sitio.lng], {
            radius: 9,
            color: "#1A1E23",
            weight: 1,
            fillColor: color,
            fillOpacity: 0.9,
          })
            .bindPopup(popup(sitio))
            .addTo(capa);
          puntos.push([sitio.lat, sitio.lng]);
        });
        if (puntos.length) {
          mapa.fitBounds(puntos, { padding: [30, 30], maxZoom: 14 });
        }
      });
  }

  filtros.addEventListener("change", cargar);
  cargar();
})();
