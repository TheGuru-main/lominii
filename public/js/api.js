const API_URLS = [
    "https://lominii-api.onrender.com",
    "https://lominii-api.fly.dev"
];

let authToken = localStorage.getItem("lominii_token") || "";

async function apiFetch(path, options = {}) {
    if (authToken) {
        options.headers = {
            ...options.headers,
            Authorization: `Bearer ${authToken}`
        };
    }

    for (const baseUrl of API_URLS) {
        try {
            const response = await fetch(`${baseUrl}${path}`, options);

            if (response.ok) {
                return response;
            }
        } catch (err) {}
    }

    throw new Error("All API servers are unreachable");
}

async function loginAsGuest() {
    try {
        const resp = await apiFetch("/auth/guest", {
            method: "POST"
        });

        const data = await resp.json();

        authToken = data.access_token;

        localStorage.setItem(
            "lominii_token",
            authToken
        );

        return true;

    } catch {

        return false;
    }
}