# This script analyzes the structure of the BBC Food website to help with scraping recipes.
import requests
from bs4 import BeautifulSoup
import json
import os
import re

def analyze_bbc_food_structure(ingredient="chocolate"):
    
    #Analyzes the BBC Food website structure to help with scraping.
    #Saves HTML files and generates a structure report.
    
    print(f"Analyzing BBC Food structure using search term: {ingredient}")
    
    #step 1: Create output directory
    os.makedirs("bbc_analysis", exist_ok=True)
    
    #step 2: Set up headers for requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    #step 3: Get the search results page
    search_url = f"https://www.bbc.co.uk/food/search?q={ingredient}"
    print(f"Fetching search results from: {search_url}")
    
    search_response = requests.get(search_url, headers=headers)
    if search_response.status_code != 200:
        print(f"Failed to retrieve search results. Status code: {search_response.status_code}")
        return
    
    #save the search results HTML
    with open(os.path.join("bbc_analysis", "search_results.html"), "w", encoding="utf-8") as f:
        f.write(search_response.text)
    
    search_soup = BeautifulSoup(search_response.text, "html.parser")
    
    #step 4: Analyze the search results structure
    print("\n=== SEARCH RESULTS PAGE ANALYSIS ===")
    
    #look for main container elements
    main_content = search_soup.find("main")
    if main_content:
        print("✅ Found main content element")
    else:
        print("❌ No main content element found")
        main_content = search_soup  
    
    #detect recipe containers/cards
    container_candidates = [
        ("div.gel-layout__item", main_content.select("div.gel-layout__item")),
        ("div.promo", main_content.select("div.promo")),
        ("li.gel-layout__item", main_content.select("li.gel-layout__item")),
        (".promo", main_content.select(".promo")),
        (".search-results__item", main_content.select(".search-results__item"))
    ]
    
    print("\nPotential recipe container elements:")
    for selector, elements in container_candidates:
        print(f"- {selector}: {len(elements)} elements")
    
    #find all recipe links
    recipe_links = []
    for link in search_soup.find_all("a", href=lambda href: href and "/food/recipes/" in href):
        url = f"https://www.bbc.co.uk{link['href']}" if not link['href'].startswith('http') else link['href']
        #find associated title
        title_elem = None
        parent = link.parent
        for _ in range(3):  
            if parent:
                title_elem = parent.find("h3")
                if title_elem:
                    break
                parent = parent.parent
        
        title = title_elem.text.strip() if title_elem else link.text.strip() or "Unknown Recipe"
        recipe_links.append({"title": title, "url": url})
    
    print(f"\nFound {len(recipe_links)} recipe links")
    for i, recipe in enumerate(recipe_links[:5], 1):
        print(f"{i}. {recipe['title']} - {recipe['url']}")
    
    #step 5: Analyze a recipe detail page
    if recipe_links:
        recipe_url = recipe_links[0]["url"]
        print(f"\n\n=== RECIPE DETAIL PAGE ANALYSIS ===")
        print(f"Analyzing recipe: {recipe_links[0]['title']}")
        print(f"URL: {recipe_url}")
        
        recipe_response = requests.get(recipe_url, headers=headers)
        if recipe_response.status_code != 200:
            print(f"Failed to retrieve recipe. Status code: {recipe_response.status_code}")
            return
        
        #save the recipe HTML
        with open(os.path.join("bbc_analysis", "recipe_detail.html"), "w", encoding="utf-8") as f:
            f.write(recipe_response.text)
        
        recipe_soup = BeautifulSoup(recipe_response.text, "html.parser")
        
        #check for JSON-LD structured data (most reliable source)
        json_ld = None
        for script in recipe_soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string)
                if "@type" in data and data["@type"] == "Recipe":
                    json_ld = data
                    break
                elif "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and "@type" in item and item["@type"] == "Recipe":
                            json_ld = item
                            break
            except:
                pass
        
        if json_ld:
            print("✅ Found JSON-LD structured data")
            print("  - Title:", json_ld.get("name", "N/A"))
            print("  - Image:", json_ld.get("image", "N/A"))
            print("  - Ingredients count:", len(json_ld.get("recipeIngredient", [])))
            print("  - Instructions count:", len(json_ld.get("recipeInstructions", [])))
        else:
            print("❌ No JSON-LD structured data found")
        
        #analyze HTML structure for key recipe elements
        print("\nKey recipe elements in HTML:")
        
        title_candidates = [
            recipe_soup.find("h1"),
            recipe_soup.find("h1", class_="content-title__text"),
            recipe_soup.find("h1", class_="recipe-header__title")
        ]
        title_elem = next((elem for elem in title_candidates if elem), None)
        print(f"- Title: {title_elem.text.strip() if title_elem else 'Not found'}")
        
        image_candidates = [
            recipe_soup.find("img", class_="recipe-media__image"),
            recipe_soup.find("div", class_="recipe-media__image"),
            recipe_soup.find("img", class_=lambda c: c and "recipe" in c)
        ]
        image_elem = next((elem for elem in image_candidates if elem), None)
        if image_elem:
            if image_elem.name == "img":
                image_url = image_elem.get("src", "")
            else:
                style = image_elem.get("style", "")
                match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                image_url = match.group(1) if match else ""
            print(f"- Image: {image_url[:60]}..." if image_url else "Not found")
        else:
            print("- Image: Not found")
        
        ingredients_sections = [
            recipe_soup.find("ul", class_=lambda c: c and "ingredients" in c.lower()),
            recipe_soup.find("section", class_=lambda c: c and "ingredients" in c.lower()),
            recipe_soup.find("div", class_=lambda c: c and "ingredients" in c.lower())
        ]
        ingredients_section = next((elem for elem in ingredients_sections if elem), None)
        if ingredients_section:
            ingredients = ingredients_section.find_all("li")
            print(f"- Ingredients section: Found with class '{ingredients_section.get('class')}', contains {len(ingredients)} items")
            if ingredients:
                print(f"  Sample: {ingredients[0].text.strip()}")
        else:
            print("- Ingredients section: Not found")
        
        instruction_sections = [
            recipe_soup.find("ol", class_=lambda c: c and ("method" in c.lower() or "steps" in c.lower())),
            recipe_soup.find("section", class_=lambda c: c and ("method" in c.lower() or "steps" in c.lower())),
            recipe_soup.find("div", class_=lambda c: c and ("method" in c.lower() or "steps" in c.lower()))
        ]
        instruction_section = next((elem for elem in instruction_sections if elem), None)
        if instruction_section:
            steps = instruction_section.find_all("li")
            print(f"- Instructions section: Found with class '{instruction_section.get('class')}', contains {len(steps)} steps")
            if steps:
                print(f"  Sample: {steps[0].text.strip()[:60]}...")
        else:
            print("- Instructions section: Not found")
        
        metadata_candidates = [
            recipe_soup.find_all("p", class_=lambda c: c and "metadata" in c.lower()),
            recipe_soup.find_all("div", class_=lambda c: c and "metadata" in c.lower()),
            recipe_soup.find_all("div", class_=lambda c: c and "detail" in c.lower())
        ]
        metadata_elems = next((elems for elems in metadata_candidates if elems), [])
        if metadata_elems:
            print(f"- Metadata: Found {len(metadata_elems)} elements")
            for elem in metadata_elems[:3]:
                print(f"  {elem.text.strip()}")
        else:
            print("- Metadata: Not found")
        
    print("\nAnalysis complete! Check the 'bbc_analysis' folder for HTML files.")

if __name__ == "__main__":
    analyze_bbc_food_structure()