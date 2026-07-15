/* ==========================================================
   LOMINII SETTINGS
   Panel Control, Preferences & BubbleJumbo Security
========================================================== */

const settingsPanel = document.getElementById("settingsPanel");


/* ==========================================================
   PANEL
========================================================== */

function openSettings() {
    settingsPanel.classList.add("open");

    loadPreferences();
    loadSecurityInfo();
}

function closeSettings() {
    settingsPanel.classList.remove("open");
}


/* ==========================================================
   PREFERENCES
========================================================== */

async function loadPreferences() {

    try {

        const resp = await apiFetch("/auth/preferences", {
            headers: {
                Authorization:
                    `Bearer ${localStorage.getItem("lominii_token")}`
            }
        });

        if (!resp.ok) return;

        const prefs = await resp.json();

        document.getElementById("settingLanguage").value =
            prefs.language || "en";

        document.getElementById("settingCountry").value =
            prefs.country || "Nigeria";

        document.getElementById("sourceWikipedia").checked =
            prefs.data_sources?.wikipedia || false;

        document.getElementById("sourceBanking").checked =
            prefs.data_sources?.banking || false;

        document.getElementById("sourceNews").checked =
            prefs.data_sources?.news !== false;

        document.getElementById("sourceDictionary").checked =
            prefs.data_sources?.dictionary !== false;

        const challenge =
            document.getElementById("bjChallenge");

        if (challenge) {
            challenge.checked =
                prefs.cell_challenge || false;
        }

    } catch (err) {

        console.error(
            "Unable to load preferences",
            err
        );

    }

}


/* ==========================================================
   SECURITY
========================================================== */

async function loadSecurityInfo() {

    const token =
        localStorage.getItem("lominii_token");

    if (!token) return;


    /* ---------- BubbleJumbo Cell ---------- */

    try {

        const payload =
            JSON.parse(atob(token.split(".")[1]));

        if (payload.bj) {

            const col = payload.bj.col;
            const row = payload.bj.row;

            const letter =
                String.fromCharCode(65 + col);

            document.getElementById("bjCell")
                .textContent =
                `(${letter}, ${row})`;

            document.getElementById("bjK")
                .textContent =
                payload.bj.K || 5;

        }

    } catch (err) {

        document.getElementById("bjCell")
            .textContent = "N/A";

    }


    /* ---------- Failure Counter ---------- */

    try {

        const resp =
            await apiFetch("/auth/failure-count", {

                headers: {
                    Authorization:
                        `Bearer ${token}`
                }

            });

        if (resp.ok) {

            const data =
                await resp.json();

            document.getElementById("bjFails")
                .textContent =
                data.failures;

        } else {

            document.getElementById("bjFails")
                .textContent = "?";

        }

    } catch (err) {

        document.getElementById("bjFails")
            .textContent = "?";

    }

}