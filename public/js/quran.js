/* LOMINII Quran workspace - placeholder.
 *
 * Pattern: HTML (#quranView in index.html) -> CSS (css/quran.css) -> JS (this
 * file) -> backend hook placeholders. No Quran text, translation or
 * prayer-time logic lives here. The reader plugs in later by assigning the
 * hooks below; until then the workspace says plainly that it is coming soon.
 */
(function () {
  "use strict";

  const hooks = {
    loadSurahList: null,   // async () => [{ number, name }]
    loadSurah: null,       // async (number) => { verses: [...] }
    searchQuran: null,     // async (query) => results
    loadPrayerTimes: null  // async ({ latitude, longitude }) => timings
  };
  window.LOMINIIQuranHooks = hooks;

  window.initialiseQuran = function initialiseQuran() {
    const view = document.getElementById("quranView");
    if (!view) return;

    let status = view.querySelector(".placeholder");
    if (!status) {
      status = document.createElement("div");
      status.className = "placeholder";
      view.appendChild(status);
    }
    status.setAttribute("role", "status");
    status.textContent = typeof hooks.loadSurahList === "function"
      ? "The Quran reader is loading."
      : "The Quran reader and prayer times are coming soon.";
  };
})();
