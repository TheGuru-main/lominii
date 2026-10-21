// LOMINII API client — combined frontend/backend deployment.
const API_URLS = [window.location.origin];

function getToken() {
  return localStorage.getItem("lominii_token") || "";
}

function getCurrentUserId() {
  return localStorage.getItem("lominii_uid") || "";
}

async function apiFetch(path, options = {}) {
  let requestPath = path;

  // FastAPI registers unified search at /api/search/.
  if (requestPath === "/api/search") {
    requestPath = "/api/search/";
  }

  const isSearch = requestPath === "/api/search/";
  let token = getToken();

  // Start a guest session when a visitor searches without signing in.
  if (isSearch && !token) {
    const guestResponse = await fetch(
      new URL("/auth/guest", window.location.origin),
      {
        method: "POST",
        headers: { "Accept": "application/json" }
      }
    );

    if (!guestResponse.ok) {
      throw new Error("Could not start a free search session.");
    }

    const guest = await guestResponse.json();

    if (!guest.access_token) {
      throw new Error("The server did not return a search session.");
    }

    token = guest.access_token;
    localStorage.setItem("lominii_token", token);
  }

  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (token) {
    headers.set("Authorization", "Bearer " + token);
  }

  const response = await fetch(
    new URL(requestPath, window.location.origin),
    { ...options, headers }
  );

  if (!response.ok) {
    let message = "Server request failed (" + response.status + ").";

    try {
      const body = await response.clone().json();

      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (typeof body.message === "string") {
        message = body.message;
      }
    } catch (_) {}

    throw new Error(message);
  }

  return response;
}
