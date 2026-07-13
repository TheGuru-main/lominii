/* ======================================
   LOMINII Search Workspace
====================================== */

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
    const letter = String.fromCharCode(65 + data.primary_cell_col);
    resultsDiv.innerHTML = `
      <h3>${data.query}</h3>
      <p><strong>Definition:</strong> ${data.definition || 'No definition found'}</p>
      <p><strong>AI Summary:</strong> ${data.ai_summary || 'Coming soon'}</p>
      <p><strong>Primary Cell:</strong> (${letter}, ${data.primary_cell_row})</p>
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