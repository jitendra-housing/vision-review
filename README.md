# Vision Review

An in-house automated GitHub PR review bot. When added as a reviewer on a pull request, it fetches the diff, applies relevant coding guidelines, and posts inline review comments with severity-tagged feedback.

---

## How It Works

1. GitHub sends a `pull_request` webhook event with action `review_requested`.
2. The bot verifies the webhook signature and checks that it was the requested reviewer.
3. PR data (diff + full file content) is fetched from GitHub.
4. Guidelines are assembled (see [Guidelines](#guidelines) below).
5. Claude reviews the PR in batches and returns structured comments.
6. Comments are posted as a GitHub pull request review. If no issues are found, the PR is approved.
7. The review is logged to a Google Sheet.

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file:

```env
ANTHROPIC_API_KEY=...
GITHUB_TOKEN=...
GITHUB_USERNAME=<bot-account-login>
GITHUB_WEBHOOK_SECRET=...
GOOGLE_SHEETS_CREDENTIALS=...   # path to service account JSON
GOOGLE_SHEET_ID=...
```

### 3. Run the server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Point your GitHub webhook at `/webhook`

Set content type to `application/json` and select the **Pull request** event.

---

## Guidelines

Guidelines are markdown files in `prompts/guidelines/` that tell Claude what to look for. They are assembled per-review in this order:

### 1. `Common.md` — always loaded

Universal standards: severity definitions (HIGH / MEDIUM / LOW), DI patterns, security checklist, performance checklist, test coverage expectations.

### 2. Repo-specific guidelines — `vision.md` first, then fallback

**Primary:** The bot fetches `vision.md` from the root of the target repo at the PR's head SHA. If found, it is used as the repo-specific guideline.

**Fallback:** If `vision.md` is not present, the bot falls back to the hardcoded `REPO_GUIDELINES` map in `claude_service.py`, which maps repo names to local guideline files (e.g. `housing.brahmand.md`, `housing.seller.md`).

To add repo-specific guidelines for a new repo without touching the code, just add a `vision.md` to the root of that repo.

### 3. Platform guidelines — `housing-app` only

For `elarahq/housing-app`, the bot also auto-detects the platform from file extensions and appends the relevant file:

| Extensions | File |
|---|---|
| `.swift`, `.m`, `.h`, `.xib`, `.storyboard` | `iOS.md` |
| `.kt`, `.java` | `Android.md` |

Platform guidelines are loaded **in addition to** whichever repo guideline was selected above.

### Priority

```
Common.md
  + vision.md (from repo root)  ← preferred
  OR fallback: REPO_GUIDELINES map
  + platform file (housing-app only)
```

---

## Project Structure

```
main.py                        # FastAPI app + webhook handler
services/
  claude_service.py            # Claude integration, guideline loading, batching
  github_service.py            # GitHub API (fetch PR data, post review)
  sheets_service.py            # Google Sheets logging
app/
  webhook_handler.py           # Signature verification
prompts/
  code_review.py               # System + user prompts
  guidelines/
    Common.md
    iOS.md
    Android.md
    housing.brahmand.md
    housing.seller.md
    housing.seo.md
    khoj.md
```

---

## Adding Guidelines

- **New repo (preferred):** Add a `vision.md` to the root of the target repo. No code changes needed.
- **New repo (fallback):** Add an entry to `REPO_GUIDELINES` in `claude_service.py` and create the corresponding `.md` file in `prompts/guidelines/`.
- **Universal rules:** Edit `prompts/guidelines/Common.md`.
- **Platform rules:** Edit `prompts/guidelines/iOS.md` or `Android.md`.
