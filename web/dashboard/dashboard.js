// Dashboard shell: reads the embedded payload and switches tabs. Each tab lives in tabs/*.js
// and is rendered once, the first time it is shown.
(function () {
  const D = JSON.parse(document.getElementById("data").textContent);
  const { store } = window.DashUI;
  const $ = window.DashUI.$;
  const renderers = window.DashTabs;

  // ---------- tabs ----------
  const tabs = [...document.querySelectorAll("[role=tab]")];
  const TAB_NAMES = tabs.map((b) => b.dataset.tab);
  const mounted = new Set();
  function showTab(name) {
    tabs.forEach((b) => {
      const on = b.dataset.tab === name;
      b.setAttribute("aria-selected", on);
      b.tabIndex = on ? 0 : -1;
      $("pane-" + b.dataset.tab).hidden = !on;
    });
    if (!mounted.has(name)) { renderers[name](D); mounted.add(name); }
    window.Charts.resizeVisible();
    store.set("tab", name);
  }
  tabs.forEach((b, i) => {
    b.addEventListener("click", () => { showTab(b.dataset.tab); history.replaceState(null, "", "#" + b.dataset.tab); });
    b.addEventListener("keydown", (e) => {
      const d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!d) return;
      const next = tabs[(i + d + tabs.length) % tabs.length];
      next.focus(); next.click();
    });
  });

  const initial = (location.hash || "").slice(1);
  const saved = store.get("tab", "pattern");
  showTab(TAB_NAMES.includes(initial) ? initial : TAB_NAMES.includes(saved) ? saved : "pattern");
})();
