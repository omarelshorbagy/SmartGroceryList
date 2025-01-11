import requests
import pandas as pd
import threading
from queue import Queue
import re

# Base URL for TheMealDB API
API_BASE_URL = "https://www.themealdb.com/api/json/v1/1/search.php?s="

# Thread-safe queue for storing API results
results_queue = Queue()

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

# Ingredient costs for cost estimation
cost_database = {
    "milk": 0.002,  # Cost per milliliter in euro
    "sugar": 0.005,  # Cost per gram in euro
    "eggs": 0.25,    # Cost per piece in euro
    "flour": 0.002,  # Cost per gram in euro
    "butter": 0.01,  # Cost per gram in euro
    "water": 0.0001, # Cost per milliliter in euro
}

# Dietary filters for ingredient exclusion
dietary_filters = {
    "vegan": ["milk", "butter", "eggs", "cheese", "cream"],
    "gluten-free": ["flour", "wheat"],
}

def validate_input(dish_name):
    """
    Validate the user's dish input by checking its existence in TheMealDB API.
    Fetches meals dynamically for the entered dish name.
    """
    try:
        url = f"{API_BASE_URL}{dish_name.strip()}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            meals = data.get('meals', [])
            if meals:
                print(f"'{dish_name}' is valid and matches '{meals[0]['strMeal']}'. Using '{meals[0]['strMeal']}'.")
                return meals[0]["strMeal"]  # Return the actual matched meal name
            else:
                print(f"No close match found for '{dish_name}'. Please try again.")
                return None
        else:
            print(f"Error: Received status code {response.status_code}. Please try again.")
            return None
    except requests.RequestException as e:
        print(f"Error fetching data for validation: {e}")
        return None

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

def consolidate_ingredients(recipes, filter_type=None):
    """
    Consolidate ingredients across multiple recipes into a single list.
    Apply dietary filters if specified.
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

    # Apply dietary filters if specified
    if filter_type:
        excluded_ingredients = dietary_filters.get(filter_type, [])
        df_grouped = df_grouped[~df_grouped["Ingredient"].str.lower().isin(excluded_ingredients)]

    return df_grouped

def calculate_costs(dataframe):
    """
    Calculate the estimated cost for each ingredient based on quantities.
    If an ingredient is missing from the cost database, assign a default value.
    """
    default_cost_per_unit = 0.10  # Default fallback cost per unit in USD

    def get_cost(ingredient, quantity):
        cost_per_unit = cost_database.get(ingredient.lower(), default_cost_per_unit)
        return cost_per_unit * quantity

    dataframe["Cost"] = dataframe.apply(
        lambda row: get_cost(row["Ingredient"], row["Quantity"]), axis=1
    )
    return dataframe

def format_output(dataframe):
    """
    Format and display the consolidated grocery list with costs.
    """
    dataframe = calculate_costs(dataframe)

    # Format Quantity to display integers as whole numbers and floats with up to 2 decimals
    dataframe["Quantity"] = dataframe["Quantity"].apply(
        lambda x: f"{int(x)}" if x.is_integer() else f"{x:.2f}"
    )
    dataframe["Cost"] = dataframe["Cost"].apply(lambda x: f"€{x:.2f}")

    print("\nConsolidated Grocery List with Costs:")
    print(dataframe.to_string(index=False))

def main():
    print("Welcome to the Smart Grocery List Generator!")
    dishes = []

    while True:
        new_dish = input("Enter a dish name: ").strip()
        if new_dish.lower() in ["yes", "no"]:
            print("Invalid input. Please enter a valid dish name instead of 'yes' or 'no'.")
            continue

        validated_dish = None
        while validated_dish is None:  # Keep asking until valid input is provided
            validated_dish = validate_input(new_dish.strip())
            if validated_dish is None:
                new_dish = input("Re-enter the dish name: ").strip()

        dishes.append(validated_dish)
        print(f"Added '{validated_dish}' to your list.")

        finished = input("Have you finished? Type 'yes' to continue or 'no' to add more dishes: ").strip().lower()
        if finished == "yes":
            break

    dietary_filter = input("Do you have any dietary preferences? (e.g., vegan, gluten-free): ").strip().lower()
    if dietary_filter not in dietary_filters:
        dietary_filter = None

    print("\nFetching recipes...")
    recipes = fetch_recipes_parallel(dishes)

    print("\nConsolidating ingredients...")
    consolidated_ingredients = consolidate_ingredients(recipes, dietary_filter)

    if consolidated_ingredients is not None:
        print("\nFormatting output...")
        format_output(consolidated_ingredients)
    else:
        print("\nNo valid recipes were processed. Please try again with different dishes.")

if __name__ == "__main__":
    main()
