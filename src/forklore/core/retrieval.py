COMPOSITE_FOODS = [
    "taco", "burrito", "sandwich", "wrap", "salad", "bowl",
    "quesadilla", "burger", "stir fry", "casserole",
    "soup", "stew", "curry", "pasta", "sub", "panini",
]


def is_composite_food(query: str) -> bool:
    """True if the food is typically made of multiple ingredients, so it makes
    sense to ask 'restaurant or homemade?'"""
    query = query.lower()
    return any(word in query for word in COMPOSITE_FOODS)


def is_coherent(foods):
    if len(foods) <= 1:
        return True
    calorie_values = []
    for food in foods[:5]:
        for n in food.get("foodNutrients", []):
            if n.get("nutrientId") == 1008:
                calorie_values.append(n.get("value", 0))
                break
    print("DEBUG calories:", calorie_values)   # ← add this
    if len(calorie_values) < 2:
        return True
    low = min(calorie_values)
    high = max(calorie_values)
    print(f"DEBUG low={low} high={high}")       # ← add this
    if low == 0:
        return True
    return (high / low) < 4