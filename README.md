# Smart Grocery List Generator

A Python CLI tool that fetches recipes from **TheMealDB API** and generates a consolidated grocery list with standardized units, optional dietary filters, and cost estimates.

## Features
- Validate and fetch recipes from TheMealDB by dish name.
- Fetch multiple recipes in parallel using threads.
- Parse messy measurements (fractions, combined units) into standardized values.
- Apply logical units (grams, milliliters, pieces) for consistency.
- Consolidate duplicate ingredients across multiple recipes.
- Apply dietary filters (vegan, gluten-free).
- Estimate ingredient costs with a simple cost database.

## How to Run
1. Clone this repository:
     git clone https://github.com/omarelshorbagy/SmartGroceryList.git
     cd SmartGroceryList
   
3. Run the script in Python:
     python smart_grocery_list.py
   
5. Enter dish names when prompted.
6. (Optional) Specify a dietary preference (vegan or gluten-free).
5.View the final consolidated grocery list with normalized quantities and estimated costs.


Example
----------------

Welcome to the Smart Grocery List Generator!
Enter a dish name: Chicken Curry
'Chicken Curry' is valid and matches 'Chicken Curry'. Added to your list.
Have you finished? Type 'yes' to continue or 'no' to add more dishes: yes

Fetching recipes...
Consolidating ingredients...

Consolidated Grocery List with Costs:
 Ingredient   Quantity      Unit       Cost
 Chicken      500           grams      €4.50
 Onions       2             pieces     €0.40
 ...
 ----------------

Notes
  
  Costs are rough estimates based on the cost_database dictionary.
  
  Unit parsing is heuristic and may not handle all free-form measures.
  
  Add or update costs and units in the script to adapt to local markets.

 
