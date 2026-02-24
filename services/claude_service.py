from langchain_anthropic import ChatAnthropic
import json
import re

class ClaudeService:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0)

    def review_pr(self, pr_data: dict) -> list:

        batches = self._create_batches(files=pr_data.get("files"))
        print(f"Split into {len(batches)} batches")

        all_comments = []
        for i, batch in enumerate(batches):
            print(f"Reviewing batch {i+1}/{len(batches)} ({len(batch)} files)")
            comments = self._review_batch(batch=batch)
            all_comments.extend(comments)
        
        return all_comments


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

    def _review_batch(self, batch: list) -> list:
        from prompts.code_review import review_prompt

        all_files_text = self._format_files(files=batch)

        prompt_value = review_prompt.invoke({
            "all_files": all_files_text
        })

        response = self.llm.invoke(prompt_value)

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
