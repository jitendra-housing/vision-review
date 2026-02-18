from langchain_anthropic import ChatAnthropic
import json
import re

class ClaudeService:
    def __init__(self):
        self.llm = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0)

    def review_pr(self, pr_data: dict) -> list:
        from prompts.code_review import review_prompt

        all_files_text = self._format_files(files=pr_data.get("files"))

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
