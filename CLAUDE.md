# CLAUDE.md — NutriGrade

> A step-by-step roadmap for building NutriGrade, an LLM-powered food
> & drink nutrition analyzer. Read top to bottom, do each step before
> the next.
>
> **Stack:** Streamlit · LangChain + Ollama (local) · USDA FoodData Central · SQLite · uv

---

## How to use this doc

The roadmap is in **Phases 0–4**, written as numbered steps you do in
order. Heavy specifications live in **appendices (§A1–§A13)** at the
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

### Architecture at a glance

NutriGrade is a **deterministic pipeline with one agentic exception**:

```
user query → search USDA → grade → analyze → render
                  │
                  └─ if 0 results or weak match → rescue agent (§A12)
                  └─ if scattered results → refinement (§A1)
```

Everything is deterministic except the rescue agent, which uses
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
mkdir nutrigrade
cd nutrigrade
```

## Step 7: Bootstrap the project with uv

```bash
uv init . --package
uv python pin 3.11
uv add streamlit requests pydantic pydantic-settings langchain langchain-ollama langchain-anthropic python-dotenv
```

This creates `pyproject.toml`, `uv.lock`, `.python-version`,
`src/nutrigrade/`, and `.venv/`. The `langchain-anthropic` dependency
enables the dual-provider toggle (see §A14) — it's used at runtime
only when the user switches to Claude in the sidebar.

## Step 8: Create `.env` and `.env.example`

Create `.env`:
```
USDA_API_KEY=paste_your_key_here
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma3:4b

# Optional — enables the Claude provider in the sidebar (see §A14)
# If not set, only the local Gemma option appears.
ANTHROPIC_API_KEY=
```

Replace the USDA placeholder with your real key. Leave
`ANTHROPIC_API_KEY` empty if you only want local. Paste your Anthropic
API key there if you want the dual-provider toggle.

Also create `.env.example` with the same contents but leave all
values empty — this one gets committed to Git.

## Step 9: Set up `.gitignore`

```bash
echo ".venv/
__pycache__/
.env
nutrigrade.db
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
food, sees a grade with a summary. Everything in `src/nutrigrade/app.py`.
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
real app. In `src/nutrigrade/app.py`:

```python
import streamlit as st

st.title("🥗 NutriGrade")
st.write("Type a food to see its nutrition grade.")
```

Run it:
```bash
uv run streamlit run src/nutrigrade/app.py
```

Browser opens at `http://localhost:8501`. **Second checkpoint** — if
you see the title, your Streamlit setup works.

## Step 16: Add input box and button

```python
import streamlit as st

st.title("🥗 NutriGrade")
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

## Step 19: Add the grading function (with hard caps and percentage)

The full rubric lives in §A6. Walking-skeleton version with FDA-aligned
hard caps already baked in:

```python
def grade_food(n: Nutrition) -> tuple[str, str, int]:
    """Return (letter_grade, hex_color, percentage_0_to_100)."""
    scores = []
    scores.append(_score_limit(n.sodium_mg, dv=2300))
    scores.append(_score_limit(n.saturated_fat_g, dv=20))
    scores.append(_score_limit(n.sugar_g, dv=50))
    scores.append(_score_get_enough(n.fiber_g, dv=28))
    scores.append(_score_get_enough(n.protein_g, dv=50))

    avg = sum(scores) / len(scores)

    if avg >= 3.6: letter = "A"
    elif avg >= 3.0: letter = "B"
    elif avg >= 2.4: letter = "C"
    elif avg >= 1.8: letter = "D"
    else: letter = "F"

    # Apply FDA-aligned hard caps (see §A6)
    if n.sugar_g > 50 or n.sodium_mg > 2300 or n.saturated_fat_g > 20 or n.trans_fat_g > 2:
        letter = "F"
    elif n.sugar_g > 30 or n.sodium_mg > 1500 or n.saturated_fat_g > 12:
        letter = _min_letter(letter, "D")
    elif n.trans_fat_g > 0:
        letter = _min_letter(letter, "C")

    pct = round(((avg - 1.0) / 3.0) * 100)
    pct = _cap_percentage(pct, letter)

    color = {"A": "#2E7D32", "B": "#2E7D32", "C": "#F9A825",
             "D": "#EF6C00", "F": "#C62828"}[letter]
    return letter, color, pct


def _score_limit(value: float, dv: float) -> int:
    pct_dv = (value / dv) * 100
    if pct_dv <= 5: return 4
    if pct_dv <= 15: return 3
    if pct_dv <= 25: return 2
    return 1


def _score_get_enough(value: float, dv: float) -> int:
    pct_dv = (value / dv) * 100
    if pct_dv >= 20: return 4
    if pct_dv >= 10: return 3
    if pct_dv >= 5: return 2
    return 1


def _min_letter(a: str, b: str) -> str:
    order = ["A", "B", "C", "D", "F"]
    return a if order.index(a) >= order.index(b) else b


def _cap_percentage(pct: int, letter: str) -> int:
    caps = {"F": 26, "D": 46, "C": 66}
    return min(pct, caps.get(letter, 100))
```

Update the button block to show the grade with the percentage:
```python
if st.button("Analyze"):
    food = fetch_from_usda(query)
    if food is None:
        st.error("No results from USDA")
    else:
        nutrition = parse_usda_response(food)
        letter, color, pct = grade_food(nutrition)

        st.markdown(
            f"<div style='background:{color};color:white;padding:24px;"
            f"text-align:center;border-radius:8px;'>"
            f"<div style='font-size:64px;font-weight:bold;line-height:1;'>{letter}</div>"
            f"<div style='font-size:24px;'>{pct}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.write(f"**{nutrition.description}**")
        # ...show nutrition fields...
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

End-to-end flow works: **input → USDA → grade with hard caps and
percentage → LLM summary → colored display.**

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

This phase introduces a small amount of structure the MVP didn't need:
a `core/retrieval.py` for the two checks, two new LLM chains, and real
branching in the analyzer. Budget ~3–4 hours.

## Step 21: Refinement loop (search-first)

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

## Step 21.5: Query rescue agent

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

# PHASE 2 — Make It Real

This is where NutriGrade gains its richer features. With the edge cases
already handled in Phase 1.5, this phase is about depth: a fuller
nutrition model, the concerns analysis, additive detection, history,
and caching.

## Step 22: Expand the nutrition data model

Switch `Nutrition` to track the rubric inputs **plus** every other
nutrient USDA returns (vitamins, minerals, etc.) in a flexible dict.
The grader still uses named fields; the UI displays everything.

**See §A7** for the full nutrient mapping and the `other_nutrients`
dict pattern.

## Step 23: Add the Concerns analysis

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

## Step 24: Add additive/dye detection

Hard-coded list of additives (Red 40, Yellow 5, BHA, BHT, sodium
nitrate, aspartame, HFCS, etc.). Regex-matched against USDA's
`ingredients` field when present. Each detected additive becomes another
"concern" in the analysis output.

USDA doesn't always return ingredient data — when missing, just skip
the additive scan for that food. Honest behavior is better than fake
detection.

**See §A9** for the additive list and detection logic.

## Step 25: SQLite history

Save every successful lookup so the sidebar can show recent searches.

**See §A2** for the schema and repo class.

## Step 26: SQLite cache

Cache the **full graded report** (nutrition + concerns + LLM summary +
explanations) keyed by the final search query. First lookup of a food
is "Fresh from USDA"; second lookup is "Loaded from cache" and is
instant.

The cache is what makes the app feel snappy and what saves your demo
when WiFi is flaky.

**See §A3** for the schema and repo class.

## ✅ Phase 2 complete

The app now handles vague queries gracefully, surfaces all health
concerns with real explanations, flags concerning additives, remembers
history, and gets faster with use. This is a real app.

---

# PHASE 3 — Refactor

The single `app.py` is getting big. Time to split into proper modules
and add tests.

## Step 27: Split into the grouped module structure

Move pieces of `app.py` into themed folders:
- **`core/`** — pure logic (no I/O)
- **`data/`** — anything that talks to USDA, SQLite, or the network
- **`ai/`** — LLM stuff
- Top-level files for entry points and orchestration

**See §A4** for the full target layout and a migration table showing
where each piece of `app.py` should land.

## Step 28: Add tests

```bash
uv add --dev pytest pytest-cov
```

Mirror the source folder structure inside `tests/`:
```
tests/
├── core/
│   ├── test_grader.py        # every grading band, all hard caps, percentage math
│   ├── test_normalize.py
│   ├── test_retrieval.py     # diversity check (calorie spread)
│   └── test_additives.py     # regex detection
├── data/
│   ├── test_history.py       # SQLite roundtrips on :memory: DB
│   ├── test_cache.py
│   └── test_usda_parse.py    # USDA response → Nutrition
├── test_models.py
└── test_analyzer.py          # full flow with fakes
```

**Don't** test against live LLM or live USDA. Use fakes everywhere.

## Step 29: Polish the UI

Now that you have working data flowing through, design the actual
layout. The information you need to display:

**Always visible (sidebar):**
- App title + tagline
- Recent lookups (clickable to re-render)
- Cache size + Clear cache button
- Clear history button
- Model name and data source

**Result view (main area):**
- Big colored grade badge with letter + percentage
- Food name and brief LLM summary
- The concerns panel (each concern in its own card with a colored header)
- The nutrition data table (rubric nutrients up top with color pills, vitamins/minerals below or collapsed)
- Cache hit/miss indicator
- USDA source citation

Streamlit gives you `st.tabs`, `st.expander`, `st.columns`, `st.metric`,
and `st.markdown` — pick what feels right when you're building. Don't
overthink the layout in advance; iterate on it once you can see real data.

## ✅ Phase 3 complete

Project matches the architecture in the appendices. Tests passing,
code organized, UI polished. Ready for capstone presentation.

---

# PHASE 4 — Stretch Goals

Optional. Only if Phases 0-3 are working and you have time.

## Step 30: FastAPI layer

Expose the nutrition logic as a parallel REST API alongside Streamlit.
Both share the same backend. Strong architecture story for your
presentation.

**See §A5** for the spec.

## Step 31: Demo polish

- Workflow diagram in `docs/workflow.png`
- Clean README with install + run instructions
- Pre-load 5 demo foods so your live demo is bulletproof even if WiFi dies

---

# Appendices

These describe the destination architecture in detail. Refer to them
when the roadmap above points here. Don't read top-to-bottom.

> **Appendix index**
> | # | Section | Topic |
> |---|---|---|
> | A1 | Refinement Loop | Cluster real USDA results when query is ambiguous |
> | A2 | SQLite History | Log every successful lookup |
> | A3 | SQLite Food Cache | Skip USDA + LLM on repeat lookups |
> | A4 | Module Structure | File layout and dependency rules |
> | A5 | FastAPI Layer | Optional HTTP API (Phase 4) |
> | A6 | Grading Rubric | Letter grade math + hard caps |
> | A7 | USDA Nutrient Mapping | Map USDA IDs to Nutrition fields |
> | A8 | Analysis Chain | LLM generates summary + concerns + positives (uses ReAct) |
> | A9 | Additive Detection | Flag concerning food additives |
> | A10 | UI Layout | Streamlit design, two-audience approach |
> | A11 | Analyzer Orchestration | The conductor — composes the full flow |
> | A12 | Query Rescue Agent | The agentic part — rescue queries USDA doesn't recognize (uses ReAct) |
> | A13 | ReAct Prompting | Concept reference for the reasoning pattern |
> | A14 | Dual-Provider Support | Toggle between Ollama (local) and Anthropic (cloud) |
> | A15 | Prompts Module Layout | Why `ai/prompts/` is a folder with one file per prompt |
>
> **Three appendices to read first** if Claude Code needs the broad
> picture: §A4 (module structure), §A11 (orchestration), §A13 (ReAct concept).

## §A1 — Refinement Loop (Step 21)

> **Quick reference**
> - **Purpose:** clarify ambiguous queries by clustering real USDA results into options
> - **Trigger:** USDA returns scattered results (calorie range > 3x across top 5)
> - **Architecture:** search-first — USDA always called *before* LLM
> - **Cap:** 2 refinement rounds, then force top result
> - **Schema:** `RefinementTurn(done, question?, options?, chosen_fdc_id?)`
> - **Options:** each carries `fdc_ids: list[int]` — LLM cannot invent items
> - **Code home:** `core/retrieval.py` (diversity check), `ai/llm_chains.py` (refine chain), `ai/prompts/refinement.py` (template)
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

Heuristic for MVP:
- **Coherent** if the calorie range across top 5 results is < 3x
  (e.g. all 200–400 kcal) AND descriptions share key terms
- **Scattered** otherwise

The calorie heuristic alone catches ~80% of cases. Add description-
similarity scoring later if needed; don't bother in Phase 2.

Edge cases:
- USDA returns 0 results → fail gracefully ("No matches, try
  rephrasing"). Don't fall back to LLM-imagined options.
- USDA returns 1 result → coherent by definition, grade it.
- USDA returns 2–3 results → coherent if calorie spread is tight.

### The chain

LangChain `ChatOllama` with structured output. The chain receives the
**actual USDA results** (descriptions + FDC IDs) and groups them into
a refinement question.

```python
class RefinementOption(BaseModel):
    label: str               # short user-facing label, e.g. "Black drip coffee"
    fdc_ids: list[int]       # USDA entries this option maps to

class RefinementTurn(BaseModel):
    done: bool
    question: str | None = None
    options: list[RefinementOption] | None = None
    chosen_fdc_id: int | None = None      # set when done=True
```

The key change: each option carries the FDC IDs it represents. When the
user picks an option, the analyzer grades one of those entries directly
— **no second USDA round-trip** needed.

### Prompt design

The refinement prompt has three layers:

1. **System message with hard rules** — "never invent items not in
   the provided list", "use natural labels", "always include Other /
   not sure", "each option must contain at least one FDC ID from input".
2. **Few-shot examples (2)** — one showing scattered "coffee" results
   being clustered into 4 buckets + Other; one showing coherent "big
   mac" results triggering `done=True`. The two examples together teach
   both behaviors.
3. **User message template** — the actual query + formatted USDA
   results get injected at runtime.

The grounding is enforced by construction: every FDC ID in the output
must come from the input list. The schema (`fdc_ids: list[int]`) makes
fabrication harder than honesty.

### Hard cap

After 2 rounds, force a search using the most recent option's FDC IDs
(or fall back to the top USDA result if the user keeps picking "Other").
Don't ask a third question.

### Free-text escape hatch

Every refinement question shows a free-text input below the option
buttons. If the user types there, treat it as a brand-new query —
restart the flow with that text as input (fresh USDA search, fresh
diversity check).

### User-facing language

The LLM-generated question is shown directly to the user, so it must
sound like a friendly question from a person — not a system prompt.

Good question phrasings:
- "Which kind of coffee did you have in mind?"
- "What kind of burger?"
- "Could you narrow that down a bit?"

Bad phrasings (avoid):
- "Specify coffee type" (robotic)
- "Refinement needed" (internal jargon)
- "Please disambiguate your query" (formal/cold)

The prompt should include this guidance as a system instruction. Pair
it with a few-shot example whose `question` field demonstrates the
desired warm tone.

Option labels follow the same rule: warm and natural.
- ✅ "Black coffee (drip or instant)"
- ✅ "Frappuccino (frozen blended)"
- ❌ "Coffee, brewed, prepared with tap water" (USDA-jargon)
- ❌ "Type 1: Standard brewed" (taxonomy-speak)

### Why this is better than LLM-imagined options

- Every option is guaranteed to resolve to real USDA data
- No hardcoded brand/size word lists to maintain
- The specificity signal is empirical (data diversity) not heuristic
- "Other" matters less because the main options actually work
- The LLM's job is easier: clustering > imagining

## §A2 — SQLite History (Step 25)

> **Quick reference**
> - **Purpose:** log every successful lookup for the sidebar history list
> - **Storage:** SQLite, stdlib `sqlite3` only (no SQLAlchemy)
> - **Code home:** `data/history.py`
> - **API:** `HistoryRepo.init() / append() / list(limit) / clear()`
> - **Failure mode:** non-fatal — logged but doesn't break the user flow

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

`HistoryRepo` class with `init`, `append`, `list(limit)`, `clear`.
Stdlib `sqlite3` only. No SQLAlchemy.

## §A3 — SQLite Food Cache (Step 26)

> **Quick reference**
> - **Purpose:** skip USDA + LLM work on repeat lookups
> - **Two-layer:** by raw query string (fast path) AND by `(fdc_id, provider, model)` composite key
> - **Cached value:** full `GradedReport` (nutrition + grade + analysis + additives)
> - **Provider-aware:** each provider (and model) has its own cached outputs — see §A14
> - **Storage:** same DB file as history (§A2), different table
> - **Code home:** `data/cache.py`
> - **API:** `FoodCacheRepo.get_by_query() / get_by_fdc_id(fdc_id, provider, model) / put() / clear() / size()`
> - **UI signal:** "⚡ Instant" pill on cache hits

Caches the **full graded report**, not just the nutrition data. This
means re-displaying a cached food doesn't re-run the LLM.

```sql
CREATE TABLE food_cache (
    fdc_id INTEGER NOT NULL,
    provider TEXT NOT NULL,           -- "ollama" or "anthropic" (see §A14)
    model TEXT,                       -- specific model used (e.g. "claude-sonnet-4-6"); null for ollama default
    report_json TEXT NOT NULL,        -- full GradedReport including LLM output
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (fdc_id, provider, model)
);

-- Separate fast-path table for raw query string lookups (provider-agnostic)
CREATE TABLE query_cache (
    query TEXT PRIMARY KEY,
    fdc_id INTEGER NOT NULL,
    cached_at TEXT NOT NULL
);
```

The composite primary key `(fdc_id, provider, model)` means each
LLM provider gets its own cached version of the same food. This is
deliberate — see §A14 for why.

`FoodCacheRepo` class with `get_by_query`, `get_by_fdc_id(fdc_id,
provider, model)`, `put`, `clear`, `size`. Same DB file as `history`,
different table.

### Behavior

- **Lazy population.** Cache starts empty.
- **Keyed by the final FDC ID**, not the user's raw input. (Under
  search-first refinement from §A1, the user's pick maps directly to
  one or more FDC IDs — that's a more stable cache key than a query
  string, since "big mac" and "Big Mac" and "mcdonald's big mac" all
  resolve to the same FDC ID.)
- **Survives app restarts** — that's the whole point.
- **No expiry for MVP.** Could add a TTL later as a stretch goal.

The analyzer's flow:
1. User query → USDA search → diversity check → (maybe refinement) →
   final FDC ID
2. Check cache by FDC ID → if hit, return cached `GradedReport`, skip
   the analysis chain
3. Cache miss → grade → run LLM analysis → write back to cache → return

UI shows 🟢 "Loaded from cache" or 🔵 "Fresh from USDA" indicator.

### Why caching matters more under search-first refinement

A cache miss on the new flow can involve: USDA search → LLM clustering →
user pick → grading → analysis chain. That's more expensive than the
old "one USDA call → grade → done" path. The cache hit rate matters
more for perceived performance now, but the win is bigger too — repeat
lookups skip *all* of that.

## §A4 — Module Structure (Step 27)

> **Quick reference**
> - **Layout:** `src/nutrigrade/` with `core/`, `data/`, `ai/` subfolders + top-level `analyzer.py` and `app.py`
> - **`core/`** = pure logic, no I/O, easy to test
> - **`data/`** = talks to USDA + SQLite
> - **`ai/`** = LLM stuff (prompts, chains)
> - **`analyzer.py`** = orchestrator, the only file that imports from all three
> - **`app.py`** = Streamlit UI, no business logic
> - **Rule:** dependencies flow `app → analyzer → (core, data, ai)`. Never reversed.

```
src/nutrigrade/
├── __init__.py
├── config.py             # env vars (USDA key, Ollama host, DB path)
├── models.py             # all Pydantic schemas
├── analyzer.py           # orchestrates the whole flow (see §A11)
├── app.py                # Streamlit entry point (UI only, no logic)
├── api.py                # FastAPI entry point (Phase 4 / optional)
│
├── core/                 # pure logic — no I/O, easy to test
│   ├── __init__.py
│   ├── normalize.py      # tiny text helper
│   ├── retrieval.py      # diversity check + weak-match check (§A1, §A12)
│   ├── grader.py         # rubric, hard caps, percentage
│   ├── additives.py      # known-additive list + regex match
│   └── colors.py         # color mapping
│
├── data/                 # talks to external systems
│   ├── __init__.py
│   ├── usda_client.py    # USDA API + parse_usda_response
│   ├── history.py        # SQLite history repo
│   └── cache.py          # SQLite food cache repo
│
└── ai/                   # LLM stuff (uses ReAct in rescue + analysis, see §A13)
    ├── __init__.py
    ├── llm_chains.py     # refine_chain + analysis_chain + rescue_chain
    └── prompts/          # one file per prompt — see §A15 for rationale
        ├── __init__.py   # re-exports REFINEMENT_PROMPT, ANALYSIS_PROMPT, RESCUE_PROMPT
        ├── refinement.py # REFINEMENT_PROMPT + helpers (§A1)
        ├── analysis.py   # ANALYSIS_PROMPT + helpers (§A8)
        └── rescue.py     # RESCUE_PROMPT + helpers (§A12)
```

### Rules

- `core/` modules are pure (same input → same output, no I/O, no LLM)
- Only `data/` and `ai/` modules do I/O
- `app.py` and `api.py` only wire UI/HTTP to `analyzer.py` — no business logic
- `analyzer.py` imports from `core/`, `data/`, `ai/` and composes the flow
- `ai/prompts/` is a folder, not a file — each prompt is substantial
  enough (~60-100 lines with few-shot examples and ReAct scaffolding)
  to deserve its own module (see §A15)
- The `__init__.py` re-exports all three prompts so consumers can use
  `from ai.prompts import RESCUE_PROMPT` without knowing the layout

### Migration table (where each piece of `app.py` goes)

| Code currently in `app.py` | Move to |
|---|---|
| Pydantic models | `models.py` |
| `fetch_from_usda`, `parse_usda_response` | `data/usda_client.py` |
| `grade_food` and rubric | `core/grader.py` |
| Specificity check, brand/size hints | `core/retrieval.py` (now: diversity check) |
| Additive detection | `core/additives.py` |
| Color mapping | `core/colors.py` |
| `write_summary` and LLM | `ai/llm_chains.py` |
| Refinement prompt template | `ai/prompts/refinement.py` |
| Analysis prompt template | `ai/prompts/analysis.py` |
| Rescue prompt template | `ai/prompts/rescue.py` |
| SQLite history | `data/history.py` |
| SQLite cache | `data/cache.py` |
| Orchestration function | `analyzer.py` |
| Streamlit UI | `app.py` (kept lean) |
| `os.getenv` / settings | `config.py` |

### Imports after the refactor

```python
from nutrigrade.core.grader import grade
from nutrigrade.core.retrieval import results_are_coherent
from nutrigrade.core.additives import find_additives
from nutrigrade.data.usda_client import USDAClient
from nutrigrade.data.history import HistoryRepo
from nutrigrade.data.cache import FoodCacheRepo
from nutrigrade.ai.llm_chains import refine_chain, analysis_chain
from nutrigrade.models import Nutrition, GradedReport
```

## §A5 — FastAPI Layer (Step 30, optional)

> **Quick reference**
> - **Status:** Phase 4 stretch goal, not required for capstone
> - **Purpose:** HTTP API alongside Streamlit, same backend
> - **Endpoints:** `POST /api/grade`, `POST /api/grade/continue`, `GET /api/history`, `GET /api/health`
> - **Code home:** `api.py` at the top level (sibling of `app.py`)
> - **Rule:** thin wrapper around `analyzer.py` — no business logic

Parallel HTTP layer alongside Streamlit. Same backend, two interfaces.

### Endpoints

```
POST /api/grade
  Body:  {"query": "big mac"}
  Returns: 200 GradedReport (if specific) OR
           409 NeedsClarification (if generic — includes question + options + history)

POST /api/grade/continue
  Body:  {"history": <RefinementHistory>, "answer": "<choice>"}
  Returns: 200 GradedReport OR 409 NeedsClarification

GET /api/history?limit=20
  Returns: 200 [GradedReport, ...]

GET /api/healthz
  Returns: 200 {"status": "ok"}
```

The 409 status for "needs clarification" is intentional — it tells the
client "I can't fulfil this yet, here's what I need." Stateless,
RESTful, demoable.

### Setup

```bash
uv add fastapi "uvicorn[standard]"
uv add --dev httpx
uv run uvicorn nutrigrade.api:app --reload --port 8000
```

Open `http://localhost:8000/docs` for interactive Swagger UI.

## §A6 — Grading Rubric & Hard Caps (Step 19, expanded for Phase 2)

> **Quick reference**
> - **Reference values:** FDA Daily Values for a 2,000 kcal/day diet
> - **Limit nutrients:** sat fat (20g), sodium (2300mg), added sugar (50g), trans fat (0g hard cap)
> - **Get-enough nutrients:** fiber (28g), protein (50g)
> - **Bands:** green / yellow / orange / red based on % DV
> - **Hard caps:** trans fat > 0g → C; sugar > 30g → D; sugar > 50g → F; sat fat > 12g → D; sat fat > 20g → F; sodium > 1500mg → D; sodium > 2300mg → F
> - **Output:** letter (A-F), percentage (0-100), color hex, triggered_caps list
> - **Code home:** `core/grader.py` — pure math, no AI

Reference values use **FDA Daily Values** for a 2,000 kcal/day diet.
Each nutrient scores on its **percentage of DV per serving**.

### Tracked nutrients

| Nutrient | DV | Type |
|---|---|---|
| Saturated fat | 20 g | Limit |
| Sodium | 2,300 mg | Limit |
| Added sugar | 50 g | Limit |
| Trans fat | 0 g | Limit (hard cap) |
| Fiber | 28 g | Get enough |
| Protein | 50 g | Get enough |

### Bands — limit-type (% DV per serving)

| % DV | Color | Points |
|---|---|---|
| ≤ 5% | green | 4 |
| 5–15% | yellow | 3 |
| 15–25% | orange | 2 |
| > 25% | red | 1 |

### Bands — get-enough type (% DV per serving)

| % DV | Color | Points |
|---|---|---|
| ≥ 20% | green | 4 |
| 10–20% | yellow | 3 |
| 5–10% | orange | 2 |
| < 5% | red | 1 |

### Average → letter

Mean of the per-nutrient point scores:
- ≥ 3.6 → **A**
- ≥ 3.0 → **B**
- ≥ 2.4 → **C**
- ≥ 1.8 → **D**
- else → **F**

### Hard caps (FDA-aligned)

If any of these trigger, the grade is forced down regardless of
average. Thresholds align with FDA Daily Values: a single food that
meets or exceeds 100% of the DV for a "limit" nutrient is automatically
an F.

| Trigger | Cap |
|---|---|
| Added sugar > 50g (≥ 100% DV) | F |
| Added sugar > 30g (≥ 60% DV) | D |
| Sodium > 2,300mg (≥ 100% DV) | F |
| Sodium > 1,500mg (≥ 65% DV) | D |
| Saturated fat > 20g (≥ 100% DV) | F |
| Saturated fat > 12g (≥ 60% DV) | D |
| Trans fat > 0g (any presence) | C |
| Trans fat > 2g | F |

The **lower** of (averaged grade, capped grade) wins.

### Percentage score (0–100)

```
pct = round(((avg - 1.0) / 3.0) * 100)
```
- avg 4.0 → 100%
- avg 1.0 → 0%

When a hard cap fires, the percentage is also capped:
- F cap → max 26%
- D cap → max 46%
- C cap → max 66%

### Color mapping

A, B → green | C → yellow | D → orange | F → red

### `triggered_caps` field

`GradedReport` includes a `triggered_caps: list[str]` recording which
caps fired (e.g. `["sugar > 50g → F", "sodium > 1500mg → D"]`). The
analysis chain (§A8) uses this to lead with the deal-breaker concerns.

## §A7 — USDA Nutrient Mapping & Data Model (Step 22)

> **Quick reference**
> - **Purpose:** map USDA's nutrient IDs to clean Pydantic fields
> - **Nutrition model:** 11 named rubric fields + flexible `other_nutrients` dict for everything else
> - **Per-100g basis:** all values normalized to per-100g for consistent comparison
> - **Missing values:** default to 0 (USDA frequently omits fields like added_sugar)
> - **Code home:** `data/usda_client.py` for parsing, `models.py` for the schema

### Rubric nutrients (named fields in `Nutrition`)

| Field | nutrientId | nutrientName |
|---|---|---|
| `calories` | 1008 | Energy |
| `total_fat_g` | 1004 | Total lipid (fat) |
| `saturated_fat_g` | 1258 | Fatty acids, total saturated |
| `trans_fat_g` | 1257 | Fatty acids, total trans |
| `cholesterol_mg` | 1253 | Cholesterol |
| `sodium_mg` | 1093 | Sodium, Na |
| `total_carbs_g` | 1005 | Carbohydrate, by difference |
| `total_sugar_g` | 2000 | Sugars, total including NLEA |
| `added_sugar_g` | 1235 | Sugars, added |
| `fiber_g` | 1079 | Fiber, total dietary |
| `protein_g` | 1003 | Protein |

### Other nutrients (kept in `other_nutrients` dict)

Anything else USDA returns — vitamins, minerals, fat breakdowns, water,
caffeine, etc. — goes into a flexible dict so the UI can display
everything without us having to define every field upfront.

### The model

```python
class NutrientValue(BaseModel):
    name: str
    value: float
    unit: str

class Nutrition(BaseModel):
    fdc_id: int
    description: str
    serving_description: str         # e.g. "473 ml" or "per 100 g"
    ingredients: str | None = None   # raw USDA ingredients string if present

    # Named fields used by grader
    calories: NonNegativeFloat = 0
    total_fat_g: NonNegativeFloat = 0
    saturated_fat_g: NonNegativeFloat = 0
    trans_fat_g: NonNegativeFloat = 0
    cholesterol_mg: NonNegativeFloat = 0
    sodium_mg: NonNegativeFloat = 0
    total_carbs_g: NonNegativeFloat = 0
    total_sugar_g: NonNegativeFloat = 0
    added_sugar_g: NonNegativeFloat = 0
    fiber_g: NonNegativeFloat = 0
    protein_g: NonNegativeFloat = 0

    # Everything else USDA returned
    other_nutrients: list[NutrientValue] = []
```

### Serving size handling

If `servingSize` is absent in USDA's response, assume 100 g and label
`serving_description` as `"per 100 g"`. **Don't fabricate serving sizes.**

### Sugar fallback

If USDA doesn't return added sugar (`nutrientId 1235`), the grader
uses total sugar (`2000`) as the fallback. The displayed value is
still labeled appropriately.

## §A8 — Analysis Chain (Step 23)

> **Quick reference**
> - **Purpose:** generate the friendly summary + concerns + positives for a graded food
> - **Uses ReAct** (see §A13) — `thought` field first, then summary/concerns/positives
> - **One chain, one call** — combines summary, concerns, and positives into a single structured output
> - **Schema:** `Analysis(thought, summary, concerns[], positives[])`
> - **Code home:** `ai/llm_chains.py::analyze()` + `ai/prompts/analysis.py::ANALYSIS_PROMPT`
> - **UI reveal:** "Why?" button shows the thought field on demand

The headline LLM feature. Combines the overall summary, concerns
list, and per-nutrient explanations into **one** structured output.

### Why one chain instead of three

We considered separate chains for "overall summary," "list concerns,"
and "explain each nutrient." Combining them into one chain is better
because:
- One LLM call instead of N (faster, simpler)
- Output is generated once, cached as part of the `GradedReport`
- Click-to-reveal in the UI just shows what's already there
- Easier to test (one mock instead of three)

### Inputs

The chain receives:
- The food's `Nutrition` (all named fields + other_nutrients + ingredients)
- The grading result (letter, percentage, `triggered_caps`, per-nutrient colors)
- The detected additives (from §A9)

### Output

```python
class Concern(BaseModel):
    label: str           # "Sugar", "Sodium", "Red 40"
    severity: Literal["red", "orange", "yellow"]
    headline: str        # short — "230g sugar (460% DV)"
    explanation: str     # 3-4 sentences with quantity comparisons

class Positive(BaseModel):
    label: str           # "Protein", "Fiber"
    note: str            # short — "Good source of protein at 22g"

class Analysis(BaseModel):
    # ReAct pattern: reason first, then write the analysis (see §A13)
    thought: str             # AI's reasoning about severity ordering and priorities
    summary: str             # 1-2 sentences, the overall takeaway
    concerns: list[Concern]  # ordered by severity, then by importance
    positives: list[Positive]  # lighter-touch — what's good about this food
```

The `thought` field is the AI's reasoning step (the **ReAct pattern**
— see §A13). Before writing the summary and concerns, the model must
write a brief paragraph explaining its prioritization: which hard caps
fired, which nutrients are most concerning, what the overall pattern
is. This forced reasoning meaningfully improves consistency on
Gemma 4B — without it, the model often leads with the wrong concern
or skips hard-cap framing entirely.

The thought is shown in the developer trace and behind an optional
"Why?" button on the user-facing result.

### Prompt rules

- **Use the actual numbers.** "230g sugar" not "a lot of sugar."
- **Compare to references the user can picture.** "230g = ~50 teaspoons"
  or "= 460% of daily value" or "= more sugar than 7 candy bars."
- **Stay grounded — no medical advice.** "Excessive sugar is associated
  with..." not "you'll get diabetes."
- **Each concern is 3-4 sentences.** Scannable, not overwhelming.
- **Lead with the worst offender.** If a hard cap was triggered, that's
  the first concern.
- **Never invent numbers.** Only use values from the input.
- **Skip green nutrients.** They're not concerns.
- **Positives are lighter touch** — short notes, not paragraphs.

### Reasoning order (chain-of-thought + ReAct)

The prompt walks the model through a fixed reasoning order, written
*into the `thought` field first*. This is ReAct combined with
chain-of-thought scaffolding — the model writes its reasoning in the
thought, then produces the structured output that follows that
reasoning. On Gemma 4B, this dramatically improves consistency
(otherwise the model drifts on ordering — leading with a yellow
concern when a red hard-cap concern should come first):

1. Identify which hard caps were triggered (if any) — those are first
2. List nutrients colored red, then orange, then yellow
3. For each, plan: headline (number + % DV) → comparison → context →
   impact on grade
4. Plan the 1–2 sentence overall summary capturing the pattern
5. Plan 1–3 short positives (only green nutrients worth noting)

The `thought` field captures steps 1-2 in compressed form. Then the
model produces summary, concerns, and positives according to that
plan.

### Few-shot example for tone & comparisons

Include one full worked example in the prompt so the model anchors on
the right style. The example shows the **ReAct pattern** (thought
first, then output) paired with a **bad** output for contrast — showing
what to avoid is often more effective than rules alone.

Good output (for a chocolate milkshake, grade F):
```
thought:  "Two hard caps fired: sugar > 50g (128g, 256% DV) and
           sat fat > 20g (24g, 120% DV). Both red. Sugar is the
           more dramatic violation in both absolute and relative
           terms, so it leads. Sat fat is second. Sodium is yellow
           but worth mentioning briefly. Protein is the one positive
           — decent at 16g. Grade is F because of the two hard caps."

summary:  "This milkshake earned an F because it blew past the FDA
           daily limits for both added sugar AND saturated fat in a
           single serving. The sugar load is the headline issue."

concerns: [
  {
    severity: "red",
    headline: "128g added sugar (256% of daily value)",
    explanation: "This single shake has more than 2.5x the FDA's
                  recommended daily limit for added sugar — roughly
                  32 teaspoons, or about as much sugar as 4 candy bars
                  combined. Diets consistently high in added sugar are
                  associated with weight gain, dental issues, and
                  elevated risk of type 2 diabetes. This alone
                  triggered an automatic F."
  },
  {
    severity: "red",
    headline: "24g saturated fat (120% of daily value)",
    explanation: "One shake exceeds your full day's recommended
                  saturated fat intake..."
  }
]

positives: [
  { label: "Protein", note: "16g, mostly from milk" }
]
```

Notice the `thought` field comes first and lays out the model's
reasoning — which concerns to prioritize, why, and how the grade
follows. Then the summary, concerns, and positives follow that plan.
The model is forced to think before writing, which keeps the output
ordered and consistent.

Bad output (what NOT to do):
```
thought:  "Sugar is high. Bad food."        ← shallow, missing detail
summary:  "Don't drink this."                ← no information
concerns: [
  {
    headline: "Lots of sugar"               ← vague, no number
    explanation: "This will give you diabetes if you eat too much.
                  You should avoid foods like this entirely."
                                             ← medical advice, alarmist
  }
]
```

The bad example is doing real work — without it, rules like "no medical
advice" and "use real numbers" are abstract. With it, the model has a
concrete target to avoid. Notice the bad thought is *shallow* — that's
also a learning signal for the model. A real ReAct thought should
genuinely reason about the data, not just summarize it.

### Iterating on this prompt

This prompt is the highest-leverage one in the project — it produces
most of what the user actually reads. Iterate on it with real foods
from the demo set (banana, big mac, milkshake, etc.) and tune the
few-shot example until outputs feel right. Don't try to perfect it
upfront; ship version 1, then refine based on actual outputs.

### Where it sits in the flow

```
USDA → Nutrition → Grader → (additive detection) → Analysis chain → GradedReport
```

The output is part of the cached `GradedReport`, so cache hits don't
re-run this chain.

## §A9 — Additive Detection (Step 24)

> **Quick reference**
> - **Purpose:** flag concerning food additives (artificial colors, certain preservatives) from ingredient lists
> - **Method:** hard-coded list + regex match against USDA's `ingredients` field
> - **Code home:** `core/additives.py` — pure logic, no AI
> - **Honest behavior:** if `ingredients` is None or empty, return `[]` — never fake detections
> - **UI:** small section below concerns if additives found, omitted entirely otherwise

Hard-coded list of concerning food additives. Detected by regex match
against USDA's `ingredients` field when it's present.

### The list

Starting set, easy to extend:

```python
ADDITIVES = {
    # Artificial colors
    "Red 40": ["red 40", "red #40", "fd&c red no. 40", "allura red"],
    "Yellow 5": ["yellow 5", "yellow #5", "fd&c yellow no. 5", "tartrazine"],
    "Yellow 6": ["yellow 6", "yellow #6", "fd&c yellow no. 6", "sunset yellow"],
    "Blue 1": ["blue 1", "blue #1", "fd&c blue no. 1", "brilliant blue"],
    "Blue 2": ["blue 2", "blue #2", "fd&c blue no. 2", "indigotine"],
    "Red 3": ["red 3", "red #3", "fd&c red no. 3", "erythrosine"],

    # Preservatives
    "BHA": ["bha", "butylated hydroxyanisole"],
    "BHT": ["bht", "butylated hydroxytoluene"],
    "Sodium benzoate": ["sodium benzoate"],
    "Potassium sorbate": ["potassium sorbate"],

    # Nitrates / nitrites
    "Sodium nitrate": ["sodium nitrate"],
    "Sodium nitrite": ["sodium nitrite"],

    # Sweeteners
    "Aspartame": ["aspartame"],
    "Sucralose": ["sucralose"],
    "High fructose corn syrup": ["high fructose corn syrup", "hfcs"],
    "Acesulfame potassium": ["acesulfame potassium", "ace-k", "acesulfame-k"],

    # Other
    "MSG": ["monosodium glutamate", "msg"],
}
```

### Detection logic

```python
def find_additives(ingredients: str | None) -> list[str]:
    """Return canonical names of additives found in the ingredients string."""
    if not ingredients:
        return []
    lower = ingredients.lower()
    found = []
    for canonical, aliases in ADDITIVES.items():
        if any(re.search(rf'\b{re.escape(alias)}\b', lower) for alias in aliases):
            found.append(canonical)
    return found
```

### Honest behavior when data is missing

USDA only returns ingredients for **branded foods**, and even then it's
inconsistent. When `ingredients` is None or empty:
- `find_additives()` returns `[]`
- The UI shows "Ingredient data not available for this food"
- No fake detection, no false reassurance

### How additives become concerns

The analyzer hands the detected additive list to the analysis chain
(§A8). The chain treats each one as a concern, writes a short
contextual explanation, and includes it in the `concerns` list with
severity "yellow" or "orange" depending on the additive.

## §A10 — UI Layout (Step 29)

> **Quick reference**
> - **Two audiences:** end users (clean view) + technical reviewers (dev trace toggle)
> - **Color palette:** green/amber/orange/red grade colors, neutral chrome background
> - **Hidden by default:** FDC IDs, cache jargon, refinement labels, dev trace
> - **Visible:** grade hero, friendly summary, concerns (with severity borders), positives (pills), nutrition grid, USDA citation
> - **"Why?" button:** reveals the AI's `thought` field from analysis or rescue (see §A13)
> - **Refinement & rescue questions:** rendered the same way (friendly question + option cards)
> - **Code home:** `app.py` for Streamlit, custom CSS injected at top

The UI has two audiences: **end users** (who want to know if their
food is healthy) and **technical reviewers / you during the demo**
(who want to see the system working). The design serves both with a
clean default user view and an opt-in developer view.

### Design principles

- **User-friendly first.** No internal jargon ("refinement needed",
  "cache miss", "FDC ID #98765") visible by default. Internal language
  goes in the dev panel.
- **Colorful but professional.** The grade colors do the heavy lifting
  visually — green / amber / orange / red telegraph health at a glance.
  Background and chrome stay neutral so the grade pops.
- **Confidence through transparency.** The data source (USDA) is
  always cited at the bottom of every result. Builds trust without
  cluttering the main view.
- **Progressive disclosure.** Summary first, concerns next, full
  nutrient breakdown in an expander. Users who want detail can dig in;
  users who want a verdict get it in 2 seconds.

### Color system

Tie the visual palette directly to the grade rubric so the UI feels
consistent. All colors meet WCAG AA contrast.

| Grade | Hex | Use |
|---|---|---|
| A / B | `#2E7D32` (green) | grade badge bg, success accents |
| C | `#F9A825` (amber) | grade badge bg, mild-warning accents |
| D | `#EF6C00` (orange) | grade badge bg, moderate-warning accents |
| F | `#C62828` (red) | grade badge bg, severe accents |

Concern severity uses the same scale:
- **Red border** for severity="red" concerns (hard caps, > 100% DV)
- **Orange border** for severity="orange" (60-100% DV)
- **Amber border** for severity="yellow" (15-60% DV)

Background and chrome:
- App background: warm off-white `#FAF8F4` (or Streamlit dark-mode default)
- Card surfaces: pure white with subtle 1px border `#E8E4DC`
- Body text: `#2C2C2A`
- Secondary text: `#6B6B68`
- Brand accent (sidebar header, links): `#1A6B4D` — a calm teal-green
  that complements the grade greens without competing

### Sidebar (always visible)

- **App branding:** "🥗 NutriGrade" in the brand accent color, with a
  one-line tagline like "Know what's in your food, instantly."
- **Recent lookups:** last 8 graded foods as compact rows. Each row
  shows a tiny grade pill + food name. Clicking re-renders.
- **About section:** "Powered by USDA FoodData Central" + a small note
  about the rubric (link to the methodology if you want).
- **Settings expander** (collapsed by default), containing:
  - Toggle: "Show developer trace" → reveals the trace panel in the
    main view (off by default for end users, on for demos)
  - **AI provider section** (see §A14):
    - Radio: "🦙 Gemma (local)" vs "✨ Claude (cloud)" — defaults to Gemma
    - Conditional dropdown: when Claude is selected, shows model options
      (Sonnet 4.6 default, Haiku 4.5, Opus 4.7)
    - The Claude option is disabled with a caption if `ANTHROPIC_API_KEY`
      is not set in `.env`
  - Button: "Clear cache" — with a small note showing cache size
  - Button: "Clear history"
  - Model and data source info (purely informational)

### Main result area

**Grade hero card** — the showpiece. Large colored card with:
- The letter grade at ~80px, white on the grade color
- The percentage below it (~24px)
- The food name to the right (~22px, bold)
- A short data citation underneath: "USDA FoodData Central"

**Summary band** — directly below the hero. The 1-2 sentence LLM
summary in body text. Plain background, no card. Reads like a friend
explaining the grade.

**Concerns section** — a stack of cards, each with:
- A colored vertical strip on the left (severity color)
- The headline (number + % DV) in bold at the top
- The 3-4 sentence explanation in body text below
- Cards are visually distinct but live in a uniform grid so they're
  easy to scan

If there are no concerns: skip the section entirely. Don't show "No
concerns 🎉" — silence is a better signal.

**Positives section** — lighter touch than concerns. A small horizontal
strip with green-tinted pills, each showing the positive label and
short note. One row, scrollable if many.

**Full nutrition expander** — collapsed by default. When expanded,
shows the rubric nutrients with color pills (matching the grade
colors), then vitamins/minerals from `other_nutrients` in a
two-column layout.

**Footer citation** — a small line at the bottom: "Data: USDA
FoodData Central · Item #{fdc_id}". This is the user-facing version
of the FDC ID — present but unobtrusive.

**"Why?" disclosure** — a small expandable button next to the grade
hero or at the bottom of the analysis section, labeled something like
"Why this grade?" or just "Why?" with a small chevron. Collapsed by
default. When expanded, it shows the AI's `thought` field from the
analysis chain (and the rescue agent's `thought`, if the result came
through rescue).

This makes the **ReAct** reasoning (see §A13) visible to curious users
without cluttering the default view. The thought is rendered as plain
prose in a soft-tinted box — not a code block, not a chat bubble. Just
the AI's reasoning in plain English, like reading a footnote.

Example expanded:

> *Why this grade?*
> Two hard caps fired — sugar above 50g and saturated fat above 20g.
> Sugar is the more dramatic violation in both absolute and relative
> terms, so it leads the concerns. Protein is the one positive worth
> mentioning. The grade is F because of the two hard caps.

For rescue agent thoughts (when a query was rewritten or asked about),
the same pattern applies — the thought appears in the "Why?" panel
explaining the AI's interpretation of the user's query.

### Refinement question presentation

When the analyzer returns a `RefinementNeeded` result, the UI shows:

- **A friendly question header** in the brand accent color, like the
  question came from a person ("Which kind of coffee did you have in
  mind?") — never "refinement needed" or "specify type".
- **A grid of option cards** below — each card has the option label
  in regular text size, a small contextual hint underneath if useful
  (e.g. "around 5 calories" or "around 200 calories"), and a hover
  state. **No FDC IDs visible.** The mapping happens behind the scenes.
- **Free-text fallback** at the bottom — a small input below the
  cards labeled something like "Don't see what you're looking for?
  Describe it here." Pressing Enter or clicking the search button
  restarts the flow with the typed query (per §A1's escape hatch).

Rule: the user should never know the words "refinement", "FDC ID",
"cache hit", "diversity check", or any other internal term. The UI
simply asks a question and shows options.

### Cache hit/miss — user-visible vs developer-visible

The original spec used 🟢 "Loaded from cache" / 🔵 "Fresh from USDA"
badges. That's developer language. User-facing version:

- **Cache hits** show no badge at all, OR a subtle "⚡ Instant" pill if
  you want to convey the speed benefit
- **Fresh lookups** show no badge — that's the default state
- The trace panel (dev mode) shows the full cache-hit / cache-miss
  / write-back log

### Developer trace panel

Hidden by default behind the "Show developer trace" toggle in the
sidebar. When enabled, appears as a collapsible section above the
result area showing:

- The 12-step trace from §A11 ([1] cache check, [2] USDA search, etc.)
- Cache hit/miss with the FDC ID
- Whether refinement was needed
- Any caps that fired
- LLM call count and latency

This is what makes the app demo-able to technical reviewers — you can
flip the toggle and walk through exactly what happened. End users
never see it.

### Streamlit implementation notes

- `st.markdown(unsafe_allow_html=True)` for the grade hero card and
  concern cards — Streamlit's native `st.metric` is too constrained
  for the visual style we want.
- `st.expander()` for the full nutrition table and developer trace.
- `st.columns()` for the option-card grid in refinement.
- `st.session_state` for refinement state across reruns (round number,
  pending query, picked options).
- `st.button()` for option cards, but styled with custom CSS via
  `st.markdown` for the card look — Streamlit's default button is too
  small for what we want.
- Custom CSS injected once at the top of `app.py` via
  `st.markdown("<style>...</style>", unsafe_allow_html=True)`.
- Toggle for dev trace: `st.sidebar.toggle("Show developer trace",
  value=False)`.

### What NOT to do

- Don't show FDC IDs, cache keys, or rubric internals to end users
- Don't use the words "refinement", "diversity check", or "hard cap"
  in user-facing copy
- Don't include emojis in the brand identity (a single 🥗 in the
  sidebar header is fine; sprinkling emojis throughout is not)
- Don't show "no concerns 🎉" placeholder text — just omit the section
- Don't auto-scroll, auto-refresh, or animate things; Streamlit handles
  state transitions naturally and animations feel jarring
- Don't put more than one CTA on screen at a time

## §A11 — Analyzer Orchestration

> **Quick reference**
> - **Role:** the conductor — imports from `core/`, `data/`, `ai/` and composes the full flow
> - **Entry points:** `analyze(query)`, `continue_with_pick(fdc_id)`, `continue_with_text(text)`
> - **Return type union:** `GradedReport | RefinementNeeded | ClarificationNeeded | AnalysisError`
> - **Stateless:** each call is independent; state lives in UI session
> - **Two cache layers:** query string (fast pre-check) + FDC ID (post-resolution)
> - **Error handling:** graceful — USDA failure / LLM failure / DB failure are all non-fatal
> - **Code home:** `analyzer.py` at the top level

The `analyzer.py` module is the conductor. It imports from `core/`,
`data/`, and `ai/`, and composes them into one coherent flow. UI
layers (Streamlit, FastAPI) call into `analyzer.py` and never touch
USDA, the LLM, or the database directly.

### The full flow

```
User query
   │
   ▼
[1] Cache check (by query string, fast pre-check)
   │      ├── hit → return cached GradedReport (skip everything below)
   │      └── miss → continue
   ▼
[2] USDA search (always — even on vague queries)
   │      ├── 0 results → return error "No matches for that food"
   │      └── 1+ results → continue
   ▼
[3] Diversity check on top N results
   │      ├── coherent (tight calorie spread) → skip refinement
   │      └── scattered → continue to [4]
   ▼
[4] Refinement chain (LLM clusters real results)
   │      ├── done=true → use chosen_fdc_id
   │      └── done=false → return RefinementTurn to UI, wait for pick
   │                       (UI calls analyzer again with the pick)
   ▼
[5] Cache check by FDC ID (more stable than query string)
   │      ├── hit → return cached GradedReport
   │      └── miss → continue
   ▼
[6] Parse USDA response → Nutrition object
   ▼
[7] Grade (rubric + hard caps + percentage + colors)
   ▼
[8] Detect additives (regex on ingredients string)
   ▼
[9] Analysis chain (LLM generates summary + concerns + positives)
   ▼
[10] Assemble GradedReport
   ▼
[11] Write to cache (by FDC ID)
   ▼
[12] Append to history
   ▼
Return GradedReport
```

### Why two cache checks

- **Step [1]** uses the raw query string. Catches exact-repeat lookups
  fast — "big mac" twice in a row hits this on the second call.
- **Step [5]** uses the FDC ID after refinement resolves. Catches
  phrasing variation — "big mac", "Big Mac", and "mcdonalds big mac"
  all converge to the same FDC ID and hit this layer.

The two-layer design means most repeat traffic skips USDA and the LLM
entirely, but variant phrasings still benefit from prior work.

### State across refinement turns

When the user is in the middle of a refinement question, the analyzer
returns early with a `NeedsClarification` object instead of a
`GradedReport`. The UI is responsible for:
1. Showing the question and options to the user
2. Storing the returned `history` list (passes back on next call)
3. Calling `analyzer.continue_with_choice(raw_query, history, chosen_fdc_ids)`
   when the user picks an option

The analyzer itself is stateless — each call is independent. State
lives in `st.session_state` (Streamlit) or in the request body
(FastAPI). This keeps the analyzer testable without faking session
state.

### Return types

The analyzer exposes two methods, both returning the same union type:

```python
analyze(query: str) -> AnalyzeResult
    # Fresh query. Returns either a finished GradedReport or a
    # NeedsClarification (the user needs to pick from grouped options).

continue_with_choice(raw_query, history, chosen_fdc_ids) -> AnalyzeResult
    # User picked an option from a refinement question. Returns a
    # finished GradedReport (or another NeedsClarification if the
    # 2-round cap hasn't been hit yet).
```

```python
# When refinement is needed:
@dataclass
class NeedsClarification:
    question: str                 # the bundled question to show
    options: list[dict]           # [{"label": ..., "fdc_ids": [...]}]
    history: list[dict]           # rounds so far, for the 2-round cap
    raw_query: str                # original query, for free-text restart

# When grading completes:
class GradedReport(BaseModel):
    fdc_id: int
    raw_query: str
    nutrition: Nutrition
    grade: str
    color: str
    percentage: int
    triggered_caps: list[str]
    color_map: dict[str, str]     # nutrient → color
    additives: list[str]
    analysis: Analysis            # from §A8
    cache_hit: bool               # for the UI badge
    refinement_history: list[dict]

# The union type:
AnalyzeResult = GradedReport | NeedsClarification
```

The UI pattern-matches on which type came back and renders accordingly.

### Error handling

- **USDA returns 0 results** → return a clean error object, not a raise
- **USDA times out** → retry once with a 5s timeout, then surface error
- **LLM returns malformed structured output** → Pydantic validation
  raises; catch it and either retry once or fall back to a simpler
  prompt with no few-shot
- **DB write fails** → log it, but still return the GradedReport. A
  failed cache write shouldn't break the user experience.

### Why this module exists

Without `analyzer.py`, the Streamlit UI would have to know about USDA,
the LLM, the cache, and the grader — making it impossible to test and
impossible to swap out for a different UI. With it:

- Streamlit's `app.py` becomes ~50 lines of pure UI code
- FastAPI's `api.py` is a thin wrapper translating HTTP to analyzer calls
- Tests can call `analyzer.analyze("big mac")` with fakes for USDA + LLM
- The flow is visible in one place instead of scattered across files

This is the orchestration boundary that makes everything testable.

---

## §A12 — Query Rescue Agent (Step 21.5)

> **Quick reference**
> - **Status:** the ONE genuinely agentic part of NutriGrade — the LLM controls flow here
> - **Triggers:** USDA returns 0 results OR weak match (query terms missing from results)
> - **Three actions:** `rewrite` (silent retry), `ask` (clarify with user), `give_up` (graceful error)
> - **Uses ReAct** (see §A13) — `thought` field first, then `action`
> - **Cap:** 2 rounds, then force `AnalysisError`
> - **Schema:** `RescueAction(thought, action, new_query?, question?, options?)`
> - **Code home:** `ai/llm_chains.py::rescue_query()`, `ai/prompts/rescue.py::RESCUE_PROMPT`, weak-match check in `core/retrieval.py`
> - **UI:** silent rewrite shows "Interpreted as: X" banner; ask renders same as refinement; give_up shows clean error

The "rescue" is the one part of NutriGrade where the AI genuinely
**makes decisions about app flow**, not just generates text inside a
slot. Everywhere else, `analyzer.py` decides what happens next. Here,
the LLM does — within a tightly scoped set of three options.

### Why this earns its place

USDA's database has rigid clinical naming. Users type natural language.
That mismatch breaks the app in two specific ways:

1. **Slang and abbreviations** — user types "PSL", USDA expects
   "pumpkin spice latte". Zero results.
2. **Cultural/colloquial dishes** — user types "korean fried chicken",
   USDA returns plain "Chicken, fried". A result is returned, but it
   doesn't match what the user asked for.

In both cases, the AI has a job humans rarely do well: bridge natural
language to database phrasing. That's a real decision worth giving the
LLM autonomy over. Outside this one spot, the flow is still
deterministic.

### What "agent" means here

This is the only place where the LLM:
- **Decides what action the app takes next** (rewrite vs ask vs give up)
- **May initiate a conversation** with the user without being prompted to
- **Can loop** (up to 2 rounds)

It's the narrowest possible agent — three actions, two rounds max,
specific trigger condition. Not a full autonomous agent driving the
whole flow.

### When the rescue fires

Two triggers, both checked after the initial USDA search:

1. **Zero results.** USDA returned an empty list.
2. **Weak match.** USDA returned results but they look like poor
   matches for the query. Heuristic in `core/retrieval.py`:
   - The query contains terms (length ≥ 4) that appear in zero of
     the result descriptions, AND
   - The top result's description shares < 50% of the query's
     significant words

   Example: query "korean fried chicken" → USDA returns "Chicken,
   fried, breast". The word "korean" appears in zero results, so the
   match is weak.

If neither trigger fires, the flow continues normally.

### The three actions

The rescue chain returns one of:

```python
class RescueAction(BaseModel):
    # ReAct pattern: reason first, then act (see §A13)
    thought: str                      # AI's reasoning, written before the decision
    action: Literal["rewrite", "ask", "give_up"]
    new_query: str | None = None      # if action == "rewrite"
    question: str | None = None       # if action == "ask"
    options: list[str] | None = None  # 2-4 user-facing options when asking
```

The `thought` field is the AI's reasoning step. It's required and
populated first — the model has to write its reasoning before
producing the action. This is the **ReAct pattern** (see §A13 for the
full concept). On Gemma 4B, this meaningfully improves decision
quality compared to picking an action directly.

The thought is shown in the developer trace (always) and optionally
behind a "Why?" button on the user-facing result (UX choice — keeps
the clean view while letting curious users see the AI's reasoning).

**`rewrite`** — LLM is confident the query needs a cleaner phrasing and
the rewrite is unambiguous. App silently retries with the new query and
continues. The result UI shows a small "Interpreted as: X" note so the
user can see what happened.

**`ask`** — LLM thinks the query is ambiguous. Returns a clarifying
question and 2-4 options for the user to pick. UI renders this the
same way as a refinement question (per Q4 of the design — UX
consistency over visual differentiation).

**`give_up`** — LLM thinks no rewrite would help (e.g. "dragonfruit
pizza" — coherent words, but USDA genuinely doesn't have it). App
returns `AnalysisError` cleanly.

### When to rewrite silently vs ask

This is a judgment call that lives in the LLM, but the prompt should
anchor it with examples:

**Silent rewrite when:**
- The query has a clear, well-known expansion ("PSL" → "pumpkin spice latte")
- The query contains a brand name USDA doesn't index but the food
  itself is generic ("Tim Hortons coffee" → "coffee")
- Removing a modifier yields a clean USDA-friendly query ("delicious
  iced coffee" → "iced coffee")

**Ask when:**
- The abbreviation could mean multiple things ("BLT" could be a
  sandwich or a brand)
- The query is in another language or uses special characters and the
  rewrite isn't obvious
- Removing terms changes the meaning materially ("korean fried chicken"
  isn't just "fried chicken" — the user specifically meant the Korean
  preparation)

**Give up when:**
- The food is something USDA genuinely doesn't track (very regional
  dishes, novel processed foods, niche brand items)
- The query is gibberish or nonsense
- Two rewrites have already failed

### Rescue rounds

Hard cap of 2 rounds. Tracked in `analyzer.py` state. Round 1 fires
when USDA's first search trips a trigger. Round 2 is allowed only if
the user's response to a Round 1 "ask" produces a new query that also
trips a trigger. After that, force `AnalysisError` rather than
continue.

### The rescue chain

Lives in `ai/llm_chains.py` as `rescue_query()`. Imports the
`RESCUE_PROMPT` from `ai.prompts` (re-exported by
`ai/prompts/__init__.py` from `ai/prompts/rescue.py`).

```python
def rescue_query(
    original_query: str,
    usda_results: list[dict],  # may be empty for zero-results case
    round_number: int,
) -> RescueAction:
    """
    Decide what to do when USDA didn't return useful results.
    Returns one of three actions: rewrite, ask, or give_up.
    """
```

### The prompt (ReAct-style few-shot)

The rescue prompt uses the **ReAct pattern** (see §A13). Every
few-shot example shows the AI reasoning first, then producing the
decision. Each example becomes a fake "User: ... → Assistant: ..."
exchange in the prompt.

The prompt needs at minimum these four examples:

**Example 1 — clear silent rewrite (PSL):**
```
User: Query: "PSL" | USDA returned: (empty)
Assistant:
  thought: "PSL is a well-known abbreviation for 'pumpkin spice latte'.
            USDA likely has the full name in its database. This expansion
            is widely recognized and unambiguous — confident rewrite."
  action: rewrite
  new_query: "pumpkin spice latte"
```

**Example 2 — legitimate ambiguity (kbbq):**
```
User: Query: "kbbq" | USDA returned: (empty)
Assistant:
  thought: "kbbq is slang for Korean BBQ, but that's a category of
            cuisine, not a single food. USDA needs a specific dish
            like bulgogi or galbi. I shouldn't guess — the nutrition
            profiles differ significantly. The user needs to clarify."
  action: ask
  question: "Which Korean BBQ dish did you have?"
  options: ["Bulgogi (marinated beef)", "Galbi (short ribs)", "Pork belly"]
```

**Example 3 — weak match (korean fried chicken):**
```
User: Query: "korean fried chicken" | USDA returned: "Chicken, fried, breast"
Assistant:
  thought: "USDA returned generic fried chicken, but the user specifically
            said Korean fried chicken — which has different breading and
            sauce. The 'korean' part of the query isn't in any result.
            The generic chicken might be close enough, but I should
            confirm rather than assume."
  action: ask
  question: "USDA only has generic fried chicken — is that close enough?"
  options: ["Yes, use generic fried chicken", "No, try a different food"]
```

**Example 4 — give up (dragonfruit pizza):**
```
User: Query: "dragonfruit pizza" | USDA returned: (empty)
Assistant:
  thought: "Dragonfruit pizza isn't a standard food. The words are
            coherent but no real database would have this exact item.
            No rewrite would help — there's no canonical version of
            this dish. Better to fail cleanly than guess."
  action: give_up
```

Notice the consistent pattern: **thought first, action second.** The
thought explains the AI's reasoning. The action commits to a decision.
The thoughts demonstrate the *kind* of reasoning we want — considering
context, weighing ambiguity, knowing when to ask vs assume vs give up.

Without these reasoning steps in the examples, Gemma 4B would just
pattern-match on surface features (length of query, presence of
brand words) and miss the deeper judgment. With them, the model
internalizes "think about whether this is ambiguous, then decide."

### How it changes §A11 (analyzer flow)

The flow diagram from §A11 gets one new branch:

```
USDA search
  │
  ├─ Zero results OR weak match
  │     ↓
  │  Rescue chain  ──→  rewrite ──→ retry USDA (counts as round 2 if it fails again)
  │     │            ├─ ask    ──→ return ClarificationNeeded to UI
  │     │            └─ give_up ──→ return AnalysisError
  │     ↓
  │  After 2 rounds, force AnalysisError
  │
  └─ Good results → normal flow (diversity check, refine if needed, etc.)
```

### How it changes the analyzer's return type

The union in §A11 grows by one:

```python
AnalyzerResult = Union[
    GradedReport,
    RefinementNeeded,
    ClarificationNeeded,   # NEW — rescue agent asking for clarification
    AnalysisError,
]
```

`ClarificationNeeded` carries the question + options just like
`RefinementNeeded`, but is rendered with the same visual style so
users see one coherent UX (per Q4 of design).

### UI behavior

Same card pattern as refinement (per Q4). The friendly question card
contains the LLM's question + option cards. User picks → flow
continues. No FDC IDs visible. No "rescue" or "agent" jargon shown.

For the silent-rewrite path, the result UI gets a small line above
the grade hero: *"Interpreted as: pumpkin spice latte. Not what you
meant? Try a different search."* — keeping the user informed without
asking permission.

### Why two rounds, not one or three

- One round is too punishing — a single ambiguous interaction kills
  the lookup
- Three rounds is annoying — by then the user knows the app can't
  understand them, no point continuing
- Two rounds is the sweet spot: one shot to ask, one shot to refine
  if the user's clarification still misses

### Edge cases

- **User picks "Other" on an ask option** → treat as round 2 free-text,
  feed back into rescue with round_number=2
- **Rewrite succeeds but the new query also returns weak matches** →
  rescue fires again (round 2), forcing a give-up if it triggers again
- **LLM fails or times out during rescue** → fall back to graceful
  `AnalysisError` rather than retry. Don't compound failures.

### Why this is the right amount of agent behavior

You could push further — let the LLM also decide whether to skip the
diversity check, or whether to call the analysis chain at all. Don't.
Every additional decision point trades reliability for flexibility,
and at this model size (Gemma 4B), reliability wins.

Keep the agent in one place. Make that one place really good. The
story for your presentation is stronger when the agent behavior is
**specifically scoped to where it earns its keep.**

---

## §A13 — ReAct Prompting

> **Quick reference**
> - **What:** prompt pattern where the LLM writes its reasoning (`thought`) before committing to an output
> - **Why:** forced reasoning meaningfully improves decision quality on small models like Gemma 4B
> - **Version used:** "light" ReAct — one thought + one action per LLM call (NOT multi-step loops)
> - **Used in:** §A12 rescue agent, §A8 analysis chain
> - **NOT used in:** §A1 refinement (pure clustering, no judgment needed)
> - **Schema convention:** `thought: str` as the FIRST field in the Pydantic output model
> - **UI exposure:** hidden by default; visible in dev trace and behind "Why?" button (see §A10)

This appendix explains **ReAct prompting**, a technique used by two
of NutriGrade's chains: the rescue agent (§A12) and the analysis chain
(§A8). It's a concept reference for spec readers and for future-you.

### What ReAct is

ReAct stands for **Reasoning + Acting**. It's a prompt pattern where
the LLM is forced to *reason out loud* before committing to an output.
Instead of the LLM jumping straight to an answer, it first writes a
short reasoning block, then produces the final output.

The pattern from the original 2022 Google paper:

```
Thought: [AI explains its reasoning here]
Action: [AI commits to a decision/output]
```

In NutriGrade we use the **light** version of ReAct — one thought
followed by one action, in a single LLM call. The full version
(multi-step think → act → observe → repeat) is more powerful but
unreliable at Gemma 3 4B parameter scale. Light ReAct gives most of
the benefit with much less risk.

### Why ReAct improves output quality on small models

Three reasons, all well-documented in the LLM research literature:

**1. Forced reasoning reduces sloppy outputs.** When a small model
goes straight to an answer, it sometimes produces incorrect or
inconsistent output. When forced to reason first, the model's own
written-out reasoning anchors its final answer.

**2. The reasoning surfaces context the model would otherwise skip.**
For example, when deciding what to do with "PSL", the thought step
forces Gemma to consider what PSL might mean before picking an action.
Without that explicit reasoning, the model might pick "rewrite" or
"ask" based on shallow pattern-matching alone.

**3. Reasoning is debuggable.** When the agent makes a weird decision
(rewrites something it shouldn't), you can read the thought and
understand the failure. With pure structured output, the model gives
you a decision but you can't see *why* — you're guessing at the
failure mode.

### How ReAct works in NutriGrade

The implementation is simple: add a `thought` field to the chain's
output schema, restructure the few-shot examples to show explicit
reasoning, and instruct the model to think before acting in the
system prompt.

```python
# Pseudocode showing the pattern in a Pydantic schema
class ChainOutput(BaseModel):
    thought: str       # AI's reasoning, written first
    # ... rest of the output fields
```

The model is told: "Before producing the rest of the output, write
a brief thought explaining your reasoning." The few-shot examples
demonstrate the pattern by example.

### When to use ReAct (and when not to)

**Use ReAct when:**
- The output involves a decision or judgment (rescue's three actions,
  analysis's severity ordering)
- The model is small and would benefit from forced structured reasoning
- You want debuggable outputs

**Don't use ReAct when:**
- The chain is a pure data transformation (e.g. refinement's clustering
  is mechanical — group these results — no real decision)
- The model is already large and reliable on its own (frontier models
  reason internally without needing the explicit pattern)
- You're optimizing for latency and the chain runs in tight loops

### Where it's used in this project

| Chain | Section | Uses ReAct? | Why |
|---|---|---|---|
| Rescue agent | §A12 | ✓ Yes | True decision-making — pick one of three actions |
| Analysis chain | §A8 | ✓ Yes | Severity ordering and concern prioritization is judgment |
| Refinement chain | §A1 | ✗ No | Pure clustering — no judgment needed |

### Light ReAct vs full ReAct

**Light ReAct (what we use):**
- One LLM call per chain invocation
- The thought is part of the same structured output as the action
- Predictable cost: 1 call, 1 response, done
- Safe on Gemma 4B

**Full ReAct (not used in this project):**
- Multiple LLM calls in a loop (think → act → observe → think → act...)
- Agent decides when to stop on its own
- More powerful for complex multi-step problems
- Unreliable on small models — Gemma tends to loop forever, hallucinate
  fake observations, or contradict its own thoughts

If a future version of NutriGrade adds more sophisticated multi-step
reasoning (e.g. an agent that searches USDA multiple times before
deciding), full ReAct becomes worth revisiting. For now, light ReAct
is the right ceiling.

### The capstone story this earns

> "My agentic decisions use ReAct prompting — the AI writes a brief
> reasoning step before committing to an action. This is the light
> version of ReAct from the 2022 Yao et al. paper, scoped to single
> LLM calls. Full multi-step ReAct would be more powerful but small
> local models like Gemma 4B aren't reliable enough for long agent
> loops. Light ReAct gives me forced reasoning, debuggable outputs,
> and improved decision quality at the cost of one extra field in
> my output schema."

This shows you understand the technique AND its limits — stronger
than just adopting the buzzy version.

---

## §A14 — Dual-Provider Support

> **Quick reference**
> - **Purpose:** support both local (Ollama/Gemma) and hosted (Anthropic/Claude) LLM providers
> - **Default:** Ollama with Gemma 3 4B (local, free, offline)
> - **Switch:** sidebar radio button toggles to Anthropic; second dropdown picks the Claude model
> - **Claude model default:** Sonnet 4.6 (`claude-sonnet-4-6`)
> - **Selectable models:** Haiku 4.5, Sonnet 4.6, Opus 4.7 (configurable list)
> - **Cache:** composite key `(fdc_id, provider)` so each model has its own cached outputs
> - **Gating:** Anthropic option only appears if `ANTHROPIC_API_KEY` is set in `.env`
> - **Code home:** `ai/llm_chains.py::get_llm()`, sidebar code in `app.py`, schema update in `data/cache.py`

### Why this exists

Two reasons, both real:

**Provider portability is a real engineering virtue.** LangChain abstracts
away the model provider, so the same prompts and chains work across
different LLMs. Demonstrating this in the actual UI proves the
architecture isn't accidentally coupled to one model.

**Different models have different strengths.** Gemma 4B is fast,
private, and free — but limited in reasoning. Claude is more capable
but costs money and requires an internet connection. Letting users
choose at runtime means each query can use the right model for its
needs.

For the capstone demo, this also creates a powerful visual moment:
run the same query under each provider and watch the difference in
output quality, side by side.

### The provider selector flow

```
User opens the app
   │
   ▼
Sidebar shows current provider (defaults to Ollama)
   │
   ▼
User toggles radio to Anthropic
   │
   ├── If ANTHROPIC_API_KEY not set → option is disabled with tooltip
   │   "Set ANTHROPIC_API_KEY in .env to enable Claude"
   │
   └── If key is set → Anthropic becomes active
           │
           ▼
       Model dropdown appears below the radio
           │
           ▼
       User picks Haiku / Sonnet / Opus (default: Sonnet 4.6)
           │
           ▼
       Selection stored in st.session_state
           │
           ▼
       Next query uses the selected provider + model
```

### The `get_llm()` factory

Lives in `ai/llm_chains.py`. The chains call this instead of constructing
their own LLM directly. This is the seam that makes provider swapping
work cleanly:

```python
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
import os

# Available Claude models (configurable, easy to update)
ANTHROPIC_MODELS = {
    "haiku":  "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",    # default
    "opus":   "claude-opus-4-7",
}

def get_llm(provider: str = "ollama", model: str | None = None,
            temperature: float = 0.2):
    """
    Returns a configured LLM. The chains call this rather than
    instantiating their own.

    provider: "ollama" (default) or "anthropic"
    model: model id within that provider; None uses provider's default
    """
    if provider == "ollama":
        model = model or "gemma3:4b"
        return ChatOllama(
            model=model,
            base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            temperature=temperature,
        )
    elif provider == "anthropic":
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set — cannot use Anthropic provider"
            )
        # Default to Sonnet 4.6 if no model specified
        model = model or ANTHROPIC_MODELS["sonnet"]
        return ChatAnthropic(
            model=model,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

Each chain function (`refine`, `analyze`, `rescue_query`) takes a
`provider` and `model` parameter that flows through to `get_llm()`.
The analyzer passes whatever's selected in the UI.

### The Streamlit sidebar

```python
# In app.py — sidebar settings section
with st.sidebar:
    st.markdown("### Settings")

    show_trace = st.checkbox("Show developer trace")

    st.markdown("**AI Provider**")
    anthropic_available = bool(os.getenv("ANTHROPIC_API_KEY"))

    provider = st.radio(
        "Provider",
        options=["ollama", "anthropic"],
        format_func=lambda x: {
            "ollama": "🦙 Gemma (local)",
            "anthropic": "✨ Claude (cloud)"
        }[x],
        index=0,  # default: ollama
        disabled=not anthropic_available,
        help="Local is free and offline. Cloud is faster and smarter."
    )

    if not anthropic_available:
        st.caption("Set ANTHROPIC_API_KEY in .env to enable Claude")

    # Model dropdown appears only when Anthropic is selected
    model = None
    if provider == "anthropic":
        model_choice = st.selectbox(
            "Claude model",
            options=["sonnet", "haiku", "opus"],
            format_func=lambda x: {
                "sonnet": "Sonnet 4.6 (balanced, recommended)",
                "haiku":  "Haiku 4.5 (cheapest, fastest)",
                "opus":   "Opus 4.7 (most capable, costly)",
            }[x],
            index=0,  # default: sonnet
        )
        model = ANTHROPIC_MODELS[model_choice]

    # Stash in session state so analyzer can use it
    st.session_state["provider"] = provider
    st.session_state["model"] = model
```

The analyzer reads `st.session_state["provider"]` and
`st.session_state["model"]` and passes them through to each chain
call.

### Cache schema update

The food cache (§A3) needs a composite key so each provider has its
own cached outputs. Without this, you'd cache a Claude-generated
analysis, then switch to Gemma, and see the Claude output show up
under "Gemma" — confusing during the demo.

Updated table:

```sql
CREATE TABLE food_cache (
    fdc_id INTEGER NOT NULL,
    provider TEXT NOT NULL,         -- "ollama" or "anthropic"
    model TEXT,                     -- specific model used, nullable for ollama default
    report_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (fdc_id, provider, model)
);
```

`FoodCacheRepo.get_by_fdc_id()` now takes `provider` and `model` args.
`FoodCacheRepo.put()` likewise.

The raw-query cache (the fast pre-check at step [1] of §A11) keeps
working as before — it's keyed by the raw query string, not provider.
A raw query hit means the user just searched the same thing recently,
regardless of provider. The post-resolution cache (step [5]) is where
the provider key matters.

### Environment variables

Add to `.env.example`:

```
# Required for local LLM
OLLAMA_HOST=http://localhost:11434

# Optional — enables Claude provider in the UI
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6   # optional override; UI also picks model
```

### Prompt adjustments per provider

The prompts in `ai/prompts/` are tuned for Gemma 4B (lots of
chain-of-thought scaffolding, detailed few-shot examples). On Claude
these are *fine* but slightly redundant — Claude reasons well
internally without as much explicit scaffolding.

For v1, just use the same prompts for both providers. Don't optimize
per-provider yet. The slight inefficiency on Claude is a few extra
input tokens — meaningless cost. Keep one set of prompts; less to
maintain.

Future enhancement: detect provider at chain invocation and use
trimmed prompts on Claude. Mention this as a "future work" item if
asked during your presentation.

### Graceful failure modes

- **No API key set and user picks Anthropic** → can't happen (radio
  is disabled), but defensive code in `get_llm()` raises a clear error
  if it does
- **Anthropic API down / rate limit hit** → catch in analyzer, surface
  a friendly error ("Couldn't reach Claude. Falling back to local Gemma."),
  and silently re-run the same query with Ollama
- **Network down during Anthropic query** → same as above; fall back to
  Ollama if available
- **User selects Claude model that no longer exists** → `ChatAnthropic`
  raises; show error and suggest a different model

### The presentation moment this enables

> "My architecture supports both local and cloud LLM providers. Let
> me show you. Same query on Gemma 4B running locally..." *show result*
> "...and now I'll switch to Claude Sonnet via Anthropic API..."
> *toggle, show result* "Same prompts, same chains, same UI — just a
> different model on the backend. Notice the difference in writing
> quality. This is what provider portability looks like."

That demo earns the dual-provider work.

### Why we didn't go further

A few things we deliberately did NOT do, in case you're asked:

- **Auto-fallback to Claude when Gemma struggles** — too complex, adds
  unpredictable cost
- **Run both providers in parallel and compare** — wasteful, no real
  user benefit
- **OpenAI / GPT-4 support** — same pattern would work, but capstone
  scope is two providers, not three

Scoping discipline. Each addition has to earn its place.

---

## §A15 — Prompts Module Layout

> **Quick reference**
> - **Structure:** `ai/prompts/` is a folder, not a single file
> - **One file per prompt:** `refinement.py`, `analysis.py`, `rescue.py`
> - **Re-exports:** `ai/prompts/__init__.py` re-exports all three templates
> - **Import convention:** `from ai.prompts import RESCUE_PROMPT` (works because of re-exports)
> - **Why split:** each prompt is 60-100 lines with system rules, ReAct
>   scaffolding, and multiple few-shot examples — too much for one file

### Rationale

The naive default would be `ai/prompts.py` — one file with all three
prompt templates. We explicitly chose against this for four reasons:

**1. Each prompt is substantial.** With ReAct scaffolding (§A13),
few-shot examples (good and bad), and system rules, each prompt runs
60-100 lines. Three together = 250-300 lines in one file. That's hard
to navigate when you're iterating.

**2. Prompts are the most-iterated code in the project.** During
testing you'll tune them constantly — adding a few-shot example here,
adjusting reasoning steps there. Smaller focused files = less scrolling
and less risk of accidentally editing the wrong prompt.

**3. Claude Code edits are safer with smaller files.** When you ask
Claude Code to "rewrite the rescue prompt's give_up example," a 300-line
file with three prompts increases the risk of accidental edits to
unrelated sections. A 80-line single-purpose file contains the blast
radius.

**4. The convention is real, not cosmetic.** Putting `# === REFINEMENT
PROMPT ===` headers in a single file is "fake separation" — it depends
on discipline to maintain. Real separation by file enforces the
convention by structure.

### Each file's contents

**`ai/prompts/refinement.py`** (~60 lines)
```python
from langchain_core.prompts import ChatPromptTemplate

REFINEMENT_SYSTEM = """..."""
REFINEMENT_FEW_SHOT = """..."""
REFINEMENT_USER = """..."""

REFINEMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", REFINEMENT_SYSTEM + "\n" + REFINEMENT_FEW_SHOT),
    ("user", REFINEMENT_USER),
])

def format_usda_results(results: list[dict]) -> str:
    """Turn raw USDA results into clean prompt text."""
    # helper used by the refinement chain
```

**`ai/prompts/analysis.py`** (~100 lines — the biggest)
```python
ANALYSIS_SYSTEM = """..."""
ANALYSIS_REASONING_STEPS = """..."""   # ReAct scaffolding
ANALYSIS_FEW_SHOT_GOOD = """..."""
ANALYSIS_FEW_SHOT_BAD = """..."""
ANALYSIS_USER = """..."""

ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     ANALYSIS_SYSTEM + "\n" + ANALYSIS_REASONING_STEPS
     + "\n" + ANALYSIS_FEW_SHOT_GOOD + "\n" + ANALYSIS_FEW_SHOT_BAD),
    ("user", ANALYSIS_USER),
])

def format_nutrient_breakdown(nutrition, color_map: dict) -> str:
    """Format nutrition data for the prompt."""
```

**`ai/prompts/rescue.py`** (~80 lines)
```python
RESCUE_SYSTEM = """..."""
RESCUE_FEW_SHOT = """..."""   # four worked examples (rewrite, ask, weak-match, give-up)
RESCUE_USER = """..."""

RESCUE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", RESCUE_SYSTEM + "\n" + RESCUE_FEW_SHOT),
    ("user", RESCUE_USER),
])
```

### The `__init__.py` re-exports

```python
# ai/prompts/__init__.py
from .refinement import REFINEMENT_PROMPT, format_usda_results
from .analysis import ANALYSIS_PROMPT, format_nutrient_breakdown
from .rescue import RESCUE_PROMPT

__all__ = [
    "REFINEMENT_PROMPT",
    "ANALYSIS_PROMPT",
    "RESCUE_PROMPT",
    "format_usda_results",
    "format_nutrient_breakdown",
]
```

This means `ai/llm_chains.py` can still do:

```python
from ai.prompts import REFINEMENT_PROMPT, ANALYSIS_PROMPT, RESCUE_PROMPT
```

without knowing or caring about the folder structure. Consumers see
a flat namespace; the folder is an internal organization choice.

### When you'd revisit this decision

Two scenarios where splitting further might make sense:

- **If a single prompt exceeds ~150 lines** — split its few-shot examples
  into a separate `<prompt>_examples.py` file alongside the main module.
- **If you add a fourth chain** (e.g. a query-rewriting chain separate
  from rescue) — just add another file in the folder. The pattern scales
  naturally.

If a prompt shrinks dramatically (e.g. you replace few-shot with simple
rules) and falls below ~30 lines, it's fine to leave it in its own file
anyway. The cost of having an extra file is negligible.

### How this differs from §A4

§A4 is the high-level module structure. §A15 is the specific design
of the prompts subfolder. They're consistent — §A4's tree shows the
folder structure; §A15 explains why it's organized this way.

---

## Definition of Done

A friendly checklist:

### Walking skeleton (Phase 1)
- [ ] `ollama_test.py` returns a sensible response from Llama 3.2 3B
- [ ] `ollama_test.py` returns a valid Pydantic object via structured output
- [ ] `usda_test.py` returns real nutrition data for "big mac"
- [ ] User types a food in Streamlit
- [ ] App calls USDA and gets real nutrition data
- [ ] App displays a colored letter grade with percentage
- [ ] LLM writes a friendly summary sentence
- [ ] Hard caps fire correctly (test "candy bar" or any high-sugar food → F)

### Real app (Phase 2)
- [ ] Generic queries trigger refinement (e.g. "coffee" → LLM asks "which kind?")
- [ ] Refinement caps at 2 rounds
- [ ] Free-text escape hatch works on every refinement
- [ ] **Rescue agent silently rewrites obvious cases** (e.g. "PSL" → "pumpkin spice latte")
- [ ] **Rescue agent asks the user when ambiguous** (e.g. "korean fried chicken" returning generic chicken)
- [ ] **Rescue agent gives up cleanly** when no rewrite would help (e.g. "dragonfruit pizza")
- [ ] **Rescue caps at 2 rounds, then forces AnalysisError**
- [ ] **Silent rewrite shows "Interpreted as: X" line above the grade**
- [ ] **Rescue agent uses ReAct pattern** — thought field populated before action
- [ ] **Analysis chain uses ReAct pattern** — thought field captures severity ordering plan
- [ ] **"Why?" button on results** reveals the AI's thought field in plain prose
- [ ] **Provider toggle in sidebar** defaults to Ollama, allows switch to Anthropic
- [ ] **Model dropdown appears** when Anthropic is selected (Sonnet 4.6 default)
- [ ] **Anthropic option disabled** with helpful caption when `ANTHROPIC_API_KEY` is missing
- [ ] **Cache uses composite key** `(fdc_id, provider, model)` so each model has its own cached outputs
- [ ] **Same query under both providers** produces different (but both valid) outputs
- [ ] Concerns panel surfaces multiple issues per food (not just the top one)
- [ ] Per-nutrient explanations use real numbers and quantity comparisons
- [ ] Additives detected when ingredient data is available (test with a branded soda)
- [ ] App handles "no ingredients data" gracefully
- [ ] Sidebar shows recent lookups across app restarts
- [ ] Repeat queries hit the cache (badge changes from blue to green)
- [ ] "Clear history" and "Clear cache" buttons work and are independent

### Refactored (Phase 3)
- [ ] Code split into `core/`, `data/`, `ai/` per §A4
- [ ] `uv run pytest` passes with ≥ 80% coverage on `core/grader.py`,
      `core/additives.py`, `data/history.py`, `data/cache.py`
- [ ] `uv run ruff check .` is clean
- [ ] UI is polished — sidebar layout, grade badge, concern cards

### Demo-ready
- [ ] App handles 5 sample foods with different grades (banana=A, salmon=A,
      oatmeal=B, big mac=D, milkshake=F)
- [ ] App handles "burger" and "coffee" with refinement
- [ ] App handles "no USDA results" gracefully
- [ ] At least one demo food triggers a hard cap (sugar > 50g or similar)
- [ ] At least one demo food shows detected additives
- [ ] README explains install + run in < 1 page
- [ ] Workflow diagram exported to `docs/workflow.png`
- [ ] 5–10 minute presentation ready
- [ ] Repo on GitHub with MIT or Apache-2.0 license

You've got this. 🥗
