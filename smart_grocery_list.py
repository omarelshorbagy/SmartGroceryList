import requests
import pandas as pd
import threading
from queue import Queue
from fuzzywuzzy import process
import re

# Base URL for TheMealDB API
API_BASE_URL = "https://www.themealdb.com/api/json/v1/1/search.php?s="

# Thread-safe queue for storing API results
results_queue = Queue()

# Known dishes for suggestion
known_dishes = [
    "French Toast", "Pancakes", "Tiramisu", "Spaghetti Carbonara", 
    "Chicken Curry", "French Fries", "Steak", "Fried Rice", "Lasagna"
]

# Known unit conversions (e.g., tablespoons to milliliters)
unit_conversions = {
    "tbs": 15,  # Tablespoons to milliliters
    "tbsp": 15,
    "tsp": 5,   # Teaspoons to milliliters
    "cup": 240, # Cups to milliliters
    "oz": 28.35, # Ounces to grams
    "lb": 453.59, # Pounds to grams
    "ml": 1,    # Milliliters to milliliters
    "l": 1000,  # Liters to milliliters
    "g": 1,     # Grams to grams
    "kg": 1000, # Kilograms to grams
}

# Logical units for common ingredients
logical_units = {
    "parsley": "bunches",
    "sugar": "grams",
    "salt": "grams",
    "flour": "grams",
    "butter": "grams",
    "milk": "milliliters",
    "water": "milliliters",
    "eggs": "pieces",
    "oil": "milliliters",
    "vanilla": "teaspoons"
}

def fetch_recipe(dish_name):
    """
    Fetch recipe details for a given dish name from TheMealDB API.
    Handles invalid responses and ensures thread-safe data handling.
    """
    try:
        url = f"{API_BASE_URL}{dish_name.strip()}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            meals = data.get('meals', [])
            if meals:
                results_queue.put({dish_name: meals})  # Add result to queue
            else:
                print(f"No data found for '{dish_name}'. Skipping.")
                results_queue.put({dish_name: None})
        else:
            print(f"Error: Received status code {response.status_code} for '{dish_name}'.")
            results_queue.put({dish_name: None})
    except requests.RequestException as e:
        print(f"Error fetching data for '{dish_name}': {e}")
        results_queue.put({dish_name: None})

def fetch_recipes_parallel(dish_names):
    """
    Fetch recipes for multiple dish names in parallel using threads.
    """
    threads = []
    for dish in dish_names:
        thread = threading.Thread(target=fetch_recipe, args=(dish,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()  # Wait for all threads to complete

    # Collect results from the queue
    results = {}
    while not results_queue.empty():
        results.update(results_queue.get())
    return results

def parse_quantity(quantity, ingredient):
    """
    Parse a quantity string to extract numeric values and standardize units.
    Assign logical units if no valid unit is detected or if the unit is ambiguous.
    """
    total = 0
    unit = None
    for part in re.split(r"\s*\+\s*", quantity):  # Split by '+'
        try:
            match = re.match(r"([\d./]+)\s*([a-zA-Z]*)", part)
            if match:
                value = eval(match.group(1))  # Evaluate fractions or floats
                unit_part = match.group(2).lower()
                if unit_part in unit_conversions:
                    value *= unit_conversions[unit_part]
                    unit = "grams" if unit_part in ["g", "kg", "oz", "lb"] else "milliliters"
                total += value
        except Exception:
            continue  # Skip invalid parts

    # Assign logical units if the unit is ambiguous or missing
    if not unit or unit == "unknown":
        ingredient_key = ingredient.lower()
        unit = logical_units.get(ingredient_key, "pieces")

    return total, unit

def consolidate_ingredients(recipes):
    """
    Consolidate ingredients across multiple recipes into a single list.
    """
    ingredients_list = []

    for dish, meals in recipes.items():
        if not meals:
            print(f"No data found for {dish}. Skipping.")
            continue
        for meal in meals:
            for i in range(1, 21):  # TheMealDB lists ingredients from strIngredient1 to strIngredient20
                ingredient = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")
                if ingredient and measure:
                    ingredients_list.append({"Ingredient": ingredient.strip(), "Quantity": measure.strip()})

    if not ingredients_list:
        print("No valid ingredients were found.")
        return None  # Return None if no ingredients are found

    # Create a DataFrame and parse numeric quantities
    df = pd.DataFrame(ingredients_list)
    df["Parsed Quantity"], df["Unit"] = zip(*df.apply(
        lambda row: parse_quantity(row["Quantity"], row["Ingredient"]), axis=1
    ))

    # Remove rows with zero quantities
    df = df[df["Parsed Quantity"] > 0]

    # Combine entries with the same ingredient
    df_grouped = (
        df.groupby("Ingredient", as_index=False)
        .apply(lambda group: pd.Series({
            "Quantity": group["Parsed Quantity"].sum(),
            "Unit": group["Unit"].mode().iloc[0]
        }))
    )

    return df_grouped

def format_output(dataframe):
    """
    Format and display the consolidated grocery list.
    """
    # Remove rows where Quantity is 0 or less
    dataframe = dataframe[dataframe["Quantity"] > 0]

    # Format Quantity to display integers as whole numbers and floats with up to 2 decimals
    dataframe["Quantity"] = dataframe["Quantity"].apply(
        lambda x: f"{int(x)}" if x.is_integer() else f"{x:.2f}"
    )

    print("\nConsolidated Grocery List:")
    print(dataframe.to_string(index=False))

def main():
    print("Welcome to the Smart Grocery List Generator!")
    dishes = []

    while True:
        new_dish = input("Enter a dish name: ")
        dishes.append(new_dish.strip())
        finished = input("Have you finished? Type 'yes' to continue or 'no' to add more dishes: ").strip().lower()
        if finished == "yes":
            break

    print("\nFetching recipes...")
    recipes = fetch_recipes_parallel(dishes)

    print("\nConsolidating ingredients...")
    consolidated_ingredients = consolidate_ingredients(recipes)

    if consolidated_ingredients is not None:
        print("\nFormatting output...")
        format_output(consolidated_ingredients)
    else:
        print("\nNo valid recipes were processed. Please try again with different dishes.")

if __name__ == "__main__":
    main()
