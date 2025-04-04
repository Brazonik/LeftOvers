import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from recipes.scraper import scrape_bbc_food

if __name__ == "__main__":
    ingredient = input("Enter ingredient to search for (default: chocolate): ") or "chocolate"
    print(f"\nTesting BBC Food scraper for '{ingredient}'...\n")
    
    recipes = scrape_bbc_food(ingredient, debug=True)
    
    print(f"\nFinal results: {len(recipes)} recipes processed")
    for i, recipe in enumerate(recipes, 1):
        print(f"{i}. {recipe['title']} ({recipe['status']})")
        print(f"   - URL: {recipe['url']}")
        print(f"   - Ingredients: {recipe['ingredients_count']}")
        print(f"   - Instructions: {recipe['instructions_length']} characters")
        print()