(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  const { mount } = window.Charts;
  const V = window.Views;
  const $ = (id) => document.getElementById(id);
  const hours = D.kpi.weekday_daytime.hours;
  const label = `평일 ${String(hours[0]).padStart(2, "0")}–${hours[1]}시`;

  mount($("r-share"), (t) => V.shareBars(t, D.kpi.weekday_daytime, label));
  mount($("r-daily"), (t) => V.dailyLine(t, D.daily.map((d) => ({ date: d.date.slice(0, 10), dow: d.dow, kwh: d.kwh }))));
  mount($("r-heat"), (t) => V.hourDowHeat(t, V.profileCells(D.profile, () => true)));
  mount($("r-tou"), (t) => V.touStrip(t, D.tou_schedule));
  V.bandLegend($("r-tou-legend"));
  mount($("r-err"), (t) => V.errorByHour(t, D.regression.error_by_hour));
  mount($("r-z"), (t) => V.dailyZ(t, D.anomaly, D.meta.anomaly_z_day));
  V.dayLegend($("r-z-legend"), D.meta.anomaly_z_day);
  mount($("r-pfbin"), (t) => V.pfByLoad(t, D.pf_by_load, D.meta.tariff.pf_threshold));
})();
