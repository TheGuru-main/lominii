/* ==========================================================
   LOMINII SETTINGS
   Panel control, preferences, BubbleJumbo cell display
========================================================== */

const settingsPanel = document.getElementById('settingsPanel');

// Open / close
function openSettings() {
  settingsPanel.classList.add('open');
  loadSecurityInfo();
}
function closeSettings() {
  settingsPanel.classList.remove('open');
}

// Load BubbleJumbo info – uses the token already stored
function loadSecurityInfo() {
  const token = localStorage.getItem('lominii_token');
  if (!token) return;

  // Decode the JWT payload (without verifying) – the bj claims are inside
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    if (payload.bj) {
      const col = payload.bj.col;
      const row = payload.bj.row;
      const letter = String.fromCharCode(65 + col);
      document.getElementById('bjCell').textContent = `(${letter}, ${row})`;
      document.getElementById('bjK').textContent = payload.bj.K || 5;
    }
  } catch (e) {
    document.getElementById('bjCell').textContent = 'N/A';
  }

  // Failed attempts – stored in memory only, so we can't show persistent value
  // But we can call an endpoint later. For now, show 0.
  document.getElementById('bjFails').textContent = '0';
}

// Reset failure counter (call the backend endpoint)
async function resetSecurityCounter() {
  try {
    const resp = await apiFetch('/auth/reset-failures', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('lominii_token')}` }
    });
    if (resp.ok) {

     // Load failed attempts from backend
async function loadSecurityInfo() {
  // … existing token/cell parsing …

  // Fetch real failure count
  try {
    const resp = await apiFetch('/auth/failure-count', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('lominii_token')}` }
    });
    if (resp.ok) {
      const data = await resp.json();
      document.getElementById('bjFails').textContent = data.failures;
    } else {
      document.getElementById('bjFails').textContent = '?';
    }
  } catch (e) {
    document.getElementById('bjFails').textContent = '?';
  }
}
      document.getElementById('settingsMsg').textContent = '✅ Security counter reset.';
    } else {
      document.getElementById('settingsMsg').textContent = '❌ Failed to reset.';
    }
  } catch (e) {
    document.getElementById('settingsMsg').textContent = '❌ Network error.';
  }
}

// Save preferences (language, country, data sources)
async function saveSettings() {
  const lang = document.getElementById('settingLanguage').value;
  const country = document.getElementById('settingCountry').value;
  const sources = {
    wikipedia: document.getElementById('sourceWikipedia').checked,
    banking: document.getElementById('sourceBanking').checked,
    news: document.getElementById('sourceNews').checked,
    dictionary: document.getElementById('sourceDictionary').checked
  };
  const challenge = document.getElementById('bjChallenge').checked;

  const payload = { language: lang, country, data_sources: sources, cell_challenge: challenge };

  try {
    const resp = await apiFetch('/auth/preferences', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('lominii_token')}`
      },
      body: JSON.stringify(payload)
    });
    if (resp.ok) {
      document.getElementById('settingsMsg').textContent = '✅ Preferences saved.';
    } else {
      document.getElementById('settingsMsg').textContent = '❌ Save failed.';
    }
  } catch (e) {
    document.getElementById('settingsMsg').textContent = '❌ Network error.';
  }
}

// Hook the existing "Language & Preferences" dropdown link (if present)
document.addEventListener('DOMContentLoaded', () => {
  const prefLink = document.querySelector('#userDropdown a[href="#"]:nth-child(4)'); // "Language & Preferences" is the 4th link? Actually it's the 4th link in the dropdown (0:My Profile,1:Privacy & Consent,2:Premium Status,3:Language & Preferences)
  if (prefLink) {
    prefLink.addEventListener('click', (e) => {
      e.preventDefault();
      openSettings();
    });
  }
});