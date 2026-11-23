/* Monitor S&P 500 · interacción mínima (mejora progresiva: sin JS el dashboard se lee igual). */
(function () {
  "use strict";
  var root = document.documentElement;

  /* --- Gráficos: se dibujan cuando entran en pantalla --- */
  function startCharts() {
    if (!window.Plotly) { root.classList.add("no-plotly"); return; }
    Plotly.register({
      moduleType: "locale", name: "es", dictionary: {},
      format: {
        days: ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
        shortDays: ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
        months: ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                 "septiembre", "octubre", "noviembre", "diciembre"],
        shortMonths: ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
        date: "%d/%m/%Y", decimal: ".", thousands: ","
      }
    });
    var nodes = Array.prototype.slice.call(document.querySelectorAll("[data-chart]"));
    function draw(el) {
      var spec = JSON.parse(document.getElementById(el.getAttribute("data-chart")).textContent);
      spec.config.locale = "es";
      Plotly.newPlot(el, spec.data, spec.layout, spec.config);
    }
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { io.unobserve(e.target); draw(e.target); }
        });
      }, { rootMargin: "300px 0px" });
      nodes.forEach(function (n) { io.observe(n); });
    } else {
      nodes.forEach(draw);
    }
  }
  // Plotly se carga con "defer": está disponible al disparar DOMContentLoaded.
  // Se espera a las fuentes para que Plotly mida bien los textos.
  function whenReady(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }
  whenReady(function () {
    var fonts = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    fonts.then(startCharts, startCharts);
  });

  /* --- Explicaciones: botones ⓘ, panel y preferencia guardada --- */
  var sheet = document.getElementById("info-sheet");
  var toggle = document.getElementById("info-toggle");
  var opener = null;
  function setInfo(on, save) {
    root.classList.toggle("info-off", !on);
    if (toggle) toggle.setAttribute("aria-checked", on ? "true" : "false");
    if (save) { try { localStorage.setItem("monitor-info", on ? "on" : "off"); } catch (e) { /* modo privado */ } }
  }
  setInfo(!root.classList.contains("info-off"), false);
  if (toggle) toggle.addEventListener("click", function () {
    setInfo(toggle.getAttribute("aria-checked") !== "true", true);
  });
  function openInfo(btn) {
    var tpl = document.getElementById("info-" + btn.getAttribute("data-info"));
    if (!tpl || !sheet || typeof sheet.showModal !== "function") return;
    opener = btn;
    document.getElementById("sheet-title").textContent = tpl.getAttribute("data-title");
    var body = document.getElementById("sheet-body");
    body.replaceChildren(tpl.content.cloneNode(true));
    body.scrollTop = 0;
    sheet.showModal();
  }
  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest && ev.target.closest(".info");
    if (btn) { openInfo(btn); return; }
    if (!sheet || !sheet.open) return;
    // Cierra con la X o tocando fuera del panel (el fondo es el propio <dialog>).
    if (ev.target.closest("[data-close]") || ev.target === sheet) sheet.close();
  });
  if (sheet) sheet.addEventListener("close", function () {
    if (opener) { opener.focus(); opener = null; }
  });

  /* --- Navegación: marca la sección visible --- */
  var links = Array.prototype.slice.call(document.querySelectorAll(".subnav a"));
  var list = document.querySelector(".subnav ul");
  if (!links.length || !("IntersectionObserver" in window)) return;
  var byId = {};
  links.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
  var current = null;
  function setCurrent(a) {
    if (a === current) return;
    if (current) current.removeAttribute("aria-current");
    current = a;
    a.setAttribute("aria-current", "true");
    // Mantiene visible el enlace activo en el carrusel del teléfono sin mover la página.
    var l = a.offsetLeft - list.offsetLeft, r = l + a.offsetWidth;
    if (l < list.scrollLeft || r > list.scrollLeft + list.clientWidth) {
      list.scrollTo({ left: Math.max(0, l - 16), behavior: "smooth" });
    }
  }
  var spy = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting && byId[e.target.id]) setCurrent(byId[e.target.id]);
    });
  }, { rootMargin: "-30% 0px -60% 0px" });
  Object.keys(byId).forEach(function (id) {
    var s = document.getElementById(id);
    if (s) spy.observe(s);
  });
})();
