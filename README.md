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


## Example
```text
Welcome to the Smart Grocery List Generator!
Enter a dish name: pizza
'pizza' is valid and matches 'Pizza Express Margherita'. Using 'Pizza Express Margherita'.
Added 'Pizza Express Margherita' to your list.
Have you finished? Type 'yes' to continue or 'no' to add more dishes: yes
Do you have any dietary preferences? (e.g., vegan, gluten-free): no

Fetching recipes...
Formatting output...

Consolidated Grocery List with Costs:
 Ingredient Quantity        Unit   Cost
 Mozzarella       70       grams  €7.00
    Passata       80       grams  €8.00
Plain Flour      225       grams €22.50
       Salt        1       grams  €0.10
      Sugar        5 milliliters  €0.03
      Water      150 milliliters  €0.02
      Yeast       15       grams  €1.50

C:\Users\hp\OneDrive\Desktop\SmartGroceryList>
```
## Notes
  
- Costs are rough estimates based on the cost_database dictionary.
  
- Unit parsing is heuristic and may not handle all free-form measures.
  
- Add or update costs and units in the script to adapt to local markets.

 
