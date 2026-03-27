# Weekly Menu Agent

A GitHub Actions workflow that runs every **Friday at ~8 am Paris time**.
It asks Claude (Anthropic) to generate a seasonal weekly dinner menu for a family,
then creates a structured task list in **Google Tasks**.

## Family constraints baked into the prompt

| Constraint | Detail |
|---|---|
| Convives | 2 adults + 1 baby (15 months) |
| Baby diet | No added salt, soft/mashed textures |
| Adult allergy | Fish, poultry, shellfish, and seafood are **forbidden** |
| Seasonality | Ingredients seasonal in France |
| Language | All output in **French** |

---

## Project structure

```
.github/workflows/weekly-menu.yml   # Scheduled GitHub Actions workflow
scripts/
  generate_menu.py                  # Core logic (Anthropic + Google Tasks)
  test_local.py                     # Local runner
requirements.txt
.env.example                        # Template for local env vars
README.md
```

---

## GitHub Secrets to configure

In your repository go to **Settings → Secrets and variables → Actions** and add:

| Secret name | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ → API Keys |
| `GOOGLE_CLIENT_ID` | Google Cloud Console (see below) |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console (see below) |
| `GOOGLE_REFRESH_TOKEN` | OAuth flow (see below) |

---

## Setting up Google OAuth

### 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com/ and create a new project (or reuse one).
2. Enable the **Google Tasks API**:
   - Navigate to **APIs & Services → Library**
   - Search for *Tasks API* and click **Enable**.

### 2. Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Choose **Desktop app** as the application type.
3. Download the JSON file (or just note the **Client ID** and **Client Secret**).
4. On the **OAuth consent screen** page add your Google account as a **Test user** (required while the app is in *Testing* mode).

### 3. Obtain a refresh token

Run the following one-time script locally (Python 3 + `requests` required):

```bash
pip install requests
python - <<'EOF'
import requests, urllib.parse, http.server, threading, webbrowser, os

CLIENT_ID     = input("Client ID     : ").strip()
CLIENT_SECRET = input("Client Secret : ").strip()
REDIRECT_URI  = "http://localhost:8080"
SCOPE         = "https://www.googleapis.com/auth/tasks"

auth_url = (
    "https://accounts.google.com/o/oauth2/v2/auth?"
    + urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })
)

code_holder = {}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code_holder["code"] = qs.get("code", [""])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"You can close this tab.")
    def log_message(self, *a): pass

server = http.server.HTTPServer(("localhost", 8080), Handler)
t = threading.Thread(target=server.handle_request)
t.start()

print("Opening browser for Google login…")
webbrowser.open(auth_url)
t.join()

resp = requests.post("https://oauth2.googleapis.com/token", data={
    "code": code_holder["code"],
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
})
data = resp.json()
print("\nRefresh token:", data.get("refresh_token"))
EOF
```

Copy the printed refresh token into the `GOOGLE_REFRESH_TOKEN` GitHub secret.

> **Why a refresh token?**  
> Access tokens expire after ~1 hour. The workflow stores a long-lived refresh token
> in GitHub Secrets and exchanges it for a fresh access token at runtime.

---

## Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in the env template
cp .env.example .env
# edit .env …
export $(cat .env | xargs)

# Test menu generation only (no Google credentials needed)
python scripts/test_local.py --menu-only

# Full test: generate menu + create Google Tasks list
python scripts/test_local.py
```

---

## Schedule & timezone

The cron expression `0 7 * * 5` (UTC) maps to:

| Period | Paris time |
|---|---|
| Winter (CET = UTC+1) | 08:00 ✅ |
| Summer (CEST = UTC+2) | 09:00 (1 h late) |

If you want strict 8 am in summer too, change the cron to `0 6 * * 5` after
the clocks spring forward (last Sunday of March), and back to `0 7 * * 5` in
October. Alternatively, you can use both schedules and add a condition in the
workflow to skip duplicates — but for a weekly household tool the 1-hour drift
is usually acceptable.

You can also trigger the workflow manually at any time from
**Actions → Weekly Menu Generator → Run workflow**.
