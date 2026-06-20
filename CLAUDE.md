# CLAUDE.md — NutriGrade (a.k.a. Forklore)

> A step-by-step roadmap for building NutriGrade / Forklore, an LLM-powered
> food & drink nutrition analyzer. Read top to bottom, do each step before
> the next.
>
> **Stack:** Streamlit · LangChain + Ollama (local) / Anthropic Claude · USDA FoodData Central + FatSecret · SQLite · uv
>
> *Note on names:* the package and app are **Forklore**; this spec was written
> as **NutriGrade**. Both names refer to the same project.

---

## How to use this doc

The roadmap is in **Phases 0–4**, written as numbered steps you do in
order. Heavy specifications live in **appendices (§A1–§A15)** at the
bottom — refer to them when a step points there.

**Phases:**
0. **Setup** — install everything, verify it works
1. **Walking skeleton** — one functional Streamlit file that runs end-to-end (this is the MVP)
1.5. **Handle the edge cases** — refinement (ambiguous queries) + rescue agent (unrecognized queries)
2. **Make it real** — expanded nutrition model, concerns analysis, additive detection, history, cache
3. **Refactor** — split into modules, add tests, polish UI
4. **Stretch goals** — FastAPI layer, deployment notes

You'll have a working **MVP** by the end of Phase 1 — a real product that
takes a food, grades it, and explains the grade. Phase 1.5 then makes it
feel smart by handling the two big edge cases (ambiguous and unrecognized
queries). Phases 2–4 build on that foundation to make it substantive and
presentation-ready. See the Phase 1 header for a full explanation of what
the MVP is and why you build it first.

### Build status at a glance

This roadmap is largely built. Quick status so you know what's live vs. planned:

| Area | Status |
|---|---|
| Phase 0 setup | ✅ Built |
| Phase 1 walking skeleton | ✅ Built |
| Refinement loop (§A1) | ✅ Built |
| Customization (real additions re-graded) | ✅ Built |
| Composite / homemade dishes | ✅ Built |
| FatSecret integration (branded items) | ✅ Built *(added beyond original spec)* |
| Dual-provider local/Claude (§A14) | ✅ Built |
| Grading rubric | ✅ Built — **now Nutri-Grade bands + per-100g thresholds, not FDA-DV math (see §A6)** |
| +/- grade modifiers | ✅ Built *(added beyond original spec)* |
| Themed result UI, 13 themes, save-results | ✅ Built *(added beyond original spec — see §A16)* |
| Phase 3 module refactor | ✅ Built |
| Rescue agent (§A12) | ⏳ Planned |
| ReAct prompting (§A13) | ⏳ Planned |
| Concerns/positives analysis (§A8) | ⏳ Planned |
| Additive detection (§A9) | ⏳ Planned |
| SQLite history + cache (§A2, §A3) | ⏳ Planned |
| FastAPI layer (§A5) | ⏳ Planned |

### Architecture at a glance

NutriGrade is a **deterministic pipeline with one agentic exception**:

```
user query → search USDA/FatSecret → grade → analyze → render
                  │
                  └─ if 0 results or weak match → rescue agent (§A12) [planned]
                  └─ if scattered results → refinement (§A1)
```

Everything is deterministic except the rescue agent (planned), which uses
**ReAct prompting** (§A13) to decide between rewriting the query,
asking the user, or giving up. The analysis chain (§A8) also uses
ReAct for better-ordered output.

### How to navigate this doc

- **Building?** Read phases top-to-bottom. Follow appendix pointers as you hit them.
- **Looking up a specific thing?** Use the **appendix index** at the start of the Appendices section.
- **Need fast facts?** Each appendix starts with a **Quick reference** box.
- **Want the why behind a design choice?** Read the narrative below the quick reference.

### Conventions used in this doc

- **`§AN`** references appendix N (e.g. §A12 = Query Rescue Agent)
- **`Step N`** references a build step in the phase roadmap
- **Pseudocode** in appendices is illustrative — actual implementations may differ in small ways

---

## The grounding principle

> **Real data comes from a trusted source. The AI only interprets it — it never invents it.**

Every nutrition number comes from USDA or FatSecret. The LLM only clusters
ambiguous results, writes the plain-language explanation, and suggests
(editable) ingredients for homemade dishes. It never produces a nutrition
value, never substitutes generic data for a specific branded item, and never
guesses a grade. If real data isn't available, the app shows nothing rather
than fabricate. This rule is the spine of the project.

---

## Why everything is per 100g/ml — the foundation

Every food is normalized to **per 100 grams** (solids) or **per 100 millilitres**
(drinks) before grading, because every threshold in the grader assumes it.

- **Same food, different package:** a 100g yogurt cup (8g sugar) and a 500g
  container of the *same* yogurt (40g sugar) are identical — but raw numbers
  would grade the big one worse, purely for being bigger. Per-100 makes both
  "8g per 100g."
- **Different foods, same raw number:** 30g of nuts with 6g sugar and a 300g
  sports drink with 6g sugar *tie* on the raw number, but normalize to 20g/100g
  vs 2g/100ml — wildly different. The common ruler separates them.
- **Why some items can't be graded:** converting to per-100g needs the item's
  **weight**. Many branded items list nutrition per "1 donut" / "1 grande" with
  **no weight**, so they can't be normalized — they're **dropped** rather than
  graded on a guessed weight. Real data or nothing.


---

# PHASE 0 — Setup

Boring but necessary. Don't skip ahead until each step's "Verify"
passes.

## Step 1: Install Ollama for Windows

1. Go to <https://ollama.com/download/windows>
2. Run the installer
3. Ollama runs as a background service after install

**Verify:** In Git Bash:
```bash
ollama --version
```

## Step 2: Pull the model

```bash
ollama pull llama3.2:3b
```
~2 GB download.

**Verify:**
```bash
ollama run llama3.2:3b
```
You'll get a `>>>` prompt. Type a question, get an answer, Ctrl+D to exit.

## Step 3: Get a free USDA API key

1. <https://fdc.nal.usda.gov/api-key-signup>
2. They email the key instantly
3. Save it — you'll paste it into `.env` in Step 8

## Step 4: Install uv

In **PowerShell** (one-time):
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close Git Bash and reopen so it picks up PATH.

**Verify:** `uv --version`

## Step 5: Verify Git is configured

```bash
git --version
git config user.name
git config user.email
```

If empty, set them:
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Step 6: Make the project folder

Pick a folder you keep code in:
```bash
cd ~/projects     # or wherever
mkdir forklore
cd forklore
```

## Step 7: Bootstrap the project with uv

```bash
uv init . --package
uv python pin 3.11
uv add streamlit requests pydantic pydantic-settings langchain langchain-ollama langchain-anthropic python-dotenv
```

This creates `pyproject.toml`, `uv.lock`, `.python-version`,
`src/forklore/`, and `.venv/`. The `langchain-anthropic` dependency
enables the dual-provider toggle (see §A14) — it's used at runtime
only when the user switches to Claude in the sidebar.

## Step 8: Create `.env` and `.env.example`

Create `.env`:
```
USDA_API_KEY=paste_your_key_here
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Branded items (Starbucks, Dunkin, etc.)
FATSECRET_KEY=
FATSECRET_SECRET=

# Optional — enables the Claude provider in the sidebar (see §A14)
# If not set, only the local option appears.
ANTHROPIC_API_KEY=
```

Replace the USDA placeholder with your real key. Add FatSecret credentials
for branded coverage. Leave `ANTHROPIC_API_KEY` empty if you only want local.

Also create `.env.example` with the same contents but leave all
values empty — this one gets committed to Git.

## Step 9: Set up `.gitignore`

```bash
echo ".venv/
__pycache__/
.env
forklore.db
*.pyc
.pytest_cache/" > .gitignore
```

Note: `ollama_test.py` and `usda_test.py` (which you'll create in
Phase 1) live at the project root and **are committed to Git** as
useful debugging tools. Don't add them to `.gitignore`.

## Step 10: Open VS Code

```bash
code .
```

Set Git Bash as the default terminal:
1. `Ctrl+Shift+P`
2. "Terminal: Select Default Profile"
3. Pick "Git Bash"

## ✅ Phase 0 complete

You should have:
- ✅ Ollama installed, model pulled, working
- ✅ USDA API key in `.env`
- ✅ uv installed
- ✅ Git configured
- ✅ Project folder bootstrapped with all dependencies
- ✅ VS Code open with Git Bash terminal

---

# PHASE 1 — Walking Skeleton

> **This phase is the MVP.** Keep it minimal on purpose — food input →
> USDA lookup → grade → LLM explanation, all in one Streamlit file. No
> refinement, rescue, caching, history, or polish; the edge cases come
> next in Phase 1.5, and the richer features in Phase 2. The goal here is
> to prove the core flow works end to end and observe how USDA actually
> behaves before adding complexity on top.

Goal: **one functional Streamlit file that runs end-to-end.** User types a
food, sees a grade with a summary. Everything in `src/forklore/app.py`.
We'll refactor in Phase 3.

The order of steps in this phase is intentional:
- **First**, verify Ollama works (Steps 11–12) — prove the LLM stack is solid
- **Then** verify USDA works (Steps 13–14) — prove the data source is solid
- **Then** connect them with a Streamlit UI (Steps 15–17) — wire it all together
- **Then** add grading and the final flow (Steps 18–20)

This order lets you confirm each external dependency works in isolation
before stacking complexity. If Ollama is broken, you find out on day 1
instead of day 5.

## Step 11: Write a tiny Ollama test script

Before touching Streamlit or USDA, prove your LLM works.

Create `ollama_test.py` at the project root (NOT inside `src/`):

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.2,
)

response = llm.invoke("What are the main nutrients in a banana? Answer in one sentence.")
print(response.content)
```

Run it:
```bash
uv run python ollama_test.py
```

**First call is slow** (5–10 seconds while the model loads into VRAM).
That's normal. Subsequent calls are fast.

**This is your first real checkpoint.** If you see a sensible answer
about bananas, your LLM stack works end-to-end. Big win — celebrate.

If you get an error:
- Connection refused → Ollama isn't running. Search "Ollama" in Start
  menu, launch it.
- Module not found → run `uv sync` again.
- Hangs forever → check that `ollama run llama3.2:3b` works from Git
  Bash directly. If that fails, the model didn't pull correctly.

## Step 12: Try a structured-output test

The real project uses structured output (LangChain's `with_structured_output`)
heavily. Worth testing it works on this small model before going further.

Update `ollama_test.py`:

```python
from langchain_ollama import ChatOllama
from pydantic import BaseModel

class FoodFact(BaseModel):
    food: str
    main_nutrients: list[str]
    is_healthy: bool

llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.2,
)

structured_llm = llm.with_structured_output(FoodFact)
result = structured_llm.invoke("Give me a quick fact about bananas.")
print(result)
print(f"Food: {result.food}")
print(f"Healthy: {result.is_healthy}")
```

Run it again. You should get a `FoodFact` object back with the fields
filled in. This proves the model can reliably return structured data —
which is what the refinement and analysis chains depend on.

If this works, **keep `ollama_test.py` around forever as a debugging
tool.** When you hit weird behavior later, you can run this script to
confirm Ollama itself is fine — narrowing down where the bug lives.

## Step 13: Write a tiny USDA test script

Now do the same thing for USDA. Create `usda_test.py` at the project root:

```python
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

response = requests.get(
    "https://api.nal.usda.gov/fdc/v1/foods/search",
    params={
        "query": "big mac",
        "api_key": os.getenv("USDA_API_KEY"),
        "pageSize": 3,
    },
    timeout=15,
)
response.raise_for_status()
data = response.json()

print(f"Found {len(data['foods'])} results")
for food in data["foods"]:
    print(f"  - {food['description']} (id: {food['fdcId']}, type: {food.get('dataType')})")

# Print full details of the top result
print("\nTop result, full data:")
print(json.dumps(data["foods"][0], indent=2)[:2000])  # truncate to first 2000 chars
```

Run it:
```bash
uv run python usda_test.py
```

You should see real nutrition data. Note the `dataType` field on each
result (`Branded`, `Foundation`, `Survey (FNDDS)`, etc.) — important
for later.

## Step 14: Try a few different queries

Still in `usda_test.py`, test a variety of inputs to understand USDA's
quirks:

- `"banana"` → should return raw banana data
- `"big mac"` → should return McDonald's branded entries
- `"coffee"` → should return many results, mostly generic
- `"xyzznotafood"` → should return zero results

Look at:
- Which queries return useful data
- Which return junk
- Whether `ingredients` field is present (it's there for branded foods,
  often missing for generic ones)
- How the `foodNutrients` array varies in size between foods

This is reconnaissance. You're getting a feel for what USDA actually
returns before you build anything on top of it.

**Keep `usda_test.py` around as a debugging tool too.**

## Step 15: Hello world Streamlit page

Now that both external dependencies are confirmed working, start the
real app. In `src/forklore/app.py`:

```python
import streamlit as st

st.title("🍴 Forklore")
st.write("Type a food to see its nutrition grade.")
```

Run it:
```bash
uv run streamlit run src/forklore/app.py
```

Browser opens at `http://localhost:8501`. **Second checkpoint** — if
you see the title, your Streamlit setup works.

## Step 16: Add input box and button

```python
import streamlit as st

st.title("🍴 Forklore")
query = st.text_input("Food name", placeholder="e.g. big mac")
if st.button("Analyze"):
    st.write(f"You typed: {query}")
```

Save → Streamlit auto-reloads. Type something, click button, see echo.

## Step 17: Wire in the USDA call

Move the USDA logic from your test script into `app.py`. Above your
Streamlit code:

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()
USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

def fetch_from_usda(query: str) -> dict | None:
    response = requests.get(
        USDA_URL,
        params={"query": query, "api_key": USDA_API_KEY, "pageSize": 5},
        timeout=15,
    )
    response.raise_for_status()
    foods = response.json().get("foods", [])
    return foods[0] if foods else None
```

Update the button block:
```python
if st.button("Analyze"):
    food = fetch_from_usda(query)
    if food is None:
        st.error("No results from USDA")
    else:
        st.write(f"Found: {food['description']}")
        st.json(food)
```

Now Streamlit + USDA are connected. Type "banana" → see USDA's response
in the browser.

## Step 18: Add the Pydantic `Nutrition` model and parse USDA's response

Now we shape USDA's messy JSON into clean data. Above your USDA function:

```python
from pydantic import BaseModel, NonNegativeFloat

class Nutrition(BaseModel):
    description: str
    calories: NonNegativeFloat = 0
    sodium_mg: NonNegativeFloat = 0
    saturated_fat_g: NonNegativeFloat = 0
    trans_fat_g: NonNegativeFloat = 0
    sugar_g: NonNegativeFloat = 0
    fiber_g: NonNegativeFloat = 0
    protein_g: NonNegativeFloat = 0

NUTRIENT_IDS = {
    1008: "calories",
    1093: "sodium_mg",
    1258: "saturated_fat_g",
    1257: "trans_fat_g",
    1235: "sugar_g",
    1079: "fiber_g",
    1003: "protein_g",
}

def parse_usda_response(food: dict) -> Nutrition:
    values = {field: 0.0 for field in NUTRIENT_IDS.values()}
    total_sugar = 0.0
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrientId")
        val = n.get("value", 0) or 0
        if nid in NUTRIENT_IDS:
            values[NUTRIENT_IDS[nid]] = val
        if nid == 2000:
            total_sugar = val
    if values["sugar_g"] == 0:        # fall back to total sugar if no added
        values["sugar_g"] = total_sugar
    return Nutrition(description=food["description"], **values)
```

Update the button block to display parsed nutrition.

## Step 19: Add the grading function

> **⚠️ Updated:** the real grader no longer uses the FDA-Daily-Value math
> shown in early drafts. It uses **fixed per-100g thresholds** for solids and
> **Singapore Nutri-Grade bands** for drinks. The current, accurate rubric is
> in **§A6** — build from that. The original DV-based snippet is kept in §A6
> under "earlier design" for history only.

The walking-skeleton grader returns `(letter, color, pct)` and branches on
drink vs. solid. See §A6 for the full current code.

```python
def grade_food(n: Nutrition) -> tuple[str, str, int]:
    """Return (letter_grade, hex_color, percentage_0_to_100).
    Drinks → Nutri-Grade bands (worse of sugar & sat fat per 100ml).
    Solids → averaged per-100g nutrient scores + hard caps."""
    if is_drink_food(n.description, n.serving_unit):
        return _grade_drink(n)
    # ... solid-food scoring + caps (see §A6) ...
```

Type "big mac" → see grade. Type "banana" → see grade. **The app is real.**

## Step 20: Add the LLM summary

Reuse the LLM connection pattern from your `ollama_test.py`. Add to `app.py`:

```python
from langchain_ollama import ChatOllama

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

@st.cache_resource
def get_llm():
    return ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_HOST, temperature=0.2)

def write_summary(nutrition: Nutrition, letter: str, pct: int) -> str:
    llm = get_llm()
    prompt = f"""You are a friendly nutrition assistant.
Write ONE short sentence (under 30 words) about why this food got this grade.
Mention the 1-2 nutrients that drove the grade.
Use the actual numbers below. Don't invent values. No medical advice.

Food: {nutrition.description}
Grade: {letter} ({pct}%)
Sodium: {nutrition.sodium_mg} mg
Saturated fat: {nutrition.saturated_fat_g} g
Sugar: {nutrition.sugar_g} g
Trans fat: {nutrition.trans_fat_g} g
Fiber: {nutrition.fiber_g} g
Protein: {nutrition.protein_g} g
"""
    return llm.invoke(prompt).content.strip()
```

Update the button block to wrap everything in a spinner and show the
summary below the grade badge.

## ✅ Phase 1 complete

End-to-end flow works: **input → USDA → grade → LLM summary → colored display.**

You also have two standalone scratch scripts (`ollama_test.py` and
`usda_test.py`) that you can keep around as debugging tools.

Commit to Git:
```bash
git init
git add .
git commit -m "feat: walking skeleton — end-to-end flow working"
```

Stop here. Don't add more features yet. Take a moment.

---

# PHASE 1.5 — Handle the Edge Cases

> **Why this is its own phase.** The MVP (Phase 1) works, but it's
> fragile: type "coffee" and it blindly grades the first result; type
> "PSL" and it dead-ends. This phase makes the app feel *smart* instead
> of brittle by handling the two big edge cases — ambiguous queries and
> unrecognized queries. These are the highest-value additions after the
> MVP, which is why they come before the Phase 2 polish features.
>
> **Status:** the refinement loop (Step 21) is **built**. The rescue agent
> (Step 21.5) is **planned, not yet built.**

This phase introduces a small amount of structure the MVP didn't need:
a `core/retrieval.py` for the two checks, two new LLM chains, and real
branching in the analyzer. Budget ~3–4 hours.

## Step 21: Refinement loop (search-first) ✅ Built

When USDA returns scattered results for a query (e.g. "coffee" hits
black coffee, lattes, and frappuccinos all at once), the LLM clusters
those real results into a focused question with 4–6 grouped options.
Hard cap of 2 rounds.

Crucially, the LLM **never invents options** — it only organizes the
USDA results that actually came back. Every option carries the FDC IDs
it represents, so user picks resolve directly to real database entries.

The trigger is the **diversity check**: if the calorie spread across
the top results is too wide (more than ~3x), the results are too varied
to assume, and refinement fires. If they're coherent, the app grades
the top result directly.

**See §A1** for the full spec — including the diversity check that
decides when refinement is needed and the prompt design that grounds
every option in real data.

## Step 21.5: Query rescue agent ⏳ Planned

> **Status: not yet built.** This is a designed-but-unbuilt feature. The
> spec below is the intended design.

The one part of the app that's genuinely **agentic** — when USDA's
database doesn't recognize the user's phrasing (e.g. "PSL" instead of
"pumpkin spice latte") or returns weak matches (e.g. "korean fried
chicken" returning plain "Chicken, fried"), the LLM gets to decide
what to do next:

- **Rewrite** silently if the fix is obvious
- **Ask** the user to clarify if the query is ambiguous
- **Give up** cleanly if no rewrite would help

The triggers are the **zero-results check** (USDA returned nothing) and
the **weak-match check** (the query's key words don't appear in any
result). Either one routes to the rescue agent.

Hard cap of 2 rounds. The LLM makes the decision; the analyzer
respects it.

This is the *only* place in the app where the LLM controls flow
rather than just generating text in a slot. Scoped tightly on purpose.

**See §A12** for the full spec, and **§A13** for the ReAct prompting
the rescue agent uses.

---

# PHASE 1.6 — Customization & Composite Foods ✅ Built

> *Added beyond the original phase numbering — these features were built
> after refinement and before the Phase 2 polish set.*

## Customization (drinks)

Drinks depend on how they're made. Rather than guess, the app lets the user
enter **what they actually added** — cup size, added sugar, added cream — and
the **real grader recalculates** on the per-100ml basis:

```
30g sugar added to a 250ml cup → 30 ÷ (250/100) = +12g per 100ml
```

`apply_additions` (in `core/customize.py`) **returns a copy** of the Nutrition
object (`model_copy(update=...)`) — it must never mutate the cached object,
because Streamlit re-runs the whole script each interaction and a mutated
object compounds (this caused grades to climb). The AI never re-grades from a
vague description; the user supplies real amounts, the real grader does the math.

## Composite / homemade dishes

For composite foods (taco, burrito, sandwich, bowl), the app asks
**restaurant or homemade?**

- **Restaurant** → look it up and grade that entry.
- **Homemade** → the AI suggests a typical ingredient list with realistic gram
  amounts (editable), then each ingredient is looked up and **combined weighted
  by amount** (`core/combine.py`):

```
each ingredient: per-100g nutrients × (its grams / 100) → contribution
whole dish:      sum contributions ÷ total grams × 100   → per-100g profile
```

Weighting by amount prevents a small amount of an intense ingredient (30g
cheese) from counting as much as a large amount of a mild one (100g rice).

---

# PHASE 2 — Make It Real

> **Status:** mostly **planned**. The concerns analysis, additive detection,
> and SQLite history/cache below are designed but **not yet built**. The
> nutrition model was partially expanded. FatSecret integration (not in the
> original Phase 2) **was** built — see "FatSecret" note at the end of this phase.

This is where NutriGrade gains its richer features. With the edge cases
already handled in Phase 1.5, this phase is about depth: a fuller
nutrition model, the concerns analysis, additive detection, history,
and caching.

## Step 22: Expand the nutrition data model ⏳ Partial

Switch `Nutrition` to track the rubric inputs **plus** every other
nutrient USDA returns (vitamins, minerals, etc.) in a flexible dict.
The grader still uses named fields; the UI displays everything.

**See §A7** for the full nutrient mapping and the `other_nutrients`
dict pattern.

## Step 23: Add the Concerns analysis ⏳ Planned

This is the headline feature. **One** LLM chain (`analysis_chain`)
takes the graded food + ingredients string and produces a structured
output with:
- The overall summary sentence (replaces the simple `write_summary`)
- A list of concerns, each with its own contextual explanation
- Quantity comparisons grounded in real numbers (e.g. "230g sugar = 50 teaspoons")

The chain returns its output as a Pydantic model so the UI can render
it however it wants.

**Per-nutrient explanations are generated upfront, not on click.** They
live inside the analysis output. UI just displays them.

**Only flags unhealthy nutrients (yellow/orange/red).** Green ones
aren't explained — they're not concerns.

**See §A8** for the full chain spec.

## Step 24: Add additive/dye detection ⏳ Planned

Hard-coded list of additives (Red 40, Yellow 5, BHA, BHT, sodium
nitrate, aspartame, HFCS, etc.). Regex-matched against USDA's
`ingredients` field when present. Each detected additive becomes another
"concern" in the analysis output.

USDA doesn't always return ingredient data — when missing, just skip
the additive scan for that food. Honest behavior is better than fake
detection.

**See §A9** for the additive list and detection logic.

## Step 25: SQLite history ⏳ Planned

Save every successful lookup so the sidebar can show recent searches.

**See §A2** for the schema and repo class.

## Step 26: SQLite cache ⏳ Planned

Cache the **full graded report** (nutrition + concerns + LLM summary +
explanations) keyed by the final search query. First lookup of a food
is "Fresh from USDA"; second lookup is "Loaded from cache" and is
instant.

The cache is what makes the app feel snappy and what saves your demo
when WiFi is flaky.

**See §A3** for the schema and repo class.

## FatSecret integration ✅ Built *(added beyond the original spec)*

USDA lacks most real chain menus (it has McDonald's, but not actual Starbucks
or Dunkin drinks). To cover branded/chain items, the app also integrates
**FatSecret**:

- `search_food(query)` returns `(results, source)` — source is `"usda"` or
  `"fatsecret"`. A routing step decides which source fits the query.
- USDA holds generics/grocery; FatSecret holds branded/chain items.
- FatSecret items are parsed into the same `Nutrition` model.
- **Data-quality filtering:** many FatSecret branded items are "weightless"
  (no per-100 weight). Those are filtered out of the pick-list — only items
  with real per-100 data are shown (real data or nothing).
- Lesson: search the *food*, not the *brand* on USDA; for a chain item, search
  e.g. "Starbucks latte" so it routes to FatSecret.

## ✅ Phase 2 status

Built: FatSecret integration (branded items), partial model expansion. Planned:
concerns analysis, additive detection, SQLite history + cache.

---

# PHASE 3 — Refactor ✅ Built

The single `app.py` got big, so it's split into proper modules.

## Step 27: Split into the grouped module structure ✅ Built

Pieces of `app.py` moved into themed folders:
- **`core/`** — pure logic (no I/O): grader, retrieval, customize, combine
- **`data/`** — anything that talks to USDA / FatSecret / the network
- **`ai/`** — LLM stuff: llm factory, refinement, ingredients, summary
- **`ui/`** — presentation: themes (and result-card helpers)
- Top-level `app.py` + `models.py`

**See §A4** for the full target layout and a migration table. (The real tree
differs slightly from §A4 — there's no `analyzer.py`/`api.py` yet, and `ui/`
was added; see the "Architecture (real)" note below.)

### Architecture (real, as built)

```
src/forklore/
├── app.py                 # Streamlit UI + orchestration
├── models.py              # Nutrition model, USDA/FatSecret parsers, is_drink_food
├── core/
│   ├── grader.py          # per-100g solids + Nutri-Grade drinks + caps + plus_minus_grade
│   ├── retrieval.py       # is_coherent (diversity check) + composite detection
│   ├── customize.py       # apply_additions (returns a copy)
│   └── combine.py         # grade_from_ingredients (weighted)
├── ai/
│   ├── llm.py             # get_llm factory (local / Claude)
│   ├── refinement.py      # ambiguity clustering
│   ├── ingredients.py     # ingredient suggestion (homemade)
│   └── summary.py         # plain-language explanation
├── data/
│   ├── usda_client.py     # USDA search + pick_best_food
│   ├── fatsecret_client.py
│   └── fatsecret_search.py # source routing
└── ui/
    └── themes.py          # 13 color themes
```

## Step 28: Add tests ⏳ Partial

```bash
uv add --dev pytest pytest-cov
```

Mirror the source folder structure inside `tests/`. **Don't** test against
live LLM or live USDA — use fakes. (Coverage scans/scripts exist for the
grader and data quality; full mirrored test suite is partial.)

## Step 29: Polish the UI ✅ Built — see §A16

The UI was fully built out: branded grade card, metric cards, warning icons,
escalating total-sugar warning, 13 themes, save-results. **See §A16** for the
full current UI spec (it supersedes the planned §A10 layout in the parts that
were built).

## ✅ Phase 3 complete

Project matches the grouped architecture. Code organized into core/ai/data/ui,
UI polished. Tests partial.

---

# PHASE 4 — Stretch Goals ⏳ Planned

Optional. Only if Phases 0-3 are working and you have time.

## Step 30: FastAPI layer ⏳ Planned

Expose the nutrition logic as a parallel REST API alongside Streamlit.
Both share the same backend. Strong architecture story for your
presentation.

**See §A5** for the spec.

## Step 31: Demo polish ✅ Mostly built

- Workflow diagram in `docs/workflow.png` ⏳
- Clean README with install + run instructions ✅ (done)
- Pre-load demo foods so your live demo is bulletproof even if WiFi dies ✅

---

# Appendices

These describe the architecture in detail. Refer to them when the roadmap
above points here. Don't read top-to-bottom.

> **Appendix index**
> | # | Section | Topic | Status |
> |---|---|---|---|
> | A1 | Refinement Loop | Cluster real USDA results when query is ambiguous | ✅ Built |
> | A2 | SQLite History | Log every successful lookup | ⏳ Planned |
> | A3 | SQLite Food Cache | Skip USDA + LLM on repeat lookups | ⏳ Planned |
> | A4 | Module Structure | File layout and dependency rules | ✅ Built (variant) |
> | A5 | FastAPI Layer | Optional HTTP API (Phase 4) | ⏳ Planned |
> | A6 | Grading Rubric | **Current: Nutri-Grade + per-100g thresholds** | ✅ Built |
> | A7 | USDA Nutrient Mapping | Map USDA IDs to Nutrition fields | ⏳ Partial |
> | A8 | Analysis Chain | summary + concerns + positives (ReAct) | ⏳ Planned |
> | A9 | Additive Detection | Flag concerning food additives | ⏳ Planned |
> | A10 | UI Layout | Streamlit design (planned) — see §A16 for built UI | ⏳ Superseded |
> | A11 | Analyzer Orchestration | The conductor | ⏳ Planned |
> | A12 | Query Rescue Agent | The agentic part (ReAct) | ⏳ Planned |
> | A13 | ReAct Prompting | Concept reference | ⏳ Planned |
> | A14 | Dual-Provider Support | Toggle Ollama / Anthropic | ✅ Built |
> | A15 | Prompts Module Layout | One file per prompt | ⏳ Planned |
> | A16 | **Result UI (as built)** | **Grade card, themes, warning, save** | ✅ Built |

## §A6 — Grading Rubric (current, as built) ✅

> **Quick reference**
> - **Solids:** fixed per-100g thresholds, 1–4 score per nutrient, averaged, + hard caps
> - **Drinks:** Singapore Nutri-Grade — worse of sugar & sat-fat per 100ml, >15g sugar → F
> - **+/- modifiers:** `plus_minus_grade()` adds A+/B-/C+ (display only)
> - **Output:** `(letter, color_hex, percentage)`
> - **Code home:** `core/grader.py` — pure math, no AI

### Solid foods (per 100g)

Each "bad" nutrient scored 1–4 (4 = healthiest):

| Nutrient | 4 | 3 | 2 | 1 |
|---|---|---|---|---|
| Sugar | ≤5g | ≤15g | ≤22.5g | else |
| Sodium | ≤90mg | ≤250mg | ≤600mg | else |
| Saturated fat | ≤1.5g | ≤5g | ≤8g | else |

**Bonus nutrients** (added to the score list only if they score ≥3, so they
raise a grade but never lower it):

| Nutrient | 4 | 3 | 2 | 1 |
|---|---|---|---|---|
| Fiber | ≥6g | ≥3g | ≥1.5g | else |
| Protein | ≥12g | ≥6g | ≥3g | else |

Average → letter: ≥3.6 A · ≥3.0 B · ≥2.4 C · ≥1.8 D · else F.

**Hard caps** (force the grade *down* only, via `_min_letter`):
- Sugar >22.5g → F; >15g → cap D
- Sodium >600mg OR sat fat >8g OR trans fat >1g → F
- Sodium >400mg OR sat fat >5g → cap D
- Any trans fat >0 → cap C

**Worked example — banana (12g sugar, 1mg sodium, 0.1g sat fat per 100g):**
3 + 4 + 4 → avg 3.67 → **A**. Near-zero in the bad nutrients; no caps fire.

### Drinks (per 100ml) — Singapore Nutri-Grade

Drinks do **not** average. Grade = **worse of** sugar-grade and sat-fat-grade:

| Sugar /100ml | Grade | | Sat fat /100ml | Grade |
|---|---|---|---|---|
| ≤1g | A | | ≤0.7g | A |
| ≤5g | B | | ≤1.2g | B |
| ≤10g | C | | ≤2.8g | C |
| ≤15g | D | | >2.8g | D |
| >15g | **F** *(custom)* | | | |

**Why no averaging:** drinks are mostly water + sugar, so they'd get "free"
perfect scores on fat/sodium that bury the sugar. Averaged, an 11g soda →
(3+4+4)/3 = 3.67 → A (absurd). Worse-of-two → **D** (correct). This mirrors
why real Nutri-Grade uses worse-of-two.

### Plus/minus modifiers

`plus_minus_grade(letter, pct, sugar, is_drink)` → A+/A/A- etc. Display only;
F has none. Solids use position in the % band; drinks use sugar's position in
the Nutri-Grade band (lower in band = +).

### Percentage & color

`_DRINK_PCT = {A:95, B:84, C:74, D:64, F:50}` for drinks; solids scale the
average within school-style bands (A 90s, B 80s, …). Color: A/B green, C amber,
D orange, F red.

### Earlier design (historical — not used)

> The original spec graded on **FDA Daily Values** (% DV with DV=2300mg sodium,
> 50g sugar, 20g sat fat, etc.) and a single drink cap (`is_drink and sugar>10
> → F`). This was **replaced** by the Nutri-Grade + fixed-threshold rubric above
> because the DV math didn't fit the per-100g basis and the single drink cap had
> a harsh cliff (3g→A but 6g→D). Kept here only for history.

---

## §A16 — Result UI (as built) ✅

> **Quick reference**
> - **Grade card:** colored badge (color = grade), icon, label, big +/- grade, %
> - **Metric cards:** sugar / sat fat / sodium
> - **Total-sugar warning:** grade vs. dose, escalates blue/yellow/red
> - **13 themes:** sidebar Appearance picker (`ui/themes.py`)
> - **Save results:** 💾 session list in the sidebar
> - **Code home:** `app.py` (render) + `ui/themes.py`

### Branded header

🍴 Forklore + tagline ("know your food, grade by grade"); page favicon set via
`st.set_page_config(page_icon="🍴")` (must be the first Streamlit call).

### Grade card

A colored badge whose color *is* the grade (green A/B, amber C, orange D, red
F), showing: an icon (✅ good / ⚠️ so-so / ⛔ avoid), a plain-language label
("great choice" … "avoid"), the big **+/- grade**, and the percentage, plus the
food name and brand. Below it, three **metric cards** (sugar / sat fat / sodium).

### Total-sugar warning (grade vs. dose)

The grade stays **per-100ml** (so cup size can't game it — a Sprite is a D
whether small or large). Separately, a warning shows the **total** sugar for
the chosen size and escalates against daily limits:

- <25g → blue info
- 25–50g → yellow "most of a day's sugar"
- >50g → red "⚠️ more than a full day's limit"

Grounded in WHO (~25g/day) and US guidelines (~50g/day). The letter answers
"is this a sugary drink?"; the warning answers "did I drink too much?".

### 13 themes

Sidebar "Appearance" picker: Cool Slate (default), Cream, Fresh Green, Soft
Sage, Berry, Dark, Ocean, Sunset, Lavender, Mocha, Midnight Blue, Mint, Classic
Green. Each is a dict of color values (bg, sidebar, text, btn, btn_hover,
btn_text, input_bg, input_border, tagline) injected as CSS, live-rethemeing the
whole app. Defined in `ui/themes.py`.

### Save results

A 💾 "Save this result" button snapshots the item (a plain dict — never the
Nutrition object, to avoid the session_state mutation trap) into a session
list shown in the sidebar, with a clear button. Session-only. Button keys must
be unique per render or the button stops responding.

### Streamlit gotchas baked into this UI

1. Module edits need a full restart (Ctrl+C + relaunch), not "Rerun".
2. Never mutate session_state objects — copy them (grades-climbing bug).
3. Unique button keys per render (save-button bug).
4. `set_page_config` first.

---

> The remaining appendices (§A1 refinement [built], §A2–§A5, §A7–§A15)
> describe the planned/partial designs. They are retained in full below as the
> backlog and design reference. Where §A6 or §A16 conflict with an older
> appendix, §A6/§A16 (the as-built sections) are authoritative.

---

## §A1 — Refinement Loop (Step 21) ✅ Built

> **Quick reference**
> - **Purpose:** clarify ambiguous queries by clustering real USDA results into options
> - **Trigger:** USDA returns scattered results (calorie range > 3x across top 5)
> - **Architecture:** search-first — USDA always called *before* LLM
> - **Cap:** 2 refinement rounds, then force top result
> - **Schema:** `RefinementTurn(done, question?, options?, chosen_fdc_id?)`
> - **Options:** each carries `fdc_ids: list[int]` — LLM cannot invent items
> - **Code home:** `core/retrieval.py` (diversity check), `ai/refinement.py` (chain)
> - **Does NOT use ReAct** — pure clustering, no judgment needed

**Search-first refinement.** The LLM never invents options out of its
head — every option shown to the user is grounded in real USDA results.
This eliminates the failure mode where the LLM offers something like
"Dunkin Iced Caramel Macchiato" only for USDA to return zero matches.

### The flow

```
User query
  ↓
USDA search (always — even on vague queries)
  ↓
Diversity check: are these results coherent or scattered?
  ↓                                ↓
Coherent (similar items)        Scattered (wide range)
  ↓                                ↓
Grade the top result            LLM clusters results into 4–6 groups
                                  ↓
                                Show grouped question to user
                                  ↓
                                User picks → maps to specific FDC IDs
                                  ↓
                                Grade the chosen item
```

The big shift from the old design: **the specificity check is no longer
based on hardcoded brand/size word lists.** The diversity of USDA
results *is* the signal. "Coffee" returns scattered results spanning
5–500 calories → refine. "Big Mac" returns five near-identical results
→ just grade the top one.

### Diversity check

Given the top N USDA results (N = 10 is fine), decide if they're
coherent enough to grade directly. Lives in `core/retrieval.py`.

Heuristic:
- **Coherent** if the calorie range across top 5 results is < 3x
  AND descriptions share key terms
- **Scattered** otherwise

Edge cases:
- USDA returns 0 results → fail gracefully. Don't fall back to LLM-imagined options.
- USDA returns 1 result → coherent by definition, grade it.
- USDA returns 2–3 results → coherent if calorie spread is tight.

### The chain

LangChain `ChatOllama` with structured output. The chain receives the
**actual USDA results** (descriptions + FDC IDs) and groups them.

```python
class RefinementOption(BaseModel):
    label: str               # short user-facing label, e.g. "Black drip coffee"
    fdc_ids: list[int]       # USDA entries this option maps to

class RefinementTurn(BaseModel):
    done: bool
    question: str | None = None
    options: list[RefinementOption] | None = None
    chosen_fdc_id: int | None = None
```

Each option carries the FDC IDs it represents. When the user picks, the
analyzer grades one of those entries directly — no second USDA round-trip.

### Prompt design

Three layers: a system message with hard rules (never invent items, natural
labels, always include "Other", each option ≥1 FDC ID from input); two
few-shot examples (scattered "coffee" → 4 buckets; coherent "big mac" →
done=True); a user template with the query + formatted results injected.

The grounding is enforced by construction: every FDC ID in the output must
come from the input list. The schema makes fabrication harder than honesty.

### Hard cap & escape hatch

After 2 rounds, force a search using the most recent option's FDC IDs (or
top result). Every refinement question shows a free-text input — typed text
restarts the flow as a brand-new query.

### User-facing language

The question is shown directly, so it must sound human:
- ✅ "Which kind of coffee did you have in mind?"
- ❌ "Specify coffee type" / "Refinement needed"

Option labels: warm and natural ("Black coffee (drip or instant)"), not
USDA-jargon ("Coffee, brewed, prepared with tap water").

---

## §A2 — SQLite History (Step 25) ⏳ Planned

> **Quick reference**
> - **Purpose:** log every successful lookup for the sidebar history list
> - **Storage:** SQLite, stdlib `sqlite3` only
> - **Code home:** `data/history.py`
> - **API:** `HistoryRepo.init() / append() / list(limit) / clear()`

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    query TEXT NOT NULL,
    refined_query TEXT NOT NULL,
    item_name TEXT NOT NULL,
    overall_grade TEXT NOT NULL,
    overall_color TEXT NOT NULL,
    percentage INTEGER NOT NULL,
    report_json TEXT NOT NULL
);
CREATE INDEX idx_history_created_at ON history(created_at DESC);
```

`HistoryRepo` class with `init`, `append`, `list(limit)`, `clear`. Stdlib
`sqlite3` only. No SQLAlchemy. Non-fatal failure mode.

---

## §A3 — SQLite Food Cache (Step 26) ⏳ Planned

> **Quick reference**
> - **Purpose:** skip USDA + LLM work on repeat lookups
> - **Two-layer:** by raw query string AND by `(fdc_id, provider, model)`
> - **Cached value:** full graded report
> - **Code home:** `data/cache.py`

Caches the full graded report, not just nutrition, so re-displaying a cached
food doesn't re-run the LLM.

```sql
CREATE TABLE food_cache (
    fdc_id INTEGER NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    report_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (fdc_id, provider, model)
);
CREATE TABLE query_cache (
    query TEXT PRIMARY KEY,
    fdc_id INTEGER NOT NULL,
    cached_at TEXT NOT NULL
);
```

Keyed by final FDC ID (stable across phrasings). Survives restarts. No expiry
for MVP. Each provider/model gets its own cached output (see §A14).

---

## §A4 — Module Structure (Step 27) ✅ Built (variant)

> **Quick reference**
> - **Layout:** `src/forklore/` with `core/`, `data/`, `ai/`, `ui/` + `app.py`, `models.py`
> - **`core/`** = pure logic · **`data/`** = USDA/FatSecret I/O · **`ai/`** = LLM · **`ui/`** = presentation
> - **Rule:** dependencies flow `app → (core, data, ai, ui)`. Never reversed.

> **As-built note:** the real tree (see Phase 3 "Architecture (real)") matches
> this closely but: there is **no `analyzer.py`/`api.py`** yet (orchestration
> lives in `app.py`), and a **`ui/` folder was added** for themes. The planned
> layout below is the original target.

```
src/nutrigrade/            # (real package: forklore)
├── __init__.py
├── config.py
├── models.py
├── analyzer.py            # planned — orchestrator (§A11)
├── app.py
├── api.py                 # planned (Phase 4)
├── core/
│   ├── normalize.py
│   ├── retrieval.py
│   ├── grader.py
│   ├── additives.py       # planned (§A9)
│   └── colors.py
├── data/
│   ├── usda_client.py
│   ├── history.py         # planned (§A2)
│   └── cache.py           # planned (§A3)
└── ai/
    ├── llm_chains.py
    └── prompts/           # planned (§A15)
```

### Rules

- `core/` modules are pure (same input → same output, no I/O, no LLM)
- Only `data/` and `ai/` modules do I/O
- `app.py` wires UI to logic
- `analyzer.py` (planned) would import from core/data/ai and compose the flow

### Migration table (where each piece of `app.py` goes)

| Code in `app.py` | Move to |
|---|---|
| Pydantic models | `models.py` |
| USDA fetch/parse | `data/usda_client.py` |
| `grade_food` and rubric | `core/grader.py` |
| Diversity check | `core/retrieval.py` |
| Additive detection | `core/additives.py` (planned) |
| `write_summary` and LLM | `ai/` |
| Refinement | `ai/refinement.py` |
| SQLite history/cache | `data/` (planned) |
| Orchestration | `analyzer.py` (planned; currently in `app.py`) |
| Streamlit UI | `app.py` + `ui/` |

---

## §A5 — FastAPI Layer (Step 30, optional) ⏳ Planned

> **Quick reference**
> - **Status:** Phase 4 stretch goal, not built
> - **Purpose:** HTTP API alongside Streamlit, same backend
> - **Endpoints:** `POST /api/grade`, `POST /api/grade/continue`, `GET /api/history`, `GET /api/healthz`
> - **Code home:** `api.py` (sibling of `app.py`)

Parallel HTTP layer, same backend, two interfaces.

```
POST /api/grade            Body {"query": "big mac"} → 200 GradedReport OR 409 NeedsClarification
POST /api/grade/continue   Body {history, answer}    → 200 GradedReport OR 409 NeedsClarification
GET  /api/history?limit=20 → 200 [GradedReport, ...]
GET  /api/healthz          → 200 {"status": "ok"}
```

409 = "needs clarification." Setup: `uv add fastapi "uvicorn[standard]"`;
`uv run uvicorn forklore.api:app --reload --port 8000`; Swagger at `/docs`.

---

## §A7 — USDA Nutrient Mapping & Data Model (Step 22) ⏳ Partial

> **Quick reference**
> - **Purpose:** map USDA's nutrient IDs to clean Pydantic fields
> - **Per-100g basis:** all values normalized to per-100g
> - **Missing values:** default to 0
> - **Code home:** `data/usda_client.py` (parse), `models.py` (schema)

### Rubric nutrients (named fields)

| Field | nutrientId | name |
|---|---|---|
| calories | 1008 | Energy |
| total_fat_g | 1004 | Total fat |
| saturated_fat_g | 1258 | Saturated |
| trans_fat_g | 1257 | Trans |
| cholesterol_mg | 1253 | Cholesterol |
| sodium_mg | 1093 | Sodium |
| total_carbs_g | 1005 | Carbs |
| total_sugar_g | 2000 | Total sugar |
| added_sugar_g | 1235 | Added sugar |
| fiber_g | 1079 | Fiber |
| protein_g | 1003 | Protein |

Everything else USDA returns goes in a flexible `other_nutrients` list so the
UI can show it without predefining every field.

### Serving size & sugar fallback

If `servingSize` is absent, assume 100g and label "per 100 g" — **don't
fabricate serving sizes**. If added sugar (1235) is absent, fall back to total
sugar (2000).

---

## §A8 — Analysis Chain (Step 23) ⏳ Planned

> **Quick reference**
> - **Purpose:** generate friendly summary + concerns + positives
> - **Uses ReAct** (§A13) — `thought` field first
> - **One chain, one call**
> - **Schema:** `Analysis(thought, summary, concerns[], positives[])`

The planned headline LLM feature. Combines summary, concerns, and per-nutrient
explanations into one structured output.

```python
class Concern(BaseModel):
    label: str
    severity: Literal["red", "orange", "yellow"]
    headline: str        # "230g sugar (460% DV)"
    explanation: str     # 3-4 sentences with quantity comparisons

class Positive(BaseModel):
    label: str
    note: str

class Analysis(BaseModel):
    thought: str             # ReAct reasoning (§A13)
    summary: str
    concerns: list[Concern]
    positives: list[Positive]
```

Rules: use actual numbers; compare to picturable references ("230g = ~50
teaspoons"); no medical advice; lead with the worst offender; skip green
nutrients; positives are lighter-touch. The `thought` field forces the model
to plan severity ordering before writing. Include one good + one bad few-shot
example for tone. Output is part of the cached report (once caching is built).

---

## §A9 — Additive Detection (Step 24) ⏳ Planned

> **Quick reference**
> - **Purpose:** flag concerning additives from ingredient lists
> - **Method:** hard-coded list + regex on USDA's `ingredients` field
> - **Honest:** if `ingredients` is None, return `[]` — never fake

```python
ADDITIVES = {
    "Red 40": ["red 40", "fd&c red no. 40", "allura red"],
    "Yellow 5": ["yellow 5", "tartrazine"],
    "BHA": ["bha", "butylated hydroxyanisole"],
    "BHT": ["bht", "butylated hydroxytoluene"],
    "Aspartame": ["aspartame"],
    "High fructose corn syrup": ["high fructose corn syrup", "hfcs"],
    "MSG": ["monosodium glutamate", "msg"],
    # ... extend as needed
}

def find_additives(ingredients: str | None) -> list[str]:
    if not ingredients:
        return []
    lower = ingredients.lower()
    return [name for name, aliases in ADDITIVES.items()
            if any(re.search(rf'\b{re.escape(a)}\b', lower) for a in aliases)]
```

USDA only returns ingredients for branded foods, inconsistently. When missing,
return `[]` and show "Ingredient data not available" — no fake detection. Each
found additive becomes a concern in §A8.

---

## §A10 — UI Layout (Step 29) ⏳ Superseded by §A16

> **Status:** the planned two-audience layout below was partly built; the
> **actual** UI is documented in **§A16** (grade card, themes, warning, save).
> This section is kept as the original design intent.

Two audiences: end users (clean view) and technical reviewers (dev trace).
Design principles: user-friendly first (no jargon), colorful but professional
(grade colors do the work), confidence through transparency (cite the data
source), progressive disclosure (summary → concerns → full breakdown).

Planned sidebar: branding, recent lookups, about, settings (dev-trace toggle,
provider radio, clear cache/history). Planned main area: grade hero card,
summary band, concerns cards (severity borders), positives pills, full
nutrition expander, footer citation, "Why?" disclosure (reveals the ReAct
thought). Refinement questions render as a friendly question + option cards,
no FDC IDs shown. Cache hit/miss shown only in dev trace.

What NOT to do: don't show FDC IDs/cache jargon/"refinement" to users; don't
show "no concerns 🎉"; don't over-emoji; don't auto-scroll/animate.

---

## §A11 — Analyzer Orchestration ⏳ Planned

> **Quick reference**
> - **Role:** the conductor — imports core/data/ai and composes the flow
> - **Status:** not built as a separate module; orchestration currently lives in `app.py`
> - **Return union:** `GradedReport | NeedsClarification | AnalysisError`
> - **Stateless:** state lives in the UI session

Planned `analyzer.py` would be the single place the whole flow lives, so the UI
(`app.py`) and a future API (`api.py`) call into it without touching USDA/LLM/DB
directly. The full planned flow:

```
[1] cache check (query string) → hit returns cached report
[2] USDA/FatSecret search → 0 results → error
[3] diversity check → coherent grades top; scattered → refine
[4] refinement chain → done uses chosen FDC; else return to UI
[5] cache check (FDC ID)
[6] parse → Nutrition
[7] grade (+caps +pct +color)
[8] detect additives
[9] analysis chain (summary+concerns+positives)
[10] assemble GradedReport
[11] write cache
[12] append history
```

Two cache checks (query string fast-path + FDC ID post-resolution). Stateless;
refinement state lives in `st.session_state`. Error handling is graceful — USDA
/ LLM / DB failures are non-fatal.

---

## §A12 — Query Rescue Agent (Step 21.5) ⏳ Planned

> **Quick reference**
> - **Status:** the ONE genuinely agentic part — **not yet built**
> - **Triggers:** USDA returns 0 results OR weak match
> - **Three actions:** `rewrite` / `ask` / `give_up`
> - **Uses ReAct** (§A13) — `thought` first
> - **Cap:** 2 rounds, then `AnalysisError`

The planned rescue is the one place the AI decides app flow (within three
scoped actions), bridging natural language ("PSL", "korean fried chicken") to
USDA's clinical naming.

```python
class RescueAction(BaseModel):
    thought: str                       # ReAct reasoning first
    action: Literal["rewrite", "ask", "give_up"]
    new_query: str | None = None
    question: str | None = None
    options: list[str] | None = None
```

**rewrite** when the expansion is clear ("PSL" → "pumpkin spice latte");
**ask** when ambiguous ("kbbq" → which dish?); **give_up** when no rewrite
helps ("dragonfruit pizza"). Two triggers: zero results, or weak match (query
terms appear in zero results). Cap 2 rounds. Four ReAct few-shot examples
(rewrite, ask, weak-match, give-up), each showing thought-before-action. Adds
a `ClarificationNeeded` branch to the analyzer union and renders like a
refinement question. Silent rewrites show an "Interpreted as: X" line.

---

## §A13 — ReAct Prompting ⏳ Planned

> **Quick reference**
> - **What:** LLM writes reasoning (`thought`) before committing to output
> - **Why:** forced reasoning improves decisions on small models
> - **Version:** "light" ReAct — one thought + one action per call
> - **Used in (planned):** §A12 rescue, §A8 analysis
> - **NOT used in:** §A1 refinement (pure clustering)

ReAct = Reasoning + Acting. The model reasons out loud, then acts. We'd use the
**light** version (one thought + one action in a single call) — the full
multi-step loop is unreliable at small-model scale. Benefits: reduces sloppy
outputs, surfaces skipped context, makes failures debuggable. Implementation:
add a `thought` field (first) to the output schema; restructure few-shots to
show reasoning; instruct "think before acting." Use it for decisions/judgment
(rescue, severity ordering), not pure transforms (refinement).

The capstone story: "My agentic decisions use light ReAct from the 2022 Yao et
al. paper, scoped to single calls — full multi-step loops aren't reliable on a
local model this size."

---

## §A14 — Dual-Provider Support ✅ Built

> **Quick reference**
> - **Purpose:** support local (Ollama) and hosted (Anthropic/Claude) providers
> - **Default:** Ollama (local, free, offline)
> - **Switch:** sidebar toggle; Claude model dropdown
> - **Gating:** Anthropic option only if `ANTHROPIC_API_KEY` set
> - **Code home:** `ai/llm.py::get_llm()`, sidebar in `app.py`

Provider portability proves the chains aren't coupled to one model, and lets
each query use the right model. The `get_llm()` factory is the seam:

```python
def get_llm(provider="ollama", model=None, temperature=0.2):
    if provider == "ollama":
        return ChatOllama(model=model or "llama3.2:3b",
                          base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                          temperature=temperature)
    if provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return ChatAnthropic(model=model or "claude-sonnet-4-6", temperature=temperature)
```

Sidebar: a toggle/radio for provider (defaults to local), a Claude model
dropdown when Anthropic is selected, disabled with a caption if no key.
Selection stored in `st.session_state["provider"]` and read by the chains.

The demo moment: same query under local vs. Claude, side by side, same prompts
and chains — different output quality.

Graceful failure: if Anthropic is down/rate-limited, surface a friendly error
and fall back to local. (When the SQLite cache is built, key it by
`(fdc_id, provider, model)` so each model has its own cached output.)

---

## §A15 — Prompts Module Layout ⏳ Planned

> **Quick reference**
> - **Structure:** `ai/prompts/` folder, one file per prompt
> - **Files:** `refinement.py`, `analysis.py`, `rescue.py`
> - **Re-exports:** `__init__.py` re-exports all three
> - **Why:** each prompt is 60–100 lines with ReAct scaffolding + few-shots

Rationale: each prompt is substantial; prompts are the most-iterated code;
smaller files contain edit blast-radius; real separation enforces the
convention. `__init__.py` re-exports so consumers do `from ai.prompts import
RESCUE_PROMPT` without knowing the layout. Revisit (split examples into a
separate file) if a prompt exceeds ~150 lines.

> **As-built note:** currently the LLM work lives in flat modules (`ai/refinement.py`,
> `ai/summary.py`, `ai/ingredients.py`, `ai/llm.py`) rather than a `prompts/`
> subfolder. Adopt this layout if/when the rescue and analysis chains are built.

---

## Definition of Done

### Walking skeleton (Phase 1) ✅
- [x] `ollama_test.py` returns a sensible response and a valid Pydantic object
- [x] `usda_test.py` returns real nutrition data
- [x] User types a food → USDA data → colored letter grade + percentage
- [x] LLM writes a friendly summary
- [x] Hard caps fire correctly

### Real app (Phase 2)
- [x] Generic queries trigger refinement; caps at 2 rounds; free-text escape works
- [ ] Rescue agent (rewrite/ask/give-up) — *planned*
- [ ] Concerns panel + per-nutrient explanations — *planned*
- [ ] Additive detection — *planned*
- [x] Dual-provider toggle (local/Claude)
- [ ] SQLite history + cache — *planned*
- [x] FatSecret branded items with real-data-only filtering
- [x] Drink customization re-grades on real math
- [x] Composite/homemade dishes graded from weighted ingredients

### Refactored (Phase 3)
- [x] Code split into `core/`, `data/`, `ai/`, `ui/`
- [ ] `uv run pytest` ≥80% coverage — *partial*
- [x] UI polished — grade card, themes, warning, save (§A16)

### Demo-ready
- [x] Handles foods across the grade range (banana A, big mac D, frappuccino F)
- [x] Handles "coffee" with refinement
- [x] Handles "no results" gracefully
- [x] At least one demo food triggers a hard cap / F
- [x] README explains install + run
- [ ] Workflow diagram — *optional*
- [x] 5–10 minute presentation ready

You've got this. 🍴