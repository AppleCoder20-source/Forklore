from forklore.models import Nutrition, parse_usda_response
from forklore.data.usda_client import usda_search_all, pick_best_food


NUTRIENT_FIELDS = [
    "calories", "sodium_mg", "saturated_fat_g", "trans_fat_g",
    "bad_sugar_g", "natural_sugar_g", "fiber_g", "protein_g",
]


def grade_from_ingredients(ingredients: list[tuple[str, float]]):
    """Look up each (name, grams) ingredient in USDA and combine their nutrients
    WEIGHTED by amount, producing one per-100g Nutrition object for the whole dish.

    Returns (combined_nutrition, found, missing). Every number is real USDA data —
    the AI never supplies a nutrient value, only the suggested amounts (editable)."""
    # Accumulate ABSOLUTE nutrient totals (grams of nutrient), not per-100g
    totals = {field: 0.0 for field in NUTRIENT_FIELDS}
    total_grams = 0.0
    found = []
    missing = []

    for name, grams in ingredients:
        foods = usda_search_all(name)
        if not foods:
            missing.append(name)
            continue
        best = pick_best_food(foods, name)
        n = parse_usda_response(best)
        found.append(name)
        total_grams += grams

        # n's values are per-100g. Scale to THIS ingredient's actual grams:
        #   actual = per_100g * (grams / 100)
        factor = grams / 100.0
        for field in NUTRIENT_FIELDS:
            totals[field] += getattr(n, field) * factor

    if total_grams == 0:
        total_grams = 1  # avoid divide-by-zero if nothing found

    # Convert the dish's absolute totals back to a per-100g basis:
    #   per_100g = (total_nutrient / total_grams) * 100
    per_100g = {field: (totals[field] / total_grams) * 100 for field in NUTRIENT_FIELDS}

    combined = Nutrition(
        description=f"Homemade ({', '.join(found)})" if found else "Homemade dish",
        serving_unit=None,
        data_type="Homemade",
        **per_100g,
    )
    return combined, found, missing