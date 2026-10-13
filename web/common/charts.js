// Shared ECharts plumbing: colors come from CSS tokens, charts redraw on theme change and resize.
(function () {
  const registry = [];

  function tokens() {
    const css = getComputedStyle(document.documentElement);
    const v = (name) => css.getPropertyValue(name).trim();
    return {
      ink: v("--ink"), ink2: v("--ink-2"), ink3: v("--ink-3"), rule: v("--rule"), grid: v("--grid"),
      surface: v("--surface"), accent: v("--accent"), accentSoft: v("--accent-soft"),
      baseline: v("--baseline"), dayShut: v("--day-shut"), critical: v("--critical"), warning: v("--warning"), good: v("--good"),
      band: { Light_Load: v("--band-light"), Medium_Load: v("--band-medium"), Maximum_Load: v("--band-max") },
      seq: [v("--seq-lo"), v("--seq-mid"), v("--seq-hi")],
      font: v("--font-ui"), mono: v("--font-num"),
    };
  }

  function base(t) {
    return {
      animationDuration: 300,
      textStyle: { fontFamily: t.font, color: t.ink2, fontSize: 12 },
      grid: { left: 8, right: 20, top: 36, bottom: 8, containLabel: true },
      tooltip: {
        backgroundColor: t.surface, borderColor: t.rule, borderWidth: 1,
        textStyle: { color: t.ink, fontFamily: t.font, fontSize: 12 },
        extraCssText: "box-shadow:none;border-radius:4px;",
      },
    };
  }

  function axis(t, extra) {
    return Object.assign({
      axisLine: { lineStyle: { color: t.rule } },
      axisTick: { show: false },
      axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12 },
      splitLine: { lineStyle: { color: t.grid } },
      nameTextStyle: { color: t.ink2, fontSize: 12, align: "left", padding: [0, 0, 4, 0] },
      nameGap: 12,
    }, extra || {});
  }

  // Axis titles: y sits above the plot, left-aligned; x sits centred under the tick labels.
  const yTitle = (name) => ({ name, nameLocation: "end" });
  const xTitle = (t, name) => ({ name, nameLocation: "middle", nameGap: 30,
    nameTextStyle: { color: t.ink2, fontSize: 12, align: "center" } });
  const withXTitle = (grid) => Object.assign({}, grid, { bottom: 34 });

  function mount(el, build) {
    if (!el || !window.echarts) return null;
    const entry = { el, build, chart: echarts.init(el, null, { renderer: "svg" }) };
    entry.chart.setOption(build(tokens()));
    registry.push(entry);
    return entry;
  }

  function update(entry) {
    entry.chart.setOption(entry.build(tokens()), true);
  }

  function redrawAll() {
    registry.forEach((e) => { if (e.el.offsetParent !== null || e.el.clientWidth) update(e); });
  }

  function resizeVisible() {
    registry.forEach((e) => { if (e.el.clientWidth) e.chart.resize(); });
  }

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redrawAll);
  new MutationObserver(redrawAll).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  window.addEventListener("resize", resizeVisible);

  // Python's format() rounds half to even; match it so a value reads the same on both pages.
  function roundHalfEven(x, d = 0) {
    const m = 10 ** d, v = x * m, f = Math.floor(v), diff = v - f;
    const r = Math.abs(diff - 0.5) < 1e-9 ? (f % 2 === 0 ? f : f + 1) : Math.round(v);
    return r / m;
  }
  const fmt = {
    int: (x) => roundHalfEven(x).toLocaleString("ko-KR"),
    dec: (x, d = 1) => roundHalfEven(Number(x), d).toLocaleString("ko-KR", { minimumFractionDigits: d, maximumFractionDigits: d }),
    pct: (x, d = 0) => roundHalfEven(x * 100, d).toFixed(d) + "%",
    won: (x) => (x / 10000).toLocaleString("ko-KR", { maximumFractionDigits: 0 }) + "만 원",
    date: (s) => `${+s.slice(5, 7)}/${+s.slice(8, 10)}`,
  };

  const DOW = ["월", "화", "수", "목", "금", "토", "일"];
  const BAND_KO = { Light_Load: "경부하(Light)", Medium_Load: "중간부하(Medium)", Maximum_Load: "최대부하(Maximum)" };

  window.Charts = { tokens, base, axis, yTitle, xTitle, withXTitle, mount, update, resizeVisible, fmt, DOW, BAND_KO };
})();
