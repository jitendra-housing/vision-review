from langchain_anthropic import ChatAnthropic
from prompts.code_review import REVIEW_SYSTEM_PROMPT, REVIEW_USER_PROMPT
import json
import re
import os

GUIDELINES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "guidelines")

REPO_GUIDELINES = {
    "elarahq/housing.brahmand": ["housing.brahmand.md"],
    "elarahq/housing.seller": ["housing.seller.md"],
    "elarahq/housing.seo": ["housing.seo.md"],
    "elarahq/khoj": ["khoj.md"],
    "elarahq/housing-app": [],
}

     
PLATFORM_GUIDELINES = {
    ".swift": "iOS.md",
    ".m": "iOS.md",
    ".h": "iOS.md",
    ".xib": "iOS.md",
    ".storyboard": "iOS.md",
    ".kt": "Android.md",
    ".java": "Android.md",
}

sonnet_4_6 = "claude-sonnet-4-6"
sonnet_4_5 = "claude-sonnet-4-5-20250929"

class ClaudeService:
    def __init__(self):
        self.llm = ChatAnthropic(model=sonnet_4_6, temperature=0)

    def review_pr(self, pr_data: dict, repo: str) -> list:
        guidelines = self._load_guidelines(repo=repo, files=pr_data.get("files"))
        system_text = REVIEW_SYSTEM_PROMPT + "\n\nGUIDELINES:\n" + guidelines

        batches = self._create_batches(files=pr_data.get("files"))
        print(f"Split into {len(batches)} batches")

        all_comments = []
        for i, batch in enumerate(batches):
            print(f"Reviewing batch {i+1}/{len(batches)} ({len(batch)} files)")
            comments = self._review_batch(batch=batch, system_text=system_text)
            all_comments.extend(comments)

        return all_comments

    def _load_guidelines(self, repo: str, files: list) -> str:
        guidelines = ""
        loaded = []

        try:
            common_path = os.path.join(GUIDELINES_DIR, "Common.md")
            with open(common_path) as f:
                guidelines = f.read()
            loaded.append("Common.md")
        except FileNotFoundError:
            print(f"Warning: Common.md not found at {common_path}")

        repo_guidelines = REPO_GUIDELINES.get(repo, [])
        for filename in repo_guidelines:
            try:
                filepath = os.path.join(GUIDELINES_DIR, filename)
                with open(filepath) as f:
                    guidelines += "\n\n" + f.read()
                loaded.append(filename)
            except FileNotFoundError:
                print(f"Warning: {filename} not found")

        if repo == "elarahq/housing-app" and files:
            platform_file = self._detect_platform(files)
            if platform_file:
                try:
                    filepath = os.path.join(GUIDELINES_DIR, platform_file)
                    with open(filepath) as f:
                        guidelines += "\n\n" + f.read()
                    loaded.append(platform_file)
                except FileNotFoundError:
                    print(f"Warning: {platform_file} not found")

        print(f"Loaded guidelines: {' + '.join(loaded) if loaded else 'none'}")
        return guidelines

    def _detect_platform(self, files: list) -> str | None:
        for file in files:
            ext = os.path.splitext(file.get("filename", ""))[1].lower()
            if ext in PLATFORM_GUIDELINES:
                return PLATFORM_GUIDELINES[ext]
        return None

    def _create_batches(self, files: list, max_tokens=150_000):
        batches = []
        current_batch = []
        current_tokens = 0

        for file in files:
            tokens = (len(file.get("full_content") or "") + len(file.get("patch") or "")) // 4

            if current_tokens + tokens > max_tokens and current_batch:
                batches.append(current_batch)
                current_batch = [file]
                current_tokens = tokens
            else:
                current_batch.append(file)
                current_tokens += tokens
        
        if current_batch:
            batches.append(current_batch)

        return batches

    def _review_batch(self, batch: list, system_text: str) -> list:

        all_files_text = self._format_files(files=batch)

        messages = [
              {
                  "role": "system",
                  "content": [
                      {
                          "type": "text",
                          "text": system_text,
                          "cache_control": {"type": "ephemeral"}
                      }
                  ],
              },
              {
                  "role": "user",
                  "content": REVIEW_USER_PROMPT.format(all_files=all_files_text),
              },
          ]

        print(f"DEBUG base_url: {self.llm._client.base_url}")
        response = self.llm.invoke(messages)

        try:
            content = response.content.strip()
            content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE).strip()
        
            comments = json.loads(content)

            for comment in comments:
                assert "path" in comment
                assert "line" in comment
                assert "body" in comment
            return comments
        except Exception as e:
            print(f"Failed to parse Claude response: {e}")
            print(f"Response: {response.content}")
            raise


    def _format_files(self, files: list) -> str:
        formatted_files = []

        for file in files:
            file_text = f"""
                {'='*60}
                FILE: {file.get("filename")}
                {'='*60}

                CHANGES (DIFF):
                {file.get("patch")}

                {'~'*60}
                FULL FILE CONTEXT:
                {'~'*60}
                {file.get("full_content") if file.get("full_content") else "[Content not available]"}
                """
            formatted_files.append(file_text)

        return "\n\n".join(formatted_files)
