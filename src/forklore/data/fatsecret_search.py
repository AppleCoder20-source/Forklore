from forklore.ai.fatsecret_routing import classify_source
from forklore.data.usda_client import usda_search_all
from forklore.data.fatsecret_client import search_fatsecret


def search_food(query, provider="local"):
    """Route a food search: specific branded -> FatSecret, generic -> USDA.
    Falls back to the other source if the first finds nothing.
    Returns (results, source) so the caller knows which parser to use."""
    route = classify_source(query, provider)

    if route == "specific":
        results = search_fatsecret(query)
        if results:
            return results, "fatsecret"
        return usda_search_all(query), "usda"          # fallback
    else:
        results = usda_search_all(query)
        if results:
            return results, "usda"
        return search_fatsecret(query), "fatsecret"    # fallback