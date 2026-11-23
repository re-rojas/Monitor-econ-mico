/* Monitor S&P 500 · pestaña Histórico.
 * Lee window.HIST (assets/historico-data.js) y dibuja dos vistas con Plotly:
 *  - Por período: varios activos en un rango de fechas.
 *  - Comparar crisis: un activo en varios episodios alineados en su fecha de inicio.
 * El estado se guarda en la URL (#...) para poder compartir o volver a una vista. */
(function () {
  "use strict";
  var H = window.HIST;
  var DAY = 864e5, MONTH = 30.4375 * DAY, YEAR = 365.25 * DAY;
  var COLORS = ["#4040b5", "#d9622b", "#0b8574", "#b8327a", "#8a6d00", "#56657f"];
  var MAX_ASSETS = COLORS.length;
  var FONT = "'Noto Sans', system-ui, -apple-system, 'Segoe UI', sans-serif";
  var root = document.getElementById("hist");
  if (!root) return;
  if (!H || !H.assets || !H.assets.length) {
    root.querySelector("[data-empty]").hidden = false;
    return;
  }

  /* ---------- Datos ---------- */
  var A = {};
  H.assets.forEach(function (a) {
    var n = a.v.length, t = new Array(n), day = a.t0;
    t[0] = day * DAY;
    for (var i = 1; i < n; i++) { day += a.dt[i - 1]; t[i] = day * DAY; }
    var peak = new Array(n), m = -Infinity;
    for (var j = 0; j < n; j++) { if (a.v[j] > m) m = a.v[j]; peak[j] = m; }
    A[a.id] = { id: a.id, name: a.name, group: a.group, t: t, v: a.v, peak: peak };
  });
  var LAST = Math.max.apply(null, H.assets.map(function (a) { return A[a.id].t[A[a.id].t.length - 1]; }));

  function lowerBound(arr, x) { var lo = 0, hi = arr.length; while (lo < hi) { var mid = (lo + hi) >> 1; if (arr[mid] < x) lo = mid + 1; else hi = mid; } return lo; }
  function iso(ms) { return new Date(ms).toISOString().slice(0, 10); }
  function parseDate(s) { var ms = Date.parse(s + "T00:00:00Z"); return isNaN(ms) ? null : ms; }
  var MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  function fecha(ms) { var d = new Date(ms); return d.getUTCDate() + " " + MES[d.getUTCMonth()] + " " + d.getUTCFullYear(); }
  function pct(x, nd) { if (x == null || !isFinite(x)) return "—"; var s = (x > 0 ? "+" : "") + x.toFixed(nd == null ? 1 : nd) + "%"; return s.replace("-", "−"); }
  function num(x) { if (x == null || !isFinite(x)) return "—"; var nd = Math.abs(x) >= 1000 ? 0 : Math.abs(x) >= 10 ? 1 : 2; return x.toLocaleString("en-US", { minimumFractionDigits: nd, maximumFractionDigits: nd }).replace("-", "−"); }
  function months(x) { return x == null ? "—" : (x < 1 ? "<1" : Math.round(x)) + (Math.round(x) === 1 ? " mes" : " meses"); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function cls(x) { return x > 0 ? "up" : x < 0 ? "down" : ""; }

  /* ---------- Estado (y URL) ---------- */
  var EP = (H.episodes || []).slice();
  var S = {
    view: "periodo",
    assets: ["^GSPC", "^NDX", "GLD"].filter(function (id) { return A[id]; }),
    range: "5A", from: null, to: null, measure: "pct", log: false,
    cAsset: A["^GSPC"] ? "^GSPC" : H.assets[0].id,
    eps: ["2008", "2020", "2022", "now"], now: null, win: "2A"
  };
  if (!S.assets.length) S.assets = [H.assets[0].id];
  (function readHash() {
    var p = new URLSearchParams(location.hash.slice(1));
    if (p.get("v") === "crisis") S.view = "crisis";
    if (p.get("a")) { var ids = p.get("a").split(",").filter(function (id) { return A[id]; }); if (ids.length) S.assets = ids.slice(0, MAX_ASSETS); }
    if (p.get("r")) S.range = p.get("r");
    if (p.get("d")) S.from = parseDate(p.get("d"));
    if (p.get("h")) S.to = parseDate(p.get("h"));
    if (["pct", "dd", "val"].indexOf(p.get("m")) >= 0) S.measure = p.get("m");
    if (p.get("log") === "1") S.log = true;
    if (p.get("c") && A[p.get("c")]) S.cAsset = p.get("c");
    if (p.get("e")) S.eps = p.get("e").split(",");
    if (p.get("n")) S.now = parseDate(p.get("n"));
    if (p.get("w")) S.win = p.get("w");
  })();
  function writeHash() {
    var p = new URLSearchParams();
    p.set("v", S.view);
    if (S.view === "periodo") {
      p.set("a", S.assets.join(",")); p.set("r", S.range); p.set("m", S.measure);
      if (S.range === "custom") { if (S.from) p.set("d", iso(S.from)); if (S.to) p.set("h", iso(S.to)); }
      if (S.log) p.set("log", "1");
    } else {
      p.set("c", S.cAsset); p.set("e", S.eps.join(",")); p.set("w", S.win);
      if (S.now) p.set("n", iso(S.now));
    }
    history.replaceState(null, "", "#" + p.toString());
  }

  /* ---------- Plotly ---------- */
  function baseLayout(extra) {
    var l = {
      template: "none", autosize: true, showlegend: false, dragmode: false,
      margin: { l: 4, r: 8, t: 8, b: 4 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { family: FONT, size: 12, color: "#6e6e6e" }, hovermode: "x unified",
      hoverlabel: { bgcolor: "#fff", bordercolor: "#e3e3e0", font: { family: FONT, size: 13, color: "#333" } },
      xaxis: { showgrid: false, zeroline: false, showline: true, linecolor: "#e3e3e0", ticks: "outside", tickcolor: "#e3e3e0", ticklen: 4,
               nticks: 6, tickangle: 0, fixedrange: true, automargin: true, showspikes: true, spikemode: "across",
               spikesnap: "cursor", spikethickness: 1, spikecolor: "#a7a8aa", spikedash: "solid" },
      yaxis: { gridcolor: "#ededeb", zeroline: false, nticks: 6, fixedrange: true, automargin: true }
    };
    for (var k in extra) {
      if (typeof extra[k] === "object" && !Array.isArray(extra[k]) && l[k]) { for (var kk in extra[k]) l[k][kk] = extra[k][kk]; }
      else l[k] = extra[k];
    }
    return l;
  }
  var CONFIG = { displayModeBar: false, responsive: true, scrollZoom: false, doubleClick: false, showTips: false, locale: "es" };
  function plot(el, traces, layout) {
    if (!window.Plotly) { el.textContent = "No se pudo cargar la librería de gráficos."; return; }
    Plotly.react(el, traces, layout, CONFIG);
  }

  /* ---------- Vista por período ---------- */
  var RANGES = { "1M": [0, 1], "6M": [0, 6], "YTD": null, "1A": [1, 0], "5A": [5, 0], "10A": [10, 0], "20A": [20, 0], "MAX": null };
  function periodBounds() {
    var to = LAST, from;
    if (S.range === "custom") {
      from = S.from; to = S.to || LAST;
    } else if (S.range === "YTD") {
      from = Date.UTC(new Date(to).getUTCFullYear(), 0, 1);
    } else if (S.range === "MAX") {
      from = Math.min.apply(null, S.assets.map(function (id) { return A[id].t[0]; }));
    } else {
      var r = RANGES[S.range] || RANGES["5A"], d = new Date(to);
      from = Date.UTC(d.getUTCFullYear() - r[0], d.getUTCMonth() - r[1], d.getUTCDate());
    }
    if (from == null) from = to - 5 * YEAR;
    if (from > to) { var x = from; from = to; to = x; }
    return [from, to];
  }

  function renderPeriod() {
    var b = periodBounds(), from = b[0], to = b[1];
    var traces = [], legend = [], rows = [];
    S.assets.forEach(function (id, k) {
      var a = A[id], i0 = lowerBound(a.t, from), i1 = lowerBound(a.t, to + DAY) - 1;
      var color = COLORS[k % COLORS.length];
      if (i1 - i0 < 1) {
        legend.push('<li><span class="swatch" style="color:' + color + '"></span>' + esc(a.name) + ' <strong>sin datos en el rango</strong></li>');
        rows.push('<tr><th scope="row"><span class="swatch" style="color:' + color + '"></span>' + esc(a.name) + '</th><td class="num" colspan="4">Sin datos en este rango</td></tr>');
        return;
      }
      var x = [], y = [], base = a.v[i0], runMax = -Infinity, worst = 0, worstT = null;
      for (var i = i0; i <= i1; i++) {
        var v = a.v[i];
        x.push(iso(a.t[i]));
        if (S.measure === "pct") y.push((v / base - 1) * 100);
        else if (S.measure === "dd") y.push((v / a.peak[i] - 1) * 100);
        else y.push(v);
        if (v > runMax) runMax = v;
        var dd = v / runMax - 1;
        if (dd < worst) { worst = dd; worstT = a.t[i]; }
      }
      var fmt = S.measure === "val" ? "%{y:,.2f}" : "%{y:.1f}%";
      traces.push({ x: x, y: y, name: a.name, type: "scatter", mode: "lines", line: { color: color, width: 2 }, hovertemplate: fmt });
      var change = (a.v[i1] / base - 1) * 100, yrs = (a.t[i1] - a.t[i0]) / YEAR;
      var cagr = yrs >= 1 ? (Math.pow(a.v[i1] / base, 1 / yrs) - 1) * 100 : null;
      var lastTxt = S.measure === "val" ? num(y[y.length - 1]) : pct(y[y.length - 1]);
      legend.push('<li><span class="swatch" style="color:' + color + '"></span>' + esc(a.name) + ' <strong>' + lastTxt + '</strong></li>');
      var late = a.t[i0] - from > 10 * DAY ? '<span class="cell-note">desde ' + fecha(a.t[i0]) + '</span>' : "";
      rows.push('<tr><th scope="row"><span class="swatch" style="color:' + color + '"></span>' + esc(a.name) + late + '</th>' +
        '<td class="num"><span class="' + cls(change) + '">' + pct(change) + '</span></td>' +
        '<td class="num">' + (cagr == null ? "—" : '<span class="' + cls(cagr) + '">' + pct(cagr) + '</span>') + '</td>' +
        '<td class="num">' + pct(worst * 100) + '</td>' +
        '<td class="num">' + (worstT ? fecha(worstT) : "—") + '</td></tr>');
    });
    var yax = { ticksuffix: S.measure === "val" ? "" : "%", type: S.measure === "val" && S.log ? "log" : "linear",
                tickformat: S.measure === "val" ? "~s" : ".0f" };
    var shapes = S.measure !== "val" ? [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: { color: "#a7a8aa", width: 1, dash: "dot" } }] : [];
    plot(q("#p-chart"), traces, baseLayout({ yaxis: yax, xaxis: { type: "date", hoverformat: "%d %b %Y" }, shapes: shapes }));
    q("#p-legend").innerHTML = legend.join("");
    q("#p-rows").innerHTML = rows.join("");
    var MEAS = { pct: "Cambio % desde el inicio del rango", dd: "Caída desde el máximo histórico", val: "Valor" + (S.log ? " (escala logarítmica)" : "") };
    q("#p-title").textContent = MEAS[S.measure];
    q("#p-sub").textContent = fecha(from) + " – " + fecha(to);
    q("#p-chart").setAttribute("aria-label", "Gráfico de líneas: " + MEAS[S.measure] + " de " +
      S.assets.map(function (id) { return A[id].name; }).join(", ") + ", del " + fecha(from) + " al " + fecha(to) + ". Los valores están en la tabla.");
    // Controles
    qa("[data-range]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-range") === S.range)); });
    qa("[data-measure]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-measure") === S.measure)); });
    q("#p-from").value = iso(from); q("#p-to").value = iso(to);
    var log = q("#p-log"); log.checked = S.log; log.disabled = S.measure !== "val";
    log.closest(".check").classList.toggle("is-disabled", S.measure !== "val");
    renderChips();
  }

  function renderChips() {
    q("#p-chips").innerHTML = S.assets.map(function (id, k) {
      return '<li><button type="button" class="chip" data-remove="' + esc(id) + '" aria-label="Quitar ' + esc(A[id].name) + '"' +
        (S.assets.length === 1 ? " disabled" : "") + '><span class="swatch" style="color:' + COLORS[k % COLORS.length] + '"></span>' +
        esc(A[id].name) + '<svg class="icon" aria-hidden="true"><use href="#i-close"/></svg></button></li>';
    }).join("");
    var sel = q("#p-add"), full = S.assets.length >= MAX_ASSETS;
    sel.disabled = full;
    sel.options[0].textContent = full ? "Máximo " + MAX_ASSETS + " activos" : "Agregar activo…";
    Array.prototype.forEach.call(sel.options, function (o) { if (o.value) o.disabled = S.assets.indexOf(o.value) >= 0; });
    sel.value = "";
  }

  /* ---------- Vista comparar crisis ---------- */
  var WINS = { "3M": 3, "6M": 6, "1A": 12, "2A": 24, "3A": 36, "5A": 60 };
  function defaultNow(a) {
    // Último máximo histórico del activo: ahí parte la caída actual (si la hay).
    var best = 0; for (var i = 1; i < a.v.length; i++) if (a.v[i] >= a.v[best]) best = i;
    return a.t[best];
  }
  function renderCrisis() {
    var a = A[S.cAsset], winM = WINS[S.win] || 24, traces = [], legend = [], rows = [];
    var nowStart = S.now || defaultNow(a);
    q("#c-now").value = iso(nowStart);
    var list = EP.concat([{ id: "now", name: "Actual", start: iso(nowStart) }]);
    var k = 1;
    list.forEach(function (e) {
      if (S.eps.indexOf(e.id) < 0) return;
      var isNow = e.id === "now", color = isNow ? COLORS[0] : COLORS[k++ % COLORS.length];
      var t0 = parseDate(e.start), i0 = lowerBound(a.t, t0);
      if (i0 >= a.t.length || a.t[i0] - t0 > 10 * DAY) {
        rows.push('<tr><th scope="row"><span class="swatch" style="color:' + color + '"></span>' + esc(e.name) + '</th><td class="num" colspan="4">Sin datos de este activo en esa fecha</td></tr>');
        return;
      }
      var end = a.t[i0] + winM * MONTH, x = [], y = [], v0 = a.v[i0], minY = 0, minI = i0;
      for (var i = i0; i < a.t.length && a.t[i] <= end; i++) {
        var yy = (a.v[i] / v0 - 1) * 100;
        x.push((a.t[i] - a.t[i0]) / MONTH); y.push(yy);
        if (yy < minY) { minY = yy; minI = i; }
      }
      var rec = null;
      for (var j = minI; j < a.t.length; j++) if (a.v[j] >= v0 && j > i0) { rec = (a.t[j] - a.t[i0]) / MONTH; break; }
      if (minI === i0) rec = 0;
      var ended = a.t[i0] + winM * MONTH <= LAST + DAY;
      traces.push({ x: x, y: y, name: e.name, type: "scatter", mode: "lines",
                    line: { color: color, width: isNow ? 3 : 2 }, hovertemplate: "%{y:.1f}%" });
      legend.push('<li><span class="swatch" style="color:' + color + '"></span>' + esc(e.name) + ' <strong>' + pct(minY) + '</strong> peor punto</li>');
      rows.push('<tr><th scope="row"><span class="swatch" style="color:' + color + '"></span>' + esc(e.name) +
        '<span class="cell-note">desde ' + fecha(a.t[i0]) + '</span></th>' +
        '<td class="num">' + pct(minY) + '</td>' +
        '<td class="num">' + (minI === i0 ? "—" : months((a.t[minI] - a.t[i0]) / MONTH)) + '</td>' +
        '<td class="num">' + (rec == null ? (isNow ? "En curso" : "Aún no") : rec === 0 ? "No cayó" : months(rec)) + '</td>' +
        '<td class="num"><span class="' + cls(y[y.length - 1]) + '">' + pct(y[y.length - 1]) + '</span>' + (ended ? "" : '<span class="cell-note">hasta hoy</span>') + '</td></tr>');
    });
    var shapes = [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 0, line: { color: "#a7a8aa", width: 1, dash: "dot" } }];
    plot(q("#c-chart"), traces, baseLayout({
      xaxis: { type: "linear", range: [0, winM], ticksuffix: " m", hoverformat: ".1f", dtick: (winM <= 6 ? 1 : winM <= 12 ? 2 : winM <= 24 ? 3 : winM <= 36 ? 6 : 12) * (q("#c-chart").clientWidth < 520 ? 2 : 1) },
      yaxis: { ticksuffix: "%", tickformat: ".0f" }, shapes: shapes }));
    q("#c-legend").innerHTML = legend.join("");
    q("#c-rows").innerHTML = rows.join("");
    q("#c-title").textContent = a.name + ": cambio % desde el inicio de cada episodio";
    q("#c-sub").textContent = "Meses desde el inicio (m) · ventana de " + winM + " meses";
    q("#c-chart").setAttribute("aria-label", "Gráfico de líneas de " + a.name + " en distintos episodios, alineados en su fecha de inicio. Los valores están en la tabla.");
    q("#c-asset").value = S.cAsset;
    qa("[data-ep]").forEach(function (b) { b.setAttribute("aria-pressed", String(S.eps.indexOf(b.getAttribute("data-ep")) >= 0)); });
    qa("[data-win]").forEach(function (b) { b.setAttribute("aria-pressed", String(b.getAttribute("data-win") === S.win)); });
  }

  /* ---------- Pestañas de vista ---------- */
  function q(s) { return root.querySelector(s); }
  function qa(s) { return Array.prototype.slice.call(root.querySelectorAll(s)); }
  var tabs = qa('[role="tab"]');
  function showView(v, focus) {
    S.view = v;
    tabs.forEach(function (t) {
      var on = t.getAttribute("data-view") === v;
      t.setAttribute("aria-selected", String(on)); t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute("aria-controls")).hidden = !on;
      if (on && focus) t.focus();
    });
    render();
  }
  function render() {
    if (S.view === "periodo") renderPeriod(); else renderCrisis();
    writeHash();
  }

  /* ---------- Eventos ---------- */
  tabs.forEach(function (t, i) {
    t.addEventListener("click", function () { showView(t.getAttribute("data-view")); });
    t.addEventListener("keydown", function (ev) {
      var d = ev.key === "ArrowRight" ? 1 : ev.key === "ArrowLeft" ? -1 : 0;
      if (d) { ev.preventDefault(); showView(tabs[(i + d + tabs.length) % tabs.length].getAttribute("data-view"), true); }
    });
  });
  root.addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b || !root.contains(b)) return;
    if (b.hasAttribute("data-range")) { S.range = b.getAttribute("data-range"); render(); }
    else if (b.hasAttribute("data-measure")) { S.measure = b.getAttribute("data-measure"); render(); }
    else if (b.hasAttribute("data-remove")) {
      var id = b.getAttribute("data-remove"), pos = S.assets.indexOf(id);
      if (S.assets.length > 1) { S.assets = S.assets.filter(function (x) { return x !== id; }); render();
        var next = qa("[data-remove]")[Math.min(pos, S.assets.length - 1)]; if (next) next.focus(); }
    }
    else if (b.hasAttribute("data-ep")) {
      var e = b.getAttribute("data-ep"), p = S.eps.indexOf(e);
      if (p >= 0) { if (S.eps.length > 1) S.eps.splice(p, 1); } else S.eps.push(e);
      render();
    }
    else if (b.hasAttribute("data-win")) { S.win = b.getAttribute("data-win"); render(); }
  });
  q("#p-add").addEventListener("change", function () {
    var v = this.value;
    if (v && A[v] && S.assets.indexOf(v) < 0 && S.assets.length < MAX_ASSETS) { S.assets.push(v); render(); }
  });
  q("#p-from").addEventListener("change", function () { var d = parseDate(this.value); if (d) { var b = periodBounds(); S.from = d; S.to = b[1]; S.range = "custom"; render(); } });
  q("#p-to").addEventListener("change", function () { var d = parseDate(this.value); if (d) { var b = periodBounds(); S.from = b[0]; S.to = d; S.range = "custom"; render(); } });
  q("#p-preset").addEventListener("change", function () {
    var e = EP.filter(function (x) { return x.id === this.value; }, this)[0];
    if (e) { var t0 = parseDate(e.start); S.from = t0 - 3 * MONTH; S.to = Math.min(t0 + 33 * MONTH, LAST); S.range = "custom"; S.measure = S.measure === "val" ? "pct" : S.measure; render(); }
    this.value = "";
  });
  q("#p-log").addEventListener("change", function () { S.log = this.checked; render(); });
  q("#c-asset").addEventListener("change", function () { S.cAsset = this.value; S.now = null; render(); });
  q("#c-now").addEventListener("change", function () { var d = parseDate(this.value); if (d) { S.now = d; if (S.eps.indexOf("now") < 0) S.eps.push("now"); render(); } });

  /* ---------- Inicio ---------- */
  function start() { showView(S.view); }
  function whenReady(fn) { if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn); else fn(); }
  whenReady(function () {
    var fonts = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    fonts.then(start, start);
  });
})();
