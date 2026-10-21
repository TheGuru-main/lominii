/* Lomimail registration UI. Uses existing LOMINII auth endpoints. */

const LOMIMAIL_COUNTRIES = [
  // Africa — 25
  ["Africa","DZ","Algeria","213"],["Africa","EG","Egypt","20"],
  ["Africa","MA","Morocco","212"],["Africa","TN","Tunisia","216"],
  ["Africa","LY","Libya","218"],["Africa","SD","Sudan","249"],
  ["Africa","SS","South Sudan","211"],["Africa","ET","Ethiopia","251"],
  ["Africa","ER","Eritrea","291"],["Africa","DJ","Djibouti","253"],
  ["Africa","SO","Somalia","252"],["Africa","KE","Kenya","254"],
  ["Africa","UG","Uganda","256"],["Africa","TZ","Tanzania","255"],
  ["Africa","RW","Rwanda","250"],["Africa","BI","Burundi","257"],
  ["Africa","CD","Congo, The Democratic Republic of the","243"],
  ["Africa","CG","Congo","242"],["Africa","GA","Gabon","241"],
  ["Africa","GQ","Equatorial Guinea","240"],["Africa","CM","Cameroon","237"],
  ["Africa","NG","Nigeria","234"],["Africa","GH","Ghana","233"],
  ["Africa","CI","Côte d'Ivoire","225"],["Africa","ZA","South Africa","27"],

  // Asia — 15
  ["Asia","CN","China","86"],["Asia","IN","India","91"],
  ["Asia","JP","Japan","81"],["Asia","KR","Korea, Republic of","82"],
  ["Asia","ID","Indonesia","62"],["Asia","MY","Malaysia","60"],
  ["Asia","SG","Singapore","65"],["Asia","TH","Thailand","66"],
  ["Asia","VN","Viet Nam","84"],["Asia","PH","Philippines","63"],
  ["Asia","PK","Pakistan","92"],["Asia","BD","Bangladesh","880"],
  ["Asia","NP","Nepal","977"],["Asia","SA","Saudi Arabia","966"],
  ["Asia","AE","United Arab Emirates","971"],

  // Europe — 15
  ["Europe","GB","United Kingdom","44"],["Europe","FR","France","33"],
  ["Europe","DE","Germany","49"],["Europe","ES","Spain","34"],
  ["Europe","IT","Italy","39"],["Europe","PT","Portugal","351"],
  ["Europe","NL","Netherlands","31"],["Europe","BE","Belgium","32"],
  ["Europe","CH","Switzerland","41"],["Europe","SE","Sweden","46"],
  ["Europe","NO","Norway","47"],["Europe","FI","Finland","358"],
  ["Europe","PL","Poland","48"],["Europe","GR","Greece","30"],
  ["Europe","IE","Ireland","353"],

  // North America — 15
  ["North America","US","United States","1"],
  ["North America","CA","Canada","1"],["North America","MX","Mexico","52"],
  ["North America","GT","Guatemala","502"],["North America","BZ","Belize","501"],
  ["North America","HN","Honduras","504"],["North America","SV","El Salvador","503"],
  ["North America","NI","Nicaragua","505"],["North America","CR","Costa Rica","506"],
  ["North America","PA","Panama","507"],["North America","CU","Cuba","53"],
  ["North America","JM","Jamaica","1-876"],["North America","HT","Haiti","509"],
  ["North America","DO","Dominican Republic","1-809"],
  ["North America","TT","Trinidad and Tobago","1-868"],

  // South America — 12 sovereign countries + 3 territories
  ["South America","AR","Argentina","54"],["South America","BO","Bolivia, Plurinational State of","591"],
  ["South America","BR","Brazil","55"],["South America","CL","Chile","56"],
  ["South America","CO","Colombia","57"],["South America","EC","Ecuador","593"],
  ["South America","GY","Guyana","592"],["South America","PY","Paraguay","595"],
  ["South America","PE","Peru","51"],["South America","SR","Suriname","597"],
  ["South America","UY","Uruguay","598"],["South America","VE","Venezuela, Bolivarian Republic of","58"],
  ["South America","GF","French Guiana","594"],
  ["South America","FK","Falkland Islands (Malvinas)","500"],
  ["South America","GS","South Georgia and the South Sandwich Islands","500"],

  // Oceania — 15 entries
  ["Oceania","AU","Australia","61"],["Oceania","NZ","New Zealand","64"],
  ["Oceania","FJ","Fiji","679"],["Oceania","PG","Papua New Guinea","675"],
  ["Oceania","SB","Solomon Islands","677"],["Oceania","VU","Vanuatu","678"],
  ["Oceania","WS","Samoa","685"],["Oceania","TO","Tonga","676"],
  ["Oceania","TV","Tuvalu","688"],["Oceania","NR","Nauru","674"],
  ["Oceania","KI","Kiribati","686"],["Oceania","FM","Micronesia, Federated States of","691"],
  ["Oceania","MH","Marshall Islands","692"],["Oceania","PW","Palau","680"],
  ["Oceania","CK","Cook Islands","682"]
];


(() => {
  "use strict";

  const API_FALLBACKS = [
    "https://lominii-api.onrender.com",
    "https://lominii-api.fly.dev"
  ];

  function el(tag, attrs = {}, text = "") {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "className") node.className = value;
      else if (key === "htmlFor") node.htmlFor = value;
      else node.setAttribute(key, value);
    }
    if (text) node.textContent = text;
    return node;
  }

  function field(labelText, name, type = "text", required = true, placeholder = "") {
    const wrap = el("div", { className: "lm-field" });
    const label = el("label", { htmlFor: "lm-" + name }, labelText);
    const input = el("input", {
      id: "lm-" + name,
      name,
      type,
      autocomplete: name === "password" ? "new-password" :
        name === "full_name" ? "name" :
        name === "phone" ? "tel-national" : "off",
      placeholder
    });
    if (required) input.required = true;
    if (type === "url") input.maxLength = 500;
    wrap.append(label, input);
    return { wrap, input };
  }

  function selectCountry() {
    const wrap = el("div", { className: "lm-field" });
    const label = el("label", { htmlFor: "lm-country" }, "Country");
    const select = el("select", { id: "lm-country", name: "country", required: "" });
    const groups = new Map();

    for (const [continent, iso, name, dial] of LOMIMAIL_COUNTRIES) {
      let group = groups.get(continent);
      if (!group) {
        group = el("optgroup", { label: continent });
        groups.set(continent, group);
        select.append(group);
      }
      const option = el("option", { value: iso });
      option.textContent = `${name} (+${dial})`;
      option.dataset.countryName = name;
      option.dataset.dial = dial;
      group.append(option);
    }

    select.value = "NG";
    wrap.append(label, select);
    return { wrap, select };
  }

  function createUI() {
    if (document.getElementById("lomimailRegistrationModal")) return;

    const overlay = el("div", {
      id: "lomimailRegistrationModal",
      className: "lm-overlay",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "lm-title",
      hidden: ""
    });

    const card = el("section", { className: "lm-card" });
    const top = el("div", { className: "lm-top" });
    const headingWrap = el("div");
    headingWrap.append(
      el("p", { className: "lm-eyebrow" }, "LOMINII · LOMIMAIL"),
      el("h2", { id: "lm-title" }, "Create your account"),
      el("p", { className: "lm-intro" },
        "Verify your phone to create your Lomimail identity.")
    );
    const close = el("button", {
      type: "button",
      className: "lm-close",
      "aria-label": "Close registration"
    }, "×");
    top.append(headingWrap, close);

    const form = el("form", { id: "lm-registration-form", novalidate: "" });
    const status = el("div", {
      id: "lm-status",
      className: "lm-status",
      role: "status",
      "aria-live": "polite"
    });

    const country = selectCountry();
    const phone = field("Phone number", "phone", "tel", true, "e.g. 08012345678");
    const phoneHint = el("p", { className: "lm-hint" },
      "Enter your national number. You can also enter the full international number starting with +.");
    const otp = field("OTP verification code", "otp", "text", true, "Enter the code sent to your phone");
    otp.input.inputMode = "numeric";
    otp.input.autocomplete = "one-time-code";
    otp.input.maxLength = 12;
    const otpWrap = otp.wrap;
    otpWrap.hidden = true;

    const name = field("Full name", "full_name", "text", true, "Your full name");
    const password = field("Password", "password", "password", true, "At least 6 characters");
    password.input.minLength = 6;
    const confirm = field("Confirm password", "confirm_password", "password", true, "Re-enter your password");
    const state = field("State / province / region", "state", "text", true, "State or region");
    const lga = field("LGA / district", "lga", "text", true, "LGA or district");

    // Preserve the original text inputs for countries without a local dataset.
    const stateTextInput = state.input;
    const lgaTextInput = lga.input;
    let nigeriaAdminData = null;
    const city = field("City", "city", "text", true, "City or town");
    const community1 = field("Primary community / location 1", "primary_community_1", "text", true, "Your main community");
    const community2 = field("Primary community / location 2 (optional)", "primary_community_2", "text", false, "Additional community");
    const picture = field("Profile picture URL (optional)", "profile_picture_url", "url", false, "https://…");
    const additional = field("Additional image URL (optional)", "additional_image_url", "url", false, "https://…");

    const phoneGrid = el("div", { className: "lm-grid" });
    phoneGrid.append(country.wrap, phone.wrap);

    const nameGrid = el("div", { className: "lm-grid" });
    nameGrid.append(name.wrap, password.wrap, confirm.wrap);

    const locationGrid = el("div", { className: "lm-grid" });
    locationGrid.append(state.wrap, lga.wrap, city.wrap);

    const communityGrid = el("div", { className: "lm-grid" });
    communityGrid.append(community1.wrap, community2.wrap);

    const imageGrid = el("div", { className: "lm-grid" });
    imageGrid.append(picture.wrap, additional.wrap);

    const otpActions = el("div", { className: "lm-actions" });
    const requestButton = el("button", {
      id: "lm-request-otp",
      type: "button",
      className: "lm-button lm-secondary"
    }, "Send verification code");

    const verifyButton = el("button", {
      id: "lm-verify",
      type: "submit",
      className: "lm-button lm-primary"
    }, "Verify & create account");
    verifyButton.hidden = true;

    otpActions.append(requestButton, verifyButton);

    const legal = el("p", { className: "lm-hint" },
      "Your phone must be accessible to receive the verification code. Image fields accept URLs; direct file uploads are not enabled here.");

    form.append(
      phoneGrid,
      otpWrap,
      nameGrid,
      locationGrid,
      communityGrid,
      imageGrid,
      status,
      otpActions,
      legal
    );

    card.append(top, form);
    overlay.append(card);
    document.body.append(overlay);

    function closeModal() {
      overlay.hidden = true;
      status.textContent = "";
      status.className = "lm-status";
    }

    close.addEventListener("click", closeModal);
    overlay.addEventListener("click", event => {
      if (event.target === overlay) closeModal();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !overlay.hidden) closeModal();
    });

    function setStatus(message, type = "info") {
      status.textContent = message;
      status.className = "lm-status lm-" + type;
    }

    function selectedCountry() {
      const option = country.select.selectedOptions[0];
      return {
        iso: country.select.value,
        name: option.dataset.countryName,
        dial: option.dataset.dial
      };
    }

    function replaceLocationControl(fieldItem, nextControl) {
      if (fieldItem.input === nextControl) return;
      fieldItem.wrap.replaceChild(nextControl, fieldItem.input);
      fieldItem.input = nextControl;
    }

    function makeLocationSelect(fieldItem, placeholder) {
      const select = el("select", {
        id: "lm-" + fieldItem.input.name,
        name: fieldItem.input.name,
        required: ""
      });

      const option = el("option", {
        value: "",
        disabled: "",
        selected: ""
      }, placeholder);

      select.append(option);
      replaceLocationControl(fieldItem, select);
      return select;
    }

    function restoreLocationInputs() {
      replaceLocationControl(state, stateTextInput);
      replaceLocationControl(lga, lgaTextInput);

      stateTextInput.placeholder = "State, province or region";
      lgaTextInput.placeholder = "LGA, district or equivalent";
    }

    function populateNigeriaLgas(stateName) {
      const select = lga.input;

      if (!(select instanceof HTMLSelectElement) || !nigeriaAdminData) {
        return;
      }

      const selectedState = nigeriaAdminData.data.state.find(
        item => item.name_en === stateName
      );

      select.replaceChildren();

      const placeholder = el("option", {
        value: "",
        disabled: "",
        selected: ""
      }, selectedState ? "Select an LGA" : "Select a state first");

      select.append(placeholder);

      if (!selectedState) return;

      const lgas = nigeriaAdminData.data.lga
        .filter(item => item.parent_id === selectedState.id)
        .sort((a, b) => a.name_en.localeCompare(b.name_en));

      for (const item of lgas) {
        select.append(el("option", { value: item.name_en }, item.name_en));
      }
    }

    async function applyLocationMode() {
      const selected = selectedCountry();

      if (selected.iso !== "NG") {
        restoreLocationInputs();
        return;
      }

      try {
        if (!nigeriaAdminData) {
          const response = await fetch(
            new URL("/data/nigeria-admin-divisions.json", window.location.origin)
          );

          if (!response.ok) {
            throw new Error("Location data request failed: " + response.status);
          }

          const data = await response.json();

          if (
            !data ||
            !data.data ||
            !Array.isArray(data.data.state) ||
            !Array.isArray(data.data.lga)
          ) {
            throw new Error("The Nigerian location dataset has an unexpected format.");
          }

          nigeriaAdminData = data;
        }

        const stateSelect = makeLocationSelect(state, "Select a state or FCT");
        const lgaSelect = makeLocationSelect(lga, "Select an LGA");

        const states = [...nigeriaAdminData.data.state]
          .sort((a, b) => a.name_en.localeCompare(b.name_en));

        for (const item of states) {
          stateSelect.append(
            el("option", { value: item.name_en }, item.name_en)
          );
        }

        stateSelect.addEventListener("change", () => {
          populateNigeriaLgas(stateSelect.value);
        });

        populateNigeriaLgas("");
        setStatus("");
      } catch (error) {
        restoreLocationInputs();
        setStatus(
          "Nigerian location data could not be loaded. You can enter the state and LGA manually.",
          "error"
        );
        console.error("Lomimail location data:", error);
      }
    }

    country.select.addEventListener("change", applyLocationMode);
    applyLocationMode();

    function internationalPhone() {
      const raw = phone.input.value.trim();
      const selected = selectedCountry();
      const digits = raw.replace(/\D/g, "");

      if (!digits) throw new Error("Enter your phone number.");

      if (raw.startsWith("+")) {
        return "+" + digits;
      }

      // Country calling codes that are shared or have a national trunk prefix
      // are handled by the selected region's backend validation.
      let national = digits;
      if (national.startsWith("0")) national = national.replace(/^0+/, "");
      if (!national) throw new Error("Enter a valid national phone number.");

      const dial = selected.dial.split("-")[0];
      return "+" + dial + national;
    }

    async function requestJSON(path, payload) {
      let response;

      try {
        response = await fetch(
          new URL(path, window.location.origin),
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "Accept": "application/json"
            },
            body: JSON.stringify(payload)
          }
        );
      } catch (_) {
        throw new Error(
          "Could not reach the registration server. Check your connection."
        );
      }

      let body = {};
      try {
        body = await response.json();
      } catch (_) {}

      if (!response.ok) {
        const detail = body.detail || body.message ||
          "Registration request failed (" + response.status + ").";

        throw new Error(
          typeof detail === "string"
            ? detail
            : "Please check your information and try again."
        );
      }

      return body;
    }

    requestButton.addEventListener("click", async () => {
      setStatus("");
      let phoneValue;
      try {
        phoneValue = internationalPhone();
      } catch (error) {
        setStatus(error.message, "error");
        phone.input.focus();
        return;
      }

      requestButton.disabled = true;
      requestButton.textContent = "Requesting code…";

      try {
        const selected = selectedCountry();
        const result = await requestJSON("/auth/phone/request", {
          phone: phoneValue,
          country: selected.name,
          country_iso2: selected.iso
        });

        phone.input.value = phoneValue;
        otpWrap.hidden = false;
        verifyButton.hidden = false;
        requestButton.textContent = "Resend verification code";
        setStatus(
          result.dev_otp
            ? "Development OTP: " + result.dev_otp
            : (result.message || "Verification code requested. Check your phone."),
          "success"
        );
        otp.input.focus();
      } catch (error) {
        setStatus(error.message || "Could not request an OTP.", "error");
        requestButton.textContent = "Send verification code";
      } finally {
        requestButton.disabled = false;
      }
    });

    form.addEventListener("submit", async event => {
      event.preventDefault();
      setStatus("");

      if (otpWrap.hidden) {
        setStatus("Request a verification code first.", "error");
        return;
      }

      if (password.input.value.length < 6) {
        setStatus("Password must contain at least 6 characters.", "error");
        password.input.focus();
        return;
      }

      if (password.input.value !== confirm.input.value) {
        setStatus("The passwords do not match.", "error");
        confirm.input.focus();
        return;
      }

      let phoneValue;
      try {
        phoneValue = internationalPhone();
      } catch (error) {
        setStatus(error.message, "error");
        return;
      }

      const selected = selectedCountry();
      const payload = {
        phone: phoneValue,
        country: selected.name,
        country_iso2: selected.iso,
        otp: otp.input.value.trim(),
        full_name: name.input.value.trim(),
        password: password.input.value,
        state: state.input.value.trim(),
        lga: lga.input.value.trim(),
        city: city.input.value.trim(),
        primary_community_1: community1.input.value.trim(),
        primary_community_2: community2.input.value.trim(),
        profile_picture_url: picture.input.value.trim(),
        additional_image_url: additional.input.value.trim()
      };

      const missing = [
        ["Full name", payload.full_name],
        ["State / region", payload.state],
        ["LGA / district", payload.lga],
        ["City", payload.city],
        ["Primary community", payload.primary_community_1],
        ["OTP", payload.otp]
      ].find(item => !item[1]);

      if (missing) {
        setStatus(missing[0] + " is required.", "error");
        return;
      }

      verifyButton.disabled = true;
      verifyButton.textContent = "Verifying…";

      try {
        const result = await requestJSON("/auth/phone/verify", payload);

        if (!result.access_token) {
          throw new Error("The server did not return an authentication token.");
        }

        // Store only the session token. Do not store the internal uID here.
        localStorage.setItem("lominii_token", result.access_token);
        if (typeof authToken !== "undefined") authToken = result.access_token;

        setStatus(
          "Account verified. Your Lomimail address is " +
          (result.lomimail_address || "ready") + ".",
          "success"
        );

        // Never render or persist result.uID in the public interface.
        if (typeof showDashboard === "function") showDashboard();

        verifyButton.hidden = true;
        requestButton.hidden = true;
        const continueButton = el("button", {
          type: "button",
          className: "lm-button lm-primary"
        }, "Continue to LOMINII");
        otpActions.append(continueButton);
        continueButton.addEventListener("click", closeModal);
      } catch (error) {
        setStatus(error.message || "Verification failed. Please try again.", "error");
      } finally {
        verifyButton.disabled = false;
        verifyButton.textContent = "Verify & create account";
      }
    });

    window.openLomimailRegistration = () => {
      overlay.hidden = false;
      phone.input.focus();
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createUI, { once: true });
  } else {
    createUI();
  }
})();
