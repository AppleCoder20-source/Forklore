import os
from dotenv import load_dotenv
from fatsecret import Fatsecret
from forklore.models import Nutrition

load_dotenv()

# Lazy connection: we DON'T create the FatSecret connection when this file is
# imported, because that can fail (credentials, auth) and crash the whole import.
# Instead we create it the first time a function actually needs it.
_fs = None


def _get_fs():
    """Create the FatSecret connection on first use (not at import time).
    FatSecret uses OAuth2 (client id + secret). We request both scopes so the
    v5 methods (premier) work alongside the basic ones."""
    global _fs
    if _fs is None:
        _fs = Fatsecret(
            os.getenv("FATSECRET_CLIENT_ID"),
            os.getenv("FATSECRET_CLIENT_SECRET"),
            auth="oauth2",
            scopes=["basic", "premier"],
        )
    return _fs


def search_fatsecret(query):
    """Search FatSecret and return the list of Food results.
    Note: these are SUMMARY results - name, brand, and a text description,
    but no structured per-100g nutrients. Use get_food_detail() for that."""
    return _get_fs().foods.search_v5(query)


def get_food_detail(food_id):
    """Fetch the FULL detailed food (with the servings list) by its id.
    This is the second step: search gives ids, this gives the real nutrition.
    Wrapped in try/except so a food the library can't parse returns None
    instead of crashing the app - the caller already handles None."""
    try:
        return _get_fs().foods.get_v5(food_id=food_id)
    except Exception:
        return None


def find_100g_serving(detail):
    """Find the per-100g serving from the food's serving list.

    FatSecret returns `serving` as a LIST when a food has multiple servings,
    but as a SINGLE object when it has only one. We normalize to a list first
    so the loop works either way."""
    servings = detail.servings.serving
    if not isinstance(servings, list):       # single serving came as one object
        servings = [servings]                # wrap it so we can loop

    for s in servings:
        if s.metric_serving_unit == "g" and float(s.metric_serving_amount) == 100:
            return s
    return None


def parse_fatsecret_response(detail):
    """Turn a detailed FatSecret food into our Nutrition object (per 100g).
    Every value is real FatSecret data - the grounding principle holds.
    Returns None if there's no detail (fetch failed) or no per-100g serving
    (can't grade it)."""
    if detail is None:                        # get_food_detail returned None
        return None

    serving = find_100g_serving(detail)
    if serving is None:
        return None

    # float(x or 0): grab the value, default to 0 if it's None, convert
    # FatSecret's Decimal to float (our Nutrition uses floats).
    return Nutrition(
        description=detail.food_name,
        brand=detail.brand_name or "",        # generic foods have no brand
        serving_unit="g",                      # FatSecret gives grams
        data_type=detail.food_type,            # "Brand" or "Generic"
        calories=float(serving.calories or 0),
        sodium_mg=float(serving.sodium or 0),
        saturated_fat_g=float(serving.saturated_fat or 0),
        trans_fat_g=float(serving.trans_fat or 0),
        # FatSecret gives total sugar; added_sugars is usually None. For drinks
        # total ~= added (syrup/sweetener), matching our USDA drink fallback.
        bad_sugar_g=float(serving.sugar or 0),
        natural_sugar_g=float(serving.sugar or 0),
        fiber_g=float(serving.fiber or 0),
        protein_g=float(serving.protein or 0),
    )