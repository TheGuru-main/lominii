// ---------- Multi‑API failover ----------
const API_URLS = [
  "https://lominii-api.onrender.com",   // Primary
  "https://lominii-api.fly.dev"         // Fallback
];

async function apiFetch(path, options = {}) {
  for (const baseUrl of API_URLS) {
    try {
      const url = `${baseUrl}${path}`;
      const response = await fetch(url, options);
      if (response.ok) return response;
    } catch (e) { continue; }
  }
  throw new Error("All API servers are unreachable");
}

// ---------- Auth helpers ----------
function getToken() {
  return localStorage.getItem('lominii_token') || '';
}
function getCurrentUserId() {
  return localStorage.getItem('lominii_uid') || '';
}