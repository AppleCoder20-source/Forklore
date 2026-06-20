import streamlit as st
import os
from dotenv import load_dotenv
from forklore.models import parse_usda_response, is_drink_food
from forklore.core.grader import grade_food, plus_minus_grade
from forklore.core.retrieval import is_coherent, is_composite_food
from forklore.core.customize import apply_additions
from forklore.core.combine   import grade_from_ingredients
from forklore.ai.refinement import refine_query
from forklore.ai.summary import write_summary
from forklore.ai.ingredients import suggest_ingredients
from forklore.data.usda_client import usda_search_all, pick_best_food
from forklore.data.fatsecret_search import search_food
from forklore.data.fatsecret_client import get_food_detail, parse_fatsecret_response
from forklore.ui.themes import THEMES


st.set_page_config(page_title="Forklore", page_icon="🍴", layout="centered")

load_dotenv()


SIZE_OPTIONS = {
    "Small (12 oz / 355ml)": 355,
    "Medium (16 oz / 473ml)": 473,
    "Large (20 oz / 590ml)": 590,
    "Extra Large (24 oz / 710ml)": 710,
    "Custom (enter ml)": None,
}


def _clear_all():
    """Reset every flow's session_state so a new search starts clean."""
    for key in ("composite_food", "composite_choice", "homemade_ingredients",
                "refinement", "chosen_food", "chosen_food_obj", "all_foods",
                "was_ambiguous", "fatsecret_results", "fatsecret_gradeable",
                "fatsecret_chosen_name"):
        st.session_state[key] = None


def run_search(query):
    """Route a query and set up the right flow. Used by Analyze and 'Other'."""
    _clear_all()

    # Composite foods (burrito, sandwich) -> ask restaurant or homemade FIRST.
    if is_composite_food(query):
        st.session_state.composite_food = query
        st.session_state.was_ambiguous = False
        return

    results, source = search_food(query, st.session_state.get("provider", "local"))

    if not results:
        st.error("No results found try again")
        return

    if source == "fatsecret":
        # Branded/chain item -> show a pick-list of menu items.
        st.session_state.fatsecret_results = results
        return

    # source == "usda" -> the original USDA flow, unchanged.
    if is_coherent(results):
        st.session_state.chosen_food = pick_best_food(results, query)
        st.session_state.all_foods = results
        st.session_state.was_ambiguous = False
    else:
        st.session_state.refinement = refine_query(
            query, results, st.session_state.get("provider", "local"))
        st.session_state.all_foods = results
        st.session_state.was_ambiguous = True


def show_grade(food):
    retrieve_food = parse_usda_response(food)
    if retrieve_food.brand:
        st.subheader(f"{retrieve_food.description} - {retrieve_food.brand}")
    else:
        st.subheader(retrieve_food.description)

    is_drink = is_drink_food(retrieve_food.description, retrieve_food.serving_unit)
    show_customization = is_drink

    if show_customization:
        st.write("How did you make it? (optional)")
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
        _render_grade(retrieve_food, show_raw=food["description"], drink_size_ml=drink_size)
        return

    _render_grade(retrieve_food, show_raw=food["description"])


def show_grade_nutrition(retrieve_food):
    """Grade an already-built Nutrition object (homemade dishes AND FatSecret
    items, which are parsed into a Nutrition rather than a raw USDA entry).
    For drinks, offer customization for EXTRA additions on top of the standard
    drink (e.g. an extra pump of syrup, extra cream) — the base drink's own
    sugar is already counted, so these are additions beyond it."""
    if retrieve_food.brand:
        st.subheader(f"{retrieve_food.description} - {retrieve_food.brand}")
    else:
        st.subheader(retrieve_food.description)

    is_drink = is_drink_food(retrieve_food.description, retrieve_food.serving_unit)

    if is_drink:
        st.write("Add anything extra you put in (optional)")
        size_choice = st.selectbox("How big is your drink?", list(SIZE_OPTIONS.keys()),
                                   key="fs_size")
        drink_size = SIZE_OPTIONS[size_choice]
        if drink_size is None:
            drink_size = st.number_input("Enter size (ml)", min_value=1.0, value=350.0,
                                         key="fs_size_custom")
        added_sugar = st.number_input("Extra sugar you added (g)", min_value=0.0, value=0.0,
                                      key="fs_sugar")
        added_fat = st.number_input("Extra cream/fat you added (g)", min_value=0.0, value=0.0,
                                    key="fs_fat")
        if added_sugar > 0 or added_fat > 0:
            retrieve_food = apply_additions(retrieve_food, drink_size, added_sugar, added_fat)
        if not st.button("Calculate grade", key="fs_calc"):
            return
        _render_grade(retrieve_food, drink_size_ml=drink_size)
        return

    _render_grade(retrieve_food)


def _render_grade(retrieve_food, show_raw=None, drink_size_ml=None):
    """Shared: grade a Nutrition object, draw the badge, write the summary.

    If drink_size_ml is given (a drink), also show the TOTAL sugar for that
    size as real-world context. The GRADE stays per-100ml (the Nutri-Grade
    standard, so package size can't game it), but the total tells the user the
    actual dose: a 330ml can of an 11g/100ml soda is ~36g sugar (~9 tsp)."""
    letter, color, pct = grade_food(retrieve_food)
    is_drink = is_drink_food(retrieve_food.description, retrieve_food.serving_unit)
    display_grade = plus_minus_grade(letter, pct, retrieve_food.bad_sugar_g, is_drink)

    # Plain-language label + icon for the badge header.
    label = {
        "A": "great choice", "B": "pretty good",
        "C": "so-so", "D": "not great", "F": "avoid",
    }[letter]
    icon = "✅" if letter in ("A", "B") else ("⚠️" if letter in ("C", "D") else "⛔")

    name = retrieve_food.description
    sub = retrieve_food.brand if retrieve_food.brand else "per 100g/ml"

    # Colored header bar — icon + name/label on the left, grade on the right.
    st.markdown(
        f"<div style='background:{color};border-radius:12px;padding:18px 22px;"
        f"display:flex;align-items:center;justify-content:space-between;'>"
        f"<div style='display:flex;align-items:center;gap:12px;'>"
        f"<span style='font-size:26px;'>{icon}</span>"
        f"<div><div style='font-size:13px;color:rgba(255,255,255,0.85);'>{name} · {sub}</div>"
        f"<div style='font-size:17px;font-weight:600;color:white;'>{label}</div></div></div>"
        f"<div style='text-align:center;line-height:1;'>"
        f"<div style='font-size:44px;font-weight:700;color:white;'>{display_grade}</div>"
        f"<div style='font-size:14px;color:rgba(255,255,255,0.85);'>{pct}%</div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Sugar", f"{retrieve_food.bad_sugar_g:.1f}g")
    m2.metric("Sat fat", f"{retrieve_food.saturated_fat_g:.1f}g")
    m3.metric("Sodium", f"{retrieve_food.sodium_mg:.0f}mg")

    # Real-world total sugar for the chosen drink size (context, not the grade).
    # The GRADE stays per-100ml (Nutri-Grade standard). This line shows the
    # actual dose and escalates the warning against daily limits: WHO ideal is
    # ~25g/day, US Dietary Guidelines cap ~50g/day. One big sugary drink can
    # blow past a whole day's budget, which the letter grade alone can't show.
    if drink_size_ml:
        total_sugar = retrieve_food.bad_sugar_g * (drink_size_ml / 100)
        teaspoons = total_sugar / 4          # ~4g sugar per teaspoon
        base = (f"At {int(drink_size_ml)}ml, that's about "
                f"**{total_sugar:.0f}g of sugar** (~{teaspoons:.0f} teaspoons).")

        if total_sugar > 50:                 # over the US daily max
            st.error(f"⚠️ {base} That's **more than a full day's recommended "
                     f"sugar limit** (~25-50g) in a single drink.")
        elif total_sugar >= 25:              # over the WHO ideal
            st.warning(f"{base} That's most of a day's recommended sugar "
                       f"(~25-50g) in one drink.")
        else:
            st.info(base)

    with st.spinner("Writing summary..."):
        summary = write_summary(retrieve_food, letter, pct,
                                st.session_state.get("provider", "local"))
    st.write(summary)

    # "Save this result" — snapshot the values (a plain dict, NOT the Nutrition
    # object) so later re-runs can't mutate it. Stored for the session only.
    st.session_state.setdefault("saved_items", [])
    snapshot = {
        "name": name, "display_grade": display_grade, "letter": letter,
        "pct": pct, "sugar": retrieve_food.bad_sugar_g,
    }
    already = snapshot in st.session_state.saved_items

    # Unique button key per render avoids Streamlit key collisions (which made
    # the button stop responding after navigating).
    st.session_state["_save_n"] = st.session_state.get("_save_n", 0) + 1
    key = f"save_{st.session_state['_save_n']}"

    if already:
        st.caption("✅ Saved to your list")
    elif st.button("💾 Save this result", key=key):
        st.session_state.saved_items.append(snapshot)
        st.rerun()                  # refresh now so the sidebar updates instantly

    if show_raw:
        st.write(show_raw)
    st.write(retrieve_food)



with st.sidebar:
    st.markdown("### Appearance")
    theme_name = st.selectbox("Theme", list(THEMES.keys()), index=0)

    # Saved results (this session). Each is a snapshot dict.
    saved = st.session_state.get("saved_items", [])
    if saved:
        st.markdown("### Saved")
        for item in saved:
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;"
                f"padding:6px 10px;background:rgba(0,0,0,0.04);border-radius:8px;"
                f"margin-bottom:5px;'>"
                f"<span style='font-size:12px;'>{item['name'][:22]}</span>"
                f"<span style='font-size:13px;font-weight:600;'>{item['display_grade']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        if st.button("Clear saved"):
            st.session_state.saved_items = []
T = THEMES[theme_name]

# Inject the chosen theme's CSS.
st.markdown(
    f"<style>"
    f".stApp{{background:{T['bg']};}}"
    f"div.stButton > button{{background:{T['btn']};color:{T['btn_text']};"
    f"border:none;border-radius:8px;font-weight:500;}}"
    f"div.stButton > button:hover{{background:{T['btn_hover']};color:{T['btn_text']};}}"
    f"div[data-testid='stTextInput'] input{{background:{T['input_bg']};"
    f"color:{T['text']};border:0.5px solid {T['input_border']};border-radius:8px;}}"
    f"section[data-testid='stSidebar']{{background:{T['sidebar']};}}"
    f"</style>",
    unsafe_allow_html=True,
)

# Branded header (brand color follows the theme).
st.markdown(
    f"<div style='display:flex;align-items:center;gap:10px;'>"
    f"<span style='font-size:32px;'>🍴</span>"
    f"<span style='font-size:30px;font-weight:700;letter-spacing:-0.5px;"
    f"color:{T['text']};'>Forklore</span>"
    f"</div>"
    f"<p style='color:{T['tagline']};font-size:14px;margin:2px 0 18px 42px;'>"
    f"know your food, grade by grade</p>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Settings")
    use_claude = st.toggle("Use Claude", value=False,
                           help="Claude gives cleaner explanations. Local runs free on your machine.")
    provider = "claude" if use_claude else "local"
    st.session_state.provider = provider

    if provider == "claude":
        st.success("Using Claude")
    else:
        st.info("Using Local (Model)")

food_input = st.text_input("Enter a food name to grade", placeholder="Big Mac")

if st.button("Analyze"):
    run_search(food_input)

# Composite food: ask restaurant or homemade
if st.session_state.get("composite_food") and not st.session_state.get("composite_choice"):
    st.write(f"Is your {st.session_state.composite_food} from a restaurant, or homemade?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Restaurant"):
            st.session_state.composite_choice = "restaurant"
    with col2:
        if st.button("Homemade"):
            st.session_state.composite_choice = "homemade"

# Restaurant -> look it up in USDA like a normal food
if st.session_state.get("composite_choice") == "restaurant":
    foods = usda_search_all(st.session_state.composite_food)
    if foods:
        st.session_state.chosen_food = pick_best_food(foods, st.session_state.composite_food)
        st.session_state.all_foods = foods
        st.session_state.was_ambiguous = False
    else:
        st.error("No restaurant version found - try homemade.")
    st.session_state.composite_food = None
    st.session_state.composite_choice = None

# Homemade -> suggest ingredients (with amounts), let user edit, then grade
if st.session_state.get("composite_choice") == "homemade":
    food_name = st.session_state.composite_food

    if not st.session_state.get("homemade_ingredients"):
        with st.spinner("Thinking of typical ingredients..."):
            suggested = suggest_ingredients(food_name, provider)
        lines = [f"{ing.name}, {int(ing.grams)}" for ing in suggested]
        st.session_state.homemade_ingredients = "\n".join(lines)

    st.write(f"Here's what's typically in a homemade {food_name} "
             f"(ingredient, grams) - edit amounts or items however you like:")
    text = st.text_area(
        "Ingredients (one per line - 'name, grams'):",
        value=st.session_state.homemade_ingredients,
        height=220,
        key="ingredient_box",
    )

    if st.button("Grade my homemade dish"):
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
                    grams = 100.0
            else:
                name, grams = line, 100.0
            if name:
                ingredients.append((name, grams))

        if not ingredients:
            st.error("Add at least one ingredient.")
        else:
            with st.spinner("Looking up each ingredient in USDA..."):
                combined, found, missing = grade_from_ingredients(ingredients)
            if not found:
                st.error("Couldn't find any of those ingredients in USDA - try simpler names.")
            else:
                if missing:
                    st.warning(f"Couldn't find in USDA (skipped): {', '.join(missing)}")
                st.session_state.chosen_food_obj = combined
                st.session_state.composite_food = None
                st.session_state.composite_choice = None
                st.session_state.homemade_ingredients = None

# FatSecret -> show a pick-list of menu items. To show ONLY items we can grade
# we fetch + parse each result up front and keep the ones with real per-100g
# data. This costs more API calls (one per result) but means every button in
# the list actually grades. The parsed Nutrition is cached so clicking doesn't
# re-fetch.
if st.session_state.get("fatsecret_results"):
    # Build the filtered, gradeable list once (cache it in session_state).
    # We ONLY keep items with REAL per-100g data from FatSecret. Weightless
    # items are dropped — we never substitute generic/made-up data for a
    # specific branded item (grounding principle: real data or nothing).
    if st.session_state.get("fatsecret_gradeable") is None:
        gradeable = []
        with st.spinner("Checking which items have nutrition data..."):
            for food in st.session_state.fatsecret_results[:10]:
                detail = get_food_detail(food.food_id)
                nutrition = parse_fatsecret_response(detail)
                if nutrition is not None:        # only real per-100g data
                    gradeable.append((food.food_name, nutrition))
        st.session_state.fatsecret_gradeable = gradeable

    gradeable = st.session_state.fatsecret_gradeable

    if not gradeable:
        st.error("None of those items have detailed nutrition data - try a "
                 "different or more generic search.")
    else:
        st.write("Which item did you mean?")
        for i, (name, nutrition) in enumerate(gradeable[:6]):
            if st.button(name, key=f"fs_{i}"):
                st.session_state.chosen_food_obj = nutrition
                st.session_state.fatsecret_chosen_name = name
                # Keep fatsecret_gradeable so the "different version" expander
                # can offer the other items. Clear only the pick-list trigger.
                st.session_state.fatsecret_results = None

    # "Other" - type a different search, re-run the router (USDA or FatSecret).
    st.write("Not listed? Type a different search:")
    other = st.text_input("Search again", key="fs_other")
    if other:
        run_search(other)

# Refinement question (for scattered USDA searches like "coffee")
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
        run_search(new_search)

# Grade a Nutrition object (homemade dish OR FatSecret item).
# Note: we do NOT clear chosen_food_obj here, because the drink customization
# box re-runs the script when the user changes an input — clearing it would
# make the drink vanish mid-customization. It's cleared on the next search
# via _clear_all().
if st.session_state.get("chosen_food_obj"):
    show_grade_nutrition(st.session_state.chosen_food_obj)

    # Offer OTHER FatSecret versions from the same search (mirrors the USDA
    # expander). Only the items that survived filtering (real per-100g data).
    fs_grade = st.session_state.get("fatsecret_gradeable")
    chosen_name = st.session_state.get("fatsecret_chosen_name")
    if fs_grade and chosen_name:
        others = [(n, nut) for (n, nut) in fs_grade if n != chosen_name]
        if others:
            with st.expander("Did you mean a different version?"):
                for j, (name, nutrition) in enumerate(others[:10]):
                    if st.button(name, key=f"fsalt_{j}"):
                        st.session_state.chosen_food_obj = nutrition
                        st.session_state.fatsecret_chosen_name = name

# Grade the chosen food (raw USDA entry)
if st.session_state.get("chosen_food"):
    show_grade(st.session_state.chosen_food)

# Offer OTHER versions (USDA only). Collapsed, out of the way.
if (st.session_state.get("chosen_food")
        and st.session_state.get("all_foods")
        and not st.session_state.get("was_ambiguous")):
    chosen = st.session_state.chosen_food
    others = [f for f in st.session_state.all_foods
              if f.get("fdcId") != chosen.get("fdcId")]
    if others:
        with st.expander("Did you mean a different version?"):
            for food in others[:15]:
                description = food.get("description", "Unknown")
                brand = food.get("brandOwner", "")
                label = f"{description} - {brand}" if brand else description
                if st.button(label, key=f"alt_{food.get('fdcId')}"):
                    st.session_state.chosen_food = food