from langchain_core.prompts import ChatPromptTemplate

review_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert code reviewer. Focus on:
  - Security vulnerabilities
  - Bugs and logic errors
  - Performance issues
  - Code quality and best practices

  Return findings as JSON array:
  [{{"path": "filename", "line": <num>, "body": "**[SEVERITY]** description"}}]

  IMPORTANT:
  - Include "path" (filename) for each comment.
  - Prefix each comment body with severity: **[HIGH]**, **[MEDIUM]**, or **[LOW]**
  - Format: "**[HIGH]** SQL injection vulnerability detected..."
  - If no issues found, return: []"""),
  ("user", """Review this Pull Request:

  **All Changes in this PR:**

  {all_files}
  Return ONLY valid JSON array, no markdown formatting, no code fences.
  Provide inline comments as JSON array. Each comment should reference the specific file and line number.""")
])