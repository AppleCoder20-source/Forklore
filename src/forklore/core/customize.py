from forklore.models import Nutrition


def apply_additions(nutrition: Nutrition, drink_size_ml: float,
                    added_sugar_g: float, added_fat_g: float) -> Nutrition:
    """Add the user's real additions to a per-100ml nutrition base.

    The base nutrition is PER 100ml, but the user's additions are for
    their WHOLE drink. So we convert each addition to per-100ml before
    adding it to the base.

    Example: 10g sugar in a 350ml drink
        factor = 350 / 100 = 3.5
        per-100ml addition = 10 / 3.5 = 2.86g
        new base sugar = base + 2.86

    Note: a SMALLER cup makes the same sugar MORE concentrated
    (denser per 100ml) → worse grade. That's nutritionally correct.
    """
    factor = drink_size_ml / 100        # e.g. 3.5 for a 350ml drink

    # Convert each addition to per-100ml, then add to the base.
    nutrition.bad_sugar_g += added_sugar_g / factor
    nutrition.saturated_fat_g += added_fat_g / factor

    return nutrition