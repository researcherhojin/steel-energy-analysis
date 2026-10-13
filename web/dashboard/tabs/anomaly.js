// Tab 3 · 휴무 · 이상: daily deviation chart, holiday and shutdown tables, 15-min review list.
(function () {
  window.DashTabs = window.DashTabs || {};
  window.DashTabs.anomaly = function (D) {
    const { mount, fmt } = window.Charts;
    const V = window.Views;
    const { $, table, dayCell } = window.DashUI;
    const A = D.anomaly;
    mount($("c-z"), (t) => V.dailyZ(t, A, D.meta.anomaly_z_day));
    V.dayLegend($("z-legend"), D.meta.anomaly_z_day);

    table($("t-hol"), [
      { label: "날짜", get: dayCell },
      { label: "공휴일", get: (r) => r.holiday },
      { label: "사용량 (kWh)", n: 1, get: (r) => fmt.int(r.kwh) },
      { label: "평일 대비", n: 1, get: (r) => (r.is_weekend ? '<span class="muted">–</span>' : fmt.pct(r.ratio_to_weekday)) },
      { label: "운영", get: (r) => r.is_weekend ? '<span class="chip">주말</span>' : r.shutdown ? '<span class="chip">휴무</span>' : '<span class="chip good">가동</span>' },
    ], A.holidays);

    const dayRows = [
      ...A.days.map((r) => ({ date: r.date, dow: r.dow, kwh: r.kwh, note: `평소 ${fmt.int(r.expected_kwh)} kWh`, tag: '<span class="chip crit">이상</span>' })),
      ...A.weekday_shutdowns.map((r) => ({ date: r.date, dow: r.dow, kwh: r.kwh, note: `평일의 ${fmt.pct(r.ratio_to_weekday)}`, tag: '<span class="chip">평일 휴무</span>' })),
    ].sort((a, b) => a.date.localeCompare(b.date));
    table($("t-days"), [
      { label: "날짜", get: dayCell },
      { label: "사용량 (kWh)", n: 1, get: (r) => fmt.int(r.kwh) },
      { label: "비교", get: (r) => `<span class="muted">${r.note}</span>` },
      { label: "구분", get: (r) => r.tag },
      { label: "추정 사유", get: (r) => `<span class="muted">${D.date_notes[r.date.slice(0, 10)] || "운영 기록 확인 필요"}</span>` },
    ], dayRows);

    table($("t-ep"), [
      { label: "시작", get: (r) => `<span class="num">${fmt.date(r.start)} ${r.start.slice(11, 16)}</span>` },
      { label: "길이", n: 1, get: (r) => fmt.int(r.slots * 15) + "분" },
      { label: "예측보다", get: (r) => (r.direction === "high" ? "많이 씀" : "적게 씀") + (r.holiday ? ` <span class="chip">${r.holiday}</span>` : "") },
      { label: "차이 합계 (kWh, 구간 전체)", n: 1, get: (r) => (r.excess_kwh > 0 ? "+" : "−") + fmt.int(Math.abs(r.excess_kwh)) },
    ], A.episodes);
  };
})();
