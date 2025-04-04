import os
import sys
import django
import pandas as pd
from django.db import transaction

# Set up Django, this file uses the cleaned database to populate the database
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Import models AFTER Django setup
from recipes.models import DatasetRecipe, DatasetIngredient

def import_dataset_recipes():
    try:
        print(" Starting dataset import...")
        
        # Load the dataset
        df = pd.read_csv("data/recipes_cleaned.csv")  # Use full dataset

        recipes_imported = 0
        batch_size = 5000  

        recipes_to_create = []
        ingredients_to_create = []

        # Use a transaction for batch insertion
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    # Create dataset recipe 
                    recipe = DatasetRecipe(
                        name=row["Name"],
                        cook_time=row.get("CookTime", ""),
                        prep_time=row.get("PrepTime", ""),
                        category=row.get("RecipeCategory", ""),
                        servings=row.get("RecipeServings", ""),
                        calories=row.get("Calories", 0),
                        protein=row.get("ProteinContent", 0),
                        carbs=row.get("CarbohydrateContent", 0),
                        fat=row.get("FatContent", 0),
                        instructions=row.get("RecipeInstructions", ""),
                    )
                    recipes_to_create.append(recipe)

                    # Handle ingredients properly 
                    ingredients = row.get("RecipeIngredientParts", "")
                    if isinstance(ingredients, str):
                        ingredients = ingredients.split(",")  # Convert to list

                    for ingredient in ingredients:
                        if ingredient.strip():  # Skip empty ingredients
                            ingredients_to_create.append(DatasetIngredient(
                                recipe=recipe,  
                                name=ingredient.strip().lower()
                            ))

                    recipes_imported += 1
                    if recipes_imported % batch_size == 0:
                        # Bulk insert every batch_size recipes
                        DatasetRecipe.objects.bulk_create(recipes_to_create)
                        DatasetIngredient.objects.bulk_create(ingredients_to_create)
                        recipes_to_create = []
                        ingredients_to_create = []
                        print(f" Imported {recipes_imported} recipes...")

                except Exception as e:
                    print(f" Error importing recipe {row['Name']}: {e}")
                    continue

            # Final batch insert for remaining items
            if recipes_to_create:
                DatasetRecipe.objects.bulk_create(recipes_to_create)
            if ingredients_to_create:
                DatasetIngredient.objects.bulk_create(ingredients_to_create)

        print(f"\n Successfully imported {recipes_imported} recipes!")

    except Exception as e:
        print(f" Error during import: {e}")

if __name__ == "__main__":
    import_dataset_recipes()
