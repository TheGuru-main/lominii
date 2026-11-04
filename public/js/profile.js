/* LOMINII profile.
 *
 * Real account details from /auth/me, profile editing, adding a phone number
 * (which also issues a Lomimail address) and linking Google. It plugs into the
 * existing account panel. Everything the server sends is shown as text, never
 * as HTML. */
(function () {
  'use strict';

  const LANGUAGES = [
    ['en', 'English'], ['fr', 'French'], ['de', 'German'],
    ['yo', 'Yorùbá'], ['ha', 'Hausa'], ['ig', 'Igbo']
  ];
  // [key, label, max length, required]
  const TEXT_FIELDS = [
    ['full_name', 'Full name', 255, true],
    ['state', 'State', 100, true],
    ['lga', 'Local government area', 100, true],
    ['city', 'City or town', 100, true],
    ['primary_community_1', 'Primary community', 150, true],
    ['primary_community_2', 'Second community', 150, false],
    ['occupation', 'Occupation', 100, false]
  ];
  const URL_FIELDS = [
    ['profile_picture_url', 'Profile picture URL'],
    ['additional_image_url', 'Additional image URL']
  ];
  const JSON_HEADERS = { 'Content-Type': 'application/json' };

  // ---- small DOM helpers (text only; nothing is parsed as HTML) ------------
  function h(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === false) return;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
      else if (key in node) node[key] = value;
      else node.setAttribute(key, value);
    });
    children.flat().forEach(child => {
      if (child === null || child === undefined || child === false) return;
      node.append(child.nodeType ? child : document.createTextNode(String(child)));
    });
    return node;
  }

  function section(title, ...children) {
    return h('section', { class: 'lm-account-section' }, h('h3', { text: title }), ...children);
  }

  function row(label, valueNode) {
    return h('div', { class: 'lm-account-row' }, h('span', { text: label }), valueNode);
  }

  function value(text, mono) {
    return h('strong', { class: mono ? 'lm-mono' : '', text });
  }

  function field(label, input) {
    return h('div', { class: 'lm-field' }, h('label', { for: input.id, text: label }), input);
  }

  function showStatus(node, message, kind) {
    node.textContent = message || '';
    node.className = 'lm-status' + (kind ? ' lm-' + kind : '');
  }

  function isRegistered() {
    return Boolean(localStorage.getItem('lominii_token')) &&
      localStorage.getItem('lominii_account_type') === 'registered';
  }

  async function send(path, method, body) {
    const response = await apiFetch(path, {
      method,
      headers: JSON_HEADERS,
      body: JSON.stringify(body)
    });
    try { return await response.json(); } catch (_) { return {}; }
  }

  function mountGoogle(container, handler) {
    if (!container || !window.LominiiGoogle) return;
    window.LominiiGoogle.render(container, handler, { text: 'signin_with', width: 260 })
      .catch(() => {});
  }

  // ---- phone numbers ----------------------------------------------------------
  function countryList() {
    const source = (typeof LOMIMAIL_COUNTRIES !== 'undefined' && Array.isArray(LOMIMAIL_COUNTRIES))
      ? LOMIMAIL_COUNTRIES
      : [];
    const list = source.map(entry => ({
      iso: entry[1], name: entry[2], dial: String(entry[3]).split('-')[0]
    }));
    return list.length ? list : [{ iso: 'NG', name: 'Nigeria', dial: '234' }];
  }

  function composePhone(raw, dial) {
    const digits = raw.replace(/\D/g, '');
    if (!digits) throw new Error('Enter your phone number.');
    if (raw.trim().startsWith('+')) return '+' + digits;
    const national = digits.replace(/^0+/, '');
    if (!national) throw new Error('Enter a valid national phone number.');
    return '+' + dial + national;
  }

  function checkPassword(password) {
    if (password.length < 6) throw new Error('Choose a password of at least 6 characters.');
    if (new TextEncoder().encode(password).length > 72) {
      throw new Error('Password is too long; use no more than 72 bytes.');
    }
  }

  function phoneBlock(me, reload) {
    const status = h('p', { class: 'lm-status', 'aria-live': 'polite' });
    const countries = countryList();
    const country = h('select', { id: 'lmPhoneCountry', name: 'country' });
    countries.forEach(item => country.append(h('option', {
      value: item.iso, text: item.name + ' (+' + item.dial + ')'
    })));
    country.value = 'NG';

    const phone = h('input', {
      id: 'lmPhoneNumber', type: 'tel', autocomplete: 'tel', inputmode: 'tel', maxlength: '20'
    });
    const password = me.has_password ? null : h('input', {
      id: 'lmPhonePassword', type: 'password', autocomplete: 'new-password'
    });
    const otp = h('input', {
      id: 'lmPhoneOtp', type: 'text', inputmode: 'numeric',
      autocomplete: 'one-time-code', maxlength: '6'
    });
    const otpField = field('Verification code', otp);
    otpField.hidden = true;
    const devNote = h('p', { class: 'lm-status lm-info', hidden: true });

    const send_ = h('button', { type: 'submit', class: 'lm-account-primary', text: 'Send code' });
    const verify = h('button', {
      type: 'button', class: 'lm-account-primary', text: 'Verify and add', hidden: true
    });
    const cancel = h('button', { type: 'button', class: 'lm-account-secondary', text: 'Cancel' });

    const form = h('form', { class: 'lm-profile-form', hidden: true, novalidate: 'true' },
      field('Country', country),
      field('Phone number', phone),
      password ? field('Create a password (needed to sign in with this number)', password) : null,
      otpField, devNote, status,
      h('div', { class: 'lm-account-actions' }, send_, verify, cancel));

    const open = h('button', {
      type: 'button', class: 'lm-account-secondary lm-wide', text: 'Add a phone number'
    });
    const note = h('p', {
      class: 'lm-hint',
      text: 'Adding a verified phone number also gives you a Lomimail address.'
    });

    let pending = null;
    const chosen = () => {
      const item = countries.find(entry => entry.iso === country.value) || countries[0];
      return item;
    };

    open.addEventListener('click', () => { form.hidden = false; open.hidden = true; note.hidden = true; phone.focus(); });
    cancel.addEventListener('click', () => { form.hidden = true; open.hidden = false; note.hidden = false; });

    form.addEventListener('submit', async event => {
      event.preventDefault();
      showStatus(status, '');
      try {
        const place = chosen();
        const number = composePhone(phone.value, place.dial);
        if (password) checkPassword(password.value);
        send_.disabled = true;
        const data = await send('/auth/phone/request', 'POST', {
          phone: number, country: place.name, country_iso2: place.iso
        });
        pending = number;
        otpField.hidden = false;
        verify.hidden = false;
        send_.textContent = 'Resend code';
        if (data.dev_otp !== undefined && data.dev_otp !== null) {
          devNote.textContent = 'BETA TEST CODE: ' + data.dev_otp;
          devNote.hidden = false;
        }
        showStatus(status, 'We sent a verification code to ' + number + '.', 'success');
      } catch (error) {
        showStatus(status, error.message || 'Could not send the code.', 'error');
      } finally {
        send_.disabled = false;
      }
    });

    verify.addEventListener('click', async () => {
      showStatus(status, '');
      try {
        const place = chosen();
        const number = composePhone(phone.value, place.dial);
        if (pending !== number) throw new Error('Send a code to this number first.');
        const code = otp.value.trim();
        if (!/^\d{6}$/.test(code)) throw new Error('Enter the 6-digit code.');
        const body = { phone: number, otp: code, country: place.name, country_iso2: place.iso };
        if (password) {
          checkPassword(password.value);
          body.password = password.value;
        }
        verify.disabled = true;
        const data = await send('/auth/phone/verify', 'POST', body);
        if (data.access_token) {
          localStorage.setItem('lominii_token', data.access_token);
          if (typeof authToken !== 'undefined') authToken = data.access_token;
        }
        await reload(data.lomimail_address
          ? 'Phone added. Your Lomimail address is ' + data.lomimail_address + '.'
          : 'Phone number added.');
      } catch (error) {
        showStatus(status, error.message || 'Could not verify the code.', 'error');
        verify.disabled = false;
      }
    });

    return h('div', { class: 'lm-phone-block' }, open, note, form);
  }

  // ---- sections ----------------------------------------------------------------
  function header(me) {
    const initial = (Array.from((me.full_name || '').trim())[0] || '?').toUpperCase();
    return h('div', { class: 'lm-profile-head' },
      h('div', { class: 'lm-avatar', 'aria-hidden': 'true', text: initial }),
      h('div', {},
        h('h3', { class: 'lm-profile-name', text: me.full_name || 'Your account' }),
        h('p', { class: 'lm-profile-sub', text: me.email || (me.phone ? 'Phone account' : 'LOMINII account') })));
  }

  function lomimailRow(me) {
    if (!me.lomimail_address) {
      return row('Lomimail', value('Not issued yet. Add a phone number to receive one.'));
    }
    const copied = h('span', { class: 'lm-copy-status', role: 'status' });
    const copy = h('button', {
      type: 'button', class: 'lm-copy', 'aria-label': 'Copy Lomimail address', text: 'Copy'
    });
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(me.lomimail_address);
        copied.textContent = 'Copied';
      } catch (_) {
        copied.textContent = 'Copy not available';
      }
      setTimeout(() => { copied.textContent = ''; }, 2000);
    });
    return row('Lomimail', h('div', { class: 'lm-address' }, value(me.lomimail_address, true), copy, copied));
  }

  function details(me) {
    const rows = [];
    if (me.email) rows.push(row('Email', value(me.email)));
    rows.push(row('Phone', value(me.phone
      ? me.phone + (me.phone_verified ? ' · verified' : '')
      : 'Not added')));
    rows.push(lomimailRow(me));
    const place = [me.city, me.lga, me.state, me.country].filter(Boolean).join(', ');
    if (place) rows.push(row('Location', value(place)));
    const communities = [me.primary_community_1, me.primary_community_2].filter(Boolean).join(' · ');
    if (communities) rows.push(row('Community', value(communities)));
    if (me.occupation) rows.push(row('Occupation', value(me.occupation)));
    const language = (LANGUAGES.find(item => item[0] === me.language) || [])[1];
    if (language) rows.push(row('Language', value(language)));
    const joined = me.created_at ? new Date(me.created_at) : null;
    if (joined && !Number.isNaN(joined.getTime())) {
      rows.push(row('Member since', value(joined.toLocaleDateString(undefined, {
        year: 'numeric', month: 'long', day: 'numeric'
      }))));
    }
    return section('Account details', ...rows);
  }

  function signIn(me, reload) {
    const status = h('p', { class: 'lm-status', 'aria-live': 'polite' });
    const parts = [
      row('Password', value(me.has_password ? 'Set' : 'Not set')),
      row('Google', value(me.google_linked ? 'Linked' : 'Not linked'))
    ];
    if (!me.google_linked) {
      const google = h('div', { class: 'lm-google', hidden: true });
      parts.push(h('p', { class: 'lm-hint', text: 'Link your Google account to sign in with it next time.' }), google, status);
      mountGoogle(google, async credential => {
        showStatus(status, '');
        try {
          await send('/auth/google/link', 'POST', { credential });
          await reload('Google account linked.');
        } catch (error) {
          showStatus(status, error.message || 'Could not link Google.', 'error');
        }
      });
    } else {
      parts.push(status);
    }
    if (!me.phone) parts.push(phoneBlock(me, reload));
    return section('Sign-in', ...parts);
  }

  function editForm(me, reload) {
    const inputs = {};
    const status = h('p', { class: 'lm-status', 'aria-live': 'polite' });
    const fields = [];

    TEXT_FIELDS.forEach(([key, label, max]) => {
      inputs[key] = h('input', {
        id: 'lmEdit_' + key, type: 'text', value: me[key] || '',
        maxlength: String(max), autocomplete: 'off'
      });
      fields.push(field(label, inputs[key]));
    });
    URL_FIELDS.forEach(([key, label]) => {
      inputs[key] = h('input', {
        id: 'lmEdit_' + key, type: 'url', value: me[key] || '',
        maxlength: '500', inputmode: 'url', autocomplete: 'off'
      });
      fields.push(field(label, inputs[key]));
    });
    inputs.language = h('select', { id: 'lmEdit_language' });
    if (!me.language) inputs.language.append(h('option', { value: '', text: 'Not set' }));
    LANGUAGES.forEach(([code, name]) => inputs.language.append(h('option', { value: code, text: name })));
    inputs.language.value = me.language || '';
    fields.push(field('Language', inputs.language));

    const save = h('button', { type: 'submit', class: 'lm-account-primary', text: 'Save changes' });
    const form = h('form', { class: 'lm-profile-form', novalidate: 'true' },
      ...fields, status, h('div', { class: 'lm-account-actions' }, save));

    form.addEventListener('submit', async event => {
      event.preventDefault();
      const changes = {};
      try {
        TEXT_FIELDS.forEach(([key, label, , required]) => {
          const text = inputs[key].value.trim();
          if (text === (me[key] || '')) return;
          if (!text && required) throw new Error(label + ' is required.');
          changes[key] = text;
        });
        URL_FIELDS.forEach(([key, label]) => {
          const text = inputs[key].value.trim();
          if (text === (me[key] || '')) return;
          if (text) {
            let valid = false;
            try {
              const url = new URL(text);
              valid = (url.protocol === 'http:' || url.protocol === 'https:') && !/\s/.test(text);
            } catch (_) {}
            if (!valid) throw new Error(label + ' must be a web address starting with http:// or https://.');
          }
          changes[key] = text;
        });
        const language = inputs.language.value;
        if (language && language !== (me.language || '')) changes.language = language;

        if (!Object.keys(changes).length) {
          showStatus(status, 'Nothing to save yet.', 'info');
          return;
        }
        save.disabled = true;
        const updated = await send('/auth/profile', 'PUT', changes);
        if (updated.full_name) localStorage.setItem('lominii_username', updated.full_name);
        await reload('Profile saved.', updated);
      } catch (error) {
        showStatus(status, error.message || 'Could not save the profile.', 'error');
        save.disabled = false;
      }
    });

    return section('Edit profile', form);
  }

  function failure(error, retry, overlay) {
    const expired = Boolean(error && error.status === 401);
    if (expired) {
      localStorage.removeItem('lominii_token');
      localStorage.setItem('lominii_account_type', 'guest');
    }
    const action = h('button', {
      type: 'button', class: 'lm-account-primary', text: expired ? 'Sign in' : 'Try again'
    });
    action.addEventListener('click', () => {
      if (expired) {
        overlay.hidden = true;
        if (typeof openLoginModal === 'function') openLoginModal();
      } else {
        retry();
      }
    });
    return h('div', { class: 'lm-profile-error', role: 'alert' },
      h('p', { text: expired
        ? 'Your session has ended. Please sign in again.'
        : (error && error.message) || 'Could not load your profile.' }),
      h('div', { class: 'lm-account-actions' }, action));
  }

  // ---~panel ---------------------------------------------------------------------
  function show(root, overlay, me, notice) {
    const reload = (message, fresh) => (fresh ? Promise.resolve(show(root, overlay, fresh, message)) : load(root, overlay, message));
    // replaceChildren(null) would insert the text "null", so skip an absent notice.
    const parts = [
      notice ? h('p', { class: 'lm-status lm-success', role: 'status', text: notice }) : null,
      header(me),
      details(me),
      signIn(me, reload),
      editForm(me, reload)
    ];
    root.replaceChildren(...parts.filter(Boolean));
  }

  async function load(root, overlay, notice) {
    root.replaceChildren(h('p', { class: 'lm-hint', role: 'status', text: 'Loading your profile…' }));
    try {
      const response = await apiFetch('/auth/me');
      show(root, overlay, await response.json(), notice);
    } catch (error) {
      root.replaceChildren(failure(error, () => load(root, overlay), overlay));
    }
  }

  function cleanup(card) {
    const old = card.querySelector('#lmProfileDynamic');
    if (old) old.remove();
    card.querySelectorAll('[data-profile-hidden]').forEach(node => {
      node.style.display = '';
      delete node.dataset.profileHidden;
    });
  }

  function open(overlay) {
    const card = overlay && overlay.querySelector('.lm-account-card');
    if (!card) return;
    cleanup(card);
    if (!isRegistered()) return;

    // The static "this browser session" details and the free-access note are for guests.
    const signup = overlay.querySelector('#lmAccountSignup');
    [card.querySelector('.lm-account-section'), signup && signup.closest('.lm-account-section')]
      .forEach(node => {
        if (!node) return;
        node.dataset.profileHidden = '1';
        node.style.display = 'none';
      });

    const root = h('div', { id: 'lmProfileDynamic', class: 'lm-profile' });
    card.insertBefore(root, card.querySelector('#lmAboutSection'));
    load(root, overlay);
  }

  window.LominiiProfile = Object.freeze({ open });
})();
