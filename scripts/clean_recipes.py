# This script cleans the raw recipe dataset and creates a new CSV file with optimized data format.
# The cleaned dataset will have the following columns: Name, CookTime, PrepTime, RecipeIngredientParts, RecipeInstructions, RecipeCategory, RecipeServings, Calories, ProteinContent, CarbohydrateContent, FatContent, Description, Images
# The RecipeIngredientParts and RecipeInstructions columns will be converted to Python lists for better handling.
# The RecipeInstructions column will be cleaned and formatted for better readability.
# The Images column will be extracted from the RecipeInstructions column.
# The cleaned dataset will be saved as 'recipes_cleaned.csv'.
# converts 300000 recipes to a cleaned dataset

import pandas as pd
import re
import json

print("Creating optimized recipe dataset (300,000 recipes)...")

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
    'FatContent',
    'Description',  
    'Images'  
]

def parse_r_vector(text):
    #Convert r vector format to Python list with improved handling
    if pd.isna(text) or text == '' or text == 'c()' or text == 'c("")':
        return []
        
    if not text.startswith('c('):
        return [text]
        
    matches = re.findall(r'c\("(.+)"\)', text)
    if matches:
        return [item.strip('"') for item in matches[0].split('", "')]
    
    if text.startswith('c(') and text.endswith(')'):
        content = text[2:-1].strip()
        if content:
            items = []
            current_item = ""
            in_quotes = False
            
            for char in content:
                if char == '"' or char == "'":
                    in_quotes = not in_quotes
                    if not in_quotes and current_item:
                        items.append(current_item.strip('"\''))
                        current_item = ""
                    continue
                    
                if char == ',' and not in_quotes:
                    if current_item:
                        items.append(current_item.strip('"\''))
                        current_item = ""
                    continue
                    
                if in_quotes or char.strip():
                    current_item += char
            
            if current_item:
                items.append(current_item.strip('"\''))
                
            return [item for item in items if item]
            
    try:
        items = text[2:-1].split(',')
        return [item.strip().strip('"').strip("'") for item in items if item.strip()]
    except:
        print(f"Could not parse: {text}")
        return []

def parse_instructions(text):
    #Special handling for instructions which can be in various formats, removes empty space, preserves plain text instructions that do not use vectory format
    parsed = parse_r_vector(text)
    
    if not parsed or (len(parsed) == 1 and not parsed[0]):
        if isinstance(text, str) and not text.startswith('c('):
            if text and text != 'nan' and len(text) > 5:
                return [text]
        return []
    # If the instructions are not in vector format, return as a list
    
    cleaned_instructions = []
    for step in parsed:
        if step and step != 'nan' and len(step) > 1:
            step = re.sub(r'\s+', ' ', step).strip()
            cleaned_instructions.append(step)
    # Clean up the instructions and remove extra spaces
    return cleaned_instructions

def parse_images(text):
    #Extract image URLs from the Images column
    images = parse_r_vector(text)
    return [img for img in images if img.startswith('http')]

try:
    print("Reading CSV file...")
    df = pd.read_csv("data/recipes.csv", nrows=300000, usecols=[col for col in columns_to_keep if col in pd.read_csv("data/recipes.csv", nrows=0).columns])
    # Load the raw dataset with selected columns
    
    print(f"\nLoaded {len(df)} recipes")
    
    print("Cleaning data...")
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
        'RecipeInstructions': 'c("")',
        'Description': '',
        'Images': 'c("")'
        #filling in missing values with default values
        #ensures that the data is clean and consistent
    })
    
    print("Converting ingredients format...")
    df['RecipeIngredientParts'] = df['RecipeIngredientParts'].apply(parse_r_vector)
    
    print("Converting instructions format...")
    print("\nSample Raw Instructions:")
    for i in range(5):
        if i < len(df):
            print(f"{df.iloc[i]['Name']}: {df.iloc[i]['RecipeInstructions'][:100]}...")
    
    df['RecipeInstructions'] = df['RecipeInstructions'].apply(parse_instructions)
    
    if 'Images' in df.columns:
        print("Processing image URLs...")
        df['Images'] = df['Images'].apply(parse_images)
    
    with_instructions = df[df['RecipeInstructions'].apply(lambda x: len(x) > 0)].shape[0]
    print(f"\nRecipes with instructions: {with_instructions} / {len(df)} ({(with_instructions/len(df))*100:.1f}%)")
    
    print("Saving cleaned dataset...")
    df.to_csv("data/recipes_cleaned.csv", index=False)
    print("\n✅ Clean dataset created and saved as 'recipes_cleaned.csv'")
    
    print("\nSample Recipe:")
    print("--------------")
    sample = df.iloc[0]
    print(f"Name: {sample['Name']}")
    if 'Description' in sample and sample['Description']:
        print(f"Description: {sample['Description'][:100]}...")
    print(f"Category: {sample['RecipeCategory']}")
    print(f"Prep Time: {sample['PrepTime']}")
    print(f"Cook Time: {sample['CookTime']}")
    print(f"Servings: {sample['RecipeServings']}")
    
    print("\nIngredients:")
    for ing in sample['RecipeIngredientParts']:
        print(f"- {ing}")
    
    print("\nInstructions:")
    if len(sample['RecipeInstructions']) > 0:
        for i, step in enumerate(sample['RecipeInstructions']):
            print(f"{i+1}. {step}")
    else:
        print("No instructions available")
    
    if 'Images' in sample and len(sample['Images']) > 0:
        print("\nImages:")
        for img in sample['Images'][:3]: 
            print(f"- {img}")
    
    print("\nNutrition Info:")
    print(f"Calories: {sample['Calories']}")
    print(f"Protein: {sample['ProteinContent']}g")
    print(f"Carbs: {sample['CarbohydrateContent']}g")
    print(f"Fat: {sample['FatContent']}g")

except Exception as e:
    print(f"Error processing dataset: {str(e)}")
    import traceback
    traceback.print_exc()