/* ======================================
   LOMINII Search Workspace
====================================== */

async function performSearch() {
    const input = document.getElementById("searchInput");
    const results = document.getElementById("searchResults");

    const query = input.value.trim();

    if (!query) return;

    results.innerHTML = "<p>Searching...</p>";

    try {
        const response = await apiFetch("/api/search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                q: query
            })
        });

        const data = await response.json();

        renderSearchResults(data);

    } catch (err) {

        results.innerHTML = `
            <div class="placeholder">
                Search failed.
            </div>
        `;
    }
}

function renderSearchResults(data) {

    const results = document.getElementById("searchResults");

    results.innerHTML = `
        <h3>${data.query}</h3>

        <p>
            <strong>Definition:</strong>
            ${data.definition || "No definition"}
        </p>

        <p>
            <strong>AI Summary:</strong>
            ${data.ai_summary || "Coming soon"}
        </p>

        <p>
            <strong>Primary Cell:</strong>
            (${String.fromCharCode(65 + data.primary_cell_col)},
            ${data.primary_cell_row})
        </p>
    `;
}

document
    .getElementById("btnSearch")
    .addEventListener("click", performSearch);

document
    .getElementById("searchInput")
    .addEventListener("keypress", (e) => {

        if (e.key === "Enter") {
            performSearch();
        }

    });