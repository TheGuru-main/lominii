// ── Global state ──────────────────────────
let authToken = localStorage.getItem('lominii_token') || '';

// ── Views ────────────────────────────────

const views = {
  home: document.getElementById('homeView'),
  games: document.getElementById('gamesView'),
  social: document.getElementById('socialView'),
  edu: document.getElementById('eduView'),
  quran: document.getElementById('quranView')
};
const footerIcons = document.querySelectorAll('.footer-nav .nav-icon');
const backToggle = document.getElementById('backToggle');
const splashScreen = document.getElementById('splashScreen');
const landingView = document.getElementById('landingView');
const dashboardView = document.getElementById('dashboardView');
const particleCanvas = document.getElementById('particleCanvas');

// ── Splash → Landing transition ─────────
setTimeout(() => {
  if (splashScreen) splashScreen.style.display = 'none';
  if (landingView) landingView.style.display = 'block';
  if (particleCanvas && typeof drawParticles === 'function') drawParticles();
}, 2000);

// ── Show Dashboard ──────────────────────
function showDashboard() {
  landingView.style.display = 'none';
  dashboardView.style.display = 'block';
  if (particleCanvas) particleCanvas.style.display = 'none';
  if (typeof animId !== 'undefined') cancelAnimationFrame(animId);
  document.body.classList.add('search-home');
  if (typeof loadHomeCards === 'function') loadHomeCards();
}

// ── Workspace Switcher ─────────────────
function switchToWorkspace(workspace) {
  // Hide all workspace views
  Object.values(views).forEach(v => { if(v) v.style.display = 'none'; });
  // Show the selected workspace
  if (views[workspace]) views[workspace].style.display = 'block';

  // Update footer icons
  footerIcons.forEach(i => i.classList.remove('active'));
  const destination = workspace === 'home' ? 'search'
    : workspace === 'games' ? 'play' : workspace;
  const activeIcon = document.querySelector(
    `.nav-icon[data-destination="${destination}"]`
  );
  if (activeIcon) activeIcon.classList.add('active');

  // Toggle home dropdown visibility
  const homeDropdown = document.getElementById('homeDropdown');
  if (workspace === 'home') {
    document.body.classList.add('search-home');
    document.body.classList.remove('workspace-view');
    if (backToggle) backToggle.style.display = 'none';
    if (homeDropdown) homeDropdown.style.display = 'block';
  } else {
    document.body.classList.remove('search-home');
    document.body.classList.add('workspace-view');
    if (backToggle) backToggle.style.display = 'block';
    if (homeDropdown) homeDropdown.style.display = 'none';
  }

  // Workspace‑specific initialisation
  switch (workspace) {
    case 'home':
      if (typeof loadHomeCards === 'function') loadHomeCards();
      break;
    case 'social':
      if (typeof initialiseSocial === 'function') initialiseSocial();
      break;
    case 'games':
      if (typeof initialiseGames === 'function') initialiseGames();
      break;
    case 'edu':
      if (typeof initialiseEdu === 'function') initialiseEdu();
      break;
    case 'quran':
      if (typeof initialiseQuran === 'function') initialiseQuran();
      break;
  }
}
function goHome() { switchToWorkspace('home'); }

// ── Footer navigation listeners ─────────
function navigateToDestination(destination) {
  const setActive = () => {
    footerIcons.forEach(icon => {
      icon.classList.toggle(
        'active',
        icon.dataset.destination === destination
      );
    });
  };

  switch (destination) {
    case 'search':
      switchToWorkspace('home');
      setActive();
      break;

    case 'play':
      switchToWorkspace('games');
      setActive();
      break;

    case 'research':
      switchToWorkspace('home');
      setActive();
      requestAnimationFrame(() => {
        document.getElementById('cardNews')?.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      });
      break;

    case 'discovery':
      switchToWorkspace('home');
      setActive();

      const scrollToDiscovery = (attempt = 0) => {
        const target = document.getElementById('scrapingbeeSection');

        if (target) {
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
          return;
        }

        if (attempt < 20) {
          window.setTimeout(() => scrollToDiscovery(attempt + 1), 100);
          return;
        }

        alert('Video discovery is not available right now. Please try again later.');
      };

      requestAnimationFrame(() => scrollToDiscovery());
      break;

    case 'quran':
      alert('Quran is unavailable — coming soon.');
      break;

    case 'connect':
      window.open(
        'https://hi-mate-messenger-apiv1-0-0-1frontr.onrender.com',
        '_blank',
        'noopener,noreferrer'
      );
      break;
  }
}

footerIcons.forEach(icon => {
  const activate = () => navigateToDestination(icon.dataset.destination);

  icon.addEventListener('click', activate);
  icon.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      activate();
    }
  });
});

document.getElementById('openGames')?.addEventListener('click', () => {
  navigateToDestination('play');
});

document.getElementById('homeLogo')?.addEventListener('click', event => {
  event.preventDefault();
  navigateToDestination('search');
});

// ── User dropdown ───────────────────────
const userIcon = document.getElementById('userIcon');
const userDropdown = document.getElementById('userDropdown');
if (userIcon) {
  userIcon.addEventListener('click', e => {
    e.stopPropagation();
    userDropdown.classList.toggle('show');
  });
}
document.addEventListener('click', () => {
  if (userDropdown) userDropdown.classList.remove('show');
});

// ── Home dropdown toggle ───────────────
const dropdownToggle = document.getElementById('dropdownToggle');
const dropdownMenu = document.getElementById('dropdownMenu');
if (dropdownToggle && dropdownMenu) {
  dropdownToggle.addEventListener('click', () => {
    dropdownMenu.classList.toggle('show');
  });
}

// ── Settings panel trigger (from user dropdown) ──
document.getElementById('btnSettings')?.addEventListener('click', openSettings);
document.getElementById('dropdownSettings')?.addEventListener('click', openSettings);
function openSettings() {
  document.getElementById('settingsPanel').classList.add('open');
}
function closeSettings() {
  document.getElementById('settingsPanel').classList.remove('open');
}

// ── Logout ──────────────────────────────
const btnLogout = document.getElementById('btnLogout');
if (btnLogout) {
  btnLogout.addEventListener('click', () => {
    localStorage.removeItem('lominii_token');
    localStorage.removeItem('lominii_uid');
    authToken = '';
    if (dashboardView) dashboardView.style.display = 'none';
    if (landingView) landingView.style.display = 'flex';
    if (particleCanvas) particleCanvas.style.display = 'block';
    if (typeof drawParticles === 'function') drawParticles();
  });
}
document.getElementById('dropdownLogout')?.addEventListener('click', () => {
  document.getElementById('btnLogout').click();
});

// ── Landing buttons and authentication ─────────────────────
async function requestAuth(path, payload) {
  const bases = (typeof API_URLS !== 'undefined' && Array.isArray(API_URLS))
    ? API_URLS
    : [window.location.origin];

  let lastError = null;

  for (const base of bases) {
    try {
      const response = await fetch(base + path, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      let data = {};
      try { data = await response.json(); } catch (_) {}

      if (response.status >= 500) {
        lastError = new Error(data.detail || 'Authentication service unavailable.');
        continue;
      }

      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Request failed. Check your details and try again.'
        );
      }

      return data;
    } catch (error) {
      if (error instanceof TypeError) {
        lastError = error;
        continue;
      }
      throw error;
    }
  }

  throw lastError || new Error('Could not reach the authentication service.');
}

function openLoginModal() {
  let overlay = document.getElementById('lominiiLoginModal');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'lominiiLoginModal';
    overlay.className = 'lm-overlay';
    overlay.hidden = true;
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'lominiiLoginTitle');

    overlay.innerHTML = `
      <section class="lm-card">
        <div class="lm-top">
          <div>
            <p class="lm-eyebrow">WELCOME BACK</p>
            <h2 id="lominiiLoginTitle">Sign in to LOMINII</h2>
            <p class="lm-intro">Continue your search, learning and discovery.</p>
          </div>
          <button type="button" class="lm-close" id="lominiiLoginClose"
            aria-label="Close login">&times;</button>
        </div>
        <form id="lominiiLoginForm">
          <div class="lm-field">
            <label for="lominiiLoginEmail">Email address</label>
            <input id="lominiiLoginEmail" name="email" type="email"
              autocomplete="username" required maxlength="254">
          </div>
          <div class="lm-field">
            <label for="lominiiLoginPassword">Password</label>
            <input id="lominiiLoginPassword" name="password" type="password"
              autocomplete="current-password" required minlength="6">
          </div>
          <p id="lominiiLoginStatus" class="lm-status" aria-live="polite"></p>
          <div class="lm-actions">
            <button class="lm-button lm-primary" id="lominiiLoginSubmit" type="submit">
              <i class="fa fa-sign-in" aria-hidden="true"></i> Sign in
            </button>
            <button class="lm-button lm-secondary" id="lominiiLoginCreate" type="button">
              Create account
            </button>
          </div>
        </form>
      </section>`;

    document.body.appendChild(overlay);

    overlay.querySelector('#lominiiLoginClose').addEventListener('click', () => {
      overlay.hidden = true;
    });

    overlay.addEventListener('click', event => {
      if (event.target === overlay) overlay.hidden = true;
    });

    overlay.querySelector('#lominiiLoginCreate').addEventListener('click', () => {
      overlay.hidden = true;
      if (typeof window.openLomimailRegistration === 'function') {
        window.openLomimailRegistration();
      } else {
        alert('Registration is still loading. Please try again.');
      }
    });

    overlay.querySelector('#lominiiLoginForm').addEventListener('submit', async event => {
      event.preventDefault();

      const form = event.currentTarget;
      const status = overlay.querySelector('#lominiiLoginStatus');
      const submit = overlay.querySelector('#lominiiLoginSubmit');

      status.textContent = '';
      submit.disabled = true;
      submit.textContent = 'Signing in…';

      try {
        const result = await requestAuth('/auth/login', {
          email: form.elements.email.value.trim(),
          password: form.elements.password.value
        });

        if (!result.access_token) {
          throw new Error('The server did not return a login token.');
        }

        localStorage.setItem('lominii_token', result.access_token);
        authToken = result.access_token;
        overlay.hidden = true;
        form.reset();
        showDashboard();
        switchToWorkspace('home');
      } catch (error) {
        status.textContent = error.message || 'Sign-in failed. Please try again.';
        status.className = 'lm-status lm-error';
      } finally {
        submit.disabled = false;
        submit.innerHTML = '<i class="fa fa-sign-in" aria-hidden="true"></i> Sign in';
      }
    });
  }

  overlay.hidden = false;
  const email = overlay.querySelector('#lominiiLoginEmail');
  if (email) email.focus();
}

async function exploreFree() {
  const button = document.getElementById('btnExplore');
  if (button) button.disabled = true;

  try {
    const result = await requestAuth('/auth/guest', {});
    if (result.access_token) {
      localStorage.setItem('lominii_token', result.access_token);
      authToken = result.access_token;
    }
  } catch (error) {
    // Browsing the public search screen should remain available if guest auth
    // is temporarily unavailable.
    console.warn('Guest session unavailable; opening public exploration.', error);
  } finally {
    if (button) button.disabled = false;
    showDashboard();
    switchToWorkspace('home');
  }
}

document.getElementById('btnExplore')?.addEventListener('click', exploreFree);

document.getElementById('btnLogin')?.addEventListener('click', openLoginModal);

document.getElementById('btnSignup')?.addEventListener('click', () => {
  if (typeof window.openLomimailRegistration === 'function') {
    window.openLomimailRegistration();
  } else {
    alert('Registration is still loading. Please try again.');
  }
});

// ── Initial load ────────────────────────
if (authToken) {
  if (splashScreen) splashScreen.style.display = 'none';
  if (landingView) landingView.style.display = 'none';
  if (dashboardView) dashboardView.style.display = 'block';
  switchToWorkspace('home');
}