// Tab 2 · 예측 · 분류: forecast and classification tables, example week, error by hour, importance, confusion matrix.
(function () {
  window.DashTabs = window.DashTabs || {};
  window.DashTabs.model = function (D) {
    const { mount, base, axis, xTitle, withXTitle, fmt, BAND_KO } = window.Charts;
    const V = window.Views;
    const { $, table, finalMark } = window.DashUI;
    const R = D.regression, C = D.classification;
    table($("t-reg"), [
      { label: "방법", get: (r) => finalMark(r.model === "hgb") + `${r.label}<br><span class="muted small">${r.desc}</span>` },
      { label: "평균 오차 (kWh/15분)", n: 1, get: (r) => fmt.dec(r.test_mae, 2) },
      { label: "오차율", n: 1, get: (r) => fmt.pct(r.test_wape, 1) },
    ], R.scores, { highlight: (r) => r.model === "hgb" });

    const firstTry = new Set(["schedule_lookup", "hgb_no_season"]);
    const withMonth = new Set(["hgb_season_month_first", "hgb_season_month_last"]);
    table($("t-clf"), [
      { label: "방법 · 입력", get: (r) => finalMark(r.model === "hgb") + `${r.label}<br><span class="muted small">${r.inputs}</span>` },
      { label: "맞힌 정도 (1–2월)", n: 1, get: (r) => fmt.dec(r.macro_f1, 2) },
    ], C.reverse, { highlight: (r) => r.model === "hgb" });
    table($("t-clf-all"), [
      { label: "방법 · 입력", get: (r) => finalMark(r.model === "hgb") + `${r.label}<br><span class="muted small">${r.inputs}</span>` +
        (firstTry.has(r.model) ? ' <span class="chip crit">계절 미반영</span>' : withMonth.has(r.model) ? ' <span class="chip">월 포함</span>' : "") },
      { label: "검증 (10월)", n: 1, get: (r) => fmt.dec(r.valid_macro_f1, 2) },
      { label: "11–12월", n: 1, get: (r) => fmt.dec(r.test_macro_f1, 2) },
    ], C.scores, { highlight: (r) => r.model === "hgb" });

    mount($("c-week"), (t) => V.forecastWeek(t, R.week));
    mount($("c-errhour"), (t) => V.errorByHour(t, R.error_by_hour));

    mount($("c-imp"), (t) => {
      const rows = R.importance.slice(0, 8).reverse();
      return Object.assign(base(t), {
        grid: withXTitle({ left: 8, right: 44, top: 8, bottom: 8, containLabel: true }),
        tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => "+" + fmt.dec(v, 2) + " kWh" }),
        xAxis: axis(t, Object.assign(xTitle(t, "평균 오차 증가 (kWh)"), { type: "value" })),
        yAxis: axis(t, { type: "category", data: rows.map((r) => r.label), axisLabel: { color: t.ink2, fontSize: 12 } }),
        series: [{ type: "bar", data: rows.map((r) => +r.mae_increase.toFixed(3)), barWidth: 12,
          itemStyle: { color: t.accent, borderRadius: [0, 3, 3, 0] },
          label: { show: true, position: "right", color: t.ink2, fontFamily: t.mono, fontSize: 12, formatter: (p) => fmt.dec(p.value, 1) } }],
      });
    });

    const SHORT = { Light_Load: "경부하", Medium_Load: "중간부하", Maximum_Load: "최대부하" };
    mount($("c-cm"), (t) => {
      const L = C.confusion.labels, M = C.confusion.matrix, cells = [];
      M.forEach((row, i) => {
        const n = row.reduce((a, b) => a + b, 0);
        // Text flips to the surface color on the saturated end of the ramp, in either theme.
        row.forEach((v, j) => cells.push({ value: [j, i, v, v / n], label: { color: v / n > 0.5 ? t.surface : t.ink } }));
      });
      return Object.assign(base(t), {
        grid: { left: 8, right: 8, top: 36, bottom: 34, containLabel: true },
        tooltip: Object.assign(base(t).tooltip, { formatter: (p) => `실제 ${BAND_KO[L[p.value[1]]]} → 예측 ${BAND_KO[L[p.value[0]]]}<br><b>${fmt.int(p.value[2])}</b>개 (${fmt.pct(p.value[3], 1)})` }),
        xAxis: axis(t, Object.assign(xTitle(t, "예측"), { type: "category", data: L.map((l) => SHORT[l]), splitLine: { show: false },
          axisLabel: { color: t.ink2, fontSize: 12, interval: 0 } })),
        yAxis: axis(t, Object.assign({ name: "실제", nameLocation: "start" }, { type: "category", data: L.map((l) => SHORT[l]), inverse: true, splitLine: { show: false },
          axisLabel: { color: t.ink2, fontSize: 12, interval: 0 } })),
        visualMap: { show: false, min: 0, max: 1, dimension: 3, inRange: { color: t.seq } },
        series: [{ type: "heatmap", data: cells, itemStyle: { borderColor: t.surface, borderWidth: 2 },
          label: { show: true, fontFamily: t.mono, fontSize: 12, formatter: (p) => fmt.int(p.value[2]) } }],
      });
    });
  };
})();
