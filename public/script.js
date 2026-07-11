/* ===== MULTI‑API FAILOVER ===== */
const API_URLS = [
  "https://lominii-api.onrender.com",
  "https://lominii-api.fly.dev"
];

async function apiFetch(path, options = {}) {
  for (const baseUrl of API_URLS) {
    try {
      const url = `${baseUrl}${path}`;
      const response = await fetch(url, options);
      if (response.ok) return response;
    } catch (error) {
      continue;
    }
  }
  throw new Error("All API servers are unreachable");
}

/* ===== PARTICLE NETWORK (landing page) ===== */
const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');
let w, h;
const particles = [];
const PARTICLE_COUNT = 80;
const CONNECT_DIST = 120;
const MOUSE_DIST = 150;
let animationId;

function resize() {
  w = canvas.width = window.innerWidth;
  h = canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

let mouse = { x: -1000, y: -1000 };
window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });
window.addEventListener('touchmove', e => { mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY; });
window.addEventListener('touchend', () => { mouse.x = -1000; mouse.y = -1000; });

for (let i = 0; i < PARTICLE_COUNT; i++) {
  particles.push({
    x: Math.random() * w, y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.5, vy: (Math.random() - 0.5) * 0.5,
    radius: Math.random() * 2 + 1.5
  });
}

function drawParticles() {
  ctx.clearRect(0, 0, w, h);
  for (let p of particles) {
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0 || p.x > w) p.vx *= -1;
    if (p.y < 0 || p.y > h) p.vy *= -1;
    ctx.beginPath(); ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(59,130,246,0.7)'; ctx.fill();
  }
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < CONNECT_DIST) {
        ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y); ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(59,130,246,${0.15 * (1 - dist / CONNECT_DIST)})`; ctx.lineWidth = 0.6; ctx.stroke();
      }
    }
    const dx = particles[i].x - mouse.x, dy = particles[i].y - mouse.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < MOUSE_DIST) {
      ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y); ctx.lineTo(mouse.x, mouse.y);
      ctx.strokeStyle = `rgba(245,158,11,${0.5 * (1 - dist / MOUSE_DIST)})`; ctx.lineWidth = 1; ctx.stroke();
    }
  }
  animationId = requestAnimationFrame(drawParticles);
}

/* ===== LANDING → DASHBOARD TRANSITION ===== */
const landingView = document.getElementById('landingView');
const dashboardView = document.getElementById('dashboardView');
const particleCanvas = document.getElementById('particleCanvas');

function showDashboard() {
  landingView.style.display = 'none';
  dashboardView.style.display = 'block';
  particleCanvas.style.display = 'none';
  if (animationId) cancelAnimationFrame(animationId);   // stop particle loop
  document.body.classList.add('search-home');
}

// button bindings (landing page)
document.getElementById('btnExplore').addEventListener('click', showDashboard);
document.getElementById('btnLogin').addEventListener('click', showDashboard);
document.getElementById('btnSignup').addEventListener('click', () => alert('Signup form coming soon'));

// Start particle animation & show landing
drawParticles();
landingView.style.display = 'block';
dashboardView.style.display = 'none';

/* ===== DASHBOARD WORKSPACE SWITCHING ===== */
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
const userIcon = document.getElementById('userIcon');
const userDropdown = document.getElementById('userDropdown');

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

userIcon.addEventListener('click', (e) => {
  e.stopPropagation();
  userDropdown.classList.toggle('show');
});
document.addEventListener('click', () => userDropdown.classList.remove('show'));

// initialise dashboard to home
switchToWorkspace('home');

/* ===== SEARCH FUNCTIONALITY (connected to real backend) ===== */
async function performSearch() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  const resultsDiv = document.getElementById('searchResults');
  resultsDiv.innerHTML = 'Searching…';

  try {
    const response = await apiFetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: query })
    });
    const data = await response.json();
    resultsDiv.innerHTML = `
      <h3>${data.query}</h3>
      <p><strong>Definition:</strong> ${data.definition || 'No definition found'}</p>
      <p><strong>AI Summary:</strong> ${data.ai_summary || 'Coming soon'}</p>
      <p><strong>Primary Cell:</strong> (${String.fromCharCode(65 + data.primary_cell_col)}, ${data.primary_cell_row})</p>
      ${data.news ? '<h4>News</h4>' + data.news.map(n => `<p>📰 ${n.title}</p>`).join('') : ''}
    `;
  } catch (err) {
    resultsDiv.innerHTML = '⚠️ Search failed. Please try again.';
  }
}

document.getElementById('btnSearch').addEventListener('click', performSearch);
document.getElementById('searchInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') performSearch();
});