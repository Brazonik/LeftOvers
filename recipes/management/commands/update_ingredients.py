from django.core.management.base import BaseCommand
import pandas as pd
from recipes.models import DatasetRecipe
from django.db import transaction
import time

class Command(BaseCommand):
    help = 'Update recipe ingredients from CSV'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write('Starting to read CSV file...')
            df = pd.read_csv('data/recipes_cleaned.csv')
            total_recipes = len(df)
            self.stdout.write(f'Found {total_recipes} recipes in CSV')
            
            # Bulk update in a single transaction
            with transaction.atomic():
                recipes_to_update = []
                start_time = time.time()
                
                for index, row in df.iterrows():
                    if index % 1000 == 0:  # Show progress every 1000 recipes
                        elapsed_time = time.time() - start_time
                        progress = (index / total_recipes) * 100
                        self.stdout.write(f'Processing {index}/{total_recipes} ({progress:.1f}%) - Elapsed time: {elapsed_time:.1f}s')
                    
                    recipe = DatasetRecipe.objects.filter(name=row['Name']).first()
                    if recipe:
                        recipe.ingredients_quantities = row['RecipeIngredientQuantities']
                        recipe.ingredients_parts = row['RecipeIngredientParts']
                        recipes_to_update.append(recipe)
                        
                    if len(recipes_to_update) >= 5000:  # Batch update every 5000 recipes
                        self.stdout.write(f'Updating batch of {len(recipes_to_update)} recipes...')
                        DatasetRecipe.objects.bulk_update(
                            recipes_to_update,
                            ['ingredients_quantities', 'ingredients_parts'],
                            batch_size=5000
                        )
                        recipes_to_update = []
                
                # Update any remaining recipes
                if recipes_to_update:
                    self.stdout.write(f'Updating final batch of {len(recipes_to_update)} recipes...')
                    DatasetRecipe.objects.bulk_update(
                        recipes_to_update,
                        ['ingredients_quantities', 'ingredients_parts'],
                        batch_size=5000
                    )

            total_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(
                f'Successfully updated recipes in {total_time:.1f} seconds'
            ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))