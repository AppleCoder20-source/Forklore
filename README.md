<div align="center">

# 🥗 Forklore

### *Grade any food A–F from real government data — and get an honest explanation why.*

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![LangChain](https://img.shields.io/badge/AI-LangChain-green)
![Data](https://img.shields.io/badge/Data-USDA%20%7C%20FatSecret-orange)
![Models](https://img.shields.io/badge/Models-Ollama%20%7C%20Claude-purple)

</div>

---

## A walk around the city

New York City has one thing in endless supply: *food*. Step outside and it's everywhere. You duck into a **Starbucks** and order an iced vanilla latte without thinking twice. A few blocks later there's a **Halal Guys** cart, so you grab chicken over rice with the white sauce. That night a friend throws a party, and you take a **soda** from the cooler because everyone's grabbing one. Three foods, three completely normal moments — none of which anyone really stops to *think* about.

And that's the point. This isn't about being against any of it. The latte is great. The halal plate is genuinely one of the best things in the city. The soda at the party is part of the fun. **Forklore isn't an anti-food app — it's not here to tell anyone to stop eating what they like.** It's here so that when you *do* buy something, you actually know what you're holding. Awareness, not guilt.

Because most people have no real sense of how these stack up against each other. Is that latte "bad"? Is the soda worse? Is the halal plate fine because it's "real food"? It's all guesswork — off vibes and marketing. Forklore looks at the *actual numbers* and just says it plainly, on a scale everyone already understands: **A to F.**

But the moment you try to compare a latte, a rice platter, and a can of soda, a problem shows up. A can of soda is 355ml. A halal plate might be 500 grams. A latte is somewhere in between. You can't just line up their sugar numbers — a bigger container will *always* look like it has "more," even if it's the same thing inside. To compare them honestly, everything has to be measured on the same ruler. That ruler is **per 100 grams** (for solids) and **per 100 millilitres** (for drinks) — and it's the foundation the entire app is built on. The next section is all about why.

---

Type in a food. Forklore looks it up in real nutrition databases, grades it from **A to F** on a transparent, science-backed rubric, and writes a plain-English explanation of *why* it earned that grade. It runs entirely on real, measured data — **it never guesses, never invents numbers, and tells you when it doesn't know something.**

### Contents

1. [The idea behind it](#the-idea-behind-it)
2. [Why everything is measured per 100g/ml](#why-everything-is-measured-per-100gml-the-foundation)
3. [What it does, end to end](#what-it-does-end-to-end)
4. [Project structure](#project-structure)
5. [The grading rubric](#1-the-grading-rubric--grounded-in-real-world-systems)
6. [How drinks are graded (Nutri-Grade)](#2-how-drinks-are-graded--the-nutri-grade-system)
7. [Picking the right food](#3-picking-the-right-food-from-messy-data)
8. [Handling ambiguity](#4-handling-ambiguous-searches--without-hallucinating)
9. [Customization](#5-customization--personalized-and-grounded)
10. [The explanation layer](#6-the-explanation-layer--language-not-math)
11. [Homemade dishes](#7-homemade-dishes--composite-foods-graded-from-real-ingredients)
12. [The result screen & UI](#8-the-result-screen--reading-a-grade-at-a-glance)
13. [Code at a glance](#code-at-a-glance)
14. [Built through testing](#built-through-testing-not-assumption)
15. [Honest limitations](#honest-limitations)
16. [Tech stack](#tech-stack)
17. [Running it](#running-it)

---

## The idea behind it

Most nutrition apps either oversimplify ("sugar bad!") or drown you in numbers you can't interpret. Forklore takes a different stance, built on one principle that shows up in every part of the system:

> **Real data comes from a trusted source. The AI only interprets it — it never invents it.**

That sentence is the spine of the whole project. The grade always comes from real, measured numbers run through a transparent rubric. The language model's *only* job is to explain those numbers in friendly terms — it is never allowed to make up a value, guess a grade, or offer a food that doesn't exist in the data. Every design decision in this document traces back to that rule.

---

## Why everything is measured per 100g/ml — *the foundation*

Before any food gets a grade, it gets **normalized to a fixed amount**: per 100 grams for solids, per 100 millilitres for drinks. This is the single most important idea in the whole project, because every threshold in the grader depends on it. It's worth understanding *why* it has to work this way.

### The problem: raw numbers measure the package, not the food

Imagine the grader just read the sugar number straight off a product, with no normalization. Now picture the **same yogurt** sold two ways:

- A small **100g cup** with 8g of sugar
- A large **500g container** with 40g of sugar

It's the *identical yogurt* — same recipe, same sweetness, same everything. But the raw numbers say "8g" and "40g." If the grader compared those directly against a fixed threshold, the large one would look five times worse — and get a worse grade **purely for being a bigger package.** That's nonsense. A grade is supposed to describe *the food*, not *the size of the container it came in*.

### A second way raw numbers fail: false ties

The package problem makes the same food look different. There's a flip side — raw numbers can also make *different* foods look the same. Picture two products:

- A **30g** snack pack of nuts with **6g of sugar**
- A **300g** bottle of sports drink with **6g of sugar**

On the raw number, they tie — both say "6g of sugar," so a naive grader would treat them as equally sugary. But they're nowhere close. Normalize them and the truth appears: the nuts are **20g of sugar per 100g** (genuinely sugary for a snack), while the sports drink is **2g per 100ml** (barely sweet). Same raw number, completely different foods. Without the common ruler, the grade can't tell them apart — and might rank them backwards.

### The fix: a common ruler

Normalizing to per-100 dissolves both problems. The two yogurts both become **"8g of sugar per 100g"** — identical, because they *are* identical. The nuts and the sports drink separate into 20g and 2g — different, because they *are* different. Now the number reflects how much sugar is packed into a fixed amount of the food (its *nutritional density*), which is exactly what I want to grade. Per-100 is the **shared ruler** that lets me compare any two foods fairly. It's also the basis real nutrition-labeling systems use, and the basis the databases report on.

### Why this means some foods can't be graded at all

Here's the consequence that surprised me in testing. To convert a food to per-100g, I need to know **how much it weighs.** Most generic foods come with that weight. But many *branded* items — especially chain-restaurant products — don't. They list nutrition per "1 donut" or "1 grande," with **no gram weight attached.**

Take a real example. A branded donut listed **13g of sugar per donut**, but with *no weight*. I have the sugar, but I'm missing the donut's grams — so I **cannot** convert it to per-100g. And without that conversion, feeding "13" into a rubric built for per-100g numbers would be comparing two completely different rulers — the grade would be meaningless.

I *could* have guessed ("a donut is probably ~60g") and faked a per-100g value. I deliberately **didn't** — that would violate the grounding principle. Instead, **weightless items are dropped** rather than graded on a fabricated weight. Real data or nothing. (This is also why the items that *do* show up in the app are always gradeable: the ones missing a weight were filtered out before you ever see them.)

> **The one-sentence version:** per-100 is the shared ruler that makes grades about the *food* instead of the *package* — and if a food doesn't carry the weight needed to measure it on that ruler, I'd rather show nothing than invent it.

---

## What it does, end to end

```
You type a food
      ↓
A real nutrition database is searched (USDA for generic, FatSecret for branded)
      ↓
The right entry is selected (prefer raw/whole foods over branded products)
      ↓
If the search is ambiguous → ask which kind you meant (grounded in real results)
      ↓
The food is normalized to per-100g/ml, then graded A–F
      ↓
A language model explains the grade in plain English
      ↓
For drinks, you can customize it (what you added / your cup size) and it re-grades on real math
```

Each of those stages was a deliberate design decision. Here's the walkthrough.

---

## Project structure

```
src/forklore/
├── app.py                 # UI + orchestration (Streamlit)
├── models.py              # Nutrition data model + parsing + drink detection
├── core/
│   ├── grader.py          # the A–F grading rubric (+ Nutri-Grade drinks, +/- grades)
│   ├── retrieval.py       # ambiguity check + composite-food detection
│   ├── customize.py       # per-100ml addition math
│   └── combine.py         # weighted ingredient combining (homemade dishes)
├── ai/
│   ├── llm.py             # model factory (local / Claude)
│   ├── refinement.py      # ambiguity clustering (grounded)
│   ├── ingredients.py     # ingredient + amount suggestion (homemade)
│   └── summary.py         # the plain-English explanation
├── data/
│   ├── usda_client.py     # USDA search + best-entry selection
│   ├── fatsecret_client.py
│   └── fatsecret_search.py
└── ui/
    └── themes.py          # the 13 color themes
```

The architecture follows a clear rule: **data shape** lives in `models.py`, **pure logic** in `core/`, **outside I/O** in `data/`, **language-model work** in `ai/`, and **UI** in `app.py` + `ui/`. Each part does one job and can be reasoned about on its own.

---

## 1. The grading rubric — grounded in real-world systems

Forklore doesn't use made-up thresholds. The grade bands are modeled on **established nutrition-labeling systems** used by real governments:

- The **UK FSA** traffic-light system
- **Chile's** front-of-package warning labels
- **Singapore's Nutri-Grade** drink rating

Everything is graded **per 100g / 100ml** — the shared ruler described above.

**Solid foods** are scored on the nutrients that actually matter:

| Nutrient | Role | Why |
|----------|------|-----|
| Sugar | Penalty | Empty calories; the core driver for drinks |
| Saturated fat | Penalty | Linked to heart-health concerns in excess |
| Sodium | Penalty | Affects blood pressure over time |
| Trans fat | Hard penalty | The worst type of fat — any amount is a red flag |
| Fiber | Bonus | Aids digestion, helps you feel full |
| Protein | Bonus | Builds and repairs the body |

Each nutrient is scored **1–4** (4 = healthiest). The three penalty nutrients are always counted; the two bonus nutrients are added **only if they score well**, so a food is never punished for lacking a nutrient it was never meant to have. The scores are **averaged** into a letter grade — and then **hard caps** are layered on top: no matter how good the average, a single extreme nutrient (very high sugar, sodium, saturated fat, or any trans fat) forces the grade down. One bad nutrient can't hide behind good ones.

### A worked example: why a banana gets an A

A banana per 100g is roughly: **12g sugar, ~1mg sodium, 0.1g saturated fat.**

- Sugar 12g → scores **3** (real sugar, but not extreme)
- Sodium ~1mg → scores **4** (basically none)
- Saturated fat 0.1g → scores **4** (basically none)
- Average = (3 + 4 + 4) / 3 = **3.67 → A**

The banana wins because it's **near-zero in the things that hurt you** — no sodium, no saturated fat. Its natural sugar is its only ding, and it isn't enough to pull the grade down. It triggers none of the hard caps, so the A stands. This is the whole concept in miniature: the grade is mostly driven by *how low the harmful nutrients are*, with small bonuses for the good stuff.

### Two design calls worth highlighting

**Added sugar vs. natural sugar.** "Sugar" isn't one thing. A banana's natural sugar shouldn't be penalized the way a soda's added sugar is. So Forklore tracks them separately — it **grades added sugar** and treats **natural sugar as display-only**. Fruit isn't punished for being fruit.

**Fiber and protein are bonuses, not requirements.** A food shouldn't be penalized for lacking a nutrient it was never meant to have — black coffee isn't a protein source. So fiber and protein can only *raise* a grade, never *lower* it. This was a fix discovered through testing (see below): without it, genuinely healthy foods like black coffee and apples were getting unfairly dragged down.

---

## 2. How drinks are graded — the Nutri-Grade system

Drinks don't use the averaging rubric at all. They're graded on **Singapore's Nutri-Grade** beverage standard — a real public-health system — and the difference is deliberate.

A drink's grade is the **worse of two sub-grades**: its sugar grade and its saturated-fat grade, each measured per 100ml.

| Sugar (per 100ml) | Grade | | Saturated fat (per 100ml) | Grade |
|---|---|---|---|---|
| ≤ 1g | A | | ≤ 0.7g | A |
| ≤ 5g | B | | ≤ 1.2g | B |
| ≤ 10g | C | | ≤ 2.8g | C |
| ≤ 15g | D | | > 2.8g | D |
| > 15g | **F** *(custom)* | | | |

The `> 15g → F` tier is a custom addition beyond the standard Nutri-Grade scale, to flag the truly sugar-loaded drinks (frappuccinos, syrup bombs) that go well past a normal soda.

### Why drinks are *not* averaged — the key insight

This is the most important design call in the drink path, and a great thing to demo. **Averaging would let a drink's sugar hide.**

Watch what happens if I average a soda (≈11g sugar, 0g saturated fat, 0mg sodium per 100ml) like a solid food:

- Sugar 11g → 3
- Saturated fat 0g → 4
- Sodium 0mg → 4
- Average = (3 + 4 + 4) / 3 = **3.67 → an A**

A **soda would get an A.** That's absurd — and it happens because drinks are mostly water plus sugar, so they get "free" perfect scores on fat and sodium they were never going to contain. Those freebies mathematically drown out the sugar, which is the *only* thing that matters for a drink.

The worse-of-two rule closes the loophole. That same soda:

- Sugar 11g → **D**
- Saturated fat 0g → A
- Worse of the two → **D** ✓

D, not A — the correct answer. By taking the *worst* sub-grade instead of the average, the sugar can't be offset by anything. This is exactly why the real Nutri-Grade standard works this way: public-health authorities don't let a soda's lack of fat excuse its sugar.

### A consequence worth showing off

Fruit juice intentionally grades poorly. Apple juice has *more* sugar per 100ml than many sodas — this is true, and most people don't expect it. Forklore surfaces that instead of hiding it: "healthy" juice and soda aren't as different as the marketing suggests.

### Plus/minus grades

On top of the letter, Forklore shows a **+/- modifier** (A+, B-, C+, …) for finer resolution, Fooducate-style. For drinks, the +/- reflects *where in the band* the sugar sits — a drink near the low edge of the C band (say 6g) gets a **C+**, while one near the high edge (9g) gets a **C-**. It's display-only: it sharpens the picture without changing the underlying grade. (F has no +/-.)

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

The threshold was **tuned by testing real foods**, not guessed.

**Clarifying it — grounded.** When a search is ambiguous, a language model clusters the *actual* results into a friendly "which did you mean?" question. Crucially, **it can only offer foods that genuinely exist in the results** — each option is tied to real database IDs. The AI physically cannot invent a food the database doesn't have. The grounding principle, enforced by the architecture itself.

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

**Why this stayed grounded:** the AI never re-grades from a vague description. *You* provide real amounts; the *real grader* does the real math. An earlier idea — let the AI estimate a grade from "I added some sugar" — was rejected because it would replace measured data with a guess.

---

## 6. The explanation layer — language, not math

Once a food is graded, a language model writes a short, friendly explanation of *why*. It focuses on whichever nutrients actually drove the grade — sugar for a soda, saturated fat and sodium for a burger, protein for grilled chicken.

It works strictly within guardrails: it's given **only the real numbers**, told to use the rubric's scales, and explicitly forbidden from inventing values or giving medical advice. The model does **language**; the code does **logic and math**. They never trade jobs.

### Choose your engine

A toggle lets you run the explanations (and the ambiguity clustering) on either:

- **Local** — `llama3.2` via Ollama, running entirely on your machine. Free and private.
- **Claude** — Anthropic's API, for cleaner, more reliable explanations.

Same app, same grounding rules — your choice between local privacy and cloud quality.

---

## 7. Homemade dishes — composite foods, graded from real ingredients

Some foods aren't a single database entry. A "burrito" or "sandwich" can be a restaurant item *or* something you made yourself. So Forklore handles them specially: when you search a composite food, it asks **restaurant or homemade?**

- **Restaurant** → it looks the dish up and grades that entry, like any other food.
- **Homemade** → the AI suggests a typical ingredient list *with realistic gram amounts*, you edit it however you like, and then **each ingredient is looked up and combined into a real grade.**

The combination is **weighted by amount**:

```
each ingredient:  per-100g nutrients × (its grams / 100)   → its real contribution
whole dish:       sum all contributions ÷ total grams × 100 → per-100g profile
```

This fixes a subtle trap: a naive equal average would let a small amount of an intense ingredient (30g of cheese at ~19g saturated fat per 100g) count the same as a large amount of a mild one (100g of rice). Weighting by real amounts keeps it fair.

**The grounding holds even here:** the AI only *suggests* ingredient names and portions, both fully editable. Every nutrient number comes from the database, and the grade comes from the same rubric as everything else.

---

## 8. The result screen — reading a grade at a glance

The grade is only useful if you can *read* it instantly. The result screen is built around a single bold card, plus context that answers "okay, but should I worry?"

### The grade card

Every result is a **colored badge** whose color *is* the grade — green for A/B, amber for C, orange for D, red for F — so the verdict registers before you read a word. On it:

- An **icon** that matches the grade (✅ good, ⚠️ so-so, ⛔ avoid)
- A **plain-language label** ("great choice", "not great", "avoid")
- The big **+/- grade** (e.g. `C+`) and a percentage
- The food name and brand

Below the card sit three **metric cards** — sugar, saturated fat, sodium — so the actual numbers behind the grade are right there.

### The total-sugar warning (grade vs. dose)

This is the screen's smartest feature, and a great talking point. The **grade stays per-100ml** (so package size can't game it — a Sprite is a D whether it's small or large). But the *amount* you drink obviously matters, so a **separate warning** shows the total sugar for the size you picked, and escalates against real daily limits:

- Under 25g → a calm blue note
- 25–50g → a yellow warning ("most of a day's sugar in one drink")
- Over 50g → a red alarm ("⚠️ more than a full day's recommended limit")

So a large frappuccino reads as, say, a **D** grade *and* a red "63g — more than a day's sugar" alarm. The letter tells you the drink's quality; the warning tells you the dose. One number can't honestly answer both, so the screen shows both — grounded in WHO (~25g/day) and US dietary guidelines (~50g/day).

### Themes

A sidebar **Appearance** picker offers **13 color themes** — Cool Slate (the default), Cream, Mocha, Dark, Fresh Green, Soft Sage, Berry, Ocean, Sunset, Lavender, Midnight Blue, Mint, and Classic Green. Each retheme the whole app (background, buttons, inputs, sidebar, brand color) live. The themes live in their own `ui/themes.py` so they're easy to extend.

### Save results

Any graded item can be kept with a **💾 Save this result** button; saved items collect in a sidebar list (name + grade) for the session, with a one-click clear. Handy for comparing a few drinks side by side during a demo.

---

## Code at a glance

A few key pieces, to show how the design ideas above turn into actual code.

### The solid-food rubric (`core/grader.py`)

Each nutrient is scored 1–4. Penalties are always counted; bonuses only count when present. The average maps to a letter, and hard caps enforce the worst offenders.

```python
scores = [
    _score_sodium(n.sodium_mg),
    _score_sat_fat(n.saturated_fat_g),
    _score_sugar(n.bad_sugar_g),
]
# Fiber & protein are BONUSES — they can raise a grade, never lower it.
if _score_fiber(n.fiber_g) >= 3:
    scores.append(_score_fiber(n.fiber_g))
if _score_protein(n.protein_g) >= 3:
    scores.append(_score_protein(n.protein_g))

avg = sum(scores) / len(scores)          # → A / B / C / D / F

# Hard caps: one extreme nutrient can't hide behind good ones.
if n.bad_sugar_g > 22.5:
    letter = "F"
```

### Drinks: worse-of-two, not averaged (`core/grader.py`)

```python
def _grade_drink(n):
    # The WORSE of the sugar grade and the saturated-fat grade — so sugar
    # can never be offset by a drink's "free" lack of fat.
    letter = _min_letter(_drink_sugar_grade(n.bad_sugar_g),
                         _drink_satfat_grade(n.saturated_fat_g))
    return letter, _COLOR[letter], _DRINK_PCT[letter]
```

### Detecting ambiguity (`core/retrieval.py`)

```python
def is_coherent(foods) -> bool:
    calories = [_calories(f) for f in foods[:5]]
    low, high = min(calories), max(calories)
    return (high / low) < 4        # coffee: 500× → ambiguous | banana: 3.6× → clear
```

### Customization math (`core/customize.py`)

```python
factor = drink_size_ml / 100             # 250ml → 2.5
nutrition.bad_sugar_g += added_sugar_g / factor   # 30g added → +12g per 100ml
```

---

## Built through testing, not assumption

Several of the best design decisions came from **running the app and noticing when a grade was wrong** — then tracing *why*:

- A banana graded a **D** → traced to a bad *branded* entry (594mg sodium) → fixed by preferring raw foods.
- Black coffee graded a **C**, apple a **B** → traced to fiber/protein unfairly penalizing clean foods → fixed by making them bonuses.
- A soda (Sprite) graded an **A** → traced to it not being detected as a drink, so it was averaged (and its sugar hidden) → fixed by improving drink detection.
- The old drink scale had a harsh cliff (3g sugar → A, but 6g → D) → replaced with the smooth Nutri-Grade bands.
- Grades that *climbed* on every interaction → traced to mutating a cached object across Streamlit re-runs → fixed by copying instead of mutating.

These weren't caught by error messages — there were no errors. They were caught by checking the output against what a grade *should* be. That kind of evaluation is the heart of the project.

---

## Honest limitations

- **Branded coverage is patchy.** USDA has McDonald's items but not real Starbucks or Dunkin drinks; FatSecret fills some of that gap, but many branded items are listed *without a weight* and therefore can't be graded (see the per-100 section). Forklore only ever offers what it can back with real data.
- **Some foods vary by preparation.** "Iced coffee" depends entirely on how it's made — handled by the customization feature.
- **Keyword-based drink detection** is a heuristic and can occasionally misfire on unusual descriptions.

Naming these isn't a weakness — it's the same principle as everything else. The app would rather be honest about what it doesn't know than fake an answer.

---

## Tech stack

| Layer | Tool |
|-------|------|
| UI | Streamlit (+ a custom themed result card) |
| Data | USDA FoodData Central + FatSecret |
| Grading | Pure-Python rubric (per-100g/ml, Nutri-Grade drinks, hard caps) |
| AI orchestration | LangChain |
| Models | Ollama (`llama3.2`) locally, or Anthropic Claude |
| Validation | Pydantic |
| Packaging | uv |

---

## Running it

**Prerequisites:** Python 3.12+, [uv](https://docs.astral.sh/uv/), and [Ollama](https://ollama.com) (for local mode).

```bash
# 1. Install dependencies
uv sync

# 2. Pull the local model (for local mode)
ollama pull llama3.2

# 3. Set up your API keys in a .env file
#    USDA_API_KEY=...        (free from fdc.nal.usda.gov)
#    FATSECRET_KEY=...       (for branded items)
#    ANTHROPIC=...           (optional, for Claude mode)

# 4. Run it
uv run streamlit run src/forklore/app.py
```

> **Tip:** after editing any module, fully restart Streamlit (Ctrl+C + relaunch) — a "Rerun" won't reload changed imports.

---

<div align="center">

**Forklore** — *grade real data, explain it honestly, never guess.*

Built with Python, Streamlit, LangChain, USDA FoodData Central, and FatSecrets .

</div>