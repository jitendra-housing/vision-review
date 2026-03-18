from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from app.webhook_handler import verify_signature
from dotenv import load_dotenv
from services.github_service import GithubRepoService
from services.claude_service import ClaudeService
from services.sheets_service import SheetsService
from datetime import datetime
import asyncio
import json
import os

load_dotenv()

app = FastAPI()

# Track PRs currently being reviewed to prevent duplicate processing
_active_reviews: set[str] = set()

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    
    # Get payload and signature
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # Verify signature
    if not verify_signature(payload=payload, signature=signature):
        raise HTTPException(status_code=401, detail="Invalid Signature")

    # Parse JSON
    data = json.loads(payload)

    # Filter PR events
    event_type = request.headers.get("X-GitHub-Event")
    if event_type != "pull_request":
        print({"status": "ignored", "reason": "not a PR event"})
        return {"status": "ignored", "reason": "not a PR event"}

    action = data.get("action")
    if action != "review_requested":
        print({"status": "ignored", "reason": f"action {action} ignored"})
        return {"status": "ignored", "reason": f"action {action} ignored"}

    # Ignore events triggered by our own bot
    sender = data.get("sender", {}).get("login")
    agent_reviewer_name = os.environ.get("GITHUB_USERNAME")
    if sender == agent_reviewer_name:
        print({"status": "ignored", "reason": "event triggered by bot itself"})
        return {"status": "ignored", "reason": "event triggered by bot itself"}

    requested_reviewer_name = data.get("requested_reviewer", {}).get("login")
    if requested_reviewer_name != agent_reviewer_name:
        print({"status": "ignored", "reason": f"requested reviewer is not {agent_reviewer_name}"})
        return {"status": "ignored", "reason": f"requested reviewer is not {agent_reviewer_name}"}

    pr_number = data["pull_request"]["number"]
    repo = data["repository"]["full_name"]

    review_key = f"{repo}#{pr_number}"
    if review_key in _active_reviews:
        print({"status": "ignored", "reason": f"review already in progress for {review_key}"})
        return {"status": "ignored", "reason": "review already in progress"}

    print(f"Reviewing PR #{pr_number} from {repo}")
    _active_reviews.add(review_key)
    background_tasks.add_task(process_review, repo, pr_number)

    return {"status": "processing", "pr": pr_number}

def _count_severities(comments: list) -> dict:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for c in comments:
        severity = c.get("severity", "").upper()
        if severity in counts:
            counts[severity] += 1
    return counts

def _prioritize_comments(comments: list, max_comments: int = 40) -> list:
    highs = [c for c in comments if c.get("severity", "").upper() == "HIGH"]
    mediums = [c for c in comments if c.get("severity", "").upper() == "MEDIUM"]

    result = highs[:max_comments]
    remaining = max_comments - len(result)
    if remaining > 0:
        result.extend(mediums[:remaining])

    if len(result) < len(comments):
        print(f"Trimmed comments from {len(comments)} to {len(result)} (HIGH: {len(highs)}, MEDIUM: {len(mediums)}, dropped LOWs)")

    return result


def process_review(repo: str, pr_number: int):
    review_key = f"{repo}#{pr_number}"
    print("Starting process_review")
    try:
        github_service = GithubRepoService()
        pr_data = github_service.fetch_pr_data(repo=repo, pr_number=pr_number)
        
        claude_service = ClaudeService()
        print("Reviewing PR with claude")  
        comments = claude_service.review_pr(pr_data=pr_data, repo=repo, github_service=github_service)
        print(f"Found {len(comments)} issues")

        comments = _prioritize_comments(comments, max_comments=40)

        if comments:
            github_service.post_review(repo=repo, pr_number=pr_number, comments=comments, commit_sha=pr_data.get("head_sha"), pr_files=pr_data.get("files"))
            print("Review posted successfully")
        else:
            github_service.approve_review(repo=repo, pr_number=pr_number, commit_sha=pr_data.get("head_sha"))
            print("No issues found - Approved")

        try:
            sheets_service = SheetsService()
            severity_counts = _count_severities(comments)
            sheets_service.log_review({
                "date": datetime.now().strftime("%d/%m/%Y"),
                "url": f"https://github.com/{repo}/pull/{pr_number}",
                "author": pr_data["author"],
                "total_comments": len(comments),
                "files_reviewed": len(pr_data["files"]),
                "high": severity_counts["HIGH"],
                "medium": severity_counts["MEDIUM"],
                "low": severity_counts["LOW"],
            })
            print("Logged to Google Sheets")
        except Exception as e:
            print(f"Sheets logging failed (non-fatal): {e}")

        return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        _active_reviews.discard(review_key)


async def stream_review(repo, pr_number):
    yield json.dumps({"status": "started"})
    try:
        success = await asyncio.to_thread(process_review, repo, pr_number)
        if success:
            yield json.dumps({"status": "done"})
        else:
            yield json.dumps({"status": "failed"})
    except Exception as e:
        yield json.dumps({"status": "failed", "error": str(e)})




@app.get("/code-review")
async def local_code_review(pr_url: str, request: Request):
    import re

    # Verify shared secret
    api_key = os.environ.get("LOCAL_REVIEW_API_KEY")
    if api_key and request.headers.get("X-API-Key") != api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse PR URL
    match = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL")

    repo = match.group(1)
    pr_number = int(match.group(2))

    print(f"Local review triggered for PR #{pr_number} from {repo}")

    return EventSourceResponse(stream_review(repo, pr_number))


@app.get("/health")
async def health():
    return {"status": "ok"}