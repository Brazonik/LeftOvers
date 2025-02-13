from django.core.management.base import BaseCommand
from recipes.scraper import scrape_bbc_food

class Command(BaseCommand):
    help = "Scrape BBC Food for recipes based on a given ingredient."

    def add_arguments(self, parser):
        parser.add_argument('ingredient', type=str, help="Ingredient to search for")

    def handle(self, *args, **kwargs):
        ingredient = kwargs['ingredient']
        recipes = scrape_bbc_food(ingredient)

        if len(recipes) > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ Successfully scraped {len(recipes)} unique recipes for '{ingredient}'"))
        else:
            self.stdout.write(self.style.WARNING(f"❌ No recipes found for '{ingredient}'"))

