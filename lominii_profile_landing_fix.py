from pathlib import Path
from datetime import datetime
import re
import subprocess
import sys

ROOT = Path.cwd()
FILES = [
    ROOT / "public/js/common.js",
    ROOT / "public/css/dashboard.css",
    ROOT / "public/css/landing.css",
]

for path in FILES:
    if not path.is_file():
        print(f"STOP: Required file not found: {path.relative_to(ROOT)}")
        sys.exit(1)

original = {p: p.read_text(encoding="utf-8") for p in FILES}
updated = dict(original)

# ---------------------------------------------------------
# 1. Replace the broken profile dropdown click handling.
# ---------------------------------------------------------
js_path = ROOT / "public/js/common.js"
js = updated[js_path]

start_marker = "// ── User dropdown ─"
end_marker = "// ── Home dropdown toggle"

if start_marker not in js or end_marker not in js:
    print("STOP: Could not safely locate the user dropdown section.")
    print("No files have been changed.")
    sys.exit(1)

start = js.index(start_marker)
end = js.index(end_marker, start)

profile_code = r'''
// ── User dropdown and account profile ───────────────────
const userIcon = document.getElementById('userIcon');
const userDropdown = document.getElementById('userDropdown');

function ensureAccountMenuItem(id, label) {
  if (!userDropdown || document.getElementById(id)) return;

  const link = document.createElement('a');
  link.href = '#';
  link.id = id;
  link.textContent = label;

  const logoutLink = userDropdown.querySelector('#btnLogout');
  if (logoutLink) {
    userDropdown.insertBefore(link, logoutLink);
  } else {
    userDropdown.appendChild(link);
  }
}

ensureAccountMenuItem('btnSignupFromProfile', 'Create account');
ensureAccountMenuItem('btnAboutLominii', 'About LOMINII');

if (userIcon && userDropdown) {
  // Replace the hard-coded "A" with a neutral profile stub.
  const initialNode = Array.from(userIcon.childNodes).find(
    node => node.nodeType === Node.TEXT_NODE && node.textContent.trim()
  );

  if (initialNode) initialNode.textContent = '👤 ';

  userIcon.setAttribute('role', 'button');
  userIcon.setAttribute('tabindex', '0');
  userIcon.setAttribute('aria-label', 'Open account menu');
  userIcon.setAttribute('aria-expanded', 'false');

  const toggleUserMenu = event => {
    event.stopPropagation();
    const isOpen = userDropdown.classList.toggle('show');
    userIcon.setAttribute('aria-expanded', String(isOpen));
  };

  userIcon.addEventListener('click', toggleUserMenu);
  userIcon.addEventListener('keydown', event => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleUserMenu(event);
    }
  });

  userDropdown.addEventListener('click', event => {
    event.stopPropagation();
  });

  document.addEventListener('click', () => {
    userDropdown.classList.remove('show', 'open');
    userIcon.setAttribute('aria-expanded', 'false');
  });
}

function closeUserMenu() {
  if (userDropdown) userDropdown.classList.remove('show', 'open');
  if (userIcon) userIcon.setAttribute('aria-expanded', 'false');
}

function openLominiiAccountPanel(section) {
  let overlay = document.getElementById('lominiiAccountPanel');

  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'lominiiAccountPanel';
    overlay.className = 'lm-account-overlay';
    overlay.hidden = true;
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'lmAccountTitle');

    overlay.innerHTML = `
      <section class="lm-account-card">
        <header class="lm-account-header">
          <div>
            <p class="lm-account-eyebrow">LOMINII ACCOUNT</p>
            <h2 id="lmAccountTitle">My Profile</h2>
          </div>
          <button type="button" id="lmAccountClose"
            class="lm-account-close" aria-label="Close profile">&times;</button>
        </header>

        <section class="lm-account-section">
          <h3>Account details</h3>
          <div class="lm-account-row">
            <span>Account type</span>
            <strong id="lmAccountType">Free search</strong>
          </div>
          <div class="lm-account-row">
            <span>Status</span>
            <strong id="lmAccountStatus">Guest session</strong>
          </div>
          <div class="lm-account-row">
            <span>Email</span>
            <strong id="lmAccountEmail">Not provided</strong>
          </div>
          <div class="lm-account-row">
            <span>Username</span>
            <strong id="lmAccountUsername">Not provided</strong>
          </div>
          <p class="lm-account-note" id="lmAccountNote">
            These details reflect information available in this browser session.
          </p>
        </section>

        <section class="lm-account-section">
          <h3>Free access</h3>
          <p>
            You can explore LOMINII search without completing registration.
            Creating an account is a separate step.
          </p>
          <div class="lm-account-actions">
            <button type="button" id="lmAccountSignup"
              class="lm-account-primary">Create account</button>
            <button type="button" id="lmAccountSignin"
              class="lm-account-secondary">Sign in</button>
          </div>
        </section>

        <section class="lm-account-section" id="lmAboutSection">
          <h3>About LOMINII</h3>
          <p>
            LOMINII is designed to bring search, knowledge, learning,
            research and discovery into one adaptive digital experience.
          </p>
          <p>
            Explore freely, then create an account when you are ready
            to access account-based features.
          </p>
        </section>
      </section>`;

    document.body.appendChild(overlay);

    overlay.querySelector('#lmAccountClose').addEventListener('click', () => {
      overlay.hidden = true;
    });

    overlay.addEventListener('click', event => {
      if (event.target === overlay) overlay.hidden = true;
    });

    overlay.querySelector('#lmAccountSignup').addEventListener('click', () => {
      overlay.hidden = true;
      if (typeof window.openLomimailRegistration === 'function') {
        window.openLomimailRegistration();
      } else {
        alert('Registration is still loading. Please try again.');
      }
    });

    overlay.querySelector('#lmAccountSignin').addEventListener('click', () => {
      overlay.hidden = true;
      if (typeof openLoginModal === 'function') {
        openLoginModal();
      } else {
        alert('Sign-in is still loading. Please try again.');
      }
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !overlay.hidden) {
        overlay.hidden = true;
      }
    });
  }

  const email = localStorage.getItem('lominii_email') || '';
  const username = localStorage.getItem('lominii_username') || '';
  const accountType = localStorage.getItem('lominii_account_type') ||
    (email ? 'registered' : 'guest');
  const isGuest = accountType !== 'registered';

  overlay.querySelector('#lmAccountType').textContent =
    isGuest ? 'Free search (guest)' : 'Registered account';

  overlay.querySelector('#lmAccountStatus').textContent =
    isGuest ? 'Exploring without registration' : 'Signed-in session';

  overlay.querySelector('#lmAccountEmail').textContent =
    email || 'Not provided in this session';

  overlay.querySelector('#lmAccountUsername').textContent =
    username || 'Not provided in this session';

  overlay.querySelector('#lmAccountNote').textContent =
    'Only details available in this browser session are shown here. ' +
    'This panel does not invent or retrieve unverified profile details.';

  overlay.querySelector('#lmAccountSignup').hidden = !isGuest;
  overlay.querySelector('#lmAccountSignin').hidden = !isGuest;

  overlay.hidden = false;

  if (section === 'about') {
    overlay.querySelector('#lmAboutSection').scrollIntoView({
      block: 'nearest'
    });
  } else {
    overlay.querySelector('#lmAccountTitle').textContent = 'My Profile';
    overlay.querySelector('#lmAccountClose').focus();
  }
}

document.getElementById('btnProfile')?.addEventListener('click', event => {
  event.preventDefault();
  closeUserMenu();
  openLominiiAccountPanel('profile');
});

document.getElementById('btnSignupFromProfile')?.addEventListener('click', event => {
  event.preventDefault();
  closeUserMenu();
  if (typeof window.openLomimailRegistration === 'function') {
    window.openLomimailRegistration();
  } else {
    alert('Registration is still loading. Please try again.');
  }
});

document.getElementById('btnAboutLominii')?.addEventListener('click', event => {
  event.preventDefault();
  closeUserMenu();
  openLominiiAccountPanel('about');
});

'''

js = js[:start] + profile_code + js[end:]

# Mark a successful sign-in as a registered session and retain the email
# entered into the login form for display in the profile stub.
login_anchor = """        localStorage.setItem('lominii_token', result.access_token);
        authToken = result.access_token;"""

login_replacement = """        localStorage.setItem('lominii_token', result.access_token);
        localStorage.setItem('lominii_account_type', 'registered');
        localStorage.setItem('lominii_email', form.elements.email.value.trim());
        authToken = result.access_token;"""

if login_anchor in js:
    js = js.replace(login_anchor, login_replacement, 1)
else:
    print("STOP: Could not safely locate the successful login block.")
    print("No files have been changed.")
    sys.exit(1)

# Free exploration should explicitly be labelled as a guest session.
explore_anchor = """async function exploreFree() {
  const button = document.getElementById('btnExplore');
  if (button) button.disabled = true;

  try {"""

explore_replacement = """async function exploreFree() {
  const button = document.getElementById('btnExplore');
  if (button) button.disabled = true;

  localStorage.setItem('lominii_account_type', 'guest');
  localStorage.removeItem('lominii_email');

  try {"""

if explore_anchor in js:
    js = js.replace(explore_anchor, explore_replacement, 1)
else:
    print("STOP: Could not safely locate the free-exploration handler.")
    print("No files have been changed.")
    sys.exit(1)

# Clear account display data when the visitor logs out.
logout_anchor = """    localStorage.removeItem('lominii_token');
    localStorage.removeItem('lominii_uid');
    authToken = '';"""

logout_replacement = """    localStorage.removeItem('lominii_token');
    localStorage.removeItem('lominii_uid');
    localStorage.removeItem('lominii_account_type');
    localStorage.removeItem('lominii_email');
    authToken = '';"""

if logout_anchor in js:
    js = js.replace(logout_anchor, logout_replacement, 1)
else:
    print("STOP: Could not safely locate the logout handler.")
    print("No files have been changed.")
    sys.exit(1)

updated[js_path] = js

# ---------------------------------------------------------
# 2. Fix dropdown class mismatch and add profile panel style.
# ---------------------------------------------------------
css_path = ROOT / "public/css/dashboard.css"
css = updated[css_path]

if ".dropdown.open" not in css:
    print("STOP: Could not locate the existing dropdown CSS rule.")
    print("No files have been changed.")
    sys.exit(1)

if ".dropdown.show" not in css:
    css = css.replace(
        ".dropdown.open{",
        ".dropdown.show,\n.dropdown.open{",
        1
    )

css += r"""

/* ── LOMINII account/profile panel ─────────────────────── */
.lm-account-overlay[hidden] {
  display: none !important;
}

.lm-account-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  overflow-y: auto;
  background: rgba(5, 12, 25, .78);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.lm-account-card {
  width: min(100%, 560px);
  max-height: min(88vh, 820px);
  overflow-y: auto;
  padding: 1.25rem;
  border: 1px solid rgba(255, 255, 255, .18);
  border-radius: 22px;
  background: #152236;
  color: #f8fafc;
  box-shadow: 0 24px 70px rgba(0, 0, 0, .4);
}

.lm-account-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.lm-account-eyebrow {
  margin-bottom: .25rem;
  color: #93c5fd;
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: .12em;
}

.lm-account-header h2 {
  font-size: 1.45rem;
}

.lm-account-close {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, .2);
  border-radius: 12px;
  font-size: 1.6rem;
}

.lm-account-section {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid rgba(255, 255, 255, .13);
  border-radius: 16px;
  background: rgba(255, 255, 255, .045);
}

.lm-account-section h3 {
  margin-bottom: .65rem;
  font-size: 1rem;
}

.lm-account-section p {
  margin: .45rem 0;
  color: #cbd5e1;
  font-size: .92rem;
  line-height: 1.55;
}

.lm-account-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: .65rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, .09);
  font-size: .9rem;
}

.lm-account-row span {
  color: #aebdd0;
}

.lm-account-row strong {
  max-width: 62%;
  overflow-wrap: anywhere;
  text-align: right;
}

.lm-account-note {
  margin-top: .8rem !important;
  font-size: .8rem !important;
}

.lm-account-actions {
  display: flex;
  flex-wrap: wrap;
  gap: .6rem;
  margin-top: 1rem;
}

.lm-account-actions button {
  min-height: 44px;
  padding: .7rem 1rem;
  border-radius: 12px;
  font-weight: 700;
}

.lm-account-primary {
  background: #4da3ff;
  color: #0b1524;
}

.lm-account-secondary {
  border: 1px solid rgba(255, 255, 255, .25);
  color: #f8fafc;
}

@media (max-width: 480px) {
  .lm-account-card {
    padding: .9rem;
    border-radius: 18px;
  }

  .lm-account-row {
    flex-direction: column;
    gap: .25rem;
  }

  .lm-account-row strong {
    max-width: 100%;
    text-align: left;
  }
}
"""
updated[css_path] = css

# ---------------------------------------------------------
# 3. Keep landing buttons clearly separated on mobile.
# ---------------------------------------------------------
landing_path = ROOT / "public/css/landing.css"
landing = updated[landing_path]

landing += r"""

/* ── Landing page spacing and mobile clarity ───────────── */
#landingView {
  width: 100%;
  min-height: 100vh;
}

.landing-container {
  width: min(100%, 560px);
  margin-inline: auto;
  gap: .85rem;
}

.landing-container .btn {
  display: flex;
  width: min(100%, 320px);
  min-height: 48px;
  flex: 0 0 auto;
  white-space: normal;
  line-height: 1.35;
}

.landing-container .tagline {
  color: var(--text-secondary);
}

.landing-container .sub-tagline {
  margin-bottom: 1rem;
}

@media (max-width: 480px) {
  #landingView {
    padding: 1.25rem .9rem;
  }

  .landing-container h1 {
    font-size: 1.85rem;
  }

  .landing-container .btn {
    width: 100%;
    max-width: 340px;
  }
}
"""
updated[landing_path] = landing

# ---------------------------------------------------------
# 4. Back up, write, then run checks.
# ---------------------------------------------------------
changed = [p for p in FILES if updated[p] != original[p]]

if not changed:
    print("No changes were needed; the expected fixes may already exist.")
    sys.exit(0)

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

for path in changed:
    backup = path.with_name(path.name + ".bak_" + stamp)
    backup.write_text(original[path], encoding="utf-8")
    path.write_text(updated[path], encoding="utf-8")
    print(f"Updated: {path.relative_to(ROOT)}")
    print(f"Backup:  {backup.relative_to(ROOT)}")

print("\nRunning JavaScript syntax check...")
check = subprocess.run(
    ["node", "--check", "public/js/common.js"],
    cwd=ROOT,
    text=True
)
if check.returncode:
    print("JavaScript check failed. Restore the backups listed above before proceeding.")
    sys.exit(check.returncode)

print("\nRunning Git whitespace check...")
check = subprocess.run(
    ["git", "diff", "--check"],
    cwd=ROOT,
    text=True
)
if check.returncode:
    print("Git whitespace check failed. Review the diff before proceeding.")
    sys.exit(check.returncode)

print("\nSUCCESS: Landing/profile patch applied and checks passed.")
print("No commit, push, or deployment was performed.")
print("\nReview with:")
print("git diff -- public/js/common.js public/css/dashboard.css public/css/landing.css")
