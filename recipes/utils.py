import re



def normalize_ingredient_name(name):
    
    #Normalize an ingredient name for better matching:
    #- Convert to lowercase
    #- Remove quantities, measurements, and prep instructions
    #- Convert plurals to singulars
    #- Remove parenthetical content
    #- Handle common ingredient substitutions
    
    if not name:
        return ""
        
    #convert to lowercase and strip whitespace
    name = name.lower().strip()
    
    #remove quotes if present
    name = name.replace("'", "").replace('"', "")
    
    #remove quantities =
    name = re.sub(r'^\d+[\s/]*', '', name)  
    name = re.sub(r'^\d+\.\d+\s*', '', name)  
    name = re.sub(r'^\d+\s*-\s*\d+\s*', '', name)  
    
    #emove fractions
    name = re.sub(r'\b\d+/\d+\b', '', name)  
    
    measurements = [
        'cup', 'cups', 'tbsp', 'tablespoon', 'tablespoons', 'tsp', 'teaspoon', 'teaspoons',
        'oz', 'ounce', 'ounces', 'pound', 'pounds', 'lb', 'lbs', 'g', 'gram', 'grams',
        'kg', 'kilogram', 'ml', 'milliliter', 'l', 'liter', 'pinch', 'pinches', 'dash',
        'handful', 'handfuls', 'clove', 'cloves', 'can', 'cans', 'jar', 'jars',
        'slice', 'slices', 'piece', 'pieces', 'bunch', 'bunches', 'sprig', 'sprigs'
    ]
    measurement_pattern = r'\b(' + '|'.join(measurements) + r')\b\s*(of\s+)?'
    name = re.sub(measurement_pattern, '', name, flags=re.IGNORECASE)
    
    prep_adjectives = [
        'fresh', 'frozen', 'dried', 'canned', 'chopped', 'minced', 'sliced', 'diced',
        'grated', 'shredded', 'ground', 'crushed', 'whole', 'halved', 'quartered',
        'peeled', 'seeded', 'pitted', 'raw', 'cooked', 'baked', 'roasted', 'grilled',
        'room temperature', 'chilled', 'boneless', 'skinless', 'extra', 'large', 'small',
        'medium', 'thick', 'thin', 'roughly', 'cubed', 'melted',
        'softened', 'cold', 'hot', 'warm', 'ripe', 'unripe', 'toasted', 'packed',
         'level', 'divided', 'organic', 'low-fat', 'low fat',
        'non-fat', 'reduced-fat', 'full-fat', 'all-purpose', 'self-rising'
    ]
    
    for adj in prep_adjectives:
        name = re.sub(r'\b' + adj + r'\b', '', name, flags=re.IGNORECASE)
    
    #remove common prefixes like "of", "for"
    name = re.sub(r'\bof\s+', '', name)
    name = re.sub(r'\bfor\s+', '', name)
    
    #remove "to taste" and similar phrases
    name = re.sub(r'\bto taste\b', '', name)
    name = re.sub(r'\bas needed\b', '', name)
    name = re.sub(r'\boptional\b', '', name)
    
    #handle common singular/plural forms 
    common_plurals = [
        ('chicken', 'chickens'), ('onion', 'onions'), ('tomato', 'tomatoes'), ('potato', 'potatoes'),
        ('carrot', 'carrots'), ('egg', 'eggs'), ('pepper', 'peppers'), ('rice', 'rices'),
        ('breast', 'breasts'), ('bean', 'beans'), ('leaf', 'leaves'), ('loaf', 'loaves'),
        ('thigh', 'thighs'), ('pea', 'peas'), ('scallion', 'scallions'), ('shallot', 'shallots'),
        ('clove', 'cloves'), ('herb', 'herbs'), ('spice', 'spices'), ('apple', 'apples'),
        ('garlic clove', 'garlic cloves'), ('olive', 'olives'), ('mushroom', 'mushrooms')
    ]
    
    for singular, plural in common_plurals:
        name = re.sub(r'\b' + plural + r'\b', singular, name, flags=re.IGNORECASE)
    
    #handle common ingredient synonyms and substitutes
    synonyms = [
        ('bell pepper', 'pepper'),
        ('red pepper', 'pepper'),
        ('green pepper', 'pepper'),
        ('yellow pepper', 'pepper'),
        ('capsicum', 'pepper'),
        ('green onion', 'scallion'),
        ('spring onion', 'scallion'),
        ('coriander', 'cilantro'),
        ('beef mince', 'ground beef'),
        ('minced beef', 'ground beef'),
        ('beef ground', 'ground beef'),
        ('mince', 'ground beef'),
        ('pasta noodle', 'pasta'),
        ('pasta noodles', 'pasta'),
        ('spaghetti', 'pasta'),
        ('fettuccine', 'pasta'),
        ('linguine', 'pasta'),
        ('penne', 'pasta'),
        ('macaroni', 'pasta'),
        ('egg noodle', 'pasta'),
        ('rice grain', 'rice'),
        ('long grain rice', 'rice'),
        ('white rice', 'rice'),
        ('brown rice', 'rice'),
        ('basmati rice', 'rice'),
        ('jasmine rice', 'rice'),
        ('vinegar', 'vinegar'),
        ('white vinegar', 'vinegar'),
        ('rice vinegar', 'vinegar'),
        ('apple cider vinegar', 'vinegar'),
        ('red wine vinegar', 'vinegar'),
        ('beef stock', 'beef broth'),
        ('chicken stock', 'chicken broth'),
        ('vegetable stock', 'vegetable broth'),
        ('aubergine', 'eggplant'),
        ('courgette', 'zucchini')
    ]
    
    for primary, normalized in synonyms:
        name = re.sub(r'\b' + primary + r'\b', normalized, name, flags=re.IGNORECASE)
    
    #remove parenthetical content
    name = re.sub(r'\(.*?\)', '', name)
    
    #clean up whitespace and punctuation
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.strip('.,;:-')
    
    if not name:
        return "unknown ingredient"
    
    return name


def get_ingredient_category(ingredient):
    
    #determines which category an ingredient belongs to for substitution purposes

    normalized = normalize_ingredient_name(ingredient)
    
    categories = {
        'oils': ['oil', 'olive oil', 'vegetable oil', 'canola oil', 'sunflower oil', 
                'coconut oil', 'sesame oil', 'peanut oil', 'avocado oil'],
        
        'vinegars': ['vinegar', 'white vinegar', 'apple cider vinegar', 'balsamic vinegar', 
                    'red wine vinegar', 'rice vinegar', 'sherry vinegar'],
        
        'sweeteners': ['sugar', 'brown sugar', 'honey', 'maple syrup', 'agave', 
                      'corn syrup', 'molasses', 'stevia'],
        
        'dairy_milk': ['milk', 'almond milk', 'soy milk', 'oat milk', 'coconut milk', 
                      'cream', 'half and half', 'buttermilk'],
        
        'dairy_yogurt': ['yogurt', 'greek yogurt', 'sour cream', 'creme fraiche'],
        
        'flour': ['flour', 'all purpose flour', 'wheat flour', 'bread flour', 'cake flour', 
                 'self rising flour', 'almond flour', 'coconut flour'],
        
        'rice': ['rice', 'jasmine rice', 'basmati rice', 'brown rice', 'white rice',
                'sushi rice', 'arborio rice', 'wild rice'],
        
        'pasta': ['pasta', 'spaghetti', 'fettuccine', 'linguine', 'penne', 
                 'macaroni', 'lasagna', 'egg noodle'],
        
        'broth': ['broth', 'stock', 'chicken broth', 'beef broth', 'vegetable broth',
                'bone broth', 'chicken stock', 'beef stock', 'vegetable stock'],
        
        'cheese_soft': ['cream cheese', 'cottage cheese', 'ricotta', 'mascarpone', 'brie', 
                       'camembert', 'feta'],
        
        'cheese_hard': ['cheddar', 'parmesan', 'mozzarella', 'swiss', 'gouda', 'gruyere',
                       'monterey jack', 'colby'],
        
        'leafy_greens': ['spinach', 'kale', 'arugula', 'lettuce', 'swiss chard', 
                        'collard green', 'cabbage'],
        
        'herbs': ['basil', 'thyme', 'rosemary', 'oregano', 'parsley', 'cilantro', 
                 'mint', 'dill', 'chive', 'sage'],
        
        'beef': ['beef', 'ground beef', 'steak', 'chuck', 'brisket', 'sirloin'],
        
        'poultry': ['chicken', 'turkey', 'duck', 'chicken breast', 'chicken thigh', 
                   'chicken wing', 'ground chicken', 'ground turkey'],
        
        'pork': ['pork', 'ham', 'bacon', 'pork chop', 'ground pork', 'pork loin', 
                'pork shoulder'],
        
        'fish': ['fish', 'salmon', 'tuna', 'cod', 'tilapia', 'halibut', 'trout', 
                'sea bass', 'snapper'],
        
        'shellfish': ['shrimp', 'crab', 'lobster', 'scallop', 'clam', 'mussel', 'oyster'],
        
        'grains': ['quinoa', 'barley', 'oat', 'bulgur', 'couscous', 'farro'],
        
        'beans': ['bean', 'black bean', 'pinto bean', 'kidney bean', 'chickpea', 'lentil']
    }
    
    for category, items in categories.items():
        for item in items:
            if item == normalized or normalized.startswith(item + ' ') or ' ' + item in normalized:
                return category
                
    return None

def check_substitution_compatibility(ingredient1, ingredient2):
    
    #checks if two ingredients can be substituted for each other
    #returns True if they are in the same category
    
    cat1 = get_ingredient_category(ingredient1)
    cat2 = get_ingredient_category(ingredient2)
    
    if cat1 and cat2 and cat1 == cat2:
        return True
    return False

def match_ingredients(user_ingredients, recipe_ingredients):
    
    # Enhanced ingredient matching algorithm with better fuzzy matching
    # and common ingredient substitution handling
    
    #Args:
    #    user_ingredients: list of ingredients the user has
    #    recipe_ingredients: list of ingredients required by the recipe
        
    #Returns:
     #   dict with:
     #   - matching_ingredients: list of recipe ingredients user has
     #   - missing_ingredients: list of recipe ingredients user doesn't have
     #   - match_percentage: percentage of recipe ingredients matched
     #   - user_ingredient_usage: percentage of user ingredients used
     #   - is_perfect_match: boolean indicating if all ingredients are matched
    
    # Normalize all ingredients
    normalized_user_ingredients = [normalize_ingredient_name(ing) for ing in user_ingredients]
    normalized_recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe_ingredients]
    
    #initialize match tracking
    matching_ingredients = []
    missing_ingredients = []
    matched_recipe_indices = set()
    used_user_indices = set()
    
    print(f"DEBUG - Normalized user ingredients: {normalized_user_ingredients}")
    
    #direct matches
    for i, recipe_ing in enumerate(normalized_recipe_ingredients):
        if not recipe_ing or recipe_ing == 'unknown ingredient':
            continue
            
        for j, user_ing in enumerate(normalized_user_ingredients):
            if not user_ing or user_ing == 'unknown ingredient':
                continue
                
            #exact match or one is contained in the other
            if recipe_ing == user_ing or (
                len(user_ing) > 3 and (
                    recipe_ing.startswith(user_ing + ' ') or
                    recipe_ing.endswith(' ' + user_ing) or
                    f' {user_ing} ' in f' {recipe_ing} '
                )
            ):
                matching_ingredients.append(recipe_ingredients[i])
                matched_recipe_indices.add(i)
                used_user_indices.add(j)
                break
    
    #category/substitution matches for remaining ingredients
    for i, recipe_ing in enumerate(normalized_recipe_ingredients):
        if i in matched_recipe_indices or not recipe_ing or recipe_ing == 'unknown ingredient':
            continue
            
        recipe_category = get_ingredient_category(recipe_ing)
        if not recipe_category:
            continue
            
        for j, user_ing in enumerate(normalized_user_ingredients):
            if j in used_user_indices or not user_ing or user_ing == 'unknown ingredient':
                continue
                
            user_category = get_ingredient_category(user_ing)
            if user_category and user_category == recipe_category:
                matching_ingredients.append(f"{recipe_ingredients[i]} (using {user_ingredients[j]})")
                matched_recipe_indices.add(i)
                used_user_indices.add(j)
                break
    
    for i, recipe_ing in enumerate(recipe_ingredients):
        if i not in matched_recipe_indices:
            missing_ingredients.append(recipe_ing)
    
    match_percentage = 0
    if recipe_ingredients:
        match_percentage = (len(matched_recipe_indices) / len(recipe_ingredients)) * 100
        
    user_ingredient_usage = 0
    if user_ingredients:
        user_ingredient_usage = (len(used_user_indices) / len(user_ingredients)) * 100
    
    is_perfect_match = len(missing_ingredients) == 0
    
    print(f"DEBUG - Match results for recipe:")
    print(f"  Match %: {match_percentage:.1f}% ({len(matched_recipe_indices)}/{len(recipe_ingredients)} ingredients)")
    print(f"  User ingredient usage: {user_ingredient_usage:.1f}% ({len(used_user_indices)}/{len(user_ingredients)} user ingredients)")
    print(f"  Matching: {matching_ingredients}")
    print(f"  Missing: {missing_ingredients}")
    print(f"  User ingredients found: {[user_ingredients[i] for i in used_user_indices]}")
    
    return {
        'matching_ingredients': matching_ingredients,
        'missing_ingredients': missing_ingredients,
        'match_percentage': round(match_percentage, 1),
        'user_ingredient_usage': round(user_ingredient_usage, 1),
        'is_perfect_match': is_perfect_match,
        'total_ingredients': len(recipe_ingredients),
        'extra_ingredients_needed': len(missing_ingredients)
    }