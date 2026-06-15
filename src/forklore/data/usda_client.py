import os
import requests
from dotenv import load_dotenv

load_dotenv()
USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


def usda_api(query):
    response = requests.get(
        USDA_URL,
        params={"query": query, "api_key": USDA_API_KEY, "pageSize": 10},
        timeout=15,
    )
    response.raise_for_status()
    foods = response.json().get("foods", [])
    return foods[0] if foods else None


# Returns the FULL list of foods (not just the first), so the
# coherence check and refinement can compare all the results.
def usda_search_all(query):
    response = requests.get(
        USDA_URL,
        params={"query": query, "api_key": USDA_API_KEY, "pageSize": 10},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("foods", [])

# Data types that represent generic/raw foods (raw banana, raw apple)
# rather than branded commercial products (banana chips, snacks).
GENERIC_TYPES = ("Survey (FNDDS)", "SR Legacy")


def pick_best_food(foods):
    """Pick the best entry to grade from USDA results.

    Priority:
      1. A 'raw' entry (e.g. "Banana, raw") — the actual unprocessed food.
      2. Any generic entry (Survey / SR Legacy) over Branded products.
      3. Whatever's first (fallback, e.g. a Big Mac that's only Branded).
    """
    # 1. Prefer an entry described as "raw" (the real unprocessed fruit/food)
    for food in foods:
        description = food.get("description", "").lower()
        if "raw" in description:
            return food

    # 2. Otherwise prefer generic data types over Branded products
    generic = [f for f in foods if f.get("dataType") in GENERIC_TYPES]
    if generic:
        return generic[0]

    # 3. Fall back to the first result
    return foods[0]