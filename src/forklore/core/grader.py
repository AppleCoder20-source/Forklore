from forklore.models import Nutrition, is_drink_food


def grade_food(n: Nutrition) -> tuple[str, str, int]:
    """Return (letter_grade, hex_color, percentage_0_to_100).
    Thresholds are per 100g/ml. Drinks use a stricter sugar scale."""
    is_drink = _is_drink(n)

    # Score each nutrient (4 = best, 1 = worst)
    scores = [
        _score_sodium(n.sodium_mg),
        _score_sat_fat(n.saturated_fat_g),
        _score_sugar(n.bad_sugar_g, is_drink),
    ]

    # Fiber & protein are "get-enough" nutrients. For SOLID foods we always
    # score them (a meal should have them). For DRINKS we only count them
    # if they're meaningfully present (e.g. a protein shake or smoothie) —
    # otherwise we don't penalize a drink like black coffee for lacking
    # nutrients you don't drink it for.
    fiber_score = _score_fiber(n.fiber_g)
    if fiber_score >= 3:                 # only count if actually present
            scores.append(_score_fiber(n.fiber_g))
    protien_score = _score_protein(n.protein_g)
    if protien_score >= 3:                 # only count if actually present
            scores.append(_score_protein(n.protein_g))

    avg = sum(scores) / len(scores)

    # Average → letter
    if avg >= 3.6:
        letter = "A"
    elif avg >= 3.0:
        letter = "B"
    elif avg >= 2.4:
        letter = "C"
    elif avg >= 1.8:
        letter = "D"
    else:
        letter = "F"

    # Hard caps (per 100g/ml). Drinks held to a stricter sugar bar.
    sugar = n.bad_sugar_g
    if is_drink:
        if sugar > 10:
            letter = "F"
        elif sugar > 5:
            letter = _min_letter(letter, "D")
    else:
        if sugar > 22.5:
            letter = "F"
        elif sugar > 15:
            letter = _min_letter(letter, "D")

    if n.sodium_mg > 600 or n.saturated_fat_g > 8 or n.trans_fat_g > 1:
        letter = "F"
    elif n.sodium_mg > 400 or n.saturated_fat_g > 5:
        letter = _min_letter(letter, "D")
    elif n.trans_fat_g > 0:
        letter = _min_letter(letter, "C")

    # Percentage score
    pct = round(((avg - 1.0) / 3.0) * 100)
    pct = _cap_percentage(pct, letter)

    # Color
    color = {
        "A": "#2E7D32",
        "B": "#2E7D32",
        "C": "#F9A825",
        "D": "#EF6C00",
        "F": "#C62828",
    }[letter]

    return letter, color, pct


# ---- Internal scoring helpers (per 100g/ml) ----

def _is_drink(n: Nutrition) -> bool:
    return is_drink_food(n.description, n.serving_unit)


def _score_sugar(value: float, is_drink: bool) -> int:
    if is_drink:                      # drinks stricter
        if value <= 2.5:
            return 4
        if value <= 5:
            return 3
        if value <= 10:
            return 2
        return 1
    else:                             # solid foods
        if value <= 5:
            return 4
        if value <= 15:
            return 3
        if value <= 22.5:
            return 2
        return 1


def _score_sodium(value_mg: float) -> int:
    if value_mg <= 90:
        return 4
    if value_mg <= 250:
        return 3
    if value_mg <= 600:
        return 2
    return 1


def _score_sat_fat(value_g: float) -> int:
    if value_g <= 1.5:
        return 4
    if value_g <= 5:
        return 3
    if value_g <= 8:
        return 2
    return 1


def _score_fiber(value_g: float) -> int:      # get-enough
    if value_g >= 6:
        return 4
    if value_g >= 3:
        return 3
    if value_g >= 1.5:
        return 2
    return 1


def _score_protein(value_g: float) -> int:    # get-enough
    if value_g >= 12:
        return 4
    if value_g >= 6:
        return 3
    if value_g >= 3:
        return 2
    return 1


def _min_letter(a: str, b: str) -> str:
    """Return the worse (lower) of two letter grades."""
    order = ["A", "B", "C", "D", "F"]
    return a if order.index(a) >= order.index(b) else b


def _cap_percentage(pct: int, letter: str) -> int:
    """Cap the percentage when a hard cap forced the grade down."""
    caps = {"F": 26, "D": 46, "C": 66}
    return min(pct, caps.get(letter, 100))