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
      body: JSON.stringify({ q: query })
    });
    const data = await response.json();

    // Build the AI Summary Card
    let html = '';

    // Did you mean?
    if (data.did_you_mean) {
      html += `<div class="did-you-mean">Did you mean: <span onclick="document.getElementById('searchInput').value='${data.did_you_mean}';performSearch()">${data.did_you_mean}</span>?</div>`;
    }

    // AI Summary (Little Double Expert / Full Board)
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
          <div class="def-badge">📖 Definition</div>
          <p>${escapeSearchHtml(data.definition)}</p>
        </div>`;
    }

    // Primary Cell info (subtle)
    html += `
      <div class="cell-info">
        📍 Cell: (${String.fromCharCode(65 + data.primary_cell_col)}, ${data.primary_cell_row}) &nbsp;|&nbsp; 🔗 L: ${data.L !== undefined ? data.L : data.Lsum}, S: ${data.S !== undefined ? data.S : data.Ssum}
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

    // Related Questions (placeholder for future)
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