/* Google sign-in button (Google Identity Services).
 *
 * The button appears only when the server has a Google client ID. The browser
 * receives a signed ID token (the "credential") and passes it to the server,
 * which verifies it. No Google identity is ever trusted from the browser. */
(function () {
  'use strict';

  const GIS_URL = 'https://accounts.google.com/gsi/client';
  let configPromise = null;
  let scriptPromise = null;
  let initialisedFor = null;
  let activeHandler = null;

  function config() {
    if (!configPromise) {
      configPromise = fetch('/auth/config', { headers: { Accept: 'application/json' } })
        .then(response => {
          if (!response.ok) throw new Error('config unavailable');
          return response.json();
        })
        .catch(() => {
          configPromise = null; // allow a retry next time
          return {};
        });
    }
    return configPromise;
  }

  function hasGoogle() {
    return Boolean(window.google && window.google.accounts && window.google.accounts.id);
  }

  function loadScript() {
    if (hasGoogle()) return Promise.resolve(true);
    if (!scriptPromise) {
      scriptPromise = new Promise(resolve => {
        const tag = document.createElement('script');
        tag.src = GIS_URL;
        tag.async = true;
        tag.defer = true;
        const finish = ok => {
          clearTimeout(timer);
          if (!ok) {
            scriptPromise = null;
            if (tag.remove) tag.remove();
          }
          resolve(ok);
        };
        const timer = setTimeout(() => finish(false), 10000);
        tag.onload = () => finish(hasGoogle());
        tag.onerror = () => finish(false);
        document.head.appendChild(tag);
      });
    }
    return scriptPromise;
  }

  // Draws the button in `container`. `onCredential(idToken)` runs after the
  // person picks an account. Resolves to true if the button is showing.
  async function render(container, onCredential, options) {
    if (!container) return false;
    container.hidden = true;
    container.textContent = '';

    const settings = await config();
    const clientId = settings && settings.google_client_id;
    if (!clientId) return false;
    if (!(await loadScript())) return false;

    activeHandler = onCredential;
    if (initialisedFor !== clientId) {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: response => {
          if (response && response.credential && activeHandler) activeHandler(response.credential);
        },
        auto_select: false,
        cancel_on_tap_outside: true
      });
      initialisedFor = clientId;
    }

    window.google.accounts.id.renderButton(container, Object.assign({
      type: 'standard',
      theme: 'filled_blue',
      size: 'large',
      shape: 'pill',
      text: 'continue_with',
      logo_alignment: 'left'
    }, options || {}));
    container.hidden = false;
    return true;
  }

  window.LominiiGoogle = Object.freeze({ render, config });
})();
