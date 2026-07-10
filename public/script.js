/* ---------- Multi‑API failover configuration ---------- */
const API_URLS = [
  "https://lominii-api.onrender.com",    // Primary (Render)
  "https://lominii-api.fly.dev"          // Secondary (Fly.io)
];

/**
 * Fetch wrapper that tries each API URL in order.
 * Returns the response from the first successful call.
 * Throws an error if all URLs fail.
 */
async function apiFetch(path, options = {}) {
  for (const baseUrl of API_URLS) {
    try {
      const url = `${baseUrl}${path}`;
      const response = await fetch(url, options);
      if (response.ok) {
        return response;
      }
      // If response is not ok (e.g., 500), try the next URL
    } catch (error) {
      // Network error, try the next URL
      continue;
    }
  }
  throw new Error("All API servers are unreachable");
}

/* ---------- Interactive particle network ---------- */
const canvas = document.getElementById('particleCanvas');
const ctx = canvas.getContext('2d');
let w, h;
const particles = [];
const PARTICLE_COUNT = 80;
const CONNECT_DIST = 120;
const MOUSE_DIST = 150;

function resize() {
  w = canvas.width = window.innerWidth;
  h = canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

// mouse / touch tracking
let mouse = { x: -1000, y: -1000 };
window.addEventListener('mousemove', e => {
  mouse.x = e.clientX;
  mouse.y = e.clientY;
});
window.addEventListener('touchmove', e => {
  mouse.x = e.touches[0].clientX;
  mouse.y = e.touches[0].clientY;
});
window.addEventListener('touchend', () => {
  mouse.x = -1000;
  mouse.y = -1000;
});

// create particles
for (let i = 0; i < PARTICLE_COUNT; i++) {
  particles.push({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.5,
    vy: (Math.random() - 0.5) * 0.5,
    radius: Math.random() * 2 + 1.5
  });
}

function draw() {
  ctx.clearRect(0, 0, w, h);
  // update & draw particles
  for (let p of particles) {
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < 0 || p.x > w) p.vx *= -1;
    if (p.y < 0 || p.y > h) p.vy *= -1;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(59,130,246,0.7)';
    ctx.fill();
  }
  // draw connections
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x;
      const dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < CONNECT_DIST) {
        ctx.beginPath();
        ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(59,130,246,${0.15 * (1 - dist / CONNECT_DIST)})`;
        ctx.lineWidth = 0.6;
        ctx.stroke();
      }
    }
    // mouse interaction
    const dx = particles[i].x - mouse.x;
    const dy = particles[i].y - mouse.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < MOUSE_DIST) {
      ctx.beginPath();
      ctx.moveTo(particles[i].x, particles[i].y);
      ctx.lineTo(mouse.x, mouse.y);
      ctx.strokeStyle = `rgba(245,158,11,${0.5 * (1 - dist / MOUSE_DIST)})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }
  requestAnimationFrame(draw);
}
draw();

/* ---------- Navigation stubs (to be replaced with real routing) ---------- */
function navigate(path) {
  alert(`Navigate to ${path}`);
}
function exploreAsGuest() {
  alert('Entering LOMINII as a guest…');
}