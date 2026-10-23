// ── Global state ──────────────────────────
let authToken = localStorage.getItem('lominii_token') || '';

// ── Views ────────────────────────────────

const views = {
  home: document.getElementById('homeView'),
  games: document.getElementById('gamesView'),
  quran: document.getElementById('quranView')
};
const footerIcons = document.querySelectorAll('.footer-nav .nav-icon');
const backToggle = document.getElementById('backToggle');
const splashScreen = document.getElementById('splashScreen');
const landingView = document.getElementById('landingView');
const dashboardView = document.getElementById('dashboardView');
const particleCanvas = document.getElementById('particleCanvas');

// Initial routing below decides which screen is visible.
 // No delayed landing-page timer: it could override authenticated routing.

// ── Show Dashboard ──────────────────────
function showDashboard() {
  if (landingView) landingView.style.display = 'none';
  if (dashboardView) dashboardView.style.display = 'block';
  if (typeof stopParticles === 'function') stopParticles();
  else if (particleCanvas) particleCanvas.style.display = 'none';
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
    case 'games':
      if (typeof initialiseGames === 'function') initialiseGames();
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


// ── User dropdown and account profile ───────────────────
const userIcon = document.getElementById('userIcon');
const userDropdown = document.getElementById('userDropdown');

function ensureAccountMenuItem(id, label) {
  if (!userDropdown || document.getElementById(id)) return;

  const link = document.createElement('a');
  link.href = '#';
  link.id = id;
  link.textContent = label;

  const logoutLink = userDropdown.querySelector('#btnLogout');
  if (logoutLink) {
    userDropdown.insertBefore(link, logoutLink);
  } else {
    userDropdown.appendChild(link);
  }
}

ensureAccountMenuItem('btnSignupFromProfile', 'Create account');
ensureAccountMenuItem('btnAboutLominii', 'About LOMINII');

if (userIcon && userDropdown) {
  // Replace the hard-coded "A" with a neutral profile stub.
  const initialNode = Array.from(userIcon.childNodes).find(
    node => node.nodeType === Node.TEXT_NODE && node.textContent.trim()
  );

  if (initialNode) initialNode.textContent = '👤 ';

  userIcon.setAttribute('role', 'button');
  userIcon.setAttribute('tabindex', '0');
  userIcon.setAttribute('aria-label', 'Open account menu');
  userIcon.setAttribute('aria-expanded', 'false');

  const toggleUserMenu = event => {
    event.stopPropagation();
    const isOpen = userDropdown.classList.toggle('show');
    userIcon.setAttribute('aria-expanded', String(isOpen));
  };

  userIcon.addEventListener('click', toggleUserMenu);
  userIcon.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleUserMenu(event);
    }
  });

  userDropdown.addEventListener('click', event => {
    event.stopPropagation();
  });

  document.addEventListener('click', () => {
    userDropdown.classList.remove('show', 'open');
    userIcon.setAttribute('aria-expanded', 'false');
  });
}

function closeUserMenu() {
  if (userDropdown) userDropdown.classList.remove('show', 'open');
  if (userIcon) userIcon.setAttribute('aria-expanded', 'false');
}

function openLominiiAccountPanel(section) {
  let overlay = document.getElementById('lominiiAccountPanel');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'lominiiAccountPanel';
    overlay.className = 'lm-account-overlay';
    overlay.hidden = true;
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'lmAccountTitle');

    overlay.innerHTML = `
      <section class="lm-account-card">
        <header class="lm-account-header">
          <div>
            <p class="lm-account-eyebrow">LOMINII ACCOUNT</p>
            <h2 id="lmAccountTitle">My Profile</h2>
          </div>
          <button type="button" id="lmAccountClose"
            class="lm-account-close" aria-label="Close profile">&times;</button>
        </header>

        <section class="lm-account-section">
          <h3>Account details</h3>
          <div class="lm-account-row">
            <span>Account type</span>
            <strong id="lmAccountType">Free search</strong>
          </div>
          <div class="lm-account-row">
            <span>Status</span>
            <strong id="lmAccountStatus">Guest session</strong>
          </div>
          <div class="lm-account-row">
            <span>Email</span>
            <strong id="lmAccountEmail">Not provided</strong>
          </div>
          <div class="lm-account-row">
            <span>Username</span>
            <strong id="lmAccountUsername">Not provided</strong>
          </div>
          <p class="lm-account-note" id="lmAccountNote">
            These details reflect information available in this browser session.
          </p>
        </section>

        <section class="lm-account-section">
          <h3>Free access</h3>
          <p>
            You can explore LOMINII search without completing registration.
            Creating an account is a separate step.
          </p>
          <div class="lm-account-actions">
            <button type="button" id="lmAccountSignup"
              class="lm-account-primary">Create account</button>
            <button type="button" id="lmAccountSignin"
              class="lm-account-secondary">Sign in</button>
          </div>
        </section>

        <section class="lm-account-section" id="lmAboutSection">
          <h3>About LOMINII</h3>
          <p>
            LOMINII is designed to bring search, knowledge, learning,
            research and discovery into one adaptive digital experience.
          </p>
          <p>
            Explore freely, then create an account when you are ready
            to access account-based features.
          </p>
        </section>
      </section>`;

    document.body.appendChild(overlay);

    overlay.querySelector('#lmAccountClose').addEventListener('click', () => {
      overlay.hidden = true;
    });

    overlay.addEventListener('click', event => {
      if (event.target === overlay) overlay.hidden = true;
    });

    overlay.querySelector('#lmAccountSignup').addEventListener('click', () => {
      overlay.hidden = true;
      if (typeof window.openLomimailRegistration === 'function') {
        window.openLomimailRegistration();
      } else {
        alert('Registration is still loading. Please try again.');
      }
    });

    overlay.querySelector('#lmAccountSignin').addEventListener('click', () => {
      overlay.hidden = true;
      if (typeof openLoginModal === 'function') {
        openLoginModal();
      } else {
        alert('Sign-in is still loading. Please try again.');
      }
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !overlay.hidden) {
        overlay.hidden = true;
      }
    });
  }

  const email = localStorage.getItem('lominii_email') || '';
  const username = localStorage.getItem('lominii_username') || '';
  const accountType = localStorage.getItem('lominii_account_type') ||
    (email ? 'registered' : 'guest');
  const isGuest = accountType !== 'registered';

  overlay.querySelector('#lmAccountType').textContent =
    isGuest ? 'Free search (guest)' : 'Registered account';

  overlay.querySelector('#lmAccountStatus').textContent =
    isGuest ? 'Exploring without registration' : 'Signed-in session';

  overlay.querySelector('#lmAccountEmail').textContent =
    email || 'Not provided in this session';

  overlay.querySelector('#lmAccountUsername').textContent =
    username || 'Not provided in this session';

  overlay.querySelector('#lmAccountNote').textContent =
    'Only details available in this browser session are shown here. ' +
    'This panel does not invent or retrieve unverified profile details.';

  overlay.querySelector('#lmAccountSignup').hidden = !isGuest;
  overlay.querySelector('#lmAccountSignin').hidden = !isGuest;

  overlay.hidden = false;

  if (section === 'about') {
    overlay.querySelector('#lmAboutSection').scrollIntoView({
      block: 'nearest'
    });
  } else {
    overlay.querySelector('#lmAccountTitle').textContent = 'My Profile';
    overlay.querySelector('#lmAccountClose').focus();
  }
}

document.getElementById('btnProfile')?.addEventListener('click', event => {
  event.preventDefault();
  closeUserMenu();
  openLominiiAccountPanel('profile');
});

document.getElementById('btnSignupFromProfile')?.addEventListener('click', event => {
  event.preventDefault();
  closeUserMenu();
  if (typeof window.openLomimailRegistration === 'function') {
    window.openLomimailRegistration();
  } else {
    alert('Registration is still loading. Please try again.');
  }
});

document.getElementById('btnAboutLominii')?.addEventListener('click', event => {
  event.preventDefault();
  closeUserMenu();
  openLominiiAccountPanel('about');
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
  btnLogout.addEventListener('click', event => {
    event.preventDefault();
    localStorage.removeItem('lominii_token');
    localStorage.removeItem('lominii_uid');
    localStorage.removeItem('lominii_account_type');
    localStorage.removeItem('lominii_email');
    localStorage.removeItem('lominii_username');
    authToken = '';

    if (dashboardView) dashboardView.style.display = 'none';
    if (landingView) landingView.style.display = '';
    document.body.classList.remove('search-home', 'workspace-view');

    if (typeof startParticles === 'function') startParticles();
    else if (particleCanvas) particleCanvas.style.display = 'block';
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
        localStorage.setItem('lominii_account_type', 'registered');
        localStorage.setItem('lominii_email', form.elements.email.value.trim());
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
    if (!result || !result.access_token) {
      throw new Error('The guest service did not return a session token.');
    }

    localStorage.setItem('lominii_token', result.access_token);
    localStorage.setItem('lominii_account_type', 'guest');
    localStorage.removeItem('lominii_email');
    authToken = result.access_token;

    showDashboard();
    switchToWorkspace('home');
  } catch (error) {
    console.error('Guest session could not be started:', error);
    alert(
      'Free exploration is temporarily unavailable. ' +
      'Please try again shortly.'
    );
  } finally {
    if (button) button.disabled = false;
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
if (splashScreen) splashScreen.style.display = 'none';

if (authToken) {
  if (landingView) landingView.style.display = 'none';
  if (dashboardView) dashboardView.style.display = 'block';
  if (particleCanvas) particleCanvas.style.display = 'none';
  document.body.classList.add('search-home');
  switchToWorkspace('home');
} else {
  if (landingView) landingView.style.display = '';
  if (dashboardView) dashboardView.style.display = 'none';
  if (particleCanvas) particleCanvas.style.display = 'block';
}