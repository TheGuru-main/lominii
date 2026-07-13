const appRoot = document.getElementById('appRoot');
const homeView = document.getElementById('homeView');
const views = {
  home: homeView,
  games: document.getElementById('gamesView'),
  social: document.getElementById('socialView'),
  edu: document.getElementById('eduView'),
  quran: document.getElementById('quranView')
};
const footerIcons = document.querySelectorAll('.footer-nav .nav-icon');
const backToggle = document.getElementById('backToggle');

function switchToWorkspace(workspace) {
  Object.values(views).forEach(v => v.style.display = 'none');
  if (views[workspace]) views[workspace].style.display = 'block';

  if (workspace === 'home') {
    document.body.classList.add('search-home');
    document.body.classList.remove('workspace-view');
    footerIcons.forEach(icon => icon.classList.remove('active'));
    document.querySelector('.nav-icon[data-workspace="home"]').classList.add('active');
    backToggle.style.display = 'none';
  } else {
    document.body.classList.remove('search-home');
    document.body.classList.add('workspace-view');
    backToggle.style.display = 'block';
  }
}

function goHome() { switchToWorkspace('home'); }

footerIcons.forEach(icon => {
  icon.addEventListener('click', () => {
    const ws = icon.getAttribute('data-workspace');
    switchToWorkspace(ws);
  });
});

// Initialise to home
switchToWorkspace('home');