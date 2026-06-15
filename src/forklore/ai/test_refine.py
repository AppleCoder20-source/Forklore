import os
import requests
from dotenv import load_dotenv
from forklore.ai.refinement import refine_query
from langchain_ollama import ChatOllama

load_dotenv()
USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


def get_all_foods(query):
    response = requests.get(
        USDA_URL,
        params={"query": query, "api_key": USDA_API_KEY, "pageSize": 30},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("foods", [])


# Test refinement on coffee (a scattered query)
# Test brand searches
for query in ["starbucks coffee", "dunkin coffee", "starbucks", "mcdonalds"]:
    foods = get_all_foods(query)
    print(f"\n=== {query} ({len(foods)} results) ===")
    for food in foods[:5]:
        print(f"  - {food.get('description')}  [{food.get('dataType')}]")