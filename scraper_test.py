import requests
from bs4 import BeautifulSoup
from datetime import datetime
from recipes.models import ScrapedRecipe, RecipeIngredient
import os
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# Now import your models
from recipes.models import ScrapedRecipe, RecipeIngredient
from recipes.scraper import scrape_bbc_food


def scrape_bbc_food(ingredient):
    """
    Scrapes BBC Food for recipes containing the given ingredient.
    """
    search_url = f"https://www.bbc.co.uk/food/search?q={ingredient}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve BBC Food for {ingredient}. Status code: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    recipes = []
    
    # Locate recipe containers (modify based on actual HTML structure)
    recipe_cards = soup.find_all("div", class_="gel-layout__item")
    
    for card in recipe_cards:
        title_tag = card.find("h3")
        if not title_tag:
            continue
        
        title = title_tag.text.strip()
        link_tag = title_tag.find("a")
        if link_tag:
            url = "https://www.bbc.co.uk" + link_tag["href"]
        else:
            continue
        
        image_tag = card.find("img")
        image_url = image_tag["src"] if image_tag else None
        
        # Fetch detailed recipe page
        recipe_response = requests.get(url, headers=headers)
        recipe_soup = BeautifulSoup(recipe_response.text, 'html.parser')
        
        instructions_section = recipe_soup.find("ol", class_="recipe-method__list")
        instructions = "\n".join([step.text.strip() for step in instructions_section.find_all("li")]) if instructions_section else "No instructions found."
        
        # Extract ingredients
        ingredients_section = recipe_soup.find_all("li", class_="recipe-ingredients__list-item")
        ingredients = [ing.text.strip() for ing in ingredients_section] if ingredients_section else []
        
        # Save recipe to database
        scraped_recipe = ScrapedRecipe.objects.create(
            title=title,
            url=url,
            image=image_url,
            instructions=instructions,
            scraped_at=datetime.now()
        )
        
        for ingredient in ingredients:
            RecipeIngredient.objects.create(recipe=scraped_recipe, name=ingredient)
        
        recipes.append(scraped_recipe)
    
    return recipes
