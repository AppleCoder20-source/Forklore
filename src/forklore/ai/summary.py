import os
import streamlit as st
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from forklore.ai.llm import get_llm        # ← use the shared factory


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")



def write_summary(nutrition, letter, pct,provider="local"):
    llm = get_llm(provider)
    is_drink = nutrition.serving_unit == "ml"
    drink_note = "This is a DRINK, judged on a stricter per-100ml sugar scale." if is_drink else ""


    prompt = f"""You are a friendly nutrition assistant helping everyday people understand their food.

Write 3-4 clear sentences explaining why this food got its grade. Use warm, plain language — like explaining to a friend.
Show the original user input ONLY IF PROMPTED for them to input sugar 
WHAT TO COVER:
- The grade and the main reason for it.
- The 2-3 nutrients that mattered most (focus on whichever are HIGH or notably LOW).
- A short note on why those nutrients are good or bad, using the guidance below.

NUTRIENT GUIDANCE (all per 100g/ml) — explain whichever ones drove the grade:

SUGAR (the "bad" added sugar):
- Scale: under 2.5g = low | 2.5-5g = moderate | 5-10g = high | over 10g = very high.
- Why high sugar is bad: it adds empty calories; in drinks it adds up fast across a whole bottle.

SATURATED FAT:
- Scale: under 1.5g = low | 1.5-5g = moderate | 5-8g = high | over 8g = very high.
- Why high saturated fat is a concern: it's the type of fat linked to heart health when eaten in excess.

SODIUM (salt):
- Scale: under 90mg = low | 90-250mg = moderate | 250-600mg = high | over 600mg = very high.
- Why high sodium is a concern: too much salt affects blood pressure over time.

TRANS FAT:
- Any amount above 0 is a red flag — it's the worst type of fat. Mention it if present.

FIBER (a GOOD nutrient — more is better):
- Scale: 6g+ = great | 3-6g = good | 1.5-3g = okay | under 1.5g = low.
- Why fiber is good: it aids digestion and helps you feel full.

PROTEIN (a GOOD nutrient — more is better):
- Scale: 12g+ = great | 6-12g = good | 3-6g = okay | under 3g = low.
- Why protein is good: it builds and repairs the body and keeps you full.

RULES:
- Use ONLY the numbers and guidance given here.
- Focus on the nutrients that actually drove THIS food's grade (the high bad ones, or notably good ones).
- Do NOT mention daily limits, daily intake, obesity, diabetes, or any disease.
- Do NOT give medical advice or invent numbers.

FOOD DATA:
Food: {nutrition.description}
Grade: {letter} ({pct}%)
{drink_note}
Added sugar: {nutrition.bad_sugar_g} g per 100g/ml
Saturated fat: {nutrition.saturated_fat_g} g per 100g/ml
Trans fat: {nutrition.trans_fat_g} g per 100g/ml
Sodium: {nutrition.sodium_mg} mg per 100g/ml
Fiber: {nutrition.fiber_g} g per 100g/ml
Protein: {nutrition.protein_g} g per 100g/ml
"""
    return llm.invoke(prompt).content.strip()