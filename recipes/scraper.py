import requests
from bs4 import BeautifulSoup
from datetime import datetime
from recipes.models import ScrapedRecipe, RecipeIngredient, TrackedIngredient
from django.contrib.auth.models import User

def scrape_recipes_for_user(user):
    """
    Scrapes BBC Food for recipes based on the user's tracked ingredients.
    """
    tracked_ingredients = TrackedIngredient.objects.filter(user=user)
    ingredient_list = [ing.ingredient_name.lower().strip() for ing in tracked_ingredients]

    if not ingredient_list:
        print("❌ No tracked ingredients found.")
        return {'error': "Please add some ingredients to find recipes."}

    if len(ingredient_list) < 2:
        return {'error': "Please add at least 2 ingredients to find recipes."}


    search_query = "+".join(ingredient_list)
    search_url = f"https://www.bbc.co.uk/food/search?q={search_query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        response = requests.get(search_url, headers=headers)
        print(f"Status Code: {response.status_code} for user {user.username}")

        if response.status_code != 200:
            print(f"❌ Failed to retrieve BBC Food for {user.username}.")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        recipe_cards = soup.find_all("div", class_="gel-layout__item")
        print(f"🔍 Found {len(recipe_cards)} recipe cards for user {user.username}.")

        recipes_list = []  

        for card in recipe_cards[:5]:  
            try:
                title_tag = card.find("h3")
                link_tag = card.find("a")

                if not title_tag or not link_tag:
                    continue

                title = title_tag.text.strip()
                url = f"https://www.bbc.co.uk{link_tag['href']}"

                recipe_response = requests.get(url, headers=headers)
                recipe_soup = BeautifulSoup(recipe_response.text, 'html.parser')

                ingredients_section = recipe_soup.find("ul", class_="recipe-ingredients__list")
                ingredients = [ing.text.strip().lower() for ing in ingredients_section.find_all("li")] if ingredients_section else []

                used_ingredients = [ing for ing in ingredient_list if any(ing in recipe_ing for recipe_ing in ingredients)]
                missing_ingredients = [ing for ing in ingredients if not any(tracked in ing for tracked in ingredient_list)]
                unused_tracked = list(set(ingredient_list) - set(used_ingredients))

                used_count = len(used_ingredients)
                total_tracked = len(ingredient_list)
                usage_percentage = (used_count / total_tracked) * 100 if total_tracked > 0 else 0

                print(f"✅ {title} uses {used_count} out of {total_tracked} ingredients ({usage_percentage:.1f}%)")

                nutrition_section = recipe_soup.find("table", class_="nutrition-table")
                nutrition_info = {}
                if nutrition_section:
                    for row in nutrition_section.find_all("tr"):
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            nutrient_name = cells[0].text.strip()
                            amount = cells[1].text.strip()
                            nutrition_info[nutrient_name] = amount

                instructions_section = recipe_soup.find("ol", class_="recipe-method__list")
                instructions = "\n".join([step.text.strip() for step in instructions_section.find_all("li")]) if instructions_section else "No instructions found."

                prep_time_section = recipe_soup.find("p", class_="recipe-metadata__prep-time")
                cook_time_section = recipe_soup.find("p", class_="recipe-metadata__cook-time")
                servings_section = recipe_soup.find("p", class_="recipe-metadata__servings")

                prep_time = prep_time_section.text.strip() if prep_time_section else "N/A"
                cook_time = cook_time_section.text.strip() if cook_time_section else "N/A"
                servings = servings_section.text.strip() if servings_section else "N/A"

                recipe_dict = {
                    'title': title,
                    'url': url,
                    'used_ingredients': used_ingredients,
                    'missing_ingredients': missing_ingredients,
                    'unused_tracked_ingredients': unused_tracked,
                    'ingredients_usage_percentage': round(usage_percentage, 1),
                    'nutrition': nutrition_info,
                    'instructions': instructions,
                    'readyInMinutes': prep_time,
                    'servings': servings
                }

                recipes_list.append(recipe_dict)

            except Exception as e:
                print(f"Error processing recipe: {str(e)}")
                continue

        recipes_list.sort(key=lambda x: x['ingredients_usage_percentage'], reverse=True)
        return recipes_list

    except Exception as e:
        print(f"Error scraping recipes: {str(e)}")
        return []

def scrape_bbc_food(ingredient):
    """
    Scrapes BBC Food for recipes containing the given ingredient.
    """
    search_url = f"https://www.bbc.co.uk/food/search?q={ingredient}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to retrieve BBC Food for {ingredient}.")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        recipes_list = []

        for card in soup.find_all("div", class_="gel-layout__item"):
            title_tag = card.find("h3")
            if title_tag:
                title = title_tag.text.strip()
                link_tag = title_tag.find("a")
                url = f"https://www.bbc.co.uk{link_tag['href']}" if link_tag else None

                if title and url:
                    recipes_list.append({
                        'title': title,
                        'url': url
                    })

        return recipes_list

    except Exception as e:
        print(f"Error scraping BBC Food: {str(e)}")
        return []
    
    