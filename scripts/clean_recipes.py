import pandas as pd
import ast
import re

print("Creating optimized recipe subset...")

# Select only the columns we need
columns_to_keep = [
    'Name',
    'CookTime',
    'PrepTime',
    'RecipeIngredientParts',
    'RecipeInstructions',
    'RecipeCategory',
    'RecipeServings',
    'Calories',
    'ProteinContent',
    'CarbohydrateContent',
    'FatContent'
]

def parse_r_vector(text):
    """Convert R vector format to Python list"""
    if pd.isna(text):
        return []
    # Extract content between c(" and ")
    matches = re.findall(r'c\("(.+)"\)', text)
    if matches:
        # Split by '", "' and remove any remaining quotes
        return [item.strip('"') for item in matches[0].split('", "')]
    return []

try:
    # Read first 50000 rows with specific columns
    df = pd.read_csv("data/recipes.csv", nrows=50000, usecols=columns_to_keep)
    
    print(f"\nLoaded {len(df)} recipes")
    
    # Clean the data
    df = df.fillna({
        'CookTime': 'Unknown',
        'PrepTime': 'Unknown',
        'RecipeCategory': 'Uncategorized',
        'RecipeServings': 4,
        'Calories': 0,
        'ProteinContent': 0,
        'CarbohydrateContent': 0,
        'FatContent': 0,
        'RecipeIngredientParts': 'c("")',
        'RecipeInstructions': 'c("")'
    })
    
    # Convert R format vectors to Python lists
    print("Converting ingredients format...")
    df['RecipeIngredientParts'] = df['RecipeIngredientParts'].apply(parse_r_vector)
    
    print("Converting instructions format...")
    df['RecipeInstructions'] = df['RecipeInstructions'].apply(parse_r_vector)
    
    # Save the cleaned subset
    print("Saving cleaned dataset...")
    df.to_csv("data/recipes_subset_clean.csv", index=False)
    print("\n✅ Clean subset created and saved as 'recipes_subset_clean.csv'")
    
    # Show a sample recipe
    print("\nSample Recipe:")
    print("--------------")
    sample = df.iloc[0]
    print(f"Name: {sample['Name']}")
    print(f"Category: {sample['RecipeCategory']}")
    print(f"Prep Time: {sample['PrepTime']}")
    print(f"Cook Time: {sample['CookTime']}")
    print(f"Servings: {sample['RecipeServings']}")
    print("\nIngredients:")
    for ing in sample['RecipeIngredientParts']:
        print(f"- {ing}")
    print("\nInstructions:")
    for i, step in enumerate(sample['RecipeInstructions'], 1):
        print(f"{i}. {step}")
    print("\nNutrition Info:")
    print(f"Calories: {sample['Calories']}")
    print(f"Protein: {sample['ProteinContent']}g")
    print(f"Carbs: {sample['CarbohydrateContent']}g")
    print(f"Fat: {sample['FatContent']}g")

except Exception as e:
    print(f"Error processing dataset: {str(e)}")
    import traceback
    traceback.print_exc()