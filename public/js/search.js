// ========== Search Home – performSearch ==========
function escapeSearchHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function searchResultLink(item) {
  const title = escapeSearchHtml(item && (item.title || item.url) || "Result");
  try {
    const parsed = new URL(String(item && item.url || ""));
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return title;
    return `<a href="${escapeSearchHtml(parsed.href)}" target="_blank" rel="noopener noreferrer">${title}</a>`;
  } catch (_) { return title; }
}

async function performSearch() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  const resultsDiv = document.getElementById('searchResults');
  resultsDiv.innerHTML = '<div class="loading-pulse">✨ LOMINII is thinking…</div>';

  try {
    const response = await apiFetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify((() => {
        const payload = { q: query };
        const languageControl = document.querySelector(
          '[name="language"], #searchLanguage, #languageSelect'
        );
        const selectedLanguage = languageControl && languageControl.value;
        if (selectedLanguage) payload.language = selectedLanguage;
        return payload;
      })())
    });
    const data = await response.json();
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      throw new Error('The search service returned an invalid response.');
    }

    let html = '';

    // Did you mean?
    if (data.did_you_mean) {
      const suggestion = escapeSearchHtml(data.did_you_mean);
      html += `<div class="did-you-mean">Did you mean: <button type="button" class="search-query-action" data-search-query="${suggestion}">${suggestion}</button>?</div>`;
    }

    // AI Summary
    if (data.ai_summary) {
      html += `
        <div class="ai-summary-card">
          <div class="ai-badge">🧠 AI Summary</div>
          <p>${escapeSearchHtml(data.ai_summary)}</p>
          <button class="btn btn-outline btn-sm" onclick="alert('Premium feature coming soon')">🔍 Discover More</button>
        </div>`;
    }

    // Dictionary Definition
    if (data.definition) {
      html += `
        <div class="definition-card">
          <div class="def-badge">📖 Dictionary</div>
          ${data.dictionary && data.dictionary.word
            ? `<strong>${escapeSearchHtml(data.dictionary.word)}</strong>`
            : ''}
          ${data.dictionary && data.dictionary.part_of_speech
            ? `<span class="dictionary-pos">${escapeSearchHtml(data.dictionary.part_of_speech)}</span>`
            : ''}
          <p>${escapeSearchHtml(data.definition)}</p>
          ${data.dictionary && data.dictionary.source
            ? `<small class="dictionary-source">Source: ${escapeSearchHtml(data.dictionary.source)}</small>`
            : ''}
        </div>`;
    }

    // Cell info
    const cellCol = Number(data.primary_cell_col);
    const cellRow = Number(data.primary_cell_row);
    const cellLabel = Number.isInteger(cellCol) && cellCol >= 0 && cellCol <= 25
      && Number.isFinite(cellRow)
      ? `(${String.fromCharCode(65 + cellCol)}, ${cellRow})`
      : 'Unavailable';
    const lValue = data.L ?? data.Lsum ?? '—';
    const sValue = data.S ?? data.Ssum ?? '—';

    html += `
      <div class="cell-info">
        📍 Cell: ${escapeSearchHtml(cellLabel)} &nbsp;|&nbsp; 🔗 L: ${escapeSearchHtml(lValue)}, S: ${escapeSearchHtml(sValue)}
      </div>`;

    // News
    if (data.news && data.news.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">📰 Related News</h4>';
      data.news.forEach(n => { html += `<div class="news-item">📌 ${searchResultLink(n)}</div>`; });
    }
    // Wikipedia
    if (data.wikipedia && data.wikipedia.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">📚 Wikipedia</h4>';
      data.wikipedia.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}${item.extract ? `<p>${escapeSearchHtml(item.extract)}</p>` : ''}</div>`; });
    }
    // General web candidates from ScrapingBee-backed search
    if (data.web_results && data.web_results.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">🌐 Web Results</h4>';
      data.web_results.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}</div>`; });
    }
    // Pages indexed by LOMINII's crawler
    if (data.crawler_results && data.crawler_results.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">🕸️ LOMINII Crawler</h4>';
      data.crawler_results.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}${item.snippet ? `<p>${escapeSearchHtml(item.snippet)}</p>` : ''}</div>`; });
    }

    // Related Questions
    if (data.related_questions && data.related_questions.length > 0) {
      html += '<h4 style="margin-top:1.5rem;">🤔 People Also Ask</h4>';
      data.related_questions.forEach(q => {
        const safeQuestion = escapeSearchHtml(q);
        html += `<button type="button" class="related-q search-query-action" data-search-query="${safeQuestion}">${safeQuestion}</button>`;
      });
    }

    resultsDiv.innerHTML = html || '<p>No results found for your query.</p>';

    // Use event listeners rather than embedding untrusted text in JavaScript.
    resultsDiv.querySelectorAll('[data-search-query]').forEach(button => {
      button.addEventListener('click', () => {
        const input = document.getElementById('searchInput');
        if (!input) return;
        input.value = button.dataset.searchQuery || '';
        performSearch();
      });
    });

  } catch (err) {
    const message = String(
      err && err.message ? err.message : "Search failed. Please try again."
    );
    const safeMessage = message.replace(/[&<>"]/g, function (c) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;"
      }[c];
    });
    resultsDiv.innerHTML =
      '<div class="error-state">⚠️ ' + safeMessage + '</div>';
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
      list.innerHTML = trends.map(function (term) {
        const safeTerm = String(term).replace(/[&<>"]/g, function (c) {
          return {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;"
          }[c];
        });
        return '<button type="button" class="trend-chip" ' +
          'onclick="document.getElementById(\'searchInput\').value=this.textContent;' +
          'performSearch()">' + safeTerm + '</button>';
      }).join(" ");
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