const userIcon = document.getElementById('userIcon');
const userDropdown = document.getElementById('userDropdown');

userIcon.addEventListener('click', (e) => {
  e.stopPropagation();
  userDropdown.classList.toggle('show');
});
document.addEventListener('click', () => {
  userDropdown.classList.remove('show');
});

// Logout
document.getElementById('btnLogout').addEventListener('click', () => {
  localStorage.removeItem('lominii_token');
  localStorage.removeItem('lominii_uid');
  landingView.style.display = 'block';
  dashboardView.style.display = 'none';
  particleCanvasEl.style.display = 'block';
  drawParticles();
});