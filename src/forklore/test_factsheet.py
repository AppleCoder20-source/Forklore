"""
Branded-item coverage scan — run from your project root:
    uv run python scan_branded.py

Searches broad terms, keeps only BRANDED items (food_type == "Brand"),
and reports which have usable weight data vs. which are weightless.
FatSecret tags each food as "Brand" or "Generic" via food_type, so we filter
on that real field rather than guessing from the name.
"""

from collections import Counter
from forklore.data.fatsecret_client import search_fatsecret, get_food_detail


SEARCH_TERMS = [
     "Starbucks Frappuccino",
    "Starbucks Latte",
    "Starbucks Caramel Macchiato",
    "Starbucks Mocha",
    "Starbucks Chai Latte",
    "Starbucks Iced Coffee",
]

RESULTS_PER_TERM = 10


def servings_of(detail):
    ss = detail.servings.serving
    if not isinstance(ss, list):
        ss = [ss]
    return ss


def classify(detail):
    servs = servings_of(detail)
    for s in servs:
        if s.metric_serving_unit == "g" and s.metric_serving_amount and float(s.metric_serving_amount) == 100:
            return "has_100g"
    for s in servs:
        if s.metric_serving_unit == "g" and s.metric_serving_amount:
            return "has_grams"
    for s in servs:
        if s.metric_serving_unit in ("ml", "oz", "fl oz") and s.metric_serving_amount:
            return "volume_only"
    return "no_weight"


def main():
    tally = Counter()
    weightless = []      # the branded items that lack weight
    has_weight = []      # the branded items that DO have weight
    seen = set()
    total_branded = 0

    for i, term in enumerate(SEARCH_TERMS, 1):
        print(f"[{i}/{len(SEARCH_TERMS)}] scanning '{term}'...")
        try:
            results = search_fatsecret(term)
        except Exception as e:
            print(f"    search failed: {e}")
            continue

        for r in results[:RESULTS_PER_TERM]:
            # Keep ONLY branded items
            if r.food_type != "Brand":
                continue
            if r.food_id in seen:
                continue
            seen.add(r.food_id)

            detail = get_food_detail(r.food_id)
            if detail is None:
                tally["detail_fail"] += 1
                total_branded += 1
                continue

            verdict = classify(detail)
            tally[verdict] += 1
            total_branded += 1

            label = f"{r.brand_name or '?'} - {r.food_name}"
            if verdict in ("has_100g", "has_grams"):
                has_weight.append(label)
            else:
                weightless.append((label, verdict))

    print("\n" + "=" * 60)
    print(f"BRANDED ITEMS CHECKED: {total_branded}")
    print("=" * 60)
    for cat in ["has_100g", "has_grams", "volume_only", "no_weight", "detail_fail"]:
        c = tally.get(cat, 0)
        if c:
            print(f"  {cat:<14} {c:>4}  ({c/total_branded*100:.0f}%)")

    gradeable = tally.get("has_100g", 0) + tally.get("has_grams", 0)
    print(f"\n  Branded gradeable directly: {gradeable}/{total_branded} "
          f"({gradeable/total_branded*100:.0f}%)")
    print(f"  Branded needing fallback:   {total_branded-gradeable}/{total_branded} "
          f"({(total_branded-gradeable)/total_branded*100:.0f}%)")

    print("\n--- BRANDED ITEMS THAT GRADE DIRECTLY ---")
    for x in has_weight:
        print(f"    OK   {x}")

    print("\n--- BRANDED ITEMS THAT NEED FALLBACK (weightless / volume) ---")
    for label, verdict in weightless:
        print(f"    {verdict:<11} {label}")


if __name__ == "__main__":
    main()