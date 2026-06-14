from pydantic import BaseModel, NonNegativeFloat

class Nutrition(BaseModel):
    description: str
    serving_unit: str | None = None          # USDA servingSizeUnit; "ml" => drink
    data_type: str | None = None             # USDA dataType; "Branded" => sugar fallback
    calories: NonNegativeFloat = 0
    sodium_mg: NonNegativeFloat = 0
    saturated_fat_g: NonNegativeFloat = 0
    trans_fat_g: NonNegativeFloat = 0
    bad_sugar_g: NonNegativeFloat = 0        # added sugar (ID 1235) — graded
    natural_sugar_g: NonNegativeFloat = 0    # total sugar (ID 2000) — display only
    fiber_g: NonNegativeFloat = 0
    protein_g: NonNegativeFloat = 0

NUTRIENT_IDS = {
    1008: "calories",
    1093: "sodium_mg",
    1258: "saturated_fat_g",
    1257: "trans_fat_g",
    1235: "bad_sugar_g",         # added sugar → bad_sugar_g
    2000: "natural_sugar_g",     # total sugar → natural_sugar_g
    1079: "fiber_g",
    1003: "protein_g",
}

def parse_usda_response(food: dict) -> Nutrition:
    values = {field: 0.0 for field in NUTRIENT_IDS.values()}
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId")
        val = n.get("value", 0) or 0
        if nid in NUTRIENT_IDS:
            values[NUTRIENT_IDS[nid]] = val

    # Branded foods: if no added sugar reported, treat total sugar as bad sugar
    # (a soda's total sugar IS added sugar — no natural sugar in it)
    is_branded = food.get("dataType") == "Branded"
    if values["bad_sugar_g"] == 0 and is_branded:
        values["bad_sugar_g"] = values["natural_sugar_g"]

    return Nutrition(
        description=food["description"],
        serving_unit=food.get("servingSizeUnit"),   # "ml" for Fanta → drink
        data_type=food.get("dataType"),              # "Branded" for Fanta
        **values,
    )