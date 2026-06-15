import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


def get_llm(provider="local"):
    """Return the LLM for the chosen provider.
    'local'  → Ollama (llama3.2, runs locally, free, private)
    'claude' → Anthropic Claude (API, cleaner output)
    """
    if provider == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")       
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=0.2,
            api_key=api_key,
        )
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.2)