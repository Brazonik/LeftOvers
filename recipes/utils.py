# utils.py (new file)
import re

def normalize_ingredient_name(name):
    """Normalize ingredient names for better matching"""
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    
    # Remove common modifiers
    modifiers = ['fresh', 'frozen', 'raw', 'cooked', 'diced', 'chopped', 'sliced', 
                'minced', 'whole', 'peeled', 'grated', 'ground', 'dried', 'canned']
    
    for modifier in modifiers:
        name = re.sub(r'\b' + modifier + r'\b', '', name)
    
    # Remove measurement words
    measurements = ['cup', 'cups', 'tablespoon', 'teaspoon', 'pound', 'ounce', 
                   'gram', 'kg', 'ml', 'liter', 'pinch', 'dash']
    
    for measure in measurements:
        name = re.sub(r'\b' + measure + r'\b', '', name)
    
    # Handle common plurals
    name = re.sub(r'(?:es|s)$', '', name)
    name = ' '.join(name.split())
    return name.strip()