import requests
import json

def get_detailed_recipes():
    try:
        API_KEY = "5fd7a331048d4bd49ff39d237b270e91"  
        
        base_url = "https://api.spoonacular.com/recipes"
        random_params = {
            'apiKey': API_KEY,
            'number': 1,
            'tags': 'dinner'
        }
        
        print("Fetching recipes...")
        response = requests.get(f"{base_url}/random", params=random_params)
        response.raise_for_status()
        
        recipes = []
        initial_data = response.json()
        
        for recipe in initial_data['recipes']:
            recipe_id = recipe['id']
            
            detail_params = {
                'apiKey': API_KEY,
                'includeNutrition': 'true'
            }
            
            print(f"\nGetting details for: {recipe['title']}")
            recipe_response = requests.get(f"{base_url}/{recipe_id}/information", params=detail_params)
            recipe_data = recipe_response.json()
            
            ingredients = []
            for ingredient in recipe_data.get('extendedIngredients', []):
                ingredients.append({
                    'name': ingredient.get('name', ''),
                    'amount': ingredient.get('amount', 0),
                    'unit': ingredient.get('unit', ''),
                    'original': ingredient.get('original', '')
                })

            nutrition = recipe_data.get('nutrition', {})
            nutrients = {}
            if 'nutrients' in nutrition:
                for nutrient in nutrition['nutrients']:
                    nutrients[nutrient['name']] = {
                        'amount': nutrient['amount'],
                        'unit': nutrient['unit']
                    }
            
            detailed_recipe = {
                'title': recipe_data['title'],
                'ready_in_minutes': recipe_data.get('readyInMinutes', 0),
                'servings': recipe_data.get('servings', 0),
                'source_url': recipe_data.get('sourceUrl', ''),  
                'spoonacular_url': recipe_data.get('spoonacularSourceUrl', ''), 
                'image': recipe_data.get('image', ''),
                'ingredients': ingredients,
                'instructions': recipe_data.get('instructions', ''),
                'nutrition': {
                    'calories': nutrients.get('Calories', {'amount': 0, 'unit': 'kcal'}),
                    'protein': nutrients.get('Protein', {'amount': 0, 'unit': 'g'}),
                    'fat': nutrients.get('Fat', {'amount': 0, 'unit': 'g'}),
                    'carbohydrates': nutrients.get('Carbohydrates', {'amount': 0, 'unit': 'g'})
                }
            }
            
            recipes.append(detailed_recipe)
            
            print(f"\nRecipe: {detailed_recipe['title']}")
            print(f"Source URL: {detailed_recipe['source_url']}")
            print(f"Spoonacular URL: {detailed_recipe['spoonacular_url']}")
            print("\nIngredients:")
            for ing in detailed_recipe['ingredients']:
                print(f"- {ing['original']}")
            print("\nNutritional Information:")
            for nutrient, value in detailed_recipe['nutrition'].items():
                print(f"- {nutrient}: {value['amount']} {value['unit']}")
            print("-" * 50)
        
        with open('detailed_recipes.json', 'w', encoding='utf-8') as f:
            json.dump(recipes, f, indent=2, ensure_ascii=False)
        print("\nDetailed recipes saved to detailed_recipes.json")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    print("Starting detailed recipe fetcher...")
    get_detailed_recipes()