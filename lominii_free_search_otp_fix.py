from pathlib import Path
from datetime import datetime
import re
import shutil
import subprocess
import sys

ROOT = Path.cwd()

def load(path):
    p = ROOT / path
    if not p.is_file():
        raise RuntimeError(f"Missing file: {path}")
    return p.read_text(encoding="utf-8")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected one match, found {count}. "
            "No files have been changed."
        )
    return text.replace(old, new, 1)

def replace_regex(text, pattern, replacement, label):
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected one match, found {count}. "
            "No files have been changed."
        )
    return updated

paths = [
    "apps/lominii/search/router.py",
    "public/js/lomimail-registration.js",
    "public/css/lomimail-registration.css",
]

original = {path: load(path) for path in paths}
updated = dict(original)

# =========================================================
# 1. FREE EXPLORE: allow guest tokens on SEARCH ONLY.
# =========================================================

path = "apps/lominii/search/router.py"
s = updated[path]

if "from lominii_platform.auth import get_current_user" in s:
    s = replace_once(
        s,
        "from lominii_platform.auth import get_current_user",
        "from lominii_platform.auth import oauth2_scheme, validate_token",
        "Search authentication import",
    )
elif not all(x in s for x in ("oauth2_scheme", "validate_token")):
    raise RuntimeError(
        "Cannot identify the search authentication import safely."
    )

if "async def get_search_identity(" not in s:
    marker = "CACHE_TTL_AUTHENTICATED = 300"
    if s.count(marker) != 1:
        raise RuntimeError("Cannot locate search cache configuration.")

    helper = '''

async def get_search_identity(token: str = Depends(oauth2_scheme)) -> str:
    """Accept valid guest tokens for free search, not other protected routes."""
    payload = validate_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    identity = payload.get("sub")
    if not isinstance(identity, str) or not identity:
        raise HTTPException(status_code=401, detail="Invalid token identity")

    return identity
'''
    s = s.replace(marker, marker + helper, 1)

if "email: str = Depends(get_current_user)" in s:
    s = replace_once(
        s,
        "email: str = Depends(get_current_user)",
        "email: str = Depends(get_search_identity)",
        "Search endpoint authentication",
    )
elif "email: str = Depends(get_search_identity)" not in s:
    raise RuntimeError("Cannot identify the search endpoint dependency.")

updated[path] = s

# =========================================================
# 2. OTP: show a separate, prominent development-code notice.
# =========================================================

path = "public/js/lomimail-registration.js"
s = updated[path]

if 'id: "lm-dev-otp-display"' not in s:
    status_pattern = (
        r'    const status = el\("div", \{\s*'
        r'id: "lm-status",\s*'
        r'className: "lm-status",\s*'
        r'role: "status",\s*'
        r'"aria-live": "polite"\s*'
        r'\}\);\s*'
    )
    status_replacement = '''    const status = el("div", {
      id: "lm-status",
      className: "lm-status",
      role: "status",
      "aria-live": "polite"
    });

    const devOtpNotice = el("div", {
      id: "lm-dev-otp-display",
      className: "lm-dev-otp",
      role: "status",
      "aria-live": "assertive",
      hidden: ""
    });
'''
    s = replace_regex(
        s, status_pattern, status_replacement, "OTP notice creation"
    )

    s = replace_once(
        s,
        "      phoneGrid,\n      otpWrap,",
        "      phoneGrid,\n      devOtpNotice,\n      otpWrap,",
        "OTP notice placement",
    )

    s = replace_once(
        s,
        '''      status.textContent = "";
      status.className = "lm-status";
    }

    close.addEventListener''',
        '''      status.textContent = "";
      status.className = "lm-status";
      devOtpNotice.textContent = "";
      devOtpNotice.hidden = true;
    }

    close.addEventListener''',
        "Clear OTP notice on close",
    )

    s = replace_once(
        s,
        '''      requestButton.disabled = true;
      requestButton.textContent = "Requesting code…";

      try {''',
        '''      requestButton.disabled = true;
      requestButton.textContent = "Requesting code…";
      devOtpNotice.textContent = "";
      devOtpNotice.hidden = true;

      try {''',
        "Reset OTP notice before request",
    )

    response_pattern = (
        r'        requestButton\.textContent = "Resend verification code";\s*'
        r'setStatus\(\s*'
        r'result\.dev_otp\s*\?\s*'
        r'"Development OTP: " \+ result\.dev_otp\s*:\s*'
        r'\(result\.message \|\| "Verification code requested\. Check your phone\."\),\s*'
        r'"success"\s*'
        r'\);\s*'
        r'        otp\.input\.focus\(\);\s*'
        r'      \} catch \(error\) \{\s*'
        r'        setStatus\(error\.message \|\| "Could not request an OTP\.", "error"\);'
    )

    response_replacement = '''        requestButton.textContent = "Resend verification code";

        if (result.dev_otp !== undefined && result.dev_otp !== null) {
          devOtpNotice.textContent =
            "BETA TEST CODE: " + String(result.dev_otp);
          devOtpNotice.hidden = false;
          setStatus(
            "Development mode is active. Enter the displayed code below.",
            "success"
          );
        } else {
          devOtpNotice.textContent = "";
          devOtpNotice.hidden = true;
          setStatus(
            result.message || "Verification code requested. Check your phone.",
            "success"
          );
        }

        otp.input.focus();
      } catch (error) {
        devOtpNotice.textContent = "";
        devOtpNotice.hidden = true;
        setStatus(error.message || "Could not request an OTP.", "error");'''

    s = replace_regex(
        s, response_pattern, response_replacement, "OTP response display"
    )

updated[path] = s

# =========================================================
# 3. OTP notice styling for mobile and desktop.
# =========================================================

path = "public/css/lomimail-registration.css"
s = updated[path]

if ".lm-dev-otp {" not in s:
    s += '''

/* Clearly visible beta OTP notice */
.lm-dev-otp[hidden] {
  display: none !important;
}

.lm-dev-otp {
  display: block;
  margin: 12px 0 16px;
  padding: 16px 12px;
  border: 2px solid #86efac;
  border-radius: 12px;
  color: #dcfce7;
  background: #14532d;
  font-size: 1.15rem;
  font-weight: 800;
  line-height: 1.5;
  letter-spacing: 0.04em;
  text-align: center;
  overflow-wrap: anywhere;
}
'''

updated[path] = s

# =========================================================
# 4. Validate all changes before writing any files.
# =========================================================

search = updated["apps/lominii/search/router.py"]
js = updated["public/js/lomimail-registration.js"]

if "email: str = Depends(get_search_identity)" not in search:
    raise RuntimeError("Search authentication validation failed.")

if "id: \"lm-dev-otp-display\"" not in js:
    raise RuntimeError("OTP notice validation failed.")

if "BETA TEST CODE:" not in js:
    raise RuntimeError("OTP display text validation failed.")

# Save backups and apply only changed files.
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
changed = [p for p in paths if updated[p] != original[p]]

if not changed:
    print("No changes needed: the requested code is already present.")
else:
    for relative in changed:
        target = ROOT / relative
        backup = target.with_name(target.name + ".backup-" + stamp)
        shutil.copy2(target, backup)
        target.write_text(updated[relative], encoding="utf-8")
        print(f"Updated: {relative}")
        print(f"Backup:  {backup.relative_to(ROOT)}")

# Syntax and whitespace checks.
checks = [
    [
        sys.executable, "-m", "py_compile",
        "apps/lominii/search/router.py",
    ],
    ["node", "--check", "public/js/lomimail-registration.js"],
    ["git", "diff", "--check"],
]

failed = False
print("\nRunning checks...")

for command in checks:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode:
        print("FAIL:", " ".join(command))
        failed = True
    else:
        print("PASS:", " ".join(command))

if failed:
    print("\nA check failed. Backups have been retained.")
    sys.exit(1)

print("\nRepair applied and checks passed.")
print("Next: review the diff, then commit and push.")
