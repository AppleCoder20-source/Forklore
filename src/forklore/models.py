from pydantic import BaseModel, NonNegativeFloat


class Nutrition(BaseModel):
    description: str
    serving_unit: str | None = None          # USDA servingSizeUnit; "ml" => drink
    data_type: str | None = None             # USDA dataType
    calories: NonNegativeFloat = 0
    sodium_mg: NonNegativeFloat = 0
    saturated_fat_g: NonNegativeFloat = 0
    trans_fat_g: NonNegativeFloat = 0
    bad_sugar_g: NonNegativeFloat = 0        # added sugar (ID 1235) — graded
    natural_sugar_g: NonNegativeFloat = 0    # total sugar (ID 2000) — display only
    brand: str = ""
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


# Words that signal a drink. Sodas are stored by FatSecret with a GRAM serving
# (serving_unit="g"), so the ml check below doesn't catch them — these brand /
# category words do. "bottle" is deliberately NOT here: it matched non-drinks
# like "bottle gourd".
DRINK_WORDS = [
    "drink", "juice", "soda", "beverage", "cola",
    "lemonade", "punch", "tea", "coffee", "smoothie",
    "latte", "macchiato", "frappuccino", "cappuccino",
    "espresso", "americano", "mocha", "cold brew",
    "iced coffee", "frappe", "refresher", "milkshake", "shake",
    # common soda brands / terms (FatSecret serves these in grams)
    "sprite", "pepsi", "fanta", "coke", "coca-cola", "coca cola",
    "mountain dew", "mtn dew", "dr pepper", "sunkist", "fizz",
    "root beer", "ginger ale", "tonic", "seltzer", "soft drink",
    "gatorade", "powerade", "energy drink", "red bull",
]


def is_drink_food(description: str, serving_unit: str | None) -> bool:
    """True if this looks like a drink — by serving unit OR description words.

    The ml check catches anything served in millilitres. But FatSecret stores
    many sodas with a GRAM serving, so we also match drink/brand words. Single
    words match whole words only (so "shake" won't match "milkshakey"); multi-
    word terms like "iced coffee" match anywhere in the description.
    """
    if serving_unit == "ml":
        return True

    desc = description.lower()
    words = set(desc.split())
    for drink_word in DRINK_WORDS:
        if " " in drink_word:          # multi-word term like "iced coffee"
            if drink_word in desc:
                return True
        elif drink_word in words:      # single word — exact whole-word match
            return True
    return False


def parse_usda_response(food: dict) -> Nutrition:
    values = {field: 0.0 for field in NUTRIENT_IDS.values()}
    values["brand"] = food.get("brandOwner", "")
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId")
        val = n.get("value", 0) or 0
        if nid in NUTRIENT_IDS:
            values[NUTRIENT_IDS[nid]] = val

    # Count sugar for drinks (catches sodas regardless of dataType).
    # Whole foods keep their natural sugar exempt.
    is_drink = is_drink_food(
        food.get("description", ""),
        food.get("servingSizeUnit"),
    )
    #Checks to see if it is a drink and if bad sugar value is 0,
    # make total sugar equal to bad sugar because for soda all of sugar is added 
    if values["bad_sugar_g"] == 0 and is_drink:
        values["bad_sugar_g"] = values["natural_sugar_g"]

    return Nutrition(
        description=food["description"],
        serving_unit=food.get("servingSizeUnit"),
        data_type=food.get("dataType"),
        **values,
    )