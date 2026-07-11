/* ===== MULTI‑API FAILOVER ===== */
const API_URLS = ["https://lominii-api.onrender.com", "https://lominii-api.fly.dev"];
async function apiFetch(path, options = {}) {
  for (const baseUrl of API_URLS) {
    try { const url = `${baseUrl}${path}`; const r = await fetch(url, options); if (r.ok) return r; } catch (e) { continue; }
  }
  throw new Error("All API servers are unreachable");
}

/* ===== PARTICLE NETWORK ===== */
const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');
let w, h, particles = [], animId;
const PARTICLE_COUNT = 80, CONNECT_DIST = 120, MOUSE_DIST = 150;
function resize() { w = canvas.width = window.innerWidth; h = canvas.height = window.innerHeight; }
window.addEventListener('resize', resize); resize();
let mouse = { x: -1000, y: -1000 };
window.addEventListener('mousemove', e => { mouse.x = e.clientX; mouse.y = e.clientY; });
window.addEventListener('touchmove', e => { mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY; });
window.addEventListener('touchend', () => { mouse.x = -1000; mouse.y = -1000; });
for (let i = 0; i < PARTICLE_COUNT; i++) {
  particles.push({ x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.5, vy: (Math.random() - 0.5) * 0.5, radius: Math.random() * 2 + 1.5 });
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
      const dx = particles[i].x - particles[j].x, dy = particles[i].y - particles[j].y, dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < CONNECT_DIST) {
        ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y); ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(59,130,246,${0.15 * (1 - dist / CONNECT_DIST)})`; ctx.lineWidth = 0.6; ctx.stroke();
      }
    }
    const dx = particles[i].x - mouse.x, dy = particles[i].y - mouse.y, dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < MOUSE_DIST) {
      ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y); ctx.lineTo(mouse.x, mouse.y);
      ctx.strokeStyle = `rgba(245,158,11,${0.5 * (1 - dist / MOUSE_DIST)})`; ctx.lineWidth = 1; ctx.stroke();
    }
  }
  animId = requestAnimationFrame(drawParticles);
}

/* ===== LANDING → DASHBOARD ===== */
const landingView = document.getElementById('landingView');
const dashboardView = document.getElementById('dashboardView');
const particleCanvas = document.getElementById('particleCanvas');
function showDashboard() {
  landingView.style.display = 'none'; dashboardView.style.display = 'block'; particleCanvas.style.display = 'none';
  if (animId) cancelAnimationFrame(animId);
  document.body.classList.add('search-home');
}
document.getElementById('btnExplore').addEventListener('click', showDashboard);
document.getElementById('btnLogin').addEventListener('click', showDashboard);
document.getElementById('btnSignup').addEventListener('click', ()=>alert('Signup form coming soon'));
drawParticles(); landingView.style.display = 'block'; dashboardView.style.display = 'none';

/* ===== WORKSPACE SWITCHING ===== */
const views = { home: document.getElementById('homeView'), games: document.getElementById('gamesView'), social: document.getElementById('socialView'), edu: document.getElementById('eduView'), quran: document.getElementById('quranView') };
const footerIcons = document.querySelectorAll('.footer-nav .nav-icon');
const backToggle = document.getElementById('backToggle');
const userIcon = document.getElementById('userIcon');
const userDropdown = document.getElementById('userDropdown');
function switchToWorkspace(ws) {
  Object.values(views).forEach(v => v.style.display = 'none');
  if (views[ws]) views[ws].style.display = 'block';
  if (ws === 'home') { document.body.classList.add('search-home'); document.body.classList.remove('workspace-view'); footerIcons.forEach(i=>i.classList.remove('active')); document.querySelector('.nav-icon[data-workspace="home"]').classList.add('active'); backToggle.style.display = 'none'; }
  else { document.body.classList.remove('search-home'); document.body.classList.add('workspace-view'); backToggle.style.display = 'block'; }
  if (ws === 'social') { loadFeed(); }
}
function goHome() { switchToWorkspace('home'); }
footerIcons.forEach(icon => icon.addEventListener('click', ()=>{ switchToWorkspace(icon.dataset.workspace); }));
userIcon.addEventListener('click', (e)=>{ e.stopPropagation(); userDropdown.classList.toggle('show'); });
document.addEventListener('click', ()=>userDropdown.classList.remove('show'));


/* ===== SEARCH ===== */
async function performSearch() {
  const q = document.getElementById('searchInput').value.trim(); if (!q) return;
  const res = document.getElementById('searchResults'); res.innerHTML = 'Searching…';
  try {
    const r = await apiFetch('/api/search', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({q}) });
    const d = await r.json();
    res.innerHTML = `<h3>${d.query}</h3><p><strong>Definition:</strong> ${d.definition||'No definition'}</p><p><strong>AI Summary:</strong> ${d.ai_summary||'Coming soon'}</p><p><strong>Primary Cell:</strong> (${String.fromCharCode(65+d.primary_cell_col)}, ${d.primary_cell_row})</p>`;
  } catch(e) { res.innerHTML = '⚠️ Search failed.'; }
}
document.getElementById('btnSearch').addEventListener('click', performSearch);
document.getElementById('searchInput').addEventListener('keypress', (e)=>{ if(e.key==='Enter') performSearch(); });

/* ===== SOCIAL ===== */
let currentSocialTab = 'feed';
document.getElementById('btnShowFeed').addEventListener('click', ()=>{ currentSocialTab='feed'; showSocialTab(); });
document.getElementById('btnShowNews').addEventListener('click', ()=>{ currentSocialTab='news'; showSocialTab(); });
document.getElementById('btnShowChat').addEventListener('click', ()=>{ currentSocialTab='chat'; showSocialTab(); });
function showSocialTab() {
  document.getElementById('feedContainer').style.display = currentSocialTab==='feed'?'block':'none';
  document.getElementById('newsContainer').style.display = currentSocialTab==='news'?'block':'none';
  document.getElementById('chatContainer').style.display = currentSocialTab==='chat'?'block':'none';
  document.getElementById('postBox').style.display = (currentSocialTab==='feed')?'block':'none';
  if (currentSocialTab === 'feed') loadFeed();
  else if (currentSocialTab === 'news') loadNews();
  else if (currentSocialTab === 'chat') loadMessages();
}
async function loadFeed() {
  const container = document.getElementById('feedContainer');
  try {
    const r = await apiFetch('/api/social/feed');
    const posts = await r.json();
    container.innerHTML = posts.map(p=>`
      <div class="social-post">
        <div class="author" onclick="viewProfile('${p.author_id}')">${p.author_name}</div>
        <p>${p.content}</p>
        <div class="actions">
          <button onclick="likePost('${p.id}')">❤️ ${p.likes}</button>
          <button onclick="commentPost('${p.id}')">💬</button>
        </div>
        <div id="comments-${p.id}" style="margin-top:0.5rem;"></div>
      </div>
    `).join('');
  } catch(e) { container.innerHTML = 'Feed unavailable.'; }
}
async function loadNews() {
  const container = document.getElementById('newsContainer');
  try {
    const r = await apiFetch('/api/social/news');
    const posts = await r.json();
    container.innerHTML = posts.map(p=>`<div class="social-post"><p>${p.content}</p><small>${new Date(p.created_at).toLocaleString()}</small></div>`).join('');
  } catch(e) { container.innerHTML = 'News unavailable.'; }
}
async function loadMessages() {
  // simple polling chat
  const msgs = document.getElementById('chatMessages');
  const recipient = document.getElementById('chatRecipient').value.trim();
  if (!recipient) { msgs.innerHTML = '<p>Enter recipient UID.</p>'; return; }
  try {
    const r = await apiFetch('/api/social/messages/inbox');
    const data = await r.json();
    msgs.innerHTML = data.filter(m=>m.from_uid===recipient || m.from_uid===localStorage.getItem('my_uid')).map(m=>`<p><b>${m.from_uid}</b>: ${m.text}</p>`).join('');
  } catch(e) { msgs.innerHTML = 'Messages unavailable.'; }
}
setInterval(() => { if (currentSocialTab==='chat') loadMessages(); }, 3000);

/* ── Social Workspace Tab Switching ── */

function switchSocialTab(tab) {
  const friendsFeed = document.getElementById('friendsFeed');
  const newsFeed = document.getElementById('newsFeed');
  const tabFriends = document.getElementById('tabFriends');
  const tabNews = document.getElementById('tabNews');

  if (tab === 'friends') {
    friendsFeed.style.display = 'block';
    newsFeed.style.display = 'none';
    tabFriends.classList.add('active');
    tabNews.classList.remove('active');
  } else {
    friendsFeed.style.display = 'none';
    newsFeed.style.display = 'block';
    tabFriends.classList.remove('active');
    tabNews.classList.add('active');
  }
}

/* ── Category Subscription (lomiNews) ── */

async function subscribeCategory(category) {
  try {
    const response = await apiFetch('/api/social/news/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: category })
    });
    if (response.ok) {
      alert(`Subscribed to ${category} news!`);
    } else {
      const err = await response.json();
      alert(err.detail || 'Subscription failed');
    }
  } catch (e) {
    alert('Network error. Please try again.');
  }
}

// ── Social Tab Switching ──
function switchSocialTab(tab) {
  const friendsFeed = document.getElementById('friendsFeed');
  const newsFeed = document.getElementById('newsFeed');
  const tabFriends = document.getElementById('tabFriends');
  const tabNews = document.getElementById('tabNews');

  if (tab === 'friends') {
    friendsFeed.style.display = 'block';
    newsFeed.style.display = 'none';
    tabFriends.classList.add('active');
    tabNews.classList.remove('active');
    loadFriendsFeed();
  } else {
    friendsFeed.style.display = 'none';
    newsFeed.style.display = 'block';
    tabFriends.classList.remove('active');
    tabNews.classList.add('active');
    loadNewsFeed();
  }
}

// ── Load Friends Feed ──
async function loadFriendsFeed() {
  const container = document.getElementById('friendsPosts');
  const loading = document.getElementById('friendsLoading');
  try {
    const resp = await apiFetch('/api/social/feed');
    if (!resp.ok) throw new Error('Failed to load feed');
    const posts = await resp.json();
    if (posts.length === 0) {
      container.innerHTML = '<div class="placeholder">No posts from friends yet. Follow someone to see their updates!</div>';
    } else {
      container.innerHTML = posts.map(p => `
        <div class="card">
          <div class="post-author">${p.author_name}</div>
          <p>${p.content}</p>
          <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
        </div>
      `).join('');
    }
    loading.style.display = 'none';
  } catch (e) {
    container.innerHTML = '<div class="placeholder">⚠️ Could not load posts. Please try again.</div>';
    loading.style.display = 'none';
  }
}

// ── Load lomiNews Feed ──
async function loadNewsFeed() {
  const container = document.getElementById('newsPosts');
  const loading = document.getElementById('newsLoading');
  try {
    const resp = await apiFetch('/api/social/news');
    if (!resp.ok) throw new Error('Failed to load news');
    const posts = await resp.json();
    if (posts.length === 0) {
      container.innerHTML = '<div class="placeholder">No news posts yet. Subscribe to categories or follow newscasters!</div>';
    } else {
      container.innerHTML = posts.map(p => `
        <div class="card">
          <div class="post-author">${p.author_name || 'Newscaster'} <span class="badge-newscaster">Newscaster</span></div>
          <p>${p.content}</p>
          <div class="post-time">${new Date(p.created_at).toLocaleString()}</div>
        </div>
      `).join('');
    }
    loading.style.display = 'none';
  } catch (e) {
    container.innerHTML = '<div class="placeholder">⚠️ Could not load news. Please try again.</div>';
    loading.style.display = 'none';
  }
}

// ── Category Subscription (lomiNews) ──
async function subscribeCategory(category) {
  try {
    const response = await apiFetch('/api/social/news/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: category })
    });
    if (response.ok) {
      alert(`Subscribed to ${category} news!`);
      loadNewsFeed();
    } else {
      const err = await response.json();
      alert(err.detail || 'Subscription failed');
    }
  } catch (e) {
    alert('Network error. Please try again.');
  }
}

// Post, like, comment actions
document.getElementById('btnPost').addEventListener('click', async () => {
  const content = document.getElementById('postContent').value.trim();
  if (!content) return;
  await apiFetch('/api/social/post', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({content}) });
  document.getElementById('postContent').value = '';
  loadFeed();
});
async function likePost(postId) {
  await apiFetch('/api/social/like', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:postId}) });
  loadFeed();
}
async function commentPost(postId) {
  const txt = prompt('Enter your comment:');
  if (!txt) return;
  await apiFetch('/api/social/comment', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({post_id:postId, content:txt}) });
  loadFeed();
}
async function viewProfile(uid) {
  const r = await apiFetch(`/api/social/profile/${uid}`);
  const profile = await r.json();
  document.getElementById('profileName').textContent = profile.full_name;
  document.getElementById('profileRole').textContent = profile.creator_role === 'newscaster' ? `Newscaster (${profile.news_category})` : 'Content Creator';
  document.getElementById('profilePosts').innerHTML = profile.posts.map(p=>`<p>${p.content}</p>`).join('');
  document.getElementById('profileModal').style.display = 'flex';
}
document.getElementById('closeProfile').addEventListener('click', ()=>{ document.getElementById('profileModal').style.display = 'none'; });
document.getElementById('btnProfile').addEventListener('click', ()=>{ const uid = localStorage.getItem('my_uid')||'demo'; viewProfile(uid); });
document.getElementById('btnLogout').addEventListener('click', ()=>{ landingView.style.display='block'; dashboardView.style.display='none'; particleCanvas.style.display='block'; drawParticles(); });
document.getElementById('btnChatSend').addEventListener('click', async ()=>{
  const to = document.getElementById('chatRecipient').value.trim();
  const txt = document.getElementById('chatInput').value.trim();
  if (!to||!txt) return;
  await apiFetch('/api/social/messages/send', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({target_uid:to, text:txt}) });
  document.getElementById('chatInput').value = '';
  loadMessages();
});

// initialize
switchToWorkspace('home');
showSocialTab();