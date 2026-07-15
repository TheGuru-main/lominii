const appRoot = document.getElementById('appRoot');
const homeView = document.getElementById('homeView');

const views = {
    home: homeView,
    games: document.getElementById('gamesView'),
    social: document.getElementById('socialView'),
    edu: document.getElementById('eduView'),
    quran: document.getElementById('quranView')
};

const footerIcons = document.querySelectorAll('.footer-nav .nav-icon');
const backToggle = document.getElementById('backToggle');

function switchToWorkspace(workspace) {

    // Hide every workspace
    Object.values(views).forEach(view => {
        if (view) view.style.display = "none";
    });

    // Show selected workspace
    if (views[workspace]) {
        views[workspace].style.display = "block";
    }

    // Footer state
    footerIcons.forEach(icon => icon.classList.remove("active"));

    const activeIcon = document.querySelector(
        `.nav-icon[data-workspace="${workspace}"]`
    );

    if (activeIcon) {
        activeIcon.classList.add("active");
    }

    if (workspace === "home") {

        document.body.classList.add("search-home");
        document.body.classList.remove("workspace-view");
        backToggle.style.display = "none";

    } else {

        document.body.classList.remove("search-home");
        document.body.classList.add("workspace-view");
        backToggle.style.display = "block";

    }

  */  ======================================================
   #Workspace Initializers
    #====================================================== */
    
switch (workspace) {
    case "home":                                    
        if (typeof loadHomeCards === "function")
            loadHomeCards();                        
        break;                                

    switch (workspace) {

        case "social":
            if (typeof initialiseSocial === "function") {
                initialiseSocial();
            }
            break;

        case "edu":
            if (typeof initialiseEdu === "function") {
                initialiseEdu();
            }
            break;

        case "games":
            if (typeof initialiseGames === "function") {
                initialiseGames();
            }
            break;

        case "quran":
            if (typeof initialiseQuran === "function") {
                initialiseQuran();
            }
            break;
    }
}

function goHome() {
    switchToWorkspace("home");
}

footerIcons.forEach(icon => {

    icon.addEventListener("click", () => {

        switchToWorkspace(
            icon.dataset.workspace
        );

    });

});

// Initial load
switchToWorkspace("home");