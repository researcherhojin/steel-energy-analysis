// Chart option builders shared by the dashboard and the report. Each takes tokens + rows and
// returns a complete ECharts option; every chart names both axes and their units.
(function () {
  const { base, axis, yTitle, xTitle, withXTitle, fmt, DOW, BAND_KO } = window.Charts;
  const tip = (t, extra) => Object.assign(base(t).tooltip, extra);
  const pad2 = (h) => String(h).padStart(2, "0");
  const lineLegend = (t) => ({ top: 0, right: 0, textStyle: { color: t.ink2, fontSize: 12 }, itemWidth: 16, itemHeight: 2, icon: "rect" });
  // Charts with a legend start their plot lower, so the legend and the y-axis title never share a line.
  const legendGrid = (t, extra) => Object.assign({}, base(t).grid, { top: 60 }, extra || {});
  const BAND_ORDER = ["Light_Load", "Medium_Load", "Maximum_Load"];

  // Month ticks already carry the unit ("3월"), so the axis needs no title.
  const monthAxis = (t) => axis(t, { type: "time", splitNumber: 12, minInterval: 28 * 864e5, splitLine: { show: false },
    axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, formatter: "{M}월", hideOverlap: true } });

  function movingAvg(xs, w) {
    return xs.map((_, i) => {
      if (i < w - 1) return null;
      let s = 0;
      for (let j = i - w + 1; j <= i; j++) s += xs[j][1];
      return [xs[i][0], +(s / w).toFixed(1)];
    });
  }

  // Insert a null after any jump of more than one day, so lines do not bridge excluded months.
  function withGaps(pts) {
    const out = [];
    pts.forEach((p, i) => {
      if (i && Date.parse(p[0]) - Date.parse(pts[i - 1][0]) > 864e5) out.push([pts[i - 1][0], null]);
      out.push(p);
    });
    return out;
  }

  // rows: {date: "YYYY-MM-DD", dow, kwh, ma?}. Pass `ma` when rows are a filtered subset:
  // the 7-day average must come from the full calendar, not from whichever rows remain.
  function dailyLine(t, rows) {
    const pts = withGaps(rows.map((d) => [d.date, +d.kwh.toFixed(1)]));
    const maPts = rows[0] && "ma" in rows[0]
      ? withGaps(rows.map((d) => [d.date, d.ma]))
      : (rows.length >= 7 ? movingAvg(rows.map((d) => [d.date, +d.kwh.toFixed(1)]), 7) : []);
    const byDate = Object.fromEntries(rows.map((d) => [d.date, d]));
    return Object.assign(base(t), {
      legend: lineLegend(t),
      grid: legendGrid(t),
      tooltip: tip(t, { trigger: "axis",
        formatter: (p) => { const d = byDate[p[0].value[0]]; return `${fmt.date(d.date)} (${DOW[d.dow]})<br>` +
          p.map((s) => `${s.marker}${s.seriesName} <b>${s.value[1] == null ? "–" : fmt.int(s.value[1])}</b> kWh`).join("<br>"); } }),
      xAxis: monthAxis(t),
      yAxis: axis(t, Object.assign(yTitle("일 사용량 (kWh)"), { type: "value" })),
      dataZoom: [{ type: "inside" }],
      series: [
        { name: "일별", type: "line", data: pts, symbol: "none", color: t.baseline, lineStyle: { width: 1, color: t.baseline } },
        { name: "7일 이동평균", type: "line", data: maPts, symbol: "none",
          color: t.accent, lineStyle: { width: 2, color: t.accent }, areaStyle: { color: t.accentSoft, opacity: 0.6 } },
      ],
    });
  }

  // cells: [dow, hour, mean kWh per 15 min]
  function hourDowHeat(t, cells) {
    const max = Math.max(1, ...cells.map((c) => c[2] || 0));
    return Object.assign(base(t), {
      grid: { left: 8, right: 8, top: 36, bottom: 56, containLabel: true },
      tooltip: tip(t, { formatter: (p) => `${DOW[p.value[0]]}요일 ${pad2(p.value[1])}시<br><b>${p.value[2] == null ? "–" : fmt.dec(p.value[2], 1)}</b> kWh / 15분` }),
      xAxis: axis(t, Object.assign(xTitle(t, "요일"), { type: "category", data: DOW, splitLine: { show: false }, nameGap: 24 })),
      // inverse axis: "start" is the top edge, where the other y titles sit.
      yAxis: axis(t, Object.assign({ name: "시각 (시)", nameLocation: "start" }, { type: "category", data: Array.from({ length: 24 }, (_, h) => pad2(h)), inverse: true, splitLine: { show: false } })),
      visualMap: { min: 0, max, calculable: false, orient: "horizontal", left: "center", bottom: 0, itemHeight: 180, itemWidth: 10,
        inRange: { color: t.seq }, textStyle: { color: t.ink2, fontFamily: t.mono, fontSize: 12 }, text: [fmt.dec(max, 0) + " kWh/15분", "0"] },
      series: [{ type: "heatmap", data: cells, itemStyle: { borderColor: t.surface, borderWidth: 1 } }],
    });
  }

  function touStrip(t, schedule) {
    const seasons = [["summer", "3–10월"], ["winter", "11–2월"]];
    const data = [];
    seasons.forEach(([k], si) => schedule.forEach((r) => data.push({ value: [r.hour, si, 1], band: r[k], itemStyle: { color: t.band[r[k]] } })));
    return Object.assign(base(t), {
      grid: { left: 8, right: 8, top: 8, bottom: 34, containLabel: true },
      tooltip: tip(t, { formatter: (p) => `${seasons[p.value[1]][1]} ${pad2(p.value[0])}시 · <b>${BAND_KO[p.data.band]}</b>` }),
      xAxis: axis(t, Object.assign(xTitle(t, "시각 (시, 구간 시작)"), { type: "category", data: schedule.map((r) => pad2(r.hour)), splitLine: { show: false } })),
      yAxis: axis(t, { type: "category", data: seasons.map((s) => s[1]), inverse: true, splitLine: { show: false }, axisLabel: { color: t.ink2, fontSize: 12 } }),
      series: [{ type: "heatmap", data, itemStyle: { borderColor: t.surface, borderWidth: 2 } }],
    });
  }

  function bandLegend(el) {
    el.innerHTML = BAND_ORDER.map((b) => `<span><i class="swatch" style="background:var(--band-${b === "Light_Load" ? "light" : b === "Medium_Load" ? "medium" : "max"})"></i>${BAND_KO[b]}</span>`).join("");
  }

  function errorByHour(t, rows) {
    return Object.assign(base(t), {
      legend: lineLegend(t),
      grid: legendGrid(t, { bottom: 34 }),
      tooltip: tip(t, { trigger: "axis", valueFormatter: (v) => fmt.dec(v, 2) + " kWh" }),
      xAxis: axis(t, Object.assign(xTitle(t, "시각 (시)"), { type: "category", data: rows.map((r) => pad2(r.hour)), boundaryGap: false,
        axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, interval: 3 } })),
      yAxis: axis(t, Object.assign(yTitle("평균 오차 (kWh/15분)"), { type: "value" })),
      series: [
        { name: "직전값 그대로", type: "line", data: rows.map((r) => r.naive_mae), symbol: "none", color: t.baseline, lineStyle: { width: 1.5, color: t.baseline } },
        { name: "예측 모델(HGB)", type: "line", data: rows.map((r) => r.mae), symbol: "none", color: t.accent, lineStyle: { width: 2, color: t.accent } },
      ],
    });
  }

  function forecastWeek(t, rows) {
    return Object.assign(base(t), {
      legend: Object.assign(lineLegend(t), { selected: { "직전값 그대로": false } }),
      grid: legendGrid(t, { bottom: 34 }),
      tooltip: tip(t, { trigger: "axis", valueFormatter: (v) => fmt.dec(v, 1) + " kWh" }),
      xAxis: axis(t, Object.assign(xTitle(t, "날짜"), { type: "category", data: rows.map((r) => r.t.slice(5, 16).replace("T", " ")), boundaryGap: false,
        axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, interval: 95, formatter: (v) => `${+v.slice(0, 2)}/${+v.slice(3, 5)}` } })),
      yAxis: axis(t, Object.assign(yTitle("사용량 (kWh/15분)"), { type: "value" })),
      dataZoom: [{ type: "inside" }],
      series: [
        { name: "직전값 그대로", type: "line", data: rows.map((r) => r.naive), symbol: "none", color: t.baseline, lineStyle: { width: 1, color: t.baseline } },
        { name: "실측", type: "line", data: rows.map((r) => r.kwh), symbol: "none", color: t.ink, lineStyle: { width: 1.5, color: t.ink } },
        { name: "예측 모델(HGB)", type: "line", data: rows.map((r) => +r.pred.toFixed(2)), symbol: "none", color: t.accent, lineStyle: { width: 1.5, color: t.accent } },
      ],
    });
  }

  const DAY_KIND = { normal: "일반", holiday: "공휴일(판정 제외)", shut: "평일 휴무", flag: "이상" };
  // Color plus shape, so the four kinds stay distinct under color-vision deficiency.
  const kindColor = (t, k) => ({ normal: t.baseline, holiday: t.band.Medium_Load, shut: t.dayShut, flag: t.critical })[k];
  const KIND_SYMBOL = { normal: "circle", holiday: "rect", shut: "triangle", flag: "diamond" };
  const KIND_GLYPH = { normal: "●", holiday: "■", shut: "▲", flag: "◆" };

  function dayKinds(A) {
    const flagged = new Set(A.days.map((d) => d.date.slice(0, 10)));
    const shut = new Set(A.weekday_shutdowns.map((d) => d.date.slice(0, 10)));
    return (r) => r.holiday ? "holiday" : flagged.has(r.date.slice(0, 10)) ? "flag" : shut.has(r.date.slice(0, 10)) ? "shut" : "normal";
  }

  function dailyZ(t, A, threshold) {
    const kind = dayKinds(A);
    const series = Object.keys(DAY_KIND).map((k) => ({
      name: DAY_KIND[k], type: "scatter", symbol: KIND_SYMBOL[k], symbolSize: k === "normal" ? 5 : 11,
      itemStyle: { color: kindColor(t, k), borderColor: t.surface, borderWidth: k === "normal" ? 0 : 2 },
      data: A.daily_z.filter((r) => kind(r) === k).map((r) => ({ value: [r.date.slice(0, 10), +r.z.toFixed(2)], r })),
    }));
    series[0].markArea = { silent: true, itemStyle: { color: t.grid, opacity: 0.7 }, data: [[{ yAxis: -threshold }, { yAxis: threshold }]] };
    return Object.assign(base(t), {
      tooltip: tip(t, { formatter: (p) => { const r = p.data.r; return `${fmt.date(r.date)} (${DOW[r.dow]})${r.holiday ? " · " + r.holiday : ""}<br>실측 <b>${fmt.int(r.kwh)}</b> kWh · 평소 ${fmt.int(r.expected_kwh)} kWh<br>편차 점수 ${r.z.toFixed(1)}`; } }),
      xAxis: monthAxis(t),
      yAxis: axis(t, Object.assign(yTitle("평소 대비 편차 (평소 변동폭의 몇 배인가)"), { type: "value" })),
      series,
    });
  }

  function dayLegend(el, threshold) {
    const t = window.Charts.tokens();
    el.innerHTML = Object.keys(DAY_KIND).map((k) => `<span><b aria-hidden="true" style="color:${kindColor(t, k)}">${KIND_GLYPH[k]}</b>${DAY_KIND[k]}</span>`).join("") +
      `<span class="muted">회색 띠: 편차 점수 ±${threshold} 이내(정상 범위)</span>`;
  }

  // Dots on a truncated axis; bars would exaggerate differences.
  function pfByLoad(t, rows, threshold) {
    return Object.assign(base(t), {
      grid: withXTitle(base(t).grid),
      tooltip: tip(t, { trigger: "axis", axisPointer: { type: "none" },
        formatter: (p) => { const r = rows[p[0].dataIndex]; return `${r.kwh_bin} kWh/15분<br>역률 <b>${r.pf.toFixed(3)}</b><br>${fmt.int(r.slots)}개 기록`; } }),
      xAxis: axis(t, Object.assign(xTitle(t, "15분 사용량 구간 (kWh)"), { type: "category", data: rows.map((r) => r.kwh_bin), splitLine: { show: false } })),
      yAxis: axis(t, Object.assign(yTitle("역률"), { type: "value", min: 0.65, max: 1, interval: 0.05,
        axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, formatter: (v) => v.toFixed(2) } })),
      series: [{ type: "scatter", symbolSize: 12,
        data: rows.map((r) => ({ value: +r.pf.toFixed(3), itemStyle: { color: r.pf < threshold ? t.critical : t.accent, borderColor: t.surface, borderWidth: 2 } })),
        label: { show: true, position: "top", color: t.ink2, fontFamily: t.mono, fontSize: 12, formatter: (p) => p.value.toFixed(3) },
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.ink3, type: "solid", width: 1 },
          label: { color: t.ink3, fontSize: 11, position: "insideStartBottom", formatter: `할증 기준 ${threshold.toFixed(2)}` }, data: [{ yAxis: threshold }] } }],
    });
  }

  // Two 100% bars: share of time vs share of energy for one highlighted window.
  function shareBars(t, share, label) {
    const rows = [["1년 시간", share.slot_share], ["1년 사용량", share.kwh_share]];
    return Object.assign(base(t), {
      grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
      tooltip: tip(t, { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => v.toFixed(1) + "%" }),
      xAxis: axis(t, { type: "value", max: 100, axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, formatter: "{value}%" } }),
      yAxis: axis(t, { type: "category", data: rows.map((r) => r[0]), inverse: true, axisLabel: { color: t.ink, fontSize: 13 } }),
      series: [
        { name: label, type: "bar", stack: "s", barWidth: 26, data: rows.map((r) => +(r[1] * 100).toFixed(1)),
          itemStyle: { color: t.accent, borderColor: t.surface, borderWidth: 2 },
          label: { show: true, position: "insideLeft", color: t.surface, fontFamily: t.mono, fontSize: 13, fontWeight: 500, formatter: (p) => `${label} ${p.value.toFixed(0)}%` } },
        { name: "그 밖의 시간", type: "bar", stack: "s", data: rows.map((r) => +(100 - r[1] * 100).toFixed(1)),
          itemStyle: { color: t.grid, borderColor: t.surface, borderWidth: 2 },
          label: { show: true, position: "insideRight", color: t.ink2, fontFamily: t.mono, fontSize: 13, formatter: (p) => `${p.value.toFixed(0)}%` } },
      ],
    });
  }

  function profileCells(P, keep) {
    const acc = new Map();
    for (let i = 0; i < P.month.length; i++) {
      if (!keep(i)) continue;
      const k = P.dow[i] * 24 + P.hour[i];
      const a = acc.get(k) || [0, 0];
      a[0] += P.sum[i]; a[1] += P.count[i];
      acc.set(k, a);
    }
    const cells = [];
    for (let h = 0; h < 24; h++) for (let d = 0; d < 7; d++) {
      const a = acc.get(d * 24 + h);
      cells.push([d, h, a ? +(a[0] / a[1]).toFixed(2) : null]);
    }
    return cells;
  }

  window.Views = { dailyLine, hourDowHeat, touStrip, bandLegend, errorByHour, forecastWeek, dailyZ, dayLegend, pfByLoad, shareBars, profileCells };
})();
