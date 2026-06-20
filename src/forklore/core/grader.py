from forklore.models import Nutrition, is_drink_food


def grade_food(n: Nutrition) -> tuple[str, str, int]:
    """Return (letter_grade, hex_color, percentage_0_to_100).

    DRINKS use the real-world Nutri-Grade bands (Singapore HPB standard) — the
    worse of sugar and saturated fat per 100ml — with one custom addition: an
    extra F tier for drinks above 15g sugar (beyond a normal soda). This
    replaces the old hard cap, which had a harsh cliff (3g sugar -> A but 6g
    sugar -> D). The bands step smoothly instead.

    SOLID FOODS keep the original score-based logic (per 100g)."""
    if _is_drink(n):
        return _grade_drink(n)

    # ---- SOLID FOODS (unchanged) ----
    scores = [
        _score_sodium(n.sodium_mg),
        _score_sat_fat(n.saturated_fat_g),
        _score_sugar(n.bad_sugar_g),
    ]

    fiber_score = _score_fiber(n.fiber_g)
    if fiber_score >= 3:
        scores.append(fiber_score)
    protein_score = _score_protein(n.protein_g)
    if protein_score >= 3:
        scores.append(protein_score)

    avg = sum(scores) / len(scores)

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

    sugar = n.bad_sugar_g
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

    pct = _scale_percentage(avg, letter)
    color = _COLOR[letter]
    return letter, color, pct


# ---- Drink grading: real-world Nutri-Grade bands (Singapore HPB) ----
# A drink's grade is the WORSE of its sugar grade and its saturated-fat grade,
# both per 100ml. These are the official Singapore Nutri-Grade beverage
# thresholds, so the grading reflects a real public-health standard.
#   sugar:    <=1 -> A | <=5 -> B | <=10 -> C | >10 -> D
#   sat fat:  <=0.7 -> A | <=1.2 -> B | <=2.8 -> C | >2.8 -> D
# CUSTOM ADDITION: drinks above 15g sugar/100ml get an F (beyond a normal soda
# ~10-12g; this flags the truly sugar-loaded drinks like frappuccinos/syrups).

_DRINK_PCT = {"A": 95, "B": 84, "C": 74, "D": 64, "F": 50}


def _drink_sugar_grade(g: float) -> str:
    if g <= 1:
        return "A"
    if g <= 5:
        return "B"
    if g <= 10:
        return "C"
    if g <= 15:
        return "D"
    return "F"            # custom: extreme sugar (>15g) -> F


def _drink_satfat_grade(g: float) -> str:
    if g <= 0.7:
        return "A"
    if g <= 1.2:
        return "B"
    if g <= 2.8:
        return "C"
    return "D"


def _grade_drink(n: Nutrition) -> tuple[str, str, int]:
    """Grade a drink by the worse of its sugar and saturated-fat Nutri-Grade."""
    letter = _min_letter(_drink_sugar_grade(n.bad_sugar_g),
                         _drink_satfat_grade(n.saturated_fat_g))
    return letter, _COLOR[letter], _DRINK_PCT[letter]


# ---- Shared color map ----
_COLOR = {
    "A": "#2E7D32",
    "B": "#2E7D32",
    "C": "#F9A825",
    "D": "#EF6C00",
    "F": "#C62828",
}


# ---- Percentage scaling (school-style bands) — solid foods ----

_GRADE_BANDS = {
    "A": (3.6, 4.0, 90, 100),
    "B": (3.0, 3.6, 80, 89),
    "C": (2.4, 3.0, 70, 79),
    "D": (1.8, 2.4, 60, 69),
    "F": (1.0, 1.8, 0, 59),
}


def _scale_percentage(avg: float, letter: str) -> int:
    """Map the average to a school-style percentage matching the letter:
    A->90s, B->80s, C->70s, D->60s, F<60. Within each band a stronger average
    sits higher. When a hard cap forced the letter down, the avg may sit
    outside the band's avg-range, so we clamp."""
    avg_low, avg_high, pct_low, pct_high = _GRADE_BANDS[letter]

    span = avg_high - avg_low
    position = (avg - avg_low) / span if span else 0
    position = max(0.0, min(1.0, position))     # clamp to [0, 1]

    pct = pct_low + position * (pct_high - pct_low)
    return round(pct)


# ---- Internal scoring helpers (per 100g) — solid foods ----

def _is_drink(n: Nutrition) -> bool:
    return is_drink_food(n.description, n.serving_unit)


def _score_sugar(value: float) -> int:        # solid foods
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


# ---- +/- grade modifiers (display only) ----
# Refine a letter grade into A+/A/A-, etc., so users get finer resolution
# (Fooducate-style). F has no +/-. The base letter/color/grade is unchanged;
# this is purely the label shown on the badge.

def plus_minus_grade(letter: str, pct: int, sugar_g: float, is_drink: bool) -> str:
    """Return the +/- display grade.

    Solid foods: split the school % band into thirds (high third -> +, low -> -).
    Drinks: use sugar's position within its Nutri-Grade band (less sugar -> +).
    """
    if letter == "F":
        return "F"            # no F+/F-

    if is_drink:
        # Sugar bands: A <=1, B 1-5, C 5-10, D 10-15. Lower in band = better (+).
        band = {"A": (0, 1), "B": (1, 5), "C": (5, 10), "D": (10, 15)}[letter]
        lo, hi = band
        span = hi - lo
        pos = (sugar_g - lo) / span if span else 0      # 0 = best edge, 1 = worst
        if pos <= 0.33:
            return letter + "+"
        if pos <= 0.66:
            return letter
        return letter + "-"

    # Solid foods: position within the school % band.
    if letter == "A":                # A spans 90-100
        if pct >= 97:
            return "A+"
        if pct >= 94:
            return "A"
        return "A-"
    ones = pct % 10                  # B/C/D each span x0-x9
    if ones >= 7:
        return letter + "+"
    if ones >= 4:
        return letter
    return letter + "-"