from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()

llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
messages = [
    {
        "role": "system",
        "content": [{"type": "text", "text": "You are a code reviewer.", "cache_control": {"type": "ephemeral"}}],
    },
    {"role": "user", "content": "Review this: print(hello)"},
]
result = llm.invoke(messages)
print(result.content[:100])
