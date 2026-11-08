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

// ---- search request state ----------------------------------------------
const SEARCH_MAX_QUERY = 300;
let searchSequence = 0;
let searchController = null;
let searchBlockedUntil = 0;
let searchCooldownTimer = null;

function setSearchBusy(busy) {
  const button = document.getElementById('btnSearch');
  if (!button) return;
  button.disabled = busy;
  button.setAttribute('aria-busy', busy ? 'true' : 'false');
}

function showSearchError(resultsDiv, message, canRetry) {
  resultsDiv.innerHTML =
    '<div class="error-state" role="alert">⚠️ ' + escapeSearchHtml(message) +
    (canRetry
      ? '<br><button type="button" class="search-retry" data-search-retry>Try again</button>'
      : '') +
    '</div>';
  const retry = resultsDiv.querySelector('[data-search-retry]');
  if (retry) retry.addEventListener('click', performSearch);
}

function startSearchCooldown(resultsDiv, seconds) {
  clearInterval(searchCooldownTimer);
  searchBlockedUntil = Date.now() + seconds * 1000;
  setSearchBusy(true);
  const tick = () => {
    const left = Math.ceil((searchBlockedUntil - Date.now()) / 1000);
    if (left <= 0) {
      clearInterval(searchCooldownTimer);
      searchBlockedUntil = 0;
      setSearchBusy(false);
      resultsDiv.innerHTML = '<p>You can search again now.</p>';
      return;
    }
    resultsDiv.innerHTML =
      '<div class="error-state" role="alert">⏳ You are searching very quickly. ' +
      'Try again in ' + left + ' second' + (left === 1 ? '' : 's') + '.</div>';
  };
  tick();
  searchCooldownTimer = setInterval(tick, 1000);
}

// The language is sent only when someone actually chose it: a language control
// on the page, or text typed with the LOMINII keyboard in that layout.
function searchLanguageFor(input) {
  const control = document.querySelector('[name="language"], #searchLanguage, #languageSelect');
  if (control && control.value) return control.value;
  const keyboard = window.LOMINIIKeyboard;
  return (keyboard && typeof keyboard.languageFor === 'function' && keyboard.languageFor(input)) || '';
}

function searchErrorMessage(err) {
  const status = err && err.status;
  if (err && err.name === 'AbortError') return 'Search took too long. Please try again.';
  if (status === 400) return String(err.message || 'That search could not be processed.');
  if (status === 401) return 'Your session has ended. Please reload the page and try again.';
  if (status >= 500) return 'Search is unavailable right now. Please try again in a moment.';
  if (err && err.name === 'TypeError') return 'Could not reach LOMINII. Check your connection and try again.';
  return String((err && err.message) || 'Search failed. Please try again.');
}

function renderSearchResults(resultsDiv, query, data) {
  const list = value => (Array.isArray(value) ? value : []);
  const news = list(data.news);
  const wikipedia = list(data.wikipedia);
  const webResults = list(data.web_results);
  const crawlerResults = list(data.crawler_results);
  const related = list(data.related_questions);
  const dictionaryMatches = list(data.dictionary_matches)
    .filter(item => item && typeof item.word === 'string' && item.word.trim());
  const didYouMean = typeof data.did_you_mean === 'string' ? data.did_you_mean.trim() : '';
  const similar = list(data.suggestions)
    .filter(word => typeof word === 'string' && word.trim() &&
      word.trim().toLowerCase() !== didYouMean.toLowerCase())
    .slice(0, 4);
  const hasResults = Boolean(
    data.ai_summary || data.definition || news.length || wikipedia.length ||
    webResults.length || crawlerResults.length || dictionaryMatches.length
  );

  let html = '';

  // Did you mean?
  if (didYouMean) {
    const suggestion = escapeSearchHtml(didYouMean);
    html += `<div class="did-you-mean">Did you mean: <button type="button" class="search-query-action" data-search-query="${suggestion}">${suggestion}</button>?</div>`;
  }
  if (similar.length) {
    html += '<div class="similar-words">Also close: ' + similar.map(word => {
      const safe = escapeSearchHtml(word.trim());
      return `<button type="button" class="search-query-action" data-search-query="${safe}">${safe}</button>`;
    }).join(' ') + '</div>';
  }

  if (!hasResults) {
    html += '<div class="no-results" role="status">No results found for “' +
      escapeSearchHtml(query) + '”. ' +
      (didYouMean || similar.length
        ? 'Check the suggestions above.'
        : 'Try different words or check the spelling.') + '</div>';
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

  // Dictionary entries found by word and definition (lexical matching)
  if (dictionaryMatches.length > 0) {
    html += '<h4 style="margin-top:1.5rem;">📖 In the dictionary</h4>';
    dictionaryMatches.forEach(item => {
      const word = escapeSearchHtml(item.word.trim());
      const partOfSpeech = item.part_of_speech
        ? ` <span class="dictionary-pos">${escapeSearchHtml(item.part_of_speech)}</span>`
        : '';
      const meaning = item.definition ? `<p>${escapeSearchHtml(item.definition)}</p>` : '';
      html += `<div class="source-item"><button type="button" class="search-query-action dict-match" data-search-query="${word}">${word}</button>${partOfSpeech}${meaning}</div>`;
    });
  }

  // Cell info: the column is the language's own letter (server label), not just A-Z.
  const cellCol = Number(data.primary_cell_col);
  const cellRow = Number(data.primary_cell_row);
  let cellLabel = 'Unavailable';
  if (Number.isInteger(cellCol) && cellCol >= 0 && Number.isFinite(cellRow)) {
    const letter = typeof data.cell_label === 'string' && data.cell_label
      ? data.cell_label
      : (cellCol <= 25 ? String.fromCharCode(65 + cellCol) : String(cellCol));
    cellLabel = `(${letter}, ${cellRow})`;
  }
  const lValue = data.L ?? data.Lsum ?? '—';
  const sValue = data.S ?? data.Ssum ?? '—';
  const languageNote = typeof data.language === 'string' && data.language
    ? ` &nbsp;|&nbsp; 🌐 ${escapeSearchHtml(data.language.toUpperCase())}`
    : '';

  html += `
    <div class="cell-info">
      📍 Cell: ${escapeSearchHtml(cellLabel)} &nbsp;|&nbsp; 🔗 L: ${escapeSearchHtml(lValue)}, S: ${escapeSearchHtml(sValue)}${languageNote}
    </div>`;

  // News
  if (news.length > 0) {
    html += '<h4 style="margin-top:1.5rem;">📰 Related News</h4>';
    news.forEach(n => { html += `<div class="news-item">📌 ${searchResultLink(n)}</div>`; });
  }
  // Wikipedia
  if (wikipedia.length > 0) {
    html += '<h4 style="margin-top:1.5rem;">📚 Wikipedia</h4>';
    wikipedia.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}${item.extract ? `<p>${escapeSearchHtml(item.extract)}</p>` : ''}</div>`; });
  }
  // General web candidates from ScrapingBee-backed search
  if (webResults.length > 0) {
    html += '<h4 style="margin-top:1.5rem;">🌐 Web Results</h4>';
    webResults.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}</div>`; });
  }
  // Pages indexed by LOMINII's crawler
  if (crawlerResults.length > 0) {
    html += '<h4 style="margin-top:1.5rem;">🕸️ LOMINII Crawler</h4>';
    crawlerResults.forEach(item => { html += `<div class="source-item">${searchResultLink(item)}${item.snippet ? `<p>${escapeSearchHtml(item.snippet)}</p>` : ''}</div>`; });
  }

  // Related Questions
  if (related.length > 0) {
    html += '<h4 style="margin-top:1.5rem;">🤔 People Also Ask</h4>';
    related.forEach(q => {
      const safeQuestion = escapeSearchHtml(q);
      html += `<button type="button" class="related-q search-query-action" data-search-query="${safeQuestion}">${safeQuestion}</button>`;
    });
  }

  resultsDiv.innerHTML = html;

  // Use event listeners rather than embedding untrusted text in JavaScript.
  resultsDiv.querySelectorAll('[data-search-query]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.getElementById('searchInput');
      if (!input) return;
      input.value = button.dataset.searchQuery || '';
      performSearch();
    });
  });
}

async function performSearch() {
  const input = document.getElementById('searchInput');
  const resultsDiv = document.getElementById('searchResults');
  if (!input || !resultsDiv) return;

  const query = input.value.replace(/\s+/g, ' ').trim();
  if (!query) return;
  if (searchBlockedUntil > Date.now()) return;
  if (query.length > SEARCH_MAX_QUERY) {
    showSearchError(resultsDiv,
      'Please shorten your search to ' + SEARCH_MAX_QUERY + ' characters or fewer.', false);
    return;
  }
  if (navigator.onLine === false) {
    showSearchError(resultsDiv, 'You appear to be offline. Reconnect and try again.', true);
    return;
  }

  // Only the newest search may update the page.
  const sequence = ++searchSequence;
  if (searchController) searchController.abort();
  const controller = new AbortController();
  searchController = controller;
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 30000);

  setSearchBusy(true);
  resultsDiv.innerHTML = '<div class="loading-pulse" role="status">✨ LOMINII is thinking…</div>';

  try {
    const payload = { q: query };
    const language = searchLanguageFor(input);
    if (language) payload.language = language;

    const response = await apiFetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    const data = await response.json();
    if (sequence !== searchSequence) return;
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      throw new Error('The search service returned an invalid response.');
    }
    renderSearchResults(resultsDiv, query, data);
  } catch (err) {
    if (sequence !== searchSequence) return;
    if (err && err.status === 429) {
      startSearchCooldown(resultsDiv, Math.max(1, err.retryAfter || 30));
      return;
    }
    showSearchError(resultsDiv,
      timedOut ? 'Search took too long. Please try again.' : searchErrorMessage(err), true);
  } finally {
    clearTimeout(timer);
    if (sequence === searchSequence && !(searchBlockedUntil > Date.now())) {
      setSearchBusy(false);
    }
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
  if (searchInput) {
    searchInput.maxLength = SEARCH_MAX_QUERY;
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.isComposing) performSearch();
    });
  }
});