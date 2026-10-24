/* LOMINII In-App Keyboard
 * Private to the LOMINII web app; never installs as an Android keyboard.
 * Supports dynamically-created search, messaging and mail text fields.
 */
(() => {
  "use strict";

  if (window.__lominiiKeyboardInstalled) return;
  window.__lominiiKeyboardInstalled = true;

  const LANGUAGES = {
    en: { name: "English", rows: ["qwertyuiop", "asdfghjkl", "zxcvbnm"], extra: [] },
    fr: { name: "Français", rows: ["azertyuiop", "qsdfghjklm", "wxcvbn"], extra: [] },
    de: { name: "Deutsch", rows: ["qwertzuiop", "asdfghjkl", "yxcvbnm"], extra: ["ä", "ö", "ü", "ß"] },
    yo: { name: "Yorùbá", rows: ["qwertyuiop", "asdfghjkl", "zxcvbnm"], extra: ["ẹ", "ọ", "ṣ"] },
    ha: { name: "Hausa", rows: ["qwertyuiop", "asdfghjkl", "zxcvbnm"], extra: ["ɓ", "ɗ", "ƙ", "ƴ"] },
    ig: { name: "Igbo", rows: ["qwertyuiop", "asdfghjkl", "zxcvbnm"], extra: ["ị", "ọ", "ụ", "ṅ"] }
  };

  const eligible = [
    'input[type="text"]',
    'input[type="search"]',
    "textarea",
    '[contenteditable="true"][role="textbox"]'
  ].join(",");

  let active = null;
  let panel = null;
  let shifted = false;
  let caps = false;
  let language = "en";
  let originalInputMode = new WeakMap();

  function currentLanguage() {
    const setting = document.querySelector("#settingLanguage, [name='language']");
    const value = (setting?.value || document.documentElement.lang || "en")
      .toLowerCase().split("-")[0];
    return LANGUAGES[value] ? value : language;
  }

  function canUseKeyboard(el) {
    if (!(el instanceof HTMLElement) || !el.matches(eligible)) return false;
    if (el.disabled || el.readOnly || el.getAttribute("aria-disabled") === "true") return false;
    if (el.closest("#lominiiKeyboard, [data-native-keyboard='true']")) return false;
    if (el.matches('input[type="password"], input[type="email"], input[type="url"], input[type="number"]')) return false;
    if (el.closest('[hidden], [aria-hidden="true"], .is-hidden')) return false;
    return true;
  }

  function isEditable(el) {
    return el instanceof HTMLElement &&
      (el.matches("textarea, input") || el.isContentEditable);
  }

  function getValue(el) {
    return "value" in el ? el.value : (el.textContent || "");
  }

  function setValue(el, value) {
    if ("value" in el) {
      el.value = value;
    } else {
      el.textContent = value;
    }
    el.dispatchEvent(new InputEvent("input", {
      bubbles: true,
      inputType: "insertText",
      data: null
    }));
  }

  function insertText(text) {
    if (!active || !isEditable(active)) return;
    const el = active;
    el.focus();

    if (el.isContentEditable && !("value" in el)) {
      const selection = window.getSelection();
      if (selection && selection.rangeCount) {
        const range = selection.getRangeAt(0);
        range.deleteContents();
        const node = document.createTextNode(text);
        range.insertNode(node);
        range.setStartAfter(node);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
        el.dispatchEvent(new InputEvent("input", {
          bubbles: true, inputType: "insertText", data: text
        }));
      } else {
        el.append(document.createTextNode(text));
        el.dispatchEvent(new Event("input", { bubbles: true }));
      }
      return;
    }

    const start = Number.isInteger(el.selectionStart) ? el.selectionStart : getValue(el).length;
    const end = Number.isInteger(el.selectionEnd) ? el.selectionEnd : start;
    const value = getValue(el);
    const next = value.slice(0, start) + text + value.slice(end);
    setValue(el, next);

    try {
      el.setSelectionRange(start + text.length, start + text.length);
    } catch (_) {}
  }

  function backspace() {
    if (!active) return;
    const el = active;
    el.focus();

    if (el.isContentEditable && !("value" in el)) {
      const selection = window.getSelection();
      if (selection && selection.rangeCount) {
        const range = selection.getRangeAt(0);
        if (!range.collapsed) {
          range.deleteContents();
        } else if (range.startOffset > 0 && range.startContainer.nodeType === Node.TEXT_NODE) {
          range.setStart(range.startContainer, range.startOffset - 1);
          range.deleteContents();
        } else {
          return;
        }
        selection.removeAllRanges();
        selection.addRange(range);
        el.dispatchEvent(new InputEvent("input", {
          bubbles: true, inputType: "deleteContentBackward"
        }));
      }
      return;
    }

    const value = getValue(el);
    const start = Number.isInteger(el.selectionStart) ? el.selectionStart : value.length;
    const end = Number.isInteger(el.selectionEnd) ? el.selectionEnd : start;
    if (start === 0 && end === 0) return;

    const from = start === end ? Math.max(0, start - 1) : start;
    const next = value.slice(0, from) + value.slice(end);
    setValue(el, next);

    try {
      el.setSelectionRange(from, from);
    } catch (_) {}
  }

  function createKey(label, action, extraClass = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "lominii-key " + extraClass;
    button.textContent = label;
    button.setAttribute("aria-label", label);
    button.addEventListener("pointerdown", event => event.preventDefault());
    button.addEventListener("click", action);
    return button;
  }

  function makeRow(container, keys) {
    const row = document.createElement("div");
    row.className = "lominii-key-row";
    keys.forEach(key => row.appendChild(key));
    container.appendChild(row);
  }

  function renderKeyboard() {
    if (!panel) return;
    language = currentLanguage();

    const layout = LANGUAGES[language];
    panel.replaceChildren();

    const header = document.createElement("div");
    header.className = "lominii-keyboard-header";

    const brand = document.createElement("span");
    brand.className = "lominii-keyboard-brand";
    brand.textContent = "LOMINII";

    const langSelect = document.createElement("select");
    langSelect.className = "lominii-keyboard-language";
    langSelect.setAttribute("aria-label", "Keyboard language");
    Object.entries(LANGUAGES).forEach(([code, item]) => {
      const option = document.createElement("option");
      option.value = code;
      option.textContent = item.name;
      option.selected = code === language;
      langSelect.appendChild(option);
    });
    langSelect.addEventListener("change", () => {
      language = langSelect.value;
      renderKeyboard();
    });

    const close = createKey("⌄", hideKeyboard, "lominii-key-close");
    close.setAttribute("aria-label", "Close LOMINII keyboard");

    header.append(brand, langSelect, close);
    panel.appendChild(header);

    layout.rows.forEach((letters, index) => {
      const keys = [...letters].map(letter => {
        const value = (shifted || caps) ? letter.toLocaleUpperCase() : letter;
        return createKey(value, () => {
          insertText(value);
          if (shifted && !caps) shifted = false;
          renderKeyboard();
        });
      });

      if (index === 2) {
        keys.unshift(createKey("⇧", () => {
          if (shifted) caps = !caps;
          shifted = !shifted;
          renderKeyboard();
        }, "lominii-key-wide"));
        keys.push(createKey("⌫", backspace, "lominii-key-wide"));
      }
      makeRow(panel, keys);
    });

    if (layout.extra.length) {
      makeRow(panel, layout.extra.map(letter =>
        createKey(letter, () => insertText((shifted || caps) ? letter.toLocaleUpperCase() : letter))
      ));
    }

    makeRow(panel, [
      createKey("123", () => renderSymbols(), "lominii-key-wide"),
      createKey(",", () => insertText(",")),
      createKey("space", () => insertText(" "), "lominii-key-space"),
      createKey(".", () => insertText(".")),
      createKey("↵", enterAction, "lominii-key-wide")
    ]);

    panel.dataset.language = language;
  }

  function renderSymbols() {
    if (!panel) return;
    panel.replaceChildren();

    const header = document.createElement("div");
    header.className = "lominii-keyboard-header";
    const label = document.createElement("span");
    label.className = "lominii-keyboard-brand";
    label.textContent = "LOMINII · Symbols";
    header.append(label, createKey("ABC", renderKeyboard, "lominii-key-wide"));
    panel.appendChild(header);

    ["1234567890", "@#$%&*-+", "()[]{}!?/;:", "'\".,:_"].forEach(rowText => {
      makeRow(panel, [...rowText].map(char => createKey(char, () => insertText(char))));
    });
    makeRow(panel, [
      createKey("space", () => insertText(" "), "lominii-key-space"),
      createKey("⌫", backspace, "lominii-key-wide"),
      createKey("↵", enterAction, "lominii-key-wide")
    ]);
  }

  function enterAction() {
    if (!active) return;
    const el = active;

    if (el.id === "searchInput" || el.matches('input[type="search"]')) {
      hideKeyboard();
      if (typeof window.performSearch === "function") {
        window.performSearch();
      } else {
        el.dispatchEvent(new KeyboardEvent("keydown", {
          key: "Enter", code: "Enter", bubbles: true
        }));
      }
      return;
    }

    if (el.matches("textarea") || el.isContentEditable) {
      insertText("\n");
      return;
    }

    el.dispatchEvent(new KeyboardEvent("keydown", {
      key: "Enter", code: "Enter", bubbles: true
    }));
  }

  function ensurePanel() {
    if (panel) return panel;
    panel = document.createElement("section");
    panel.id = "lominiiKeyboard";
    panel.className = "lominii-keyboard";
    panel.setAttribute("role", "group");
    panel.setAttribute("aria-label", "LOMINII in-app keyboard");
    panel.hidden = true;
    document.body.appendChild(panel);
    renderKeyboard();
    return panel;
  }

  function showKeyboard(el) {
    if (!canUseKeyboard(el)) return;
    active = el;
    ensurePanel();
    panel.hidden = false;
    renderKeyboard();

    if (!originalInputMode.has(el)) {
      originalInputMode.set(el, el.getAttribute("inputmode"));
    }
    el.setAttribute("inputmode", "none");
    el.setAttribute("data-lominii-keyboard-active", "true");

    document.documentElement.classList.add("lominii-keyboard-open");
    requestAnimationFrame(() => {
      if (!panel || !active) return;
      const bottom = panel.getBoundingClientRect().height;
      const rect = active.getBoundingClientRect();
      if (rect.bottom > window.innerHeight - bottom) {
        active.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
  }

  function hideKeyboard() {
    if (active && originalInputMode.has(active)) {
      const previous = originalInputMode.get(active);
      if (previous === null) active.removeAttribute("inputmode");
      else active.setAttribute("inputmode", previous);
      active.removeAttribute("data-lominii-keyboard-active");
    }
    if (panel) panel.hidden = true;
    active = null;
    document.documentElement.classList.remove("lominii-keyboard-open");
  }

  function prepare(el) {
    if (!canUseKeyboard(el)) return;
    if (!originalInputMode.has(el)) {
      originalInputMode.set(el, el.getAttribute("inputmode"));
    }
    el.setAttribute("inputmode", "none");
    el.setAttribute("data-lominii-keyboard", "true");
  }

  function prepareAll(root = document) {
    if (root.matches && root.matches(eligible)) prepare(root);
    root.querySelectorAll?.(eligible).forEach(prepare);
  }

  function boot() {
    prepareAll();

    document.addEventListener("focusin", event => {
      if (canUseKeyboard(event.target)) showKeyboard(event.target);
    });

    document.addEventListener("pointerdown", event => {
      if (panel && !panel.hidden && !panel.contains(event.target) &&
          event.target !== active && !event.target.closest(eligible)) {
        hideKeyboard();
      }
    });

    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && panel && !panel.hidden) hideKeyboard();
    });

    document.addEventListener("change", event => {
      if (event.target.matches("#settingLanguage, [name='language']") &&
          panel && !panel.hidden) {
        language = currentLanguage();
        renderKeyboard();
      }
    });

    new MutationObserver(records => {
      for (const record of records) {
        record.addedNodes.forEach(node => {
          if (node.nodeType === Node.ELEMENT_NODE) prepareAll(node);
        });
      }
    }).observe(document.body, { childList: true, subtree: true });

    // Close on route/tab changes that remove the active field.
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) hideKeyboard();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }

  window.LOMINIIKeyboard = Object.freeze({
    show: showKeyboard,
    hide: hideKeyboard,
    setLanguage(code) {
      if (LANGUAGES[code]) {
        language = code;
        renderKeyboard();
      }
    }
  });
})();
