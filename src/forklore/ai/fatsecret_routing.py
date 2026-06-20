from pydantic import BaseModel
from forklore.ai.llm import get_llm


class SourceChoice(BaseModel):
    source: str        # "specific" or "generic"


CLASSIFY_PROMPT = """You are routing a food search to the right database.

The user searched for: "{query}"

Decide which type of food this is:
- "specific" — a branded item from a specific restaurant or chain
  (e.g. "Dunkin caramel latte", "Starbucks frappuccino", "Halal Guys platter",
   "Oreo milkshake from Dunkin"). These are menu items from named places.
- "generic" — a general food, grocery product, or commodity
  (e.g. "chicken breast", "banana", "Coca-Cola", "Big Mac", "ice cream",
   "ground beef"). These are common foods or store products.

Reply with ONLY "specific" or "generic"."""


def classify_source(query, provider="local"):
    """Ask the AI whether this is a specific branded item (-> FatSecret) or a
    generic food (-> USDA). The AI only classifies the ROUTE — it never supplies
    nutrition data, so the grounding principle holds."""
    llm = get_llm(provider)
    structured = llm.with_structured_output(SourceChoice)
    result = structured.invoke(CLASSIFY_PROMPT.format(query=query))
    return result.source