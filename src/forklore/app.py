import streamlit as st
import os
import requests
from dotenv import load_dotenv
from forklore.models import parse_usda_response
from forklore.core.grader import grade_food


load_dotenv()
USDA_API_KEY = os.getenv("USDA_API_KEY")
USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

def usda_api(query):
    response = requests.get(
        USDA_URL,
        params = {
            "query": query, "api_key" : USDA_API_KEY, "pageSize": 10
            },
            timeout = 15,     
    )
    
    response.raise_for_status()
    foods = response.json().get("foods", [])
    return foods[0] if foods else None

st.title("🥗 Forklore")
food_input = st.text_input("Enter a food name to grade", placeholder = "Big Mac")

if st.button("Analyze"):
    food = usda_api(food_input)
    if food is None:
        st.error("No results found try again")
    else:
        #st.write(f"Found: {food['description']}")
        #st.json(food) #Original Json data very messy to read 
        retrieve_food = parse_usda_response(food) #Uses a parsing function to make data more readable and organized 
        letter, color, pct = grade_food(retrieve_food) #Grades the food, returns letter/color/percentage

        #Colored grade badge
        st.markdown(
            f"<div style='background:{color};color:white;padding:24px;"
            f"text-align:center;border-radius:8px;'>"
            f"<div style='font-size:64px;font-weight:bold;line-height:1;'>{letter}</div>"
            f"<div style='font-size:24px;'>{pct}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.write(food["description"])    # which exact Fanta is this?
        st.write(retrieve_food)          # the clean parsed nutrition