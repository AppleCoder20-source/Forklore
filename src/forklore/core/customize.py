from forklore.models import Nutrition


def apply_additions(nutrition: Nutrition, drink_size_ml: float,
                    added_sugar_g: float, added_fat_g: float) -> Nutrition:
    """Add the user's real additions to a per-100ml nutrition base.

    The base nutrition is PER 100ml, but the user's additions are for their
    WHOLE drink. So we convert each addition to per-100ml before adding it.

    Example: 10g sugar in a 350ml drink
        factor = 350 / 100 = 3.5
        per-100ml addition = 10 / 3.5 = 2.86g
        new base sugar = base + 2.86

    A SMALLER cup makes the same sugar MORE concentrated per 100ml -> worse
    grade. That's nutritionally correct.

    IMPORTANT: returns a NEW Nutrition object via model_copy. We must NOT mutate
    the input, because in Streamlit the same cached Nutrition lives in
    session_state and the script re-runs on every interaction. Mutating it with
    += would re-apply the additions on every re-run, compounding the numbers and
    corrupting the grade. Copying keeps the cached base clean.
    """
    factor = drink_size_ml / 100        # e.g. 3.5 for a 350ml drink

    return nutrition.model_copy(update={
        "bad_sugar_g": nutrition.bad_sugar_g + added_sugar_g / factor,
        "saturated_fat_g": nutrition.saturated_fat_g + added_fat_g / factor,
    })