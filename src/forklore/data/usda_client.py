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



def pick_best_food(foods, query=""):
    query = query.lower().strip()

    # 1. If the search closely matches a BRANDED product name, prefer it.
    #    (e.g. searching "drumstick" when there's a branded "DRUMSTICK")
    if query:
        for food in foods:
            desc = food.get("description", "").lower()
            is_branded = food.get("dataType") == "Branded"
            # strong match: the query is the whole description, or vice versa
            if is_branded and (query in desc or desc in query):
                return food

    # 2. Prefer an entry described as "raw" (real whole food)
    for food in foods:
        if "raw" in food.get("description", "").lower():
            return food

    # 3. Otherwise prefer generic data types over Branded
    generic = [f for f in foods if f.get("dataType") in GENERIC_TYPES]
    if generic:
        return generic[0]

    # 4. Fall back to the first result
    return foods[0]