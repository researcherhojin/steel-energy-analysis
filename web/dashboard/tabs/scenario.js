// Tab 4 · 절감 시나리오: power-factor and load-shift sliders with their readouts and charts.
(function () {
  window.DashTabs = window.DashTabs || {};
  window.DashTabs.scenario = function (D) {
    const { mount, update, base, axis, yTitle, xTitle, withXTitle, fmt } = window.Charts;
    const V = window.Views;
    const { $, store } = window.DashUI;
    const S = D.scenarios;
    const pfIdx = Math.max(0, S.pf.findIndex((r) => Math.abs(r.target_pf - D.meta.pf_target) < 1e-9));
    const shIdx = Math.max(0, S.shift.findIndex((r) => Math.abs(r.fraction - 0.1) < 1e-9));
    const pfS = $("pf-slider"), shS = $("shift-slider");
    pfS.max = S.pf.length - 1; pfS.value = store.get("pf", pfIdx);
    shS.max = S.shift.length - 1; shS.value = store.get("shift", shIdx);

    const delta = (a, b, f) => {
      const d = b - a;
      if (Math.abs(d) < 1e-9) return "<small>변화 없음</small>";
      return `<small class="${d < 0 ? "delta-down" : "delta-up"}">${d > 0 ? "+" : "−"}${f(Math.abs(d))}</small>`;
    };
    const item = (label, before, after, f) => `<div><dt>${label}</dt><dd>${f(after)}${delta(before, after, f)}</dd></div>`;
    // Money in 만 원 is rounded first, so the change equals the difference of the shown values (as in the report).
    const wonItem = (label, before, after) => item(label, Math.round(before / 1e4), Math.round(after / 1e4), fmt.int);

    let pfChart, shChart;
    function renderPf() {
      const r = S.pf[pfS.value];
      $("pf-value").textContent = r.target_pf.toFixed(2);
      $("pf-readout").innerHTML =
        item("지상 무효전력량 (MVarh/년)", r.kvarh_before / 1000, r.kvarh_after / 1000, (v) => fmt.int(v)) +
        item("최대 피상전력 (kVA)", r.peak_kva_before, r.peak_kva_after, (v) => fmt.int(v)) +
        item("연간 역률", r.annual_pf_before, r.annual_pf_after, (v) => v.toFixed(3)) +
        wonItem("역률 할증 (만 원/년)", r.surcharge_before, r.surcharge_after);
      store.set("pf", +pfS.value);
      if (pfChart) update(pfChart);
    }
    function renderShift() {
      const r = S.shift[shS.value];
      $("shift-value").textContent = fmt.pct(r.fraction);
      $("shift-readout").innerHTML =
        wonItem("전력량요금 (만 원/년)", r.energy_cost_before, r.energy_cost_after) +
        wonItem("기본요금 (만 원/년)", r.demand_cost_before, r.demand_cost_after) +
        wonItem("역률 할증 (만 원/년)", r.surcharge_before, r.surcharge_after) +
        wonItem("합계 (만 원/년)", r.total_cost_before, r.total_cost_after);
      store.set("shift", +shS.value);
      if (shChart) update(shChart);
    }
    pfS.addEventListener("input", renderPf);
    shS.addEventListener("input", renderShift);
    renderPf(); renderShift();

    const kvarhNow = S.pf[0].kvarh_before / 1000;
    pfChart = mount($("c-pf"), (t) => Object.assign(base(t), {
      grid: withXTitle({ left: 8, right: 16, top: 36, bottom: 8, containLabel: true }),
      tooltip: Object.assign(base(t).tooltip, { trigger: "axis", valueFormatter: (v) => fmt.int(v) + " MVarh" }),
      xAxis: axis(t, Object.assign(xTitle(t, "목표 역률"), { type: "category", data: S.pf.map((r) => r.target_pf.toFixed(2)) })),
      yAxis: axis(t, Object.assign(yTitle("보상 후 지상 무효전력량 (MVarh/년)"), { type: "value", min: 0, max: Math.ceil(kvarhNow / 100) * 100 })),
      series: [{ type: "bar", barMaxWidth: 26, data: S.pf.map((r, i) => ({ value: +(r.kvarh_after / 1000).toFixed(1),
        itemStyle: { color: i === +pfS.value ? t.accent : t.baseline, borderRadius: [3, 3, 0, 0] } })),
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.ink3, type: "solid", width: 1 },
          label: { color: t.ink2, fontSize: 11, position: "insideStartTop", formatter: `현재 ${fmt.int(kvarhNow)}` }, data: [{ yAxis: +kvarhNow.toFixed(1) }] } }],
    }));
    shChart = mount($("c-shift"), (t) => {
      const parts = [["전력량요금", "energy_cost", t.accent], ["기본요금", "demand_cost", t.baseline], ["역률 할증", "surcharge", t.ink3]];
      const delta = (r, k) => Math.round(r[k + "_after"] / 1e4) - Math.round(r[k + "_before"] / 1e4);
      return Object.assign(base(t), {
        legend: { top: 0, right: 0, textStyle: { color: t.ink2, fontSize: 12 }, itemWidth: 12, itemHeight: 8 },
        grid: withXTitle({ left: 8, right: 16, top: 40, bottom: 8, containLabel: true }),
        tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => (v > 0 ? "+" : "") + fmt.int(v) + "만 원" }),
        xAxis: axis(t, Object.assign(xTitle(t, "이동 비율"), { type: "category", data: S.shift.map((r) => fmt.pct(r.fraction)) })),
        yAxis: axis(t, Object.assign(yTitle("연간 요금 변화 (만 원)"), { type: "value" })),
        series: [
          ...parts.map(([name, k, color]) => ({ name, type: "bar", stack: "d", barMaxWidth: 26, data: S.shift.map((r) => delta(r, k)),
            itemStyle: { color, borderColor: t.surface, borderWidth: 1 } })),
          { name: "합계", type: "scatter", symbolSize: 10, color: t.ink, data: S.shift.map((r, i) => ({ value: delta(r, "total_cost"),
            itemStyle: { color: i === +shS.value ? t.critical : t.ink, borderColor: t.surface, borderWidth: 2 } })) },
        ],
      });
    });
  };
})();
