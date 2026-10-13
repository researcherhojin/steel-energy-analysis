// Dashboard-wide helpers shared by every tab: storage, DOM lookups, table and label markup.
(function () {
  const { fmt, DOW } = window.Charts;
  const BANDS = ["Light_Load", "Medium_Load", "Maximum_Load"];
  const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);
  const $ = (id) => document.getElementById(id);

  const store = {
    get(k, fallback) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : fallback; } catch { return fallback; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage unavailable */ } },
  };

  function table(el, cols, rows, opts = {}) {
    const head = "<thead><tr>" + cols.map((c) => `<th class="${c.n ? "n" : ""}">${c.label}</th>`).join("") + "</tr></thead>";
    const body = rows.map((r) => {
      const cls = opts.highlight && opts.highlight(r) ? ' class="hl"' : "";
      return `<tr${cls}>` + cols.map((c) => `<td class="${c.n ? "n" : ""}">${c.get(r)}</td>`).join("") + "</tr>";
    }).join("");
    el.innerHTML = head + "<tbody>" + body + "</tbody>";
  }
  const bandVar = (b) => (b === "Light_Load" ? "light" : b === "Medium_Load" ? "medium" : "max");
  const bandSwatch = (b) => `<span class="swatch" style="background:var(--band-${bandVar(b)})"></span>`;
  const dayCell = (r) => `<span class="num">${fmt.date(r.date)}</span> ${DOW[r.dow]}`;
  const finalMark = (on) => (on ? '<span class="final">▸</span> ' : "");

  window.DashUI = { BANDS, MONTHS, $, store, table, bandVar, bandSwatch, dayCell, finalMark };
})();
