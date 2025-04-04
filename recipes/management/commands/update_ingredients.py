# This script updates the ingredients of the recipes in the database using a CSV file
# It reads the csv file and processes each recipe to update the ingredients, instructions, and images
# The script uses bulk_update to update the recipes in batches for better performance
# Uses clean recipes CSV file with cleaned data
# The CSV file should have the following columns: Name, RecipeIngredientQuantities, RecipeIngredientParts, RecipeInstructions, Images
# To run this command, use the following command:
# python manage.py update_ingredients


from django.core.management.base import BaseCommand
import pandas as pd
from recipes.models import DatasetRecipe
from django.db import transaction
from django.db.models import Q  
import time
import json
import re

class Command(BaseCommand):
    help = 'Update recipe ingredients from CSV'
    
    def parse_instructions(self, text):
        """Better handling for instructions data"""
        if isinstance(text, list):
            return '\n'.join(text)
            
        if not text or text == '[]' or text == 'c("")':
            return ''
        # If it's a single instruction, return as a list with one item
        
        
            
        # If it's already a JSON string, parse it into newline sperated strings
        if isinstance(text, str) and text.startswith('['):
            try:
                instructions_list = json.loads(text.replace("'", '"'))
                return '\n'.join(instructions_list)
            except:
                pass
                
        return text
    # Function to parse the instructions data
    # If the data is a list, it will join the list into a string
    
    
    def handle(self, *args, **kwargs):
        try:
            self.stdout.write('Starting to read CSV file...')
            df = pd.read_csv('data/recipes_cleaned.csv')
            total_recipes = len(df)
            self.stdout.write(f'Found {total_recipes} recipes in CSV')
            
            
            with_instructions = sum(1 for _, row in df.iterrows() 
                                if row.get('RecipeInstructions') and 
                                   row.get('RecipeInstructions') != '[]')
            self.stdout.write(f'CSV contains {with_instructions} recipes with instructions ({with_instructions/total_recipes*100:.1f}%)')
            # Count the number of recipes with instructions in the CSV file
            with transaction.atomic():
                recipes_to_update = []
                start_time = time.time()
                recipes_updated = 0
                #empty list to store recipes
                
                for index, row in df.iterrows():
                    if index % 1000 == 0:  # Show progress every 1000 recipes
                        elapsed_time = time.time() - start_time
                        progress = (index / total_recipes) * 100
                        self.stdout.write(f'Processing {index}/{total_recipes} ({progress:.1f}%) - Elapsed time: {elapsed_time:.1f}s')
                        #
                    
                    recipe = DatasetRecipe.objects.filter(name=row['Name']).first()
                    if recipe:
                        # Handle ingredients
                        recipe.ingredients_quantities = row.get('RecipeIngredientQuantities', '')
                        recipe.ingredients_parts = row.get('RecipeIngredientParts', '[]')
                        recipe.images = row.get('Images', '[]')
                        
                        instructions = row.get('RecipeInstructions', '')
                        recipe.instructions = self.parse_instructions(instructions)
                        # Improved instructions handling
                        # Update the recipe object with the values from the csv file
                        # Update the ingredients, instructions, and images
                        
                        
                        recipes_to_update.append(recipe)
                        recipes_updated += 1
                        # Add the recipe to the list of recipes to update
                        # Increment the counter for updated recipes
                        # Update the recipe in the database

                    if len(recipes_to_update) >= 5000:  
                        self.stdout.write(f'Updating batch of {len(recipes_to_update)} recipes...')
                        DatasetRecipe.objects.bulk_update(
                            recipes_to_update,
                            ['ingredients_quantities', 'ingredients_parts', 'instructions', 'images'],
                            batch_size=5000
                        )
                        recipes_to_update = []
                        # Update the recipes in batches of 5000
                        
                
                if recipes_to_update:
                    self.stdout.write(f'Updating final batch of {len(recipes_to_update)} recipes...')
                    DatasetRecipe.objects.bulk_update(
                        recipes_to_update,
                        ['ingredients_quantities', 'ingredients_parts', 'instructions', 'images'],
                        batch_size=5000
                    )
                    # Update any remaining recipes
                    
            
            # Check how many recipes now have instructions after updating
            # Calculate the total time taken to update the recipes
            
            with_instructions_after = DatasetRecipe.objects.filter(
                ~Q(instructions='') & ~Q(instructions='[]') & ~Q(instructions=None)
            ).count()
            
            total_time = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(
                f'Successfully updated {recipes_updated} recipes in {total_time:.1f} seconds\n'
                f'Recipes with instructions: {with_instructions_after} / {DatasetRecipe.objects.count()} '
                f'({with_instructions_after/DatasetRecipe.objects.count()*100:.1f}%)'
            ))
            # Print the number of recipes updated and the time taken to update them

            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))