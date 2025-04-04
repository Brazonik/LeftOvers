import os
import sys
import django
import pandas as pd
import numpy as np
from django.db import transaction
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from recipes.models import DatasetRecipe

def parse_c_format(text):
    if pd.isna(text):
        return []
    if text.startswith('c(') and text.endswith(')'):
        text = text[2:-1]
    items = [item.strip().strip('"').strip("'") for item in text.split(',')]
    return [item for item in items if item]

def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except:
        return default

def import_recipes():
    print("Starting recipe import...")
    start_time = time.time()
    
    try:
        df = pd.read_csv('data/recipes.csv', nrows=100000)
        total_recipes = len(df)
        print(f"Found {total_recipes} recipes to import")
        
        DatasetRecipe.objects.all().delete()
        print("Cleared existing recipes")
        
        recipes_to_create = []
        recipes_imported = 0
        errors = 0
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    servings = row.get('RecipeServings')
                    if pd.isna(servings):
                        servings = 4
                    else:
                        try:
                            servings = int(float(servings))
                        except:
                            servings = 4

                    recipe = DatasetRecipe(
                        name=row['Name'],
                        cook_time=row.get('CookTime', 'Unknown'),
                        prep_time=row.get('PrepTime', 'Unknown'),
                        category=row.get('RecipeCategory', 'Uncategorized'),
                        servings=servings,
                        ingredients_parts=parse_c_format(row['RecipeIngredientParts']),
                        ingredients_quantities=parse_c_format(row['RecipeIngredientQuantities']),
                        calories=safe_float(row.get('Calories', 0)),
                        protein=safe_float(row.get('ProteinContent', 0)),
                        carbs=safe_float(row.get('CarbohydrateContent', 0)),
                        fat=safe_float(row.get('FatContent', 0))
                    )
                    recipes_to_create.append(recipe)
                    recipes_imported += 1
                    
                    if len(recipes_to_create) >= 1000:
                        DatasetRecipe.objects.bulk_create(recipes_to_create)
                        elapsed_time = time.time() - start_time
                        progress = (recipes_imported / total_recipes) * 100
                        print(f'Progress: {progress:.1f}% ({recipes_imported}/{total_recipes}) - Time elapsed: {elapsed_time:.1f}s')
                        recipes_to_create = []
                        
                except Exception as e:
                    errors += 1
                    if errors <= 10:  
                        print(f'Error with recipe {row.get("Name", "Unknown")}: {str(e)}')
                    continue
            
            if recipes_to_create:
                DatasetRecipe.objects.bulk_create(recipes_to_create)
        
        total_time = time.time() - start_time
        final_count = DatasetRecipe.objects.count()
        print(f'\nFinished importing {final_count} recipes in {total_time:.1f} seconds')
        if errors > 0:
            print(f'Encountered {errors} errors during import')
        
    except Exception as e:
        print(f'Error during import: {str(e)}')

if __name__ == "__main__":
    import_recipes()