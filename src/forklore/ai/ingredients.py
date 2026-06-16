from pydantic import BaseModel
from forklore.ai.llm import get_llm


class Ingredient(BaseModel):
    name: str
    grams: float          # typical amount in one serving


class IngredientList(BaseModel):
    ingredients: list[Ingredient]


INGREDIENT_PROMPT = """You are helping estimate what goes into a homemade {food}.

List the typical ingredients in one serving of a homemade {food}, with a
realistic amount in grams for each.

RULES:
- Give 4 to 8 common ingredients.
- Each name must be a simple, generic food name that would appear in a
  nutrition database — e.g. "flour tortilla", "ground beef", "cheddar cheese".
- Give a realistic gram amount for ONE serving (e.g. a tortilla ~70g,
  cheese ~30g, ground beef ~85g, rice ~100g).
- No brand names, no measurements other than grams, no salt/pepper/spices,
  no water.
- Focus on ingredients that contribute real calories and nutrients.

Return the list of ingredients with their gram amounts."""


def suggest_ingredients(food: str, provider: str = "local") -> list[Ingredient]:
    """Ask the AI for a typical ingredient list WITH gram amounts for a homemade
    version of `food`. The AI suggests names and realistic portions — it does
    not grade. Each name is looked up in USDA afterward."""
    llm = get_llm(provider)
    structured = llm.with_structured_output(IngredientList)
    result = structured.invoke(INGREDIENT_PROMPT.format(food=food))
    return result.ingredients