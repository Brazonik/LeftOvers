import requests
from bs4 import BeautifulSoup
from datetime import datetime
from recipes.models import ScrapedRecipe, RecipeIngredient
import json  
import time
import random
import re 

def scrape_bbc_food(ingredient, debug=True):
    
    #Scrapes BBC Food for recipes containing the given ingredient.
    #Uses JSON-LD structured data only.
    
    if debug:
        print(f" Searching BBC Food for '{ingredient}'")
    
    search_url = f"https://www.bbc.co.uk/food/search?q={ingredient}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            if debug:
                print(f" Failed to retrieve BBC Food search results. Status code: {response.status_code}")
            return []
        
        if debug:
            print(f" Got search page response (Status: {response.status_code}, Length: {len(response.text)} bytes)")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        recipe_links = []
        seen_urls = set()
        
        #find all links that contain /food/recipes/ in the href
        for link in soup.find_all('a', href=lambda href: href and '/food/recipes/' in href):
            url = f"https://www.bbc.co.uk{link['href']}" if not link['href'].startswith('http') else link['href']
            
            if url in seen_urls:
                continue
                
            #try to find title in parent elements
            title = None
            parent = link.parent
            for _ in range(3):  #look up to 3 levels of parents
                if parent:
                    title_elem = parent.find('h3')
                    if title_elem:
                        title = title_elem.text.strip()
                        break
                    parent = parent.parent
            
            #if no title found, use link text or extract from URL
            if not title or len(title) < 2:
                title = link.text.strip()
                if not title or len(title) < 2:
                    path_parts = url.split('/')
                    if path_parts:
                        title = path_parts[-1].replace('_', ' ').title()
            
            if title and len(title) > 2:
                recipe_links.append({"title": title, "url": url})
                seen_urls.add(url)
        
        if debug:
            print(f" Found {len(recipe_links)} recipe links")
            for i, recipe in enumerate(recipe_links[:5], 1):
                print(f"  {i}. {recipe['title']} - {recipe['url']}")
        
        #process recipes (limited to 5 for testing)
        recipes_to_process = min(5, len(recipe_links))
        processed_recipes = []
        
        for i, recipe_data in enumerate(recipe_links[:recipes_to_process]):
            if debug:
                print(f"\n Processing recipe {i+1}/{recipes_to_process}: {recipe_data['title']}")
            
            #small delay between requests
            time.sleep(random.uniform(1, 2))
            
            try:
                recipe_response = requests.get(recipe_data['url'], headers=headers)
                if recipe_response.status_code != 200:
                    if debug:
                        print(f" Failed to retrieve recipe page. Status: {recipe_response.status_code}")
                    continue
                
                recipe_soup = BeautifulSoup(recipe_response.text, 'html.parser')
                
                #try to extract JSON-LD first (most reliable)
                json_ld = None
                for script in recipe_soup.find_all('script', {'type': 'application/ld+json'}):
                    try:
                        data = json.loads(script.string)
                        
                        #check for recipe type directly
                        if "@type" in data and data["@type"] == "Recipe":
                            json_ld = data
                            break
                            
                        #check in @graph array 
                        elif "@graph" in data:
                            for item in data["@graph"]:
                                if isinstance(item, dict) and "@type" in item and item["@type"] == "Recipe":
                                    json_ld = item
                                    break
                            if json_ld:
                                break
                    except:
                        pass
                
                if json_ld and debug:
                    print(" Found JSON-LD structured data")
                elif debug:
                    print(" No JSON-LD data found, skipping recipe")
                    continue  #skip this recipe if no JSON-LD data
                
                #extract recipe details
                title = recipe_data["title"]
                image_url = None
                ingredients = []
                instructions = ""
                ready_in_minutes = 30  # Default
                servings = 4  # Default
                
                #get data from JSON-LD if available
                if json_ld:
                    
                    if "name" in json_ld:
                        title = json_ld["name"]
                    
                    
                    if "image" in json_ld:
                        img = json_ld["image"]
                        if isinstance(img, str):
                            image_url = img
                        elif isinstance(img, dict) and "url" in img:
                            image_url = img["url"]
                        elif isinstance(img, list) and img:
                            if isinstance(img[0], str):
                                image_url = img[0]
                            elif isinstance(img[0], dict) and "url" in img[0]:
                                image_url = img[0]["url"]
                    
                    if "recipeIngredient" in json_ld:
                        ingredients = json_ld["recipeIngredient"]
                        
                    if "recipeInstructions" in json_ld:
                        instructions_data = json_ld["recipeInstructions"]
                        if isinstance(instructions_data, list):
                            if instructions_data and isinstance(instructions_data[0], dict) and "text" in instructions_data[0]:
                                instructions = "\n".join(f"{i+1}. {step['text']}" for i, step in enumerate(instructions_data))
                            else:
                                instructions = "\n".join(f"{i+1}. {step}" for i, step in enumerate(instructions_data))
                        else:
                            instructions = instructions_data
                    
                    #cooking time
                    total_minutes = 0
                    
                    if "prepTime" in json_ld:
                        prep_time = json_ld["prepTime"]
                        # Parse ISO duration format (PT1H30M)
                        hours = re.search(r'(\d+)H', prep_time)
                        minutes = re.search(r'(\d+)M', prep_time)
                        
                        if hours:
                            total_minutes += int(hours.group(1)) * 60
                        if minutes:
                            total_minutes += int(minutes.group(1))
                    
                    if "cookTime" in json_ld:
                        cook_time = json_ld["cookTime"]
                        # Parse ISO duration format
                        hours = re.search(r'(\d+)H', cook_time)
                        minutes = re.search(r'(\d+)M', cook_time)
                        
                        if hours:
                            total_minutes += int(hours.group(1)) * 60
                        if minutes:
                            total_minutes += int(minutes.group(1))
                    
                    if "totalTime" in json_ld and total_minutes == 0:
                        total_time = json_ld["totalTime"]
                        # Parse ISO duration format
                        hours = re.search(r'(\d+)H', total_time)
                        minutes = re.search(r'(\d+)M', total_time)
                        
                        if hours:
                            total_minutes += int(hours.group(1)) * 60
                        if minutes:
                            total_minutes += int(minutes.group(1))
                    
                    if total_minutes > 0:
                        ready_in_minutes = total_minutes
                    
                    #servings
                    if "recipeYield" in json_ld:
                        try:
                            yield_text = json_ld["recipeYield"]
                            if isinstance(yield_text, list):
                                yield_text = yield_text[0]
                            
                            num_match = re.search(r'\d+', str(yield_text))
                            if num_match:
                                servings = int(num_match.group(0))
                        except:
                            pass
                
                #fix relative URLs if needed
                if image_url and not image_url.startswith(('http:', 'https:')):
                    image_url = f"https:{image_url}" if image_url.startswith('//') else f"https://www.bbc.co.uk{image_url}"
                
                if debug:
                    print(f" Image URL: {image_url if image_url else 'Not found'}")
                    print(f" Found {len(ingredients)} ingredients")
                    if ingredients and len(ingredients) > 0:
                        print(f"  Sample: {ingredients[0]}")
                    print(f" Instructions length: {len(instructions)} characters")
                
                #check if we have the minimum required data
                if (title and instructions and ingredients) or (title and (instructions or ingredients)):
                    try:
                        #save to database
                        scraped_recipe, created = ScrapedRecipe.objects.get_or_create(
                            url=recipe_data["url"],
                            defaults={
                                "title": title,
                                "image": image_url,
                                "instructions": instructions,
                                "ready_in_minutes": ready_in_minutes,
                                "servings": servings,
                                "scraped_at": datetime.now()
                            }
                        )
                        
                        #if recipe already exists, update it
                        if not created:
                            scraped_recipe.title = title
                            if image_url:  
                                scraped_recipe.image = image_url
                            scraped_recipe.instructions = instructions
                            scraped_recipe.ready_in_minutes = ready_in_minutes
                            scraped_recipe.servings = servings
                            scraped_recipe.scraped_at = datetime.now()
                            scraped_recipe.save()
                        
                        #clear existing ingredients and add new ones
                        RecipeIngredient.objects.filter(recipe=scraped_recipe).delete()
                        for ingredient_text in ingredients:
                            RecipeIngredient.objects.create(
                                recipe=scraped_recipe,
                                name=ingredient_text
                            )
                        
                        processed_recipes.append({
                            "id": scraped_recipe.id,
                            "title": scraped_recipe.title,
                            "url": scraped_recipe.url,
                            "image": scraped_recipe.image,
                            "ingredients_count": len(ingredients),
                            "instructions_length": len(instructions),
                            "status": "created" if created else "updated"
                        })
                        
                        if debug:
                            print(f" Recipe successfully {'created' if created else 'updated'} in database")
                    
                    except Exception as e:
                        if debug:
                            print(f" Error saving recipe: {str(e)}")
                else:
                    if debug:
                        print(" Insufficient recipe data")
                        if not title:
                            print("  - Missing title")
                        if not instructions:
                            print("  - Missing instructions")
                        if not ingredients:
                            print("  - Missing ingredients")
            
            except Exception as e:
                if debug:
                    print(f" Error processing recipe: {str(e)}")
        
        if debug:
            print(f"\n Successfully processed {len(processed_recipes)} recipes")
        
        return processed_recipes
    
    except Exception as e:
        if debug:
            print(f" Error during scraping: {str(e)}")
        return []