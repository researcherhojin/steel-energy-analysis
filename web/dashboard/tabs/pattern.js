// Tab 1 · 사용 패턴: month and tariff-band filters, daily line, heatmap, band shares, monthly charts.
(function () {
  window.DashTabs = window.DashTabs || {};
  window.DashTabs.pattern = function (D) {
    const { mount, update, base, axis, yTitle, fmt, BAND_KO } = window.Charts;
    const V = window.Views;
    const { BANDS, MONTHS, $, store, table, bandSwatch } = window.DashUI;
    const state = { months: new Set(store.get("months", MONTHS)), bands: new Set(store.get("bands", BANDS)) };

    function segButtons(el, items, set, label, key) {
      el.innerHTML = "";
      items.forEach((it) => {
        const b = document.createElement("button");
        b.type = "button";
        b.innerHTML = label(it);
        b.setAttribute("aria-pressed", set.has(it));
        b.addEventListener("click", () => {
          if (set.has(it) && set.size === 1) return; // keep at least one selected
          set.has(it) ? set.delete(it) : set.add(it);
          b.setAttribute("aria-pressed", set.has(it));
          store.set(key, [...set]);
          refreshPattern();
        });
        el.appendChild(b);
      });
    }
    const drawFilters = () => {
      segButtons($("month-filter"), MONTHS, state.months, (m) => m + "월", "months");
      segButtons($("band-filter"), BANDS, state.bands, (b) => bandSwatch(b) + BAND_KO[b], "bands");
    };

    function filtered() {
      const P = D.profile;
      const bandAgg = Object.fromEntries(BANDS.map((b) => [b, { kwh: 0, n: 0 }]));
      for (let i = 0; i < P.month.length; i++) {
        if (!state.months.has(P.month[i])) continue;
        bandAgg[P.load_type[i]].kwh += P.sum[i];
        bandAgg[P.load_type[i]].n += P.count[i];
      }
      const heat = V.profileCells(P, (i) => state.months.has(P.month[i]) && state.bands.has(P.load_type[i]));
      // Moving average over the whole year first, then keep the selected months.
      const full = D.daily.map((d) => ({
        date: d.date.slice(0, 10), dow: d.dow, month: d.month,
        kwh: BANDS.reduce((s, b) => s + (state.bands.has(b) ? d["kwh_" + b] || 0 : 0), 0),
      }));
      full.forEach((d, i) => {
        d.ma = i < 6 ? null : +(full.slice(i - 6, i + 1).reduce((s, x) => s + x.kwh, 0) / 7).toFixed(1);
      });
      const daily = full.filter((d) => state.months.has(d.month));
      return { heat, bandAgg, daily };
    }

    let F = null;
    const charts = {};

    function refreshPattern() {
      F = filtered();
      const label = state.bands.size === 3 ? "전체" : [...state.bands].map((b) => BAND_KO[b]).join(" · ") + " 시간대";
      $("daily-title").textContent = `일 사용량 · ${label}`;
      const total = F.daily.reduce((s, d) => s + d.kwh, 0);
      $("daily-caption").textContent = `회색 선은 날마다의 사용량, 파란 선은 앞 7일 평균이다. 톱니처럼 내려간 곳이 주말이다. 선택 기간 합계 ${fmt.dec(total / 1000, 1)} MWh.`;
      const kT = BANDS.reduce((s, b) => s + F.bandAgg[b].kwh, 0);
      const nT = BANDS.reduce((s, b) => s + F.bandAgg[b].n, 0);
      const mx = F.bandAgg.Maximum_Load;
      $("bands-title").textContent = `최대부하 시간대는 시간 ${fmt.pct(mx.n / nT)}에 사용량 ${fmt.pct(mx.kwh / kT)}`;
      table($("t-bands"), [
        { label: "요금 시간대", get: (b) => `<span class="chip">${bandSwatch(b)}${BAND_KO[b]}</span>` },
        { label: "15분 평균 사용량 (kWh)", n: 1, get: (b) => fmt.dec(F.bandAgg[b].kwh / Math.max(F.bandAgg[b].n, 1), 1) },
        { label: "시간 비중", n: 1, get: (b) => fmt.pct(F.bandAgg[b].n / nT) },
        { label: "사용량 비중", n: 1, get: (b) => fmt.pct(F.bandAgg[b].kwh / kT) },
      ], BANDS);
      Object.values(charts).forEach(update);
    }

    drawFilters();
    $("reset-filters").addEventListener("click", () => {
      state.months = new Set(MONTHS); state.bands = new Set(BANDS);
      store.set("months", MONTHS); store.set("bands", BANDS);
      drawFilters(); refreshPattern();
    });
    F = filtered();

    charts.daily = mount($("c-daily"), (t) => V.dailyLine(t, F.daily));
    charts.heat = mount($("c-heat"), (t) => V.hourDowHeat(t, F.heat));

    charts.bands = mount($("c-bands"), (t) => {
      const kT = BANDS.reduce((s, b) => s + F.bandAgg[b].kwh, 0), nT = BANDS.reduce((s, b) => s + F.bandAgg[b].n, 0);
      return Object.assign(base(t), {
        grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
        tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" },
          formatter: (p) => p[0].axisValue + "<br>" + p.map((s) => `${s.marker}${BAND_KO[s.seriesName]} <b>${s.value.toFixed(1)}%</b>`).join("<br>") }),
        xAxis: axis(t, { type: "value", max: 100, axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, formatter: "{value}%" } }),
        yAxis: axis(t, { type: "category", data: ["시간 비중", "사용량 비중"], inverse: true, axisLabel: { color: t.ink2, fontSize: 12 } }),
        series: BANDS.map((b) => ({ name: b, type: "bar", stack: "s", barWidth: 22,
          itemStyle: { color: t.band[b], borderColor: t.surface, borderWidth: 2 },
          data: [100 * F.bandAgg[b].n / nT, 100 * F.bandAgg[b].kwh / kT] })),
      });
    });

    charts.month = mount($("c-month"), (t) => {
      const rows = MONTHS.filter((m) => state.months.has(m)).map((m) => {
        const days = F.daily.filter((d) => +d.date.slice(5, 7) === m);
        return [m + "월", days.length ? +(days.reduce((s, d) => s + d.kwh, 0) / days.length).toFixed(0) : 0];
      });
      return Object.assign(base(t), {
        tooltip: Object.assign(base(t).tooltip, { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => fmt.int(v) + " kWh/일" }),
        xAxis: axis(t, { type: "category", data: rows.map((r) => r[0]) }),
        yAxis: axis(t, Object.assign(yTitle("하루 평균 사용량 (kWh)"), { type: "value" })),
        series: [{ type: "bar", name: "하루 평균", data: rows.map((r) => r[1]), barMaxWidth: 26,
          itemStyle: { color: t.accent, borderRadius: [3, 3, 0, 0] } }],
      });
    });

    mount($("c-month-pf"), (t) => Object.assign(base(t), {
      tooltip: Object.assign(base(t).tooltip, { trigger: "axis", valueFormatter: (v) => fmt.dec(v, 3) }),
      xAxis: axis(t, { type: "category", data: D.monthly.map((m) => m.month + "월") }),
      yAxis: axis(t, Object.assign(yTitle("역률"), { type: "value", min: 0.84, max: 0.94, interval: 0.02,
        axisLabel: { color: t.ink3, fontFamily: t.mono, fontSize: 12, formatter: (v) => v.toFixed(2) } })),
      series: [{ type: "line", name: "역률", symbolSize: 9, color: t.accent, lineStyle: { width: 2, color: t.accent },
        data: D.monthly.map((m) => ({ value: +m.pf.toFixed(4),
          itemStyle: { color: m.pf < D.meta.tariff.pf_threshold ? t.critical : t.accent, borderColor: t.surface, borderWidth: 2 } })),
        label: { show: true, position: "top", color: t.ink2, fontFamily: t.mono, fontSize: 11, formatter: (p) => p.value.toFixed(3) },
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.ink3, type: "solid", width: 1 },
          label: { color: t.ink3, fontSize: 11, position: "insideStartBottom", formatter: "할증 기준" }, data: [{ yAxis: D.meta.tariff.pf_threshold }] } }],
    }));

    mount($("c-tou"), (t) => V.touStrip(t, D.tou_schedule));
    V.bandLegend($("tou-legend"));
    mount($("c-pfbin"), (t) => V.pfByLoad(t, D.pf_by_load, D.meta.tariff.pf_threshold));

    refreshPattern();
  };
})();
