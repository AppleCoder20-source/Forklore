# Project Proposal: Forklore — An LLM-Powered Food & Drink Nutrition Grader

**Course:** CAP 942
**Date:** June 2026

---

## Problem Statement

Most people have no reliable way to judge how healthy a food or drink actually
is at the moment they buy it. Nutrition labels are dense and easy to
misread, and they report values **per serving** — a figure the manufacturer
defines, which can obscure how much sugar, fat, or sodium a product really
contains. Two foods with the same label number can have very different
nutritional density, and a larger package can appear "worse" than an identical
smaller one simply because of its size. Meanwhile, popular nutrition apps tend
to either oversimplify ("sugar is bad") or overwhelm the user with numbers they
cannot interpret. The result is that everyday decisions — a coffee on the way to
work, a fast-food lunch, a soda at a gathering — are made on intuition and
marketing rather than on real, comparable data.

Forklore addresses this gap. It takes a food or drink the user names, retrieves
its real nutrition data from trusted databases, grades it on a transparent A–F
scale, and uses a language model to explain *why* it earned that grade in plain
language. The guiding principle of the entire system is that **real data comes
from a trusted source, and the AI only interprets it — it never invents it.**

## Why This Project Matters

This project matters because it turns opaque nutrition information into an
immediate, understandable verdict without sacrificing honesty. Several design
decisions make it meaningful rather than merely convenient:

- **A common ruler.** Every food is normalized to a per-100g (solids) or
  per-100ml (drinks) basis before grading, so comparisons reflect the food
  itself rather than package size. This also defends against a genuine marketing
  tactic — serving sizes chosen to make a product's numbers look smaller than
  the amount people actually consume.
- **Honesty over false confidence.** When a product lacks the data required to
  grade it fairly (for example, a branded item reported without a weight, so it
  cannot be normalized), Forklore declines to grade it rather than fabricating a
  value. This reflects a real concern in health technology, where a confident
  wrong answer is worse than an honest "not enough data."
- **Awareness, not restriction.** The goal is not to discourage people from
  eating what they enjoy, but to give them clear information so they can make
  their own informed choices.

The project also has a credible path toward real-world relevance: the author
works in health information technology at a hospital system, creating an
opportunity to validate the grading logic against guidance from clinicians and
dietitians.

## Tools and Frameworks Chosen

Forklore is built on a deliberately scoped stack, with each tool selected for a
specific role:

- **Python 3.12** — the implementation language.
- **Streamlit** — the user interface and application layer, chosen for rapid
  development of an interactive data app.
- **Pydantic** — for a clean, validated nutrition data model that keeps the
  data shape consistent across the system.
- **LangChain** — to orchestrate the language-model calls in a
  provider-agnostic way.
- **Ollama (llama3.2), with an Anthropic Claude option** — a dual-provider
  design lets the explanations run locally and free (private, offline) or on a
  hosted model for higher quality. The same prompts and logic work across both,
  demonstrating that the architecture is not coupled to any single model.
- **USDA FoodData Central** — the authoritative source for generic, whole foods.
- **FatSecret** — a second data source providing branded and chain-restaurant
  coverage that USDA lacks (e.g., specific Starbucks or Dunkin items), so the
  app can grade both everyday whole foods and the branded products people
  actually buy.
- **uv** — for dependency management and packaging.

The architecture separates concerns cleanly: a `models` layer for data shape,
a `core` layer for pure logic (grading, retrieval, customization, ingredient
combination), a `data` layer for external API access, an `ai` layer for all
language-model work, and a `ui` layer for presentation. Crucially, **grading is
deterministic Python**, not an AI judgment — the language model is reserved for
clustering ambiguous search results and writing explanations, the tasks only it
can do.

## Expected Output and User Interaction

The user types the name of a food or drink. The system routes the search to the
appropriate database (generic queries to USDA, branded/chain queries to
FatSecret), selects the most relevant entry, and — if the search is ambiguous
(for example, "coffee," which could mean black coffee or a frappuccino) — asks a
grounded clarifying question built only from results that genuinely exist in the
data. The chosen food is normalized to a per-100 basis and graded:

- **Solid foods** are scored across sugar, sodium, and saturated fat (with small
  bonuses for fiber and protein), averaged into a letter, and subject to hard
  caps that prevent one extreme nutrient from hiding behind good ones.
- **Drinks** are graded on the real Singapore Nutri-Grade beverage standard —
  the worse of their sugar and saturated-fat grades per 100ml — because liquid
  sugar is the dominant health concern in drinks and should not be averaged away.

The result is presented as a color-coded grade card showing the letter grade
(with +/- resolution), a percentage, the key nutrient figures, and a plain-
language explanation generated by the language model. For drinks, a separate
warning shows the **total** sugar for the user's chosen cup size and escalates
it against daily limits — distinguishing the drink's quality (per-100ml grade)
from the dose (how much is actually consumed). Additional interactions include
customizing a drink with real additions (cup size, added sugar or cream) for an
honest re-grade, building a homemade dish from editable, weighted ingredients,
switching among themes, and saving results for comparison.

## Data or Input Sources

Forklore relies on two real, external nutrition databases. All grades are
computed from these sources; no nutrition values are generated by the language
model.

**1. USDA FoodData Central (public, U.S. government).** This is the
authoritative source for generic and whole foods — for example, "Banana, raw,"
"Coffee, brewed," or "Chicken breast." Each entry contains a description, a data
type (such as Foundation, SR Legacy, Survey/FNDDS, or Branded), and a list of
nutrients identified by numeric IDs (calories, sodium, saturated fat, trans fat,
total and added sugar, fiber, protein, and others). It is accessed through a
free API key. Its main limitation is that it does not cover most
chain-restaurant menus.

**2. FatSecret (commercial nutrition database).** This is the source for branded
and chain-restaurant items that USDA lacks — for example, specific Starbucks or
Dunkin products. It is accessed through an authenticated API and returns a list
of serving sizes per food, each with its own nutrient values. Its main
limitation is uneven data quality, which the preprocessing step below addresses.

### Preprocessing steps

The two sources return data in very different shapes — USDA as a flat list of
nutrients keyed by numeric IDs, FatSecret as a nested list of serving objects —
so a substantial preprocessing layer converts both into one consistent,
validated `Nutrition` model (built with Pydantic) before any grading occurs. The
steps below run in order for every food:

**1. Mapping raw nutrient codes to named fields.** USDA does not return
human-readable nutrient names; it returns a list tagged with numeric nutrient
IDs. The parser holds an explicit lookup table mapping each relevant ID to a
clean field name — e.g., 1008 → calories, 1093 → sodium, 1258 → saturated fat,
1257 → trans fat, 1235 → added sugar, 2000 → total sugar, 1079 → fiber, 1003 →
protein. It iterates the nutrient list and writes each recognized ID's value into
the matching field. Every field is initialized to zero first (databases
frequently omit nutrients, and a missing field must read as 0, not crash), and
each value is coerced to a non-negative float.

**2. Separating added sugar from natural sugar.** Sugar is split into two fields:
added sugar (graded) and total/natural sugar (display only). This avoids
penalizing whole foods for naturally occurring sugar — a banana's natural sugar
is recorded but never lowers its grade. One deliberate exception is handled here:
for drinks, databases often report only total sugar and leave added sugar empty,
which would make a sugary soda look like it has no gradeable sugar and score an
A. So a guarded fallback runs — if the food is a drink and its added-sugar field
is empty, total sugar is copied into the graded field. The guard applies only to
drinks, so whole foods keep their natural-sugar exemption.

**3. Detecting whether the item is a drink.** Because solids and drinks grade on
different scales, each food is classified during preprocessing, using the serving
unit ("ml" indicates a drink) plus keyword matching on the description (some
beverages are stored with a gram unit). This drives both the sugar fallback above
and the choice of grading path.

**4. Normalizing everything to a per-100 basis.** All grading thresholds assume
per-100g (solids) or per-100ml (drinks), so every food is placed on that common
ruler first. USDA already reports per 100g and is read directly; FatSecret
returns several servings per food, and the parser selects the one whose metric
unit is grams and whose amount equals exactly 100. This ensures the grader sees
nutritional density, not an arbitrary manufacturer-defined serving.

**5. Filtering out un-gradeable (weightless) items.** Some branded items report
nutrition only "per item" (e.g., per donut) with no gram weight. Without a
weight, they can't be normalized to per-100 and can't be graded fairly. Rather
than fabricate a weight, the parser drops them: when no exact 100g serving
exists, it returns nothing for that food, excluding it from the options shown.
This enforces the grounding principle — real data or nothing — so every
selectable item is one the system can actually grade.

**6. Selecting the most relevant entry from messy results.** A single search
often returns many loosely related entries (searching "banana" returns raw
bananas, banana chips, banana bread, and incidental branded snacks). Deterministic
logic chooses the best match: prefer entries labeled "raw," then generic USDA
data types over branded products, then fall back to the first result. This is
plain code, not a language-model decision, because it is a factual choice with a
correct answer.

Together, these steps turn inconsistent, real-world API responses into clean,
comparable, per-100 nutrition data — and decide honestly when the data is not
good enough to grade at all.

## Status and Planned Next Steps

A working foundation is already built: real-data retrieval from both sources,
the full grading rubric (including the Nutri-Grade drink logic and +/- grades),
ambiguity handling, drink customization, homemade-dish grading, the dual-provider
language-model layer, and the themed result interface. Planned next steps include
recruiting collaborators to grow the project, consulting clinicians and
dietitians (via the author's hospital affiliation) to validate the grading
thresholds against professional guidance, and adding barcode scanning so a
product can be identified by scanning its package rather than typing its name.
Further planned extensions documented in the project's specification include a
food-additive detection layer, search history and caching for speed, and an
optional REST API alongside the existing interface.

---

*Forklore — grade real data, explain it honestly, never guess.*