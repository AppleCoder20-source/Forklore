import streamlit as st
import os
from dotenv import load_dotenv
from forklore.models import parse_usda_response, is_drink_food
from forklore.core.grader import grade_food
from forklore.core.retrieval import is_coherent, is_composite_food
from forklore.core.customize import apply_additions
from forklore.core.combine   import grade_from_ingredients
from forklore.ai.refinement import refine_query
from forklore.ai.summary import write_summary
from forklore.ai.ingredients import suggest_ingredients
from forklore.data.usda_client import usda_search_all, pick_best_food


load_dotenv()


SIZE_OPTIONS = {
    "Small mug (250ml)": 250,
    "Medium cup (350ml)": 350,
    "Large cup (475ml)": 475,
    "Extra large (590ml)": 590,
    "Custom (enter ml)": None,
}


def show_grade(food):
    retrieve_food = parse_usda_response(food)
    if retrieve_food.brand:
        st.subheader(f"{retrieve_food.description} — {retrieve_food.brand}")
    else:
        st.subheader(retrieve_food.description)

    is_drink = is_drink_food(retrieve_food.description, retrieve_food.serving_unit)
    show_customization = is_drink

    if show_customization:
        st.write("☕ How did you make it? (optional)")
        size_choice = st.selectbox("How big is your drink?", list(SIZE_OPTIONS.keys()))
        drink_size = SIZE_OPTIONS[size_choice]
        if drink_size is None:
            drink_size = st.number_input("Enter size (ml)", min_value=1.0, value=350.0)
        added_sugar = st.number_input("Sugar you added (g)", min_value=0.0, value=0.0)
        added_fat = st.number_input("Cream/fat you added (g)", min_value=0.0, value=0.0)
        if added_sugar > 0 or added_fat > 0:
            retrieve_food = apply_additions(retrieve_food, drink_size, added_sugar, added_fat)
        if not st.button("Calculate grade", key="calc"):
            return

    _render_grade(retrieve_food, show_raw=food["description"])


def show_grade_nutrition(retrieve_food):
    """Grade an already-built Nutrition object (used for homemade dishes,
    which are combined from ingredients rather than a single USDA entry)."""
    st.subheader(retrieve_food.description)
    _render_grade(retrieve_food)


def _render_grade(retrieve_food, show_raw=None):
    """Shared: grade a Nutrition object, draw the badge, write the summary."""
    letter, color, pct = grade_food(retrieve_food)

    st.markdown(
        f"<div style='background:{color};color:white;padding:24px;"
        f"text-align:center;border-radius:8px;'>"
        f"<div style='font-size:64px;font-weight:bold;line-height:1;'>{letter}</div>"
        f"<div style='font-size:24px;'>{pct}%</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    with st.spinner("Writing summary..."):
        summary = write_summary(retrieve_food, letter, pct,
                                st.session_state.get("provider", "local"))
    st.write(summary)

    if show_raw:
        st.write(show_raw)
    st.write(retrieve_food)


st.title("🥗 Forklore")
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    use_claude = st.toggle("✨ Use Claude", value=False,
                           help="Claude gives cleaner explanations. Local runs free on your machine.")
    provider = "claude" if use_claude else "local"
    st.session_state.provider = provider

    # Little status indicator so it's clear which is active
    if provider == "claude":
        st.success("Using Claude ✨")
    else:
        st.info("Using Local 🖥️ (Model)")
food_input = st.text_input("Enter a food name to grade", placeholder="Big Mac")

if st.button("Analyze"):
    # Composite foods (burrito, sandwich) → ask restaurant or homemade FIRST,
    # before any USDA lookup.
    if is_composite_food(food_input):
        st.session_state.composite_food = food_input
        st.session_state.composite_choice = None
        st.session_state.homemade_ingredients = None
        st.session_state.refinement = None
        st.session_state.chosen_food = None
        st.session_state.chosen_food_obj = None
        st.session_state.all_foods = None
        st.session_state.was_ambiguous = False
    else:
        st.session_state.composite_food = None
        foods = usda_search_all(food_input)

        if not foods:
            st.error("No results found try again")
            st.session_state.refinement = None
            st.session_state.chosen_food = None
            st.session_state.all_foods = None
            st.session_state.was_ambiguous = False
        elif is_coherent(foods):
            # Coherent → auto-grab the best entry (prefers raw fruit/food).
            # Also save the full list so we can offer other versions below.
            st.session_state.chosen_food = pick_best_food(foods)
            st.session_state.all_foods = foods
            st.session_state.refinement = None
            st.session_state.was_ambiguous = False
        else:
            # Scattered (e.g. "coffee") → ask which kind
            st.session_state.refinement = refine_query(food_input, foods, provider)
            st.session_state.all_foods = foods
            st.session_state.chosen_food = None
            st.session_state.was_ambiguous = True

# Composite food: ask restaurant or homemade
if st.session_state.get("composite_food") and not st.session_state.get("composite_choice"):
    st.write(f"Is your {st.session_state.composite_food} from a restaurant, or homemade?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏪 Restaurant"):
            st.session_state.composite_choice = "restaurant"
    with col2:
        if st.button("🏠 Homemade"):
            st.session_state.composite_choice = "homemade"

# Restaurant → look it up in USDA like a normal food
if st.session_state.get("composite_choice") == "restaurant":
    foods = usda_search_all(st.session_state.composite_food)
    if foods:
        st.session_state.chosen_food = pick_best_food(foods, st.session_state.composite_food)
        st.session_state.all_foods = foods
        st.session_state.was_ambiguous = False
    else:
        st.error("No restaurant version found — try homemade.")
    st.session_state.composite_food = None
    st.session_state.composite_choice = None

# Homemade → suggest ingredients (with amounts), let user edit, then grade
if st.session_state.get("composite_choice") == "homemade":
    food_name = st.session_state.composite_food

    # Suggest ingredients (with grams) once, store as editable text
    if not st.session_state.get("homemade_ingredients"):
        with st.spinner("Thinking of typical ingredients..."):
            suggested = suggest_ingredients(food_name, provider)
        # format as "name, grams" per line
        lines = [f"{ing.name}, {int(ing.grams)}" for ing in suggested]
        st.session_state.homemade_ingredients = "\n".join(lines)

    st.write(f"Here's what's typically in a homemade {food_name} "
             f"(ingredient, grams) — edit amounts or items however you like:")
    text = st.text_area(
        "Ingredients (one per line — 'name, grams'):",
        value=st.session_state.homemade_ingredients,
        height=220,
        key="ingredient_box",
    )

    if st.button("Grade my homemade dish"):
        # Parse "name, grams" lines into (name, grams) tuples
        ingredients = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if "," in line:
                name, _, grams = line.rpartition(",")
                name = name.strip()
                try:
                    grams = float(grams.strip())
                except ValueError:
                    grams = 100.0          # default if they typed a bad number
            else:
                name, grams = line, 100.0  # no amount given → assume 100g
            if name:
                ingredients.append((name, grams))

        if not ingredients:
            st.error("Add at least one ingredient.")
        else:
            with st.spinner("Looking up each ingredient in USDA..."):
                combined, found, missing = grade_from_ingredients(ingredients)
            if not found:
                st.error("Couldn't find any of those ingredients in USDA — try simpler names.")
            else:
                if missing:
                    st.warning(f"Couldn't find in USDA (skipped): {', '.join(missing)}")
                st.session_state.chosen_food_obj = combined
                st.session_state.composite_food = None
                st.session_state.composite_choice = None
                st.session_state.homemade_ingredients = None

# Refinement question (for scattered searches like "coffee")
if st.session_state.get("refinement"):
    ref = st.session_state.refinement
    st.write(ref.question)
    for opt in ref.options:
        if opt.fdc_ids and st.button(opt.label, key=opt.label):
            chosen_id = opt.fdc_ids[0]
            for food in st.session_state.all_foods:
                if food.get("fdcId") == chosen_id:
                    st.session_state.chosen_food = food
                    st.session_state.refinement = None

    st.write("None of these? Type a different search:")
    new_search = st.text_input("Search again", key="refine_search")
    if new_search:
        new_foods = usda_search_all(new_search)
        if new_foods:
            st.session_state.chosen_food = pick_best_food(new_foods)
            st.session_state.all_foods = new_foods
            st.session_state.refinement = None
            st.session_state.was_ambiguous = False
        else:
            st.error("No results for that — try another search")

# Grade a homemade combined dish (already a Nutrition object)
if st.session_state.get("chosen_food_obj"):
    show_grade_nutrition(st.session_state.chosen_food_obj)
    st.session_state.chosen_food_obj = None

# Grade the chosen food (raw USDA entry)
if st.session_state.get("chosen_food"):
    show_grade(st.session_state.chosen_food)

# Offer OTHER versions of the food (e.g. banana chips, bread) in case the
# auto-picked raw one wasn't what they wanted. Collapsed so it's out of the way.
# Only show for non-ambiguous foods (ambiguous ones already use refinement).
if (st.session_state.get("chosen_food")
        and st.session_state.get("all_foods")
        and not st.session_state.get("was_ambiguous")):
    chosen = st.session_state.chosen_food
    others = [f for f in st.session_state.all_foods
              if f.get("fdcId") != chosen.get("fdcId")]
    if others:
        with st.expander("Did you mean a different version?"):
            for food in others[:6]:
                label = food.get("description", "Unknown")
                if st.button(label, key=f"alt_{food.get('fdcId')}"):
                    st.session_state.chosen_food = food