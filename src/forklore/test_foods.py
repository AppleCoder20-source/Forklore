from forklore.data.fatsecret_client import get_food_detail, find_100g_serving

detail = get_food_detail(28350)        # chocolate donut
print(find_100g_serving(detail))        # serving = works, None = no 100g