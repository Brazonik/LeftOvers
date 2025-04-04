#Custom Django management command to scrape BBC Food for recipes based on a given ingredient.

from django.core.management.base import BaseCommand
from recipes.scraper import scrape_bbc_food_updated
import re 

class Command(BaseCommand):
    help = "Scrape BBC Food for recipes based on a given ingredient."

    def add_arguments(self, parser):
        parser.add_argument('ingredient', type=str, help="Ingredient to search for")
        parser.add_argument('--count', type=int, default=5, help="Number of recipes to scrape")
        parser.add_argument('--debug', action='store_true', help="Show detailed debug output")

    def handle(self, *args, **kwargs):
        ingredient = kwargs['ingredient']
        debug = kwargs.get('debug', True)
        count = kwargs.get('count', 5)
        
        self.stdout.write(f"Scraping BBC Food for '{ingredient}' recipes...")
        recipes = scrape_bbc_food_updated(ingredient, debug=debug)
        
        if len(recipes) > 0:
            self.stdout.write(self.style.SUCCESS(f" Successfully scraped {len(recipes)} recipes for '{ingredient}'"))
            
            for i, recipe in enumerate(recipes, 1):
                self.stdout.write(f"{i}. {recipe['title']} ({recipe['status']})")
                self.stdout.write(f"   URL: {recipe['url']}")
                self.stdout.write(f"   Ingredients: {len(recipe['ingredients'])}")
                self.stdout.write(f"   Ready in: {recipe['ready_in_minutes']} minutes")
                self.stdout.write("")
        else:
            self.stdout.write(self.style.WARNING(f" No recipes found for '{ingredient}'"))

