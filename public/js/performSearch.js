/* LOMINII search compatibility entry.
 * Canonical search implementation: public/js/search.js.
 * Do not redeclare performSearch here; doing so causes search logic drift.
 * This file intentionally leaves the canonical global untouched.
 */
(() => {
  "use strict";
  if (typeof window.performSearch !== "function") {
    console.warn("LOMINII: load public/js/search.js before using performSearch.js");
  }
})();
