#!/usr/bin/env python3
"""
LOMINII maintenance patch:
- Remove obsolete Social and Education screens/assets/hooks.
- Remove unused Social/Education ORM stubs only when unreferenced.
- Improve OTP verification database error handling.
- Back up every modified or deleted file.
"""

from pathlib import Path
from datetime import datetime
import ast
import re
import shutil
import subprocess
import sys

ROOT = Path.cwd()
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = ROOT / "backups" / f"social_edu_otp_{STAMP}"
BACKUP.mkdir(parents=True, exist_ok=False)

changed = []
deleted = []
skipped = []
errors = []


def backup_file(path):
    """Preserve the original file, maintaining its relative path."""
    rel = path.relative_to(ROOT)
    target = BACKUP / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def save_file(path, content):
    old = path.read_text(encoding="utf-8")
    if old == content:
        return False
    backup_file(path)
    path.write_text(content, encoding="utf-8")
    changed.append(str(path.relative_to(ROOT)))
    return True


def remove_file(path):
    if not path.exists() or not path.is_file():
        return
    backup_file(path)
    path.unlink()
    deleted.append(str(path.relative_to(ROOT)))


def replace_once(text, old, new, label):
    count = text.count(old)
    if count == 0:
        skipped.append(f"{label}: expected code not found; left unchanged")
        return text
    if count != 1:
        errors.append(f"{label}: expected one match, found {count}")
        return text
    return text.replace(old, new, 1)


print(f"\nBackup directory: {BACKUP.relative_to(ROOT)}")

# ------------------------------------------------------------
# A. Remove feature screen markup from the HTML.
# ------------------------------------------------------------
html_path = ROOT / "public/index.html"

if html_path.exists():
    html = html_path.read_text(encoding="utf-8")
    original = html

    # Remove Social workspace, retaining the following Education marker.
    social_pattern = re.compile(
        r"<!--\s*SOCIAL WORKSPACE\s*-->.*?"
        r"(?=<!--\s*(?:<!--\s*)?EDU WORKSPACE)",
        re.IGNORECASE | re.DOTALL,
    )
    html, social_count = social_pattern.subn("", html, count=1)

    if social_count:
        print("Removed Social workspace markup.")
    else:
        skipped.append("Social HTML block marker not found.")

    # Remove Education workspace up to, but not including, Quran.
    edu_pattern = re.compile(
        r"<!--\s*(?:<!--\s*)?EDU WORKSPACE\s*-->\s*-->.*?"
        r"(?=<!--\s*QURAN WORKSPACE\s*-->)",
        re.IGNORECASE | re.DOTALL,
    )
    html, edu_count = edu_pattern.subn("", html, count=1)

    if edu_count:
        print("Removed Education workspace markup.")
    else:
        skipped.append("Education HTML block marker not found.")

    # Remove stylesheet and script references to these feature files.
    html, css_count = re.subn(
        r'^[ \t]*<link\b[^>]*href=["\'][^"\']*/?css/(?:social|edu)\.css["\'][^>]*>\s*\n?',
        "",
        html,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    html, js_count = re.subn(
        r'^[ \t]*<script\b[^>]*src=["\'][^"\']*/?js/(?:social|edu)\.js["\'][^>]*>\s*</script>\s*\n?',
        "",
        html,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    if css_count:
        print(f"Removed {css_count} Social/Education stylesheet reference(s).")
    if js_count:
        print(f"Removed {js_count} Social/Education script reference(s).")

    if html != original:
        save_file(html_path, html)
else:
    errors.append("public/index.html not found.")

# ------------------------------------------------------------
# B. Remove obsolete workspace initialization cases.
# ------------------------------------------------------------
common_path = ROOT / "public/js/common.js"

if common_path.exists():
    common = common_path.read_text(encoding="utf-8")
    original = common

    for workspace in ("social", "edu"):
        pattern = re.compile(
            r"(?m)^[ \t]*case\s+['\"]"
            + re.escape(workspace)
            + r"['\"]\s*:\s*\n"
            r"(?:(?!^[ \t]*case\s+['\"]|^[ \t]*default\s*:).*\n)*?"
            r"^[ \t]*break\s*;\s*\n?",
        )
        common, count = pattern.subn("", common, count=1)
        if count:
            print(f"Removed common.js workspace case: {workspace}")
        else:
            skipped.append(
                f"common.js case '{workspace}' not found; left unchanged."
            )

    if common != original:
        save_file(common_path, common)
else:
    skipped.append("public/js/common.js not found.")

# ------------------------------------------------------------
# C. Check references before removing ORM stubs.
#    Exclude the model files themselves and backups.
# ------------------------------------------------------------
model_candidates = [
    ROOT / "backend/lominii_platform/models/social.py",
    ROOT / "backend/lominii_platform/models/edu.py",
]

python_files = []
for base in (ROOT / "apps", ROOT / "backend"):
    if base.exists():
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            if any(
                ".bak" in part or ".backup" in part or ".pre_" in part
                for part in p.parts
            ):
                continue
            python_files.append(p)

for model in model_candidates:
    if not model.exists():
        continue

    module = model.stem
    references = []

    # Look for imports of the model module from other Python files.
    import_pattern = re.compile(
        r"(?m)^\s*(?:from\s+[\w.]*"
        + re.escape(module)
        + r"\s+import\b|import\s+[\w.]*"
        + re.escape(module)
        + r"(?:\s|$))"
    )

    for source in python_files:
        if source.resolve() == model.resolve():
            continue
        try:
            content = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if import_pattern.search(content):
            references.append(str(source.relative_to(ROOT)))

    if references:
        skipped.append(
            f"Kept {model.relative_to(ROOT)}; imported by: "
            + ", ".join(references[:8])
        )
    else:
        print(f"No direct Python imports found for {model.relative_to(ROOT)}.")
        print(
            "Keeping model file for now: ORM stubs can have indirect "
            "dependencies that a text scan cannot rule out."
        )
        skipped.append(
            f"Model retained pending ORM metadata/dependency validation: "
            f"{model.relative_to(ROOT)}"
        )

# ------------------------------------------------------------
# D. Harden OTP verification's initial database flush.
# ------------------------------------------------------------
auth_path = ROOT / "apps/lominii/auth/router.py"

if not auth_path.exists():
    errors.append("apps/lominii/auth/router.py not found.")
else:
    auth = auth_path.read_text(encoding="utf-8")
    original = auth

    old_flush = """        db.add(user)
        await db.flush()
    else:
"""

    new_flush = """        db.add(user)
        try:
            # Flush now so uniqueness and database constraints are handled
            # before the rest of the identity handshake proceeds.
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    "An account or identity already exists for this phone. "
                    "Please retry verification or contact support."
                ),
            )
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Could not create the account during verification.",
            )
    else:
"""

    auth = replace_once(
        auth, old_flush, new_flush, "OTP user flush error handling"
    )

    # Include logging so unexpected commit/token failures have a server
    # traceback instead of silently hiding the root cause.
    if "import logging\n" not in auth and "import logging\r\n" not in auth:
        if re.search(r"(?m)^import os\s*$", auth):
            auth = re.sub(
                r"(?m)^import os\s*$",
                "import os\nimport logging",
                auth,
                count=1,
            )
        else:
            auth = "import logging\n" + auth

    if "logger = logging.getLogger(__name__)" not in auth:
        # Put logger declaration after imports where possible.
        import_end = 0
        lines = auth.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(("import ", "from ")):
                import_end = i + 1
        lines.insert(import_end, "\nlogger = logging.getLogger(__name__)\n")
        auth = "".join(lines)

    old_commit = """    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Identity conflict occurred. Please retry verification.",
        )

    token = create_bjt(user.email)
"""

    new_commit = """    try:
        # Generate the token before committing so token configuration errors
        # do not leave the OTP consumed while the client receives a 500.
        token = create_bjt(user.email)
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Identity conflict occurred. Please retry verification.",
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.exception("Unexpected error during phone OTP verification")
        raise HTTPException(
            status_code=500,
            detail="Phone verification could not be completed. Please retry.",
        )

"""

    auth = replace_once(
        auth, old_commit, new_commit, "OTP commit/token error handling"
    )

    if auth != original:
        # Refuse to write malformed Python.
        try:
            ast.parse(auth)
        except SyntaxError as exc:
            errors.append(
                f"OTP patch would make auth/router.py invalid: {exc}. "
                "Original file was not changed."
            )
        else:
            save_file(auth_path, auth)
    else:
        skipped.append("No OTP changes applied; expected source may differ.")

# ------------------------------------------------------------
# E. Remove feature-only frontend assets, preserving backups.
# ------------------------------------------------------------
for rel in (
    "public/js/social.js",
    "public/js/edu.js",
    "public/css/social.css",
    "public/css/edu.css",
):
    remove_file(ROOT / rel)

# ------------------------------------------------------------
# F. Remove only generated bytecode for these deleted models.
# ------------------------------------------------------------
for rel in (
    "backend/lominii_platform/models/__pycache__/social.cpython-314.pyc",
    "backend/lominii_platform/models/__pycache__/edu.cpython-314.pyc",
):
    p = ROOT / rel
    if p.exists():
        remove_file(p)

# ------------------------------------------------------------
# G. Report changes and run syntax checks.
# ------------------------------------------------------------
print("\n=== PATCH SUMMARY ===")
print("Modified:")
for item in changed:
    print("  ", item)
if not changed:
    print("   (none)")

print("\nDeleted:")
for item in deleted:
    print("  ", item)
if not deleted:
    print("   (none)")

print("\nSkipped / review:")
for item in skipped:
    print("  -", item)
if not skipped:
    print("   (none)")

print("\nBackups saved under:", BACKUP.relative_to(ROOT))

if errors:
    print("\nERRORS:")
    for item in errors:
        print("  -", item)
    print("\nPatch stopped with errors. Review the backups and report above.")
    sys.exit(1)

print("\n=== PYTHON SYNTAX ===")
py_targets = [
    ROOT / "apps/lominii/auth/router.py",
    ROOT / "backend/main.py",
]
for p in py_targets:
    if p.exists():
        try:
            ast.parse(p.read_text(encoding="utf-8"))
            print("OK:", p.relative_to(ROOT))
        except SyntaxError as exc:
            print("FAIL:", p.relative_to(ROOT), exc)
            sys.exit(2)

print("\n=== JAVASCRIPT SYNTAX ===")
node = shutil.which("node")
if node:
    for rel in (
        "public/js/common.js",
        "public/js/search.js",
        "public/js/lomimail-registration.js",
    ):
        p = ROOT / rel
        if p.exists():
            result = subprocess.run(
                [node, "--check", str(p)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            if result.returncode:
                print("FAIL:", rel)
                print(result.stdout)
                sys.exit(3)
            print("OK:", rel)
else:
    print("Node.js not found; skipped JavaScript syntax checks.")

print("\n=== REMAINING FEATURE REFERENCES ===")
for rel in ("public/index.html", "public/js/common.js", "backend/main.py"):
    p = ROOT / rel
    if not p.exists():
        continue
    content = p.read_text(encoding="utf-8", errors="replace")
    matches = [
        (i, line.strip())
        for i, line in enumerate(content.splitlines(), 1)
        if re.search(
            r"socialView|eduView|initialiseSocial|initialiseEdu|"
            r"switchSocialTab|switchEduTab|css/social\.css|css/edu\.css|"
            r"js/social\.js|js/edu\.js",
            line,
            re.IGNORECASE,
        )
    ]
    for line_no, line in matches:
        print(f"{rel}:{line_no}: {line}")

print("\nPatch finished. Review the diff before committing or deploying.")
