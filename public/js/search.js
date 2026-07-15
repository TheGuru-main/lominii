// ========== Search Home – performSearch ==========
async function performSearch() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  const resultsDiv = document.getElementById('searchResults');
  resultsDiv.innerHTML = '<div class="loading-pulse">✨ LOMINII is thinking…</div>';

  try {
    const response = await apiFetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: query })
    });
    const data = await response.json();

    let html = '';

    // Did you mean?
    if (data.did_you_mean) {
      html += `<div class="did-you-mean">Did you mean: <span onclick="document.getElementById('searchInput').value='${data.did_you_mean}';performSearch()">${data.did_you_mean}</span>?</div>`;
    }

    // AI Summary
    if (data.ai_summary) {
      html += `
        <div class="ai-summary-card">
          <div class="ai-badge">🧠 AI Summary</div>
          <p>${data.ai_summary}</p>
          <button class="btn btn-outline btn-sm" onclick="alert('Premium feature coming soon')">🔍 Discover More</button>
        </div>`;
    }

    // Dictionary Definition
    if (data.definition) {
      html += `
        <div class="definition-card">
          <div class="def-badge">📖 Definition</div>
          <p>${data.definition}</p>
        </div>`;
    }

    // Cell info
    html += `
      <div class="cell-info">
        📍 Cell: (${String.fromCharCode(65 + data.primary_cell_col)}, ${data.primary_cell_row}) &nbsp;|&nbsp; 🔗 L‑sum: ${data.Lsum}, S‑sum: ${data.Ssum}
      </div>`;

    // News
    if (data.news && data.news.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">📰 Related News</h4>';
      data.news.forEach(n => {
        html += `<div class="news-item">📌 ${n.title}</div>`;
      });
    }

    // Related Questions
    if (data.related_questions && data.related_questions.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">🤔 People Also Ask</h4>';
      data.related_questions.forEach(q => {
        html += `<div class="related-q" onclick="document.getElementById('searchInput').value='${q}';performSearch()">${q}</div>`;
      });
    }

    resultsDiv.innerHTML = html || '<p>No results found for your query.</p>';

  } catch (err) {
    resultsDiv.innerHTML = '<div class="error-state">⚠️ Search failed. Please try again.</div>';
  }
}

// ========== Home Screen Cards ==========
async function loadHomeCards() {
  // 1. Trending
  try {
    const tr = await apiFetch('/api/trending');
    const trends = await tr.json();
    const list = document.getElementById('trendingList');
    if (trends && trends.length) {
      list.innerHTML = trends.map(t => `<span class="trend-chip">${t}</span>`).join(' ');
    } else {
      list.innerHTML = 'Nothing trending yet.';
    }
  } catch (e) {
    document.getElementById('trendingList').innerHTML = 'Trending unavailable.';
  }

  // 2. News
  try {
    const nw = await apiFetch('/api/news?category=general');
    const data = await nw.json();
    const list = document.getElementById('newsList');
    if (data.articles && data.articles.length) {
      list.innerHTML = data.articles.slice(0,4).map(a =>
        `<div class="news-headline">📌 ${a.title}</div>`).join('');
    } else {
      list.innerHTML = 'No news right now.';
    }
  } catch (e) {
    document.getElementById('newsList').innerHTML = 'News unavailable.';
  }

  // 3. Prayer Times
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(async pos => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      try {
        const resp = await fetch(`https://api.aladhan.com/v1/timings?latitude=${lat}&longitude=${lon}&method=2`);
        const data = await resp.json();
        const timings = data.data.timings;
        document.getElementById('prayerList').innerHTML = `
          Fajr: ${timings.Fajr}<br>Dhuhr: ${timings.Dhuhr}<br>Asr: ${timings.Asr}<br>Maghrib: ${timings.Maghrib}<br>Isha: ${timings.Isha}`;
      } catch (e) {
        document.getElementById('prayerList').innerHTML = 'Prayer times unavailable.';
      }
    }, () => {
      document.getElementById('prayerList').innerHTML = 'Location needed for prayer times.';
    });
  } else {
    document.getElementById('prayerList').innerHTML = 'Location not supported.';
  }

  // 4. Mini Map
  if (typeof L !== 'undefined' && document.getElementById('mapStatus')) {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(pos => {
        const mapDiv = document.getElementById('cardMap');
        mapDiv.innerHTML = `<div id="miniMap" style="height:120px; border-radius:12px;"></div>`;
        const miniMap = L.map('miniMap').setView([pos.coords.latitude, pos.coords.longitude], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap'
        }).addTo(miniMap);
        L.marker([pos.coords.latitude, pos.coords.longitude]).addTo(miniMap);
      }, () => {
        document.getElementById('mapStatus').innerHTML = 'Location unavailable.';
      });
    } else {
      document.getElementById('mapStatus').innerHTML = 'Geolocation not supported.';
    }
  }
}

// ========== Event listeners (keep your existing ones) ==========
document.addEventListener('DOMContentLoaded', () => {
  const btnSearch = document.getElementById('btnSearch');
  const searchInput = document.getElementById('searchInput');
  if (btnSearch) btnSearch.addEventListener('click', performSearch);
  if (searchInput) searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });
});