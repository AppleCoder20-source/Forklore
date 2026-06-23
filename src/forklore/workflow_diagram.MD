
## Architecture diagrams

Now that the two data sources are clear, here's how a search actually moves
through the system. The first diagram is the **detailed flow** (every decision
point, including ambiguous queries); the second is a **UML class view** of the
core types and one-way module dependencies. Both render automatically on GitHub.

### Flow — a query's full journey

```mermaid
flowchart TD
    A([User types a food]) --> ROUTE{Route the query<br/>generic or branded?}

    ROUTE -- "generic<br/>(banana, coffee)" --> USDA[(USDA<br/>FoodData Central)]
    ROUTE -- "branded/chain<br/>(Starbucks, Dunkin)" --> FS[(FatSecret)]

    USDA --> ANY{Any results?}
    FS --> ANY
    ANY -- no --> NORES[Show: no real data<br/>don't fake it]
    ANY -- yes --> WEIGHT{Has a real<br/>per-100 weight?}

    WEIGHT -- "no (weightless<br/>branded item)" --> DROP[Drop it —<br/>can't normalize]
    WEIGHT -- yes --> COHERE{Results coherent?<br/>calorie spread < ~3x}

    COHERE -- "scattered<br/>(coffee: 5–500 cal)" --> AMB[Ambiguous query]
    AMB --> CLUSTER[AI clusters the REAL results<br/>into grouped options]
    CLUSTER --> ASK[/“Which kind did you mean?”<br/>Black coffee · Latte · Frappuccino/]
    ASK --> PICK[User picks → maps to real IDs]
    PICK --> PARSE

    COHERE -- "coherent<br/>(banana)" --> BEST[Pick best entry<br/>prefer raw/whole food]
    BEST --> PARSE[Parse → Nutrition object]

    PARSE --> NORM[Normalize to<br/>per-100g / per-100ml]
    NORM --> DRINK{Drink or solid?<br/>is_drink_food}

    DRINK -- drink --> NG[Nutri-Grade:<br/>worse of sugar &amp; sat-fat<br/>per 100ml]
    DRINK -- solid --> SOLID[Score sugar/sodium/sat-fat 1–4<br/>+ fiber/protein bonus<br/>average + hard caps]

    NG --> GRADE[Letter + plus/minus + %]
    SOLID --> GRADE
    GRADE --> SUMMARY[LLM writes plain-English<br/>“why this grade” &mdash; numbers only]
    SUMMARY --> CARD[Themed result card<br/>+ escalating total-sugar warning]

    %% Customization loop for drinks
    CARD -. "user edits cup size /<br/>added sugar (drinks)" .-> CUSTOM[apply_additions<br/>recompute per-100ml]
    CUSTOM --> NORM

    %% Composite / homemade branch (special case, shown last)
    A -. "composite food<br/>(taco, burrito, bowl)" .-> COMP{Restaurant<br/>or homemade?}
    COMP -- restaurant --> ROUTE
    COMP -- homemade --> ING[AI suggests ingredients<br/>+ realistic gram amounts]
    ING --> EDIT[User edits the list]
    EDIT --> COMBINE[Weighted combine<br/>each ingredient × its grams]
    COMBINE --> NORM
```

**How to read it:** the spine runs top-to-bottom — **route → fetch → validate
(weight check) → resolve ambiguity → parse → normalize → grade → explain →
render.** Two side-loops hang off the spine: the **customization loop** (drinks
re-grade when you enter your real cup size / additions) and the **composite
branch** (a homemade dish is built from weighted ingredients, then rejoins the
normal path at normalization). Notice every "fork" is a real decision in the
code: *any results?*, *has a weight?*, *coherent or ambiguous?*, *drink or
solid?* — each maps to a specific check.

### UML — core types and module dependencies

```mermaid
classDiagram
    class Nutrition {
        +str description
        +str serving_unit
        +float bad_sugar_g
        +float natural_sugar_g
        +float sodium_mg
        +float saturated_fat_g
        +float trans_fat_g
        +float fiber_g
        +float protein_g
        +str brand
    }

    class models {
        +parse_usda_response(food) Nutrition
        +parse_fatsecret_response(food) Nutrition
        +is_drink_food(desc, unit) bool
    }

    class data_sources {
        +search_food(query) results, source
        +usda_search_all(query)
        +search_fatsecret(query)
        +get_food_detail(id)
    }

    class grader {
        +grade_food(n) tuple
        +plus_minus_grade(...) str
        -_grade_drink(n)
        -_score_sugar/sodium/sat_fat()
    }

    class retrieval {
        +is_coherent(foods) bool
        +is_composite(query) bool
    }

    class ai {
        +get_llm(provider)
        +write_summary(n, grade)
        +refine_query(query, results)
        +suggest_ingredients(dish)
    }

    class customize {
        +apply_additions(n, ...) Nutrition
    }

    class combine {
        +grade_from_ingredients(items) Nutrition
    }

    class app {
        Streamlit UI + orchestration
    }

    app --> data_sources : 1. fetch
    app --> retrieval : 2. coherent? composite?
    app --> ai : 3. refine / explain
    app --> grader : 4. grade
    app --> customize : drinks
    app --> combine : homemade
    data_sources --> models : raw JSON →
    models --> Nutrition : builds
    grader --> Nutrition : reads
    customize --> Nutrition : returns a copy
    combine --> Nutrition : builds
    ai ..> Nutrition : reads for summary
```

The UML captures the spine: **data sources feed `models`, which build a
`Nutrition`; `retrieval` decides routing/ambiguity; `grader` judges; `ai`
explains; `customize`/`combine` handle the two special cases; `app` orchestrates
everything.** Dependencies flow one way — `app` knows about all of them, but
`grader` and `models` know nothing about the UI, which is what keeps the core
logic testable in isolation.

---