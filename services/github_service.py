from github import Github, Auth, GithubException, Repository
from github.PullRequest import PullRequest
from github.File import File
from dotenv import load_dotenv
import os

class GithubService:
    def __init__(self):
        self.g = self._initialize_github()
    
    def _initialize_github(self) -> Github:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is not set")
        return Github(auth=Auth.Token(token))


class GithubRepoService(GithubService):
    def __init__(self):
        super().__init__()

    def fetch_pr_data(self, repo: str, pr_number: int) -> dict:
        repo = self.g.get_repo(repo)
        pr = repo.get_pull(pr_number)

        files = []
        for file in pr.get_files():
            if file.status != "removed" and file.patch:
                full_file_code = self._fetch_full_file(file=file, repo=repo, pr=pr)
                files.append({
                    "filename": file.filename,
                    "patch": file.patch,
                    "full_content": full_file_code
                })
        
        return {
            "title": pr.title,
            "description": pr.body or "",
            "author": pr.user.login,
            "head_sha": pr.head.sha,
            "files": files
        }

    def post_review(self, repo: str, pr_number: int, comments: list, commit_sha: str):
        repo = self.g.get_repo(repo)
        pr = repo.get_pull(pr_number)

        review_comments = []
        for c in comments:
            review_comments.append(
                {
                    "path": c.get("path"),
                    "line": c.get("line"),
                    "body": c.get("body")
                }
            )
        
        # event = "APPROVE" if len(review_comments) == 0 else "REQUEST_CHANGES"
        pr.create_review(
            commit=repo.get_commit(commit_sha),
            event="REQUEST_CHANGES",
            comments=review_comments
        )
        print(f"Posted {len(comments)} inline comments")

    def approve_review(self, repo: str, pr_number: int, commit_sha: str):
        repo = self.g.get_repo(repo)
        pr = repo.get_pull(pr_number)

        pr.create_review(
            commit=repo.get_commit(commit_sha),
            event="APPROVE"
        )


    def _fetch_full_file(self, file: File, repo: Repository, pr: PullRequest) -> str | None:
        try:
            file_content = repo.get_contents(file.filename, ref=pr.head.sha)
            full_code = file_content.decoded_content.decode()
        except Exception as e:
            print(f"Could not fetch full content for {file.filename}: {e}")
            full_code = None

        return full_code




