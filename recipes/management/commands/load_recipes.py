# This script will load the recipes from the CSV file into the database
# The CSV file should be placed in the 'data' directory of the Django project
# The CSV file should have the following columns: Name, CookTime, PrepTime, RecipeCategory, RecipeServings, RecipeIngredientParts, RecipeIngredientQuantities, Calories, ProteinContent, CarbohydrateContent, FatContent, RecipeInstructions
# To run this command, use the following command:
# python manage.py load_recipes
# Smaller dataset was used for testing

from django.core.management.base import BaseCommand
import pandas as pd
from recipes.models import DatasetRecipe
from django.db import transaction

class Command(BaseCommand):
    help = 'Load recipes from CSV file'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write('Starting to read CSV file...')
            #use the recipes_subset_clean.csv 
            df = pd.read_csv('data/recipes_subset_clean.csv')
            total_recipes = len(df)
            self.stdout.write(f'Found {total_recipes} recipes in CSV')
            #counts number of recipes in the CSV file

            #clear existing recipes first
            DatasetRecipe.objects.all().delete()

            #bulk create in batches
            with transaction.atomic():
                batch_size = 1000
                #empty list to store recipes
                recipes_to_create = []
                
                for index, row in df.iterrows():
                    if index % 1000 == 0:
                        #prints the number of recipes processed
                    
                        self.stdout.write(f'Processing recipe {index}/{total_recipes}')
                        
                    
                    recipe = DatasetRecipe(
                        #creating a new recipe object for each row in the csv file
                        #setting the values of the recipe object to the values in the csv file
                        
                        name=row['Name'],
                        cook_time=row.get('CookTime', 'Unknown'),
                        prep_time=row.get('PrepTime', 'Unknown'),
                        category=row.get('RecipeCategory', 'Uncategorized'),
                        servings=row.get('RecipeServings', 4),
                        ingredients_parts=row.get('RecipeIngredientParts', '[]'),
                        ingredients_quantities=row.get('RecipeIngredientQuantities', '[]'),
                        calories=float(row.get('Calories', 0)),
                        protein=float(row.get('ProteinContent', 0)),
                        carbs=float(row.get('CarbohydrateContent', 0)),
                        fat=float(row.get('FatContent', 0)),
                        instructions=row.get('RecipeInstructions', '')
                    )
                    recipes_to_create.append(recipe)
                    #used to collect recipes in batches of 1000
                    
                    
                    if len(recipes_to_create) >= batch_size:
                        DatasetRecipe.objects.bulk_create(recipes_to_create)
                        recipes_to_create = []
                        #create recipes in batches of 1000
                
                #create any remaining recipes
                if recipes_to_create:
                    DatasetRecipe.objects.bulk_create(recipes_to_create)
                    

            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {total_recipes} recipes'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            #prints error message if there is an error