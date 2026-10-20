/* LOMINII: independent ScrapingBee video discovery workspace */
(() => {
  "use strict";

  const STORAGE_KEY = "lominii_scrapingbee_saved_v1";
  let section;

  const savedVideos = () => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch (_) {
      return [];
    }
  };

  const saveVideos = (items) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 100)));
  };

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  const safeThumbnail = (value) => {
    try {
      const url = new URL(value);
      return url.protocol === "https:" ? url.href : "";
    } catch (_) {
      return "";
    }
  };

  function renderVideoList(container, videos, savedMode = false) {
    container.replaceChildren();

    if (!videos.length) {
      container.append(make("p", "sb-empty",
        savedMode
          ? "Your saved videos will appear here."
          : "No suggestions to show yet. Try another search."
      ));
      return;
    }

    videos.forEach((video) => {
      const card = make("article", "sb-video-card");
      const thumbnail = safeThumbnail(video.thumbnail || "");

      if (thumbnail) {
        const img = make("img", "sb-thumbnail");
        img.src = thumbnail;
        img.alt = "";
        img.loading = "lazy";
        img.referrerPolicy = "no-referrer";
        card.append(img);
      }

      const body = make("div", "sb-video-body");
      body.append(make("h4", "", video.title || "Online video"));

      if (video.description) {
        body.append(make("p", "sb-description", video.description));
      }

      body.append(make("small", "sb-source",
        video.platform || "Online video"
      ));

      const actions = make("div", "sb-video-actions");
      const open = make("a", "sb-link", "Open video");
      open.href = video.url;
      open.target = "_blank";
      open.rel = "noopener noreferrer";
      actions.append(open);

      if (!savedMode) {
        const save = make("button", "sb-button", "Save to My Videos");
        save.type = "button";
        save.addEventListener("click", () => {
          const items = savedVideos();
          if (!items.some((item) => item.url === video.url)) {
            items.unshift(video);
            saveVideos(items);
          }
          renderSaved();
          setStatus("Video saved to My Videos.");
        });
        actions.append(save);
      } else {
        const remove = make("button", "sb-button sb-remove", "Remove");
        remove.type = "button";
        remove.addEventListener("click", () => {
          saveVideos(savedVideos().filter((item) => item.url !== video.url));
          renderSaved();
        });
        actions.append(remove);
      }

      body.append(actions);
      card.append(body);
      container.append(card);
    });
  }

  function setStatus(message, isError = false) {
    const status = section.querySelector("#sbStatus");
    status.textContent = message;
    status.classList.toggle("sb-error", isError);
  }

  function renderSaved() {
    renderVideoList(
      section.querySelector("#sbSavedVideos"),
      savedVideos(),
      true
    );
  }

  async function searchVideos() {
    const query = section.querySelector("#sbQuery").value.trim();
    if (!query) {
      setStatus("Enter a topic to discover videos.", true);
      return;
    }

    const button = section.querySelector("#sbSearch");
    button.disabled = true;
    setStatus("Discovering videos through ScrapingBee…");

    try {
      const response = await fetch(
        "/api/media/scrapingbee/suggestions?q=" + encodeURIComponent(query)
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Video discovery failed.");
      }

      renderVideoList(
        section.querySelector("#sbSuggestions"),
        data.suggestions || []
      );

      setStatus(
        data.count
          ? `${data.count} suggestion(s) retrieved.`
          : "No results were extracted. Try a different topic."
      );
    } catch (error) {
      setStatus(error.message || "Video discovery failed.", true);
    } finally {
      button.disabled = false;
    }
  }

  async function submitVideo() {
    const input = section.querySelector("#sbVideoUrl");
    const url = input.value.trim();

    if (!url) {
      setStatus("Paste an online video URL first.", true);
      return;
    }

    const button = section.querySelector("#sbAddVideo");
    button.disabled = true;
    setStatus("Retrieving video details…");

    try {
      const response = await fetch("/api/media/scrapingbee/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not retrieve this video.");
      }

      const items = savedVideos().filter((item) => item.url !== data.url);
      items.unshift({
        ...data,
        platform: new URL(data.url).hostname.replace(/^www\./, "")
      });
      saveVideos(items);

      renderVideoList(
        section.querySelector("#sbPreview"),
        [data]
      );
      renderSaved();
      setStatus("Video details retrieved and saved to My Videos.");
      input.value = "";
    } catch (error) {
      setStatus(error.message || "Could not retrieve this video.", true);
    } finally {
      button.disabled = false;
    }
  }

  function init() {
    const home = document.getElementById("homeView");
    if (!home || document.getElementById("scrapingbeeSection")) return;

    section = make("section", "sb-workspace");
    section.id = "scrapingbeeSection";
    section.innerHTML = `
      <div class="sb-heading">
        <div class="sb-eyebrow">LOMINII · MEDIA DISCOVERY</div>
        <h2>Discover &amp; Collect Videos</h2>
        <p>Find public video suggestions or add an online video to your collection.</p>
      </div>

      <div class="sb-panel">
        <h3>🔎 Video Suggestions</h3>
        <div class="sb-search-row">
          <input id="sbQuery" type="search"
            placeholder="Search video topics…" maxlength="120">
          <button id="sbSearch" class="sb-button" type="button">Discover</button>
        </div>
        <div id="sbSuggestions" class="sb-video-grid">
          <p class="sb-empty">Search a topic to get started.</p>
        </div>
      </div>

      <div class="sb-panel">
        <h3>🔗 Add an Online Video</h3>
        <p class="sb-help">Paste a public HTTPS video link from a supported platform.</p>
        <div class="sb-search-row">
          <input id="sbVideoUrl" type="url"
            placeholder="https://…" maxlength="2048">
          <button id="sbAddVideo" class="sb-button" type="button">Add Video</button>
        </div>
        <div id="sbPreview" class="sb-video-grid"></div>
      </div>

      <p id="sbStatus" class="sb-status" aria-live="polite"></p>

      <div class="sb-panel">
        <h3>📚 My Videos</h3>
        <div id="sbSavedVideos" class="sb-video-grid"></div>
      </div>
    `;

    home.append(section);

    section.querySelector("#sbSearch").addEventListener("click", searchVideos);
    section.querySelector("#sbQuery").addEventListener("keydown", (event) => {
      if (event.key === "Enter") searchVideos();
    });
    section.querySelector("#sbAddVideo").addEventListener("click", submitVideo);
    section.querySelector("#sbVideoUrl").addEventListener("keydown", (event) => {
      if (event.key === "Enter") submitVideo();
    });

    renderSaved();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
