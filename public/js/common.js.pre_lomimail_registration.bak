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
  const activeIcon = document.querySelector(`.nav-icon[data-workspace="${workspace}"]`);
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
footerIcons.forEach(icon => {
  icon.addEventListener('click', () => switchToWorkspace(icon.dataset.workspace));
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
document.getElementById('dropdownToggle').addEventListener('click', () => {
  document.getElementById('dropdownMenu').classList.toggle('show');
});

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
document.getElementById('btnLogout').addEventListener('click', () => {
  localStorage.removeItem('lominii_token');
  authToken = '';
  dashboardView.style.display = 'none';
  landingView.style.display = 'block';
  if (particleCanvas) particleCanvas.style.display = 'block';
  if (typeof drawParticles === 'function') drawParticles();
});
document.getElementById('dropdownLogout')?.addEventListener('click', () => {
  document.getElementById('btnLogout').click();
});

// ── Landing buttons ─────────────────────
document.getElementById('btnExplore')?.addEventListener('click', showDashboard);
document.getElementById('btnLogin')?.addEventListener('click', showDashboard);
document.getElementById('btnSignup')?.addEventListener('click', () => alert('Signup coming soon.'));

// ── Initial load ────────────────────────
if (authToken) {
  splashScreen.style.display = 'none';
  landingView.style.display = 'none';
  dashboardView.style.display = 'block';
  switchToWorkspace('home');
}