/* ==========================================================
   LOMINII COMMON
   Shared UI and Workspace Controller
========================================================== */

/* ===== Workspace Views ===== */

const views = {
    home: document.getElementById("homeView"),
    games: document.getElementById("gamesView"),
    social: document.getElementById("socialView"),
    edu: document.getElementById("eduView"),
    quran: document.getElementById("quranView"),
};

const footerIcons =
    document.querySelectorAll(".footer-nav .nav-icon");

const backToggle =
    document.getElementById("backToggle");

const userIcon =
    document.getElementById("userIcon");

const userDropdown =
    document.getElementById("userDropdown");


/* ===== Dashboard ===== */

const landingView =
    document.getElementById("landingView");

const dashboardView =
    document.getElementById("dashboardView");

function showDashboard() {
    landingView.style.display = "none";
    dashboardView.style.display = "block";

    if (particleCanvas)
        particleCanvas.style.display = "none";

    if (typeof animId !== "undefined") {
        cancelAnimationFrame(animId);
    }

    document.body.classList.add("search-home");

    if (typeof stopParticles === 'function') stopParticles();
    }
}

/* ===== Workspace Switching ===== */


function switchToWorkspace(workspace) {
    // 1. Hide all workspace views

    Object.values(views).forEach(view => {
        if (view) view.style.display = "none";
    });

    // 2. Show the selected workspace

    if (views[workspace]) {
        views[workspace].style.display = "block";
    }

    // 3. Update active state on footer icons
    footerIcons.forEach(icon => icon.classList.remove("active"));
    const active = document.querySelector(`.nav-icon[data-workspace="${workspace}"]`);
    if (active) active.classList.add("active");

    // 4. Toggle body classes and back toggle
    if (workspace === "home") {
        document.body.classList.add("search-home");
        document.body.classList.remove("workspace-view");
        if (backToggle) backToggle.style.display = "none";
    } else {
        document.body.classList.remove("search-home");
        document.body.classList.add("workspace-view");
        if (backToggle) backToggle.style.display = "block";
    }

    // 5. Workspace‑specific initialisation

    switch (workspace) {
        case "home":
            if (typeof loadHomeCards === "function") loadHomeCards();
            break;
        case "social":
            if (typeof loadFriendsFeed === "function") loadFriendsFeed();
            break;
        case "games":
            if (typeof loadGames === "function") loadGames();
            break;
        case "edu":
            if (typeof loadCourses === "function") loadCourses();
            break;
        case "quran":
            if (typeof loadQuran === "function") loadQuran();
            break;
    }
}


/* ===== Footer Navigation ===== */

footerIcons.forEach(icon => {

    icon.addEventListener("click", () => {

        switchToWorkspace(icon.dataset.workspace);

    });

});


/* ===== User Menu ===== */

if (userIcon) {

    userIcon.addEventListener("click", e => {

        e.stopPropagation();

        userDropdown.classList.toggle("show");

    });

}

document.addEventListener("click", () => {

    if (userDropdown)
        userDropdown.classList.remove("show");

});


/* ===== Logout ===== */

const logoutButton =
    document.getElementById("btnLogout");

if (logoutButton) {

    logoutButton.addEventListener("click", () => {

        localStorage.removeItem("lominii_token");

        authToken = "";

        landingView.style.display = "block";

        dashboardView.style.display = "none";

        if (particleCanvas)
            particleCanvas.style.display = "block";

        if (typeof startParticles === 'function') startParticles();

    });

}


/* ===== Landing Buttons ===== */

document.getElementById("btnExplore")
?.addEventListener("click", showDashboard);

document.getElementById("btnLogin")
?.addEventListener("click", showDashboard);

document.getElementById("btnSignup")
?.addEventListener("click", () => {

    alert("Signup page coming soon.");

});