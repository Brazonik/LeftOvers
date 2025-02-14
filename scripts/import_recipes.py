import os
import sys
import django

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
import json
from recipes.models import DatasetRecipe

def import_recipes():
    print("Starting bulk import of recipes...")
    
    try:
        # Clear existing recipes
        DatasetRecipe.objects.all().delete()
        
        # Read the CSV file
        df = pd.read_csv("data/recipes_cleaned.csv")
        print(f"Found {len(df)} recipes to import")
        
        # Prepare recipes in batches
        batch_size = 5000
        recipes_to_create = []
        
        for index, row in df.iterrows():
            try:
                ingredients = row.get('RecipeIngredientParts', '[]')
                if isinstance(ingredients, str):
                    try:
                        ingredients = eval(ingredients)
                    except:
                        ingredients = []

                recipe = DatasetRecipe(
                    name=row['Name'],
                    cook_time=row.get('CookTime', 'Unknown'),
                    prep_time=row.get('PrepTime', 'Unknown'),
                    category=row.get('RecipeCategory', 'Uncategorized'),
                    servings=row.get('RecipeServings', 4),
                    calories=float(row.get('Calories', 0)),
                    protein=float(row.get('ProteinContent', 0)),
                    carbs=float(row.get('CarbohydrateContent', 0)),
                    fat=float(row.get('FatContent', 0)),
                    instructions=row.get('RecipeInstructions', ''),
                    ingredients_list=json.dumps(ingredients)
                )
                recipes_to_create.append(recipe)
                
                # Bulk create when batch size is reached
                if len(recipes_to_create) >= batch_size:
                    DatasetRecipe.objects.bulk_create(recipes_to_create)
                    print(f"Imported {index + 1} recipes...")
                    recipes_to_create = []
                
            except Exception as e:
                print(f"Error with recipe {row.get('Name', 'Unknown')}: {str(e)}")
                continue
        
        # Create any remaining recipes
        if recipes_to_create:
            DatasetRecipe.objects.bulk_create(recipes_to_create)
            
        print(f"\n✅ Successfully imported {DatasetRecipe.objects.count()} recipes")
        
    except Exception as e:
        print(f"\n🚨 Error during import: {str(e)}")

if __name__ == "__main__":
    import_recipes()