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

    // Primary Cell info (subtle)
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