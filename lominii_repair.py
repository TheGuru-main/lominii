from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import sys

ROOT = Path.cwd()

FILES = [
    "public/js/api.js",
    "public/js/search.js",
    "public/js/lomimail-registration.js",
    "public/css/search.css",
    "backend/main.py",
    "apps/lominii/auth/router.py",
]

missing = [name for name in FILES if not (ROOT / name).is_file()]
if missing:
    print("Run this script from the LOMINII repository root.")
    print("Missing files:", ", ".join(missing))
    sys.exit(1)


def read_file(name):
    return (ROOT / name).read_text(encoding="utf-8")


def write_file(name, content):
    path = ROOT / name

    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(path.name + ".backup-" + stamp)
        shutil.copy2(path, backup)
        print("Backup created:", backup)

    path.write_text(content, encoding="utf-8")
    print("Updated:", name)


def replace_exact(content, old, new, label):
    count = content.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected one matching section; found {count}. "
            "No repair files have been written."
        )
    return content.replace(old, new, 1)


def replace_section(content, start, end, replacement, label):
    if content.count(start) != 1 or content.count(end) != 1:
        raise RuntimeError(
            f"{label}: section markers do not match the expected source."
        )

    first = content.index(start)
    last = content.index(end, first)

    if last <= first:
        raise RuntimeError(f"{label}: invalid section boundaries.")

    return content[:first] + replacement + content[last:]


# ---------------------------------------------------------
# 1. API CLIENT: SAME-ORIGIN REQUESTS + GUEST AUTHENTICATION
# ---------------------------------------------------------

api_js = r'''// LOMINII API client — combined frontend/backend deployment.
const API_URLS = [window.location.origin];

function getToken() {
  return localStorage.getItem("lominii_token") || "";
}

function getCurrentUserId() {
  return localStorage.getItem("lominii_uid") || "";
}

async function apiFetch(path, options = {}) {
  let requestPath = path;

  // FastAPI registers unified search at /api/search/.
  if (requestPath === "/api/search") {
    requestPath = "/api/search/";
  }

  const isSearch = requestPath === "/api/search/";
  let token = getToken();

  // Start a guest session when a visitor searches without signing in.
  if (isSearch && !token) {
    const guestResponse = await fetch(
      new URL("/auth/guest", window.location.origin),
      {
        method: "POST",
        headers: { "Accept": "application/json" }
      }
    );

    if (!guestResponse.ok) {
      throw new Error("Could not start a free search session.");
    }

    const guest = await guestResponse.json();

    if (!guest.access_token) {
      throw new Error("The server did not return a search session.");
    }

    token = guest.access_token;
    localStorage.setItem("lominii_token", token);
  }

  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (token) {
    headers.set("Authorization", "Bearer " + token);
  }

  const response = await fetch(
    new URL(requestPath, window.location.origin),
    { ...options, headers }
  );

  if (!response.ok) {
    let message = "Server request failed (" + response.status + ").";

    try {
      const body = await response.clone().json();

      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (typeof body.message === "string") {
        message = body.message;
      }
    } catch (_) {}

    throw new Error(message);
  }

  return response;
}
'''

# ---------------------------------------------------------
# 2. SEARCH: USEFUL ERRORS AND CLICKABLE TRENDING TERMS
# ---------------------------------------------------------

search_js = read_file("public/js/search.js")

search_js = replace_exact(
    search_js,
    "resultsDiv.innerHTML = '<div class=\"error-state\">⚠️ Search failed. Please try again.</div>';",
    """const message = String(
      err && err.message ? err.message : "Search failed. Please try again."
    );
    const safeMessage = message.replace(/[&<>"]/g, function (c) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;"
      }[c];
    });
    resultsDiv.innerHTML =
      '<div class="error-state">⚠️ ' + safeMessage + '</div>';""",
    "Search error handling"
)

search_js = replace_exact(
    search_js,
    "list.innerHTML = trends.map(t => `<span class=\"trend-chip\">${t}</span>`).join(' ');",
    """list.innerHTML = trends.map(function (term) {
        const safeTerm = String(term).replace(/[&<>"]/g, function (c) {
          return {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;"
          }[c];
        });
        return '<button type="button" class="trend-chip" ' +
          'onclick="document.getElementById(\\'searchInput\\').value=this.textContent;' +
          'performSearch()">' + safeTerm + '</button>';
      }).join(" ");""",
    "Trending term rendering"
)

# ---------------------------------------------------------
# 3. LOMIMAIL: SAME-ORIGIN REGISTRATION + DEV OTP DISPLAY
# ---------------------------------------------------------

registration_js = read_file("public/js/lomimail-registration.js")

registration_js = replace_section(
    registration_js,
    "    async function requestJSON(path, payload) {",
    '    requestButton.addEventListener("click", async () => {',
    r'''    async function requestJSON(path, payload) {
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

''',
    "Lomimail registration request"
)

registration_js = replace_exact(
    registration_js,
    'setStatus(result.message || "Verification code requested. Check your phone.", "success");',
    '''setStatus(
          result.dev_otp
            ? "Development OTP: " + result.dev_otp
            : (result.message || "Verification code requested. Check your phone."),
          "success"
        );''',
    "Development OTP display"
)

# ---------------------------------------------------------
# 4. AUTH: DEVELOPMENT OTP IS EXPLICITLY OPT-IN AND HOST-GATED
# ---------------------------------------------------------

auth_py = read_file("apps/lominii/auth/router.py")

auth_py = replace_exact(
    auth_py,
    "from datetime import datetime, timedelta\n",
    "from datetime import datetime, timedelta\nimport os\n",
    "Auth environment import"
)

auth_py = replace_exact(
    auth_py,
    '''    if not sent:
        raise HTTPException(status_code=502, detail="OTP delivery failed. Request a new code.")

    return {
        "message": "OTP sent successfully",
        "phone": phone,
        "country": country,
        "country_iso2": region,
        "expires_in_seconds": 300,
    }
''',
    '''    # Development OTP is returned only when explicitly enabled on the
    # designated beta hostname. Normal production requests never expose it.
    dev_otp_enabled = (
        os.getenv("DEV_OTP_ENABLED", "").strip().lower() == "true"
        and request.url.hostname == "lominii-search-beta.onrender.com"
    )

    if not sent and not dev_otp_enabled:
        raise HTTPException(
            status_code=502,
            detail="OTP delivery failed. Request a new code."
        )

    result = {
        "message": (
            "Development OTP ready for testing"
            if dev_otp_enabled
            else "OTP sent successfully"
        ),
        "phone": phone,
        "country": country,
        "country_iso2": region,
        "expires_in_seconds": 300,
    }

    if dev_otp_enabled:
        result["dev_otp"] = otp_code
        result["development_mode"] = True

    return result
''',
    "Development OTP response"
)

# ---------------------------------------------------------
# 5. HOME ENDPOINTS: REAL DATABASE DATA, NEVER INVENTED NEWS
# ---------------------------------------------------------

home_router_path = ROOT / "apps/lominii/search/home_router.py"

if home_router_path.exists():
    raise RuntimeError(
        "apps/lominii/search/home_router.py already exists. "
        "No files have been changed; merge the endpoints into that file."
    )

home_router_py = '''"""LOMINII home cards backed by stored search and news data."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lominii_platform.database import get_db
from lominii_platform.models.search import Search, Trending, NewsArticle, NewsCache

router = APIRouter(tags=["Home"])


@router.get("/api/trending")
async def get_trending(db: AsyncSession = Depends(get_db)):
    """Return saved trending terms, falling back to search-history counts."""
    try:
        rows = (
            await db.execute(
                select(Trending.query)
                .where(Trending.query.is_not(None))
                .order_by(Trending.count.desc(), Trending.updated_at.desc())
                .limit(10)
            )
        ).scalars().all()

        if rows:
            return list(dict.fromkeys(
                str(item) for item in rows if str(item).strip()
            ))

        derived = (
            await db.execute(
                select(Search.query, func.count(Search.id).label("hits"))
                .where(Search.query.is_not(None))
                .group_by(Search.query)
                .order_by(func.count(Search.id).desc())
                .limit(10)
            )
        ).all()

        return [str(row[0]) for row in derived if row[0]]

    except Exception as exc:
        await db.rollback()
        print(f"Trending endpoint unavailable: {exc}")
        return []


@router.get("/api/news")
async def get_news(
    category: str = "general",
    db: AsyncSession = Depends(get_db)
):
    """Return cached or stored articles without fabricating headlines."""
    requested = (category or "general").strip().lower()[:50]

    try:
        cached = (
            await db.execute(
                select(NewsCache)
                .where(NewsCache.category == requested)
                .limit(1)
            )
        ).scalar_one_or_none()

        if cached and isinstance(cached.articles, list):
            return {
                "category": requested,
                "articles": cached.articles[:10]
            }

        query = select(NewsArticle).order_by(
            NewsArticle.published_at.desc()
        )

        if requested != "general":
            query = query.where(NewsArticle.category == requested)

        rows = (await db.execute(query.limit(10))).scalars().all()

        articles = [
            {
                "title": row.title,
                "url": row.url,
                "source": row.source,
                "published_at": (
                    row.published_at.isoformat()
                    if row.published_at else None
                )
            }
            for row in rows
            if row.title and row.url
        ]

        return {"category": requested, "articles": articles}

    except Exception as exc:
        await db.rollback()
        print(f"News endpoint unavailable: {exc}")
        return {"category": requested, "articles": []}
'''

# ---------------------------------------------------------
# 6. REGISTER THE HOME ROUTER
# ---------------------------------------------------------

main_py = read_file("backend/main.py")

main_py = replace_exact(
    main_py,
    "from apps.lominii.search.router import router as search_router\n",
    "from apps.lominii.search.router import router as search_router\n"
    "from apps.lominii.search.home_router import router as home_router\n",
    "Home router import"
)

main_py = replace_exact(
    main_py,
    "app.include_router(search_router)\n",
    "app.include_router(search_router)\n"
    "app.include_router(home_router)\n",
    "Home router registration"
)

main_py = replace_exact(
    main_py,
    '        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS news"))\n',
    '        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS news"))\n'
    '        await connection.execute(text("CREATE SCHEMA IF NOT EXISTS search"))\n',
    "Search database schema"
)

# ---------------------------------------------------------
# 7. FIX CSS SYNTAX AND RESPONSIVE HOME PRESENTATION
# ---------------------------------------------------------

search_css = read_file("public/css/search.css")

search_css = replace_exact(
    search_css,
    "border-radius: var(--color-glass-highlight);",
    "border-radius: 18px;",
    "Search input border radius"
)

search_css = replace_exact(
    search_css,
    "  margin-bottom: 1.5rem;\n\n.ai-summary-card {",
    "  margin-bottom: 1.5rem;\n}\n\n.ai-summary-card {",
    "Placeholder CSS closing brace"
)

search_css = replace_exact(
    search_css,
    "  50% {\n    opacity: .5;\n  }\n\n/* ── Small button variant",
    "  50% {\n    opacity: .5;\n  }\n}\n\n/* ── Small button variant",
    "Pulse animation closing brace"
)

search_css += r'''

/* LOMINII search home: responsive layout and readable cards */
#homeView {
  width: 100%;
  max-width: 1180px;
  padding: clamp(1rem, 3vw, 2.2rem);
  padding-bottom: calc(6rem + env(safe-area-inset-bottom));
}

.search-section {
  display: flex;
  align-items: stretch;
  gap: .55rem;
  width: 100%;
  max-width: 860px;
  margin: 0 auto 1.4rem;
  padding: .45rem;
  border: 1px solid rgba(96, 165, 250, .35);
  border-radius: 22px;
  background: rgba(255, 255, 255, .97);
  box-shadow: 0 14px 38px rgba(0, 0, 0, .18);
}

.search-input {
  min-width: 0;
  width: 100%;
  color: #172338;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 16px;
}

.search-input::placeholder { color: #738096; }

.search-input:focus {
  border-color: rgba(59, 130, 246, .45);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, .12);
}

#btnSearch {
  flex: 0 0 auto;
  min-height: 48px;
  padding: 0 1.35rem;
  border: 0;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 6px 18px rgba(37, 99, 235, .25);
  font-weight: 700;
}

#searchResults {
  width: 100%;
  max-width: 860px;
  margin: 0 auto 1.5rem;
}

#homeCards {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}

#homeCards > .card {
  min-width: 0;
  width: 100%;
  border-radius: 20px;
  text-align: left;
  overflow-wrap: anywhere;
  box-shadow: 0 10px 28px rgba(0, 0, 0, .10);
}

#homeCards > .card .icon { font-size: 2rem; }
#homeCards > .card h3 { color: #172338; }

#homeCards > .card p,
#homeCards > .card #newsList,
#homeCards > .card #trendingList,
#homeCards > .card #prayerList { color: #41516a; }

.trend-chip {
  display: inline-flex;
  align-items: center;
  margin: .2rem;
  padding: .5rem .8rem;
  border: 1px solid rgba(59, 130, 246, .22);
  border-radius: 999px;
  background: rgba(59, 130, 246, .09);
  color: #1d4ed8;
  font: inherit;
  cursor: pointer;
}

.news-headline {
  padding: .65rem 0;
  border-bottom: 1px solid #e5eaf1;
  line-height: 1.45;
}

.game-carousel { padding: 0; margin-top: 1rem; }
.game-card { border-radius: 20px; }

@media (max-width: 640px) {
  #homeView {
    padding: 1rem .8rem calc(6rem + env(safe-area-inset-bottom));
  }

  .search-section { gap: .3rem; border-radius: 18px; }
  .search-input { padding: .9rem .7rem; font-size: 1rem; }
  #btnSearch { min-height: 44px; padding: 0 .9rem; }
  #homeCards { grid-template-columns: minmax(0, 1fr); gap: .8rem; }
  #homeCards > .card { padding: 1.15rem; }
}
'''

# All expected source patterns have been checked before writing any changes.
changes = {
    "public/js/api.js": api_js,
    "public/js/search.js": search_js,
    "public/js/lomimail-registration.js": registration_js,
    "apps/lominii/auth/router.py": auth_py,
    "backend/main.py": main_py,
    "public/css/search.css": search_css,
    "apps/lominii/search/home_router.py": home_router_py,
}

# Save files with backups.
for filename, content in changes.items():
    write_file(filename, content)

print("\nRunning syntax and whitespace checks...")
failed = False

commands = [
    [
        sys.executable, "-m", "py_compile",
        "backend/main.py",
        "apps/lominii/auth/router.py",
        "apps/lominii/search/home_router.py"
    ],
    ["node", "--check", "public/js/api.js"],
    ["node", "--check", "public/js/search.js"],
    ["node", "--check", "public/js/lomimail-registration.js"],
    ["git", "diff", "--check"]
]

for command in commands:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=45
        )

        if result.returncode == 0:
            print("PASS:", " ".join(command))
        else:
            failed = True
            print("FAIL:", " ".join(command))
            print((result.stderr or result.stdout).strip())

    except FileNotFoundError:
        print("SKIP: Tool not installed:", command[0])
    except subprocess.TimeoutExpired:
        failed = True
        print("FAIL: Timed out:", " ".join(command))

print()
if failed:
    print("Repair applied, but at least one available check reported an issue.")
    print("Do not deploy until the reported syntax issue is resolved.")
else:
    print("Repair complete. Available syntax and whitespace checks passed.")

print()
print("To test development OTP, set this Render environment variable:")
print("DEV_OTP_ENABLED=true")
print("It is only honoured on lominii-search-beta.onrender.com.")
print("Review the exact changed files before committing.")
