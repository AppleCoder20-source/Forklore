import os
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from forklore.ai.llm import get_llm

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")


class RefinementOption(BaseModel):
    label: str               # "Black coffee", "Frappuccino", etc.
    fdc_ids: list[int]       # which USDA entries this option covers


class RefinementTurn(BaseModel):
    question: str                       # "Which kind of coffee did you mean?"
    options: list[RefinementOption]     # the grouped choices


REFINEMENT_PROMPT = """You are a friendly nutrition assistant helping a user pick the right food.

The user searched for: "{query}"

USDA returned these results:
{results}

Group these results into 4-6 simple, friendly options so the user can pick which they meant.

RULES:
- Use ONLY the results above. Never invent foods not in the list.
- Each option must include the fdc_ids of the results it covers.
- Write a short, friendly question (like "Which kind of coffee did you mean?").
- Use natural labels a normal person would recognize (e.g. "Black coffee", "Latte", "Frappuccino").
- Always include an "Other / not sure" option (with an empty fdc_ids list).
"""


def format_results(foods):
    lines = []
    for food in foods:
        fdc_id = food.get("fdcId")
        description = food.get("description")
        lines.append(f"- FDC {fdc_id}: {description}")
    return "\n".join(lines)


def refine_query(query, foods, provider="local"):
      llm = get_llm(provider)                                     
      structured_llm = llm.with_structured_output(RefinementTurn)
      prompt = REFINEMENT_PROMPT.format(query=query, results=format_results(foods))
      return structured_llm.invoke(prompt)