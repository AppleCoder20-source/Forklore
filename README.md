# Forklore
<div align="center">

# 🥗 Forklore

### *Grade any food A–F from real government data — and get an honest explanation why.*

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![LangChain](https://img.shields.io/badge/AI-LangChain-green)
![Data](https://img.shields.io/badge/Data-USDA%20FoodData%20Central-orange)
![Models](https://img.shields.io/badge/Models-Ollama%20%7C%20Claude-purple)

</div>

---

Type in a food. Forklore looks it up in the USDA's official database, grades it from **A to F** on a transparent, science-backed rubric, and writes a plain-English explanation of *why* it earned that grade. It runs entirely on real, measured data — **it never guesses, never invents numbers, and tells you when it doesn't know something.**

### Contents

1. [The idea behind it](#the-idea-behind-it)
2. [What it does, end to end](#what-it-does-end-to-end)
3. [The grading rubric](#1-the-grading-rubric--grounded-in-real-world-systems)
4. [Stricter scale for drinks](#2-drinks-are-graded-on-a-stricter-scale)
5. [Picking the right food](#3-picking-the-right-food-from-messy-data)
6. [Handling ambiguity](#4-handling-ambiguous-searches--without-hallucinating)
7. [Customization](#5-customization--personalized-and-grounded)
8. [The explanation layer](#6-the-explanation-layer--language-not-math)
9. [Code at a glance](#code-at-a-glance)
10. [Built through testing](#built-through-testing-not-assumption)
11. [Honest limitations](#honest-limitations)
12. [Tech stack & structure](#tech-stack)
13. [Running it](#running-it)

---

## The idea behind it

Most nutrition apps either oversimplify ("sugar bad!") or drown you in numbers you can't interpret. Forklore takes a different stance, built on one principle that shows up in every part of the system:

> **Real data comes from a trusted source. The AI only interprets it — it never invents it.**

That sentence is the spine of the whole project. The grade always comes from real, measured USDA numbers run through a transparent rubric. The language model's *only* job is to explain those numbers in friendly terms — it is never allowed to make up a value, guess a grade, or offer a food that doesn't exist in the data. Every design decision in this document traces back to that rule.

---

## What it does, end to end

```
You type a food
      ↓
USDA FoodData Central is searched (real, official data)
      ↓
The right entry is selected (prefer raw/whole foods over branded products)
      ↓
If the search is ambiguous → ask which kind you meant (grounded in real results)
      ↓
The food is graded A–F on a per-100g/ml rubric
      ↓
A language model explains the grade in plain English
      ↓
For drinks, you can customize it (what you added) and it re-grades on real math
```

Each of those stages was a deliberate design decision. Here's the walkthrough.

---

## 1. The grading rubric — grounded in real-world systems

Forklore doesn't use made-up thresholds. The grade bands are modeled on **established nutrition-labeling systems** used by real governments:

- The **UK FSA** traffic-light system
- **Chile's** front-of-package warning labels
- **Singapore's Nutri-Grade** drink rating

Foods are graded **per 100g / 100ml** — the same basis those systems use, and the basis USDA reports on. This matters: it measures *nutritional density* (how much sugar/fat/salt is packed into a fixed amount), not an arbitrary "serving" that varies by product.

Each food is scored on the nutrients that actually matter:

| Nutrient | Role | Why |
|----------|------|-----|
| Added sugar | Penalty | Empty calories; the core driver for drinks |
| Saturated fat | Penalty | Linked to heart-health concerns in excess |
| Sodium | Penalty | Affects blood pressure over time |
| Trans fat | Hard penalty | The worst type of fat — any amount is a red flag |
| Fiber | Bonus | Aids digestion, helps you feel full |
| Protein | Bonus | Builds and repairs the body |

The scores are averaged into a letter grade, with **hard caps** layered on top: a drink over a sugar threshold can't escape a poor grade no matter how clean it is otherwise, mirroring how real warning-label systems work.

### Two design calls worth highlighting

**Added sugar vs. natural sugar.** "Sugar" isn't one thing. A banana's natural sugar shouldn't be penalized the way a soda's added sugar should. So Forklore tracks them separately — it **grades added sugar** and treats **natural sugar as display-only**. Fruit isn't punished for being fruit.

**Fiber and protein are bonuses, not requirements.** A food shouldn't be penalized for lacking a nutrient it was never meant to have — black coffee isn't a protein source, and an apple isn't a fiber powerhouse. So fiber and protein can only *raise* a grade, never *lower* it. This was a fix discovered through testing (see below): without it, genuinely healthy foods like black coffee and apples were getting unfairly dragged down.

---

## 2. Drinks are graded on a stricter scale

A drink and a solid food with the same sugar aren't equivalent — you drink far more than 100ml at once, liquid sugar hits faster (no fiber to slow it), and a sugary drink is often *only* sugar. So Forklore detects drinks and grades them on a **stricter sugar scale**.

**A consequence worth showing off:** fruit juice intentionally grades poorly. Apple juice has *more* sugar per 100ml than many sodas — this is true, and most people don't expect it. Forklore surfaces that instead of hiding it. The app becomes a small myth-buster: "healthy" juice and soda aren't as different as the marketing suggests.

---

## 3. Picking the *right* food from messy data

USDA returns a mix of entries — and not all of them are what you mean. Search "banana" and you'll get raw bananas, banana chips, banana bread, dried banana powder, *and* odd branded products (one "BANANA" entry is a snack with 594mg of sodium — nothing like real fruit).

Forklore's selection logic prefers the **real, whole food**:

1. Prefer entries labeled **"raw"** (the actual unprocessed food)
2. Otherwise prefer **generic** data types (USDA's Survey / SR Legacy) over branded products
3. Fall back to the first result only if nothing better exists

So "banana" lands on **"Banana, raw,"** not a sodium-loaded branded snack — while foods that only exist as branded entries (a Big Mac) still work via the fallback.

---

## 4. Handling ambiguous searches — without hallucinating

Some searches are genuinely ambiguous. "Coffee" could mean black coffee (≈1 calorie) or a frappuccino (≈500). Grading the first result would be a coin flip.

**Detecting ambiguity.** Forklore measures the **calorie spread** across the top results as a proxy for "is this one food, or many?"

- "Coffee" → spread of ~500× (black coffee vs. frappuccino) → **ambiguous** → ask which kind
- "Banana" → spread of ~3.6× → **coherent** → just grade it

The threshold was **tuned by testing real foods**, not guessed — coffee, banana, Big Mac, and pizza were each run through it until the line correctly separated "ambiguous" from "clear."

**Clarifying it — grounded.** When a search is ambiguous, a language model clusters the *actual* USDA results into a friendly "which did you mean?" question (e.g. "Black coffee / Espresso / Cappuccino"). Crucially, **it can only offer foods that genuinely exist in the results** — each option is tied to real database IDs. The AI physically cannot invent a "Starbucks Caramel Macchiato" that USDA doesn't have. The grounding principle, enforced by the architecture itself.

---

## 5. Customization — personalized *and* grounded

Drinks depend on how you make them. A black iced coffee and a syrup-loaded one are completely different drinks. Rather than guess, Forklore lets you **enter what you actually added** — your cup size and how much sugar or cream — and the **real grader recalculates** on those real numbers.

The math respects the per-100ml basis:

```
You added 30g of sugar to a 250ml cup
  → 30g ÷ (250 / 100) = 12g per 100ml
  → graded as 12g/100ml (concentrated, because it's a small cup)
```

A smaller cup makes the same sugar *more concentrated* → a worse grade, which is nutritionally correct.

**Why this stayed grounded:** the AI never re-grades from a vague description. *You* provide real amounts; the *real grader* does the real math. This was a deliberate line — an earlier idea (let the AI estimate a grade from "I added some sugar") was rejected because it would replace measured data with a guess.

---

## 6. The explanation layer — language, not math

Once a food is graded, a language model writes a short, friendly explanation of *why*. It focuses on whichever nutrients actually drove the grade — sugar for a soda, saturated fat and sodium for a burger, protein for grilled chicken.

It works strictly within guardrails: it's given **only the real numbers**, told to use the rubric's scales, and explicitly forbidden from inventing values, citing daily limits, or giving medical advice. The model does **language**; the code does **logic and math**. They never trade jobs.

### Choose your engine

A toggle lets you run the explanations (and the ambiguity clustering) on either:

- **Local** — `llama3.2` via Ollama, running entirely on your machine. Free and private.
- **Claude** — Anthropic's API, for cleaner, more reliable explanations.

Same app, same grounding rules — your choice between local privacy and cloud quality.

---

## Code at a glance

A few key pieces, to show how the design ideas above turn into actual code. Each is small on purpose — the logic stays readable.

### The grading rubric (`core/grader.py`)

Each nutrient is scored 1–4. Penalties (sugar, fat, sodium) are always counted; bonuses (fiber, protein) only count when present, so a clean food is never punished for what it lacks. The average maps to a letter, and hard caps enforce the worst offenders.

```python
# "Bad" nutrients — always scored. Too much tanks the grade.
scores = [
    _score_sodium(n.sodium_mg),
    _score_sat_fat(n.saturated_fat_g),
    _score_sugar(n.bad_sugar_g, is_drink),   # drinks use a stricter scale
]

# Fiber & protein are BONUSES — they can raise a grade, never lower it.
if _score_fiber(n.fiber_g) >= 3:
    scores.append(_score_fiber(n.fiber_g))
if _score_protein(n.protein_g) >= 3:
    scores.append(_score_protein(n.protein_g))

avg = sum(scores) / len(scores)          # → A / B / C / D / F

# Hard caps: a sugary drink can't escape a bad grade no matter what else.
if is_drink and n.bad_sugar_g > 10:
    letter = "F"
```

### Detecting ambiguity (`core/retrieval.py`)

The calorie spread across results is a proxy for "one food, or many?" A wide spread means the search is ambiguous and should ask the user which they meant.

```python
def is_coherent(foods) -> bool:
    calories = [_calories(f) for f in foods[:5]]
    low, high = min(calories), max(calories)
    return (high / low) < 4        # coffee: 500× → ambiguous | banana: 3.6× → clear
```

### Picking the right food (`data/usda_client.py`)

Prefer the real, whole food over branded products — so "banana" lands on raw fruit, not a sodium-heavy snack.

```python
def pick_best_food(foods):
    for food in foods:                          # 1. prefer a "raw" entry
        if "raw" in food.get("description", "").lower():
            return food
    generic = [f for f in foods if f.get("dataType") in GENERIC_TYPES]
    return generic[0] if generic else foods[0]  # 2. generic, else 3. fallback
```

### Grounded clustering (`ai/refinement.py`)

When a search is ambiguous, the model groups the *real* results into options — and the schema forces every option to carry real database IDs, so it can't invent a food that doesn't exist.

```python
class RefinementOption(BaseModel):
    label: str               # "Black coffee", "Espresso", ...
    fdc_ids: list[int]       # must map to REAL USDA entries — can't be invented
```

### Customization math (`core/customize.py`)

The user's real additions are converted to the per-100ml basis the grader uses, then re-graded — real numbers, real math, no guessing.

```python
factor = drink_size_ml / 100             # 250ml → 2.5
nutrition.bad_sugar_g += added_sugar_g / factor   # 30g added → +12g per 100ml
```

---

## Built through testing, not assumption

Several of the best design decisions came from **running the app and noticing when a grade was wrong** — then tracing *why*:

- A banana graded a **D** → traced to a bad *branded* entry (594mg sodium) → fixed by preferring raw foods.
- Black coffee graded a **C**, apple a **B** → traced to fiber/protein unfairly penalizing clean foods → fixed by making them bonuses.
- The diversity threshold was **tuned against real foods** until it correctly told ambiguous (coffee) from clear (banana).

These weren't caught by error messages — there were no errors. They were caught by checking the output against what a grade *should* be. That kind of evaluation is the heart of the project.

---

## Honest limitations

A system is only as trustworthy as it is honest about its edges:

- **USDA's branded coverage is patchy.** It has McDonald's menu items but not actual Starbucks or Dunkin coffee drinks. Forklore only ever offers what genuinely exists — it never promises a food it can't back with real data. *(Roadmap: integrate Open Food Facts for broader branded coverage.)*
- **Some foods vary by preparation.** "Iced coffee" depends entirely on how it's made — handled by the customization feature, where you supply the real additions.
- **Keyword-based drink detection** is a heuristic and can occasionally misfire on unusual descriptions.

Naming these isn't a weakness — it's the same principle as everything else. The app would rather be honest about what it doesn't know than fake an answer.

---

## Tech stack

| Layer | Tool |
|-------|------|
| UI | Streamlit |
| Data | USDA FoodData Central API |
| Grading | Pure-Python rubric (per-100g/ml, hard caps) |
| AI orchestration | LangChain |
| Models | Ollama (`llama3.2`) locally, or Anthropic Claude |
| Validation | Pydantic |
| Packaging | uv |

### Project structure

```
src/forklore/
├── app.py                 # UI + orchestration (Streamlit)
├── models.py              # Nutrition data model + USDA parsing + drink detection
├── core/
│   ├── grader.py          # the A–F grading rubric
│   ├── retrieval.py       # ambiguity (diversity) check
│   └── customize.py       # per-100ml addition math
├── ai/
│   ├── llm.py             # model factory (local / Claude)
│   ├── refinement.py      # ambiguity clustering (grounded)
│   └── summary.py         # the plain-English explanation
└── data/
    └── usda_client.py     # USDA search + best-entry selection
```

The architecture follows a clear rule: **data shape** lives in `models.py`, **pure logic** in `core/`, **outside I/O** in `data/`, **language-model work** in `ai/`, and **UI** in `app.py`. Each part does one job and can be reasoned about on its own.

---

## Running it

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), and [Ollama](https://ollama.com) (for local mode).

```bash
# 1. Install dependencies
uv sync

# 2. Pull the local model (for local mode)
ollama pull llama3.2

# 3. Set up your API key in a .env file
#    USDA_API_KEY=...        (free from fdc.nal.usda.gov)
#    ANTHROPIC=...           (optional, for Claude mode)

# 4. Run it
uv run streamlit run src/forklore/app.py
```

---

## What's next

Forklore's foundation is complete: principled grading, grounded ambiguity handling, raw-food selection, real-math customization, and a dual-model explanation layer. Planned next steps include a richer concerns analysis, additive/dye detection, search history and caching, and a multi-step "rescue agent" for queries the database doesn't recognize — each extending the same core principle: **grade real data, explain it honestly, never guess.**

---

<div align="center">

**Forklore** — *grade real data, explain it honestly, never guess.*

Built with Python, Streamlit, LangChain, and USDA FoodData Central.

</div>