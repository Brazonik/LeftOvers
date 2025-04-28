# template filters for the recipes app.

from datetime import datetime, timedelta
from django import template
import json
import re

register = template.Library()

@register.filter
def json_parse(value):
    # Convert a JSON string to a Python list
    try:
        if not isinstance(value, str):
            return value
            
        #if empty, return empty list
        if not value or value == '[]':
            return []
            
        if value.startswith('[') or value.startswith('{'):
            try:
                #replace single quotes with double quotes for valid JSON
                return json.loads(value.replace("'", '"'))
            except:
                pass
                
        #handle the case where the string has bullets/dots (•) between chars
        if '•' in value:
            #first remove brackets
            clean_text = value.strip('[]')
                
            #split by commas
            parts = clean_text.split(',')
                
            clean_parts = []
            for part in parts:
                #remove special characters and get the actual text
                clean_part = re.sub(r'[^a-zA-Z0-9 ,]', '', part).strip()
                if clean_part:
                    clean_parts.append(clean_part)
                        
            return clean_parts
                
        if value:
            return [value]
                
        return []
    except Exception as e:
        # If all parsing fails, return original value
        return value
    
    #Why it's useful: Makes it possible to loop through ingredients in templates

@register.filter
def get_primary_image(recipe):
    #Get the primary image for a recipe, works with both Recipe and DatasetRecipe
    #Looks for a recipe image in various places where it might be stored
    #Ensures recipes always show an image if one exists
    try:
        #first check for user-uploaded image
        if hasattr(recipe, 'image') and recipe.image:
            return recipe.image.url
            
        #then looks for a method to get the image. Check if the object has the method directly
        if hasattr(recipe, 'get_primary_image_url') and callable(getattr(recipe, 'get_primary_image_url')):
            img_url = recipe.get_primary_image_url()
            if img_url:
                return img_url
                
        if hasattr(recipe, 'images'):
            images = recipe.images
            if isinstance(images, list) and len(images) > 0:
                return images[0]
                    
            if isinstance(images, str) and images.startswith('['):
                images_list = json_parse(images)
                if images_list and len(images_list) > 0:
                    return images_list[0]
                    
        return None
    except Exception as e:
        print(f"Error in get_primary_image: {e}")
        return None

@register.filter
def has_image(recipe):
    #check if a recipe has at least one image
    #shows a placeholder image if there isn't one
    try:
        if hasattr(recipe, 'image') and recipe.image:
            return True
            
        return get_primary_image(recipe) is not None
    except Exception as e:
        print(f"Error in has_image: {e}")
        return False

@register.filter
def get_title(recipe):
    if hasattr(recipe, 'title'):
        return recipe.title
    elif hasattr(recipe, 'name'):
        return recipe.name
    return "Untitled Recipe"

@register.filter
def format_duration(value):
    #displays prep and cook times in human-readable format
    #turns PT10M to human-readable format 10 min
    
    if not value:
        return "Not specified"
        
    try:
        value_str = str(value)
        
        #handle ISO 8601 durations
        if value_str.startswith('PT'):
            value_str = value_str[2:]
            
            if 'M' in value_str:
                minutes = value_str.split('M')[0]
                return f"{minutes} min"
            elif 'H' in value_str:
                hours = value_str.split('H')[0]
                return f"{hours} hr"
        
        #if not ISO format but has numeric value assume it is minutes
        if value_str.isdigit():
            return f"{value_str} min"
            
        return value_str
    except:
        return str(value)

@register.filter
def has_tried(recipe, user):
    #check if a user has tried a recipe
    #allows showing different options for tried vs. untried recipes
    
    from recipes.models import TriedRecipe, Recipe, DatasetRecipe
    
    if not user.is_authenticated:
        return False
    
        
    if isinstance(recipe, Recipe):
        return TriedRecipe.objects.filter(recipe=recipe, user=user).exists()
    elif isinstance(recipe, DatasetRecipe):
        return TriedRecipe.objects.filter(dataset_recipe=recipe, user=user).exists()
    
    return False

@register.filter
def subtract(value, arg):
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value
    
    #this filter lets you perform subtraction directly in your templates without needing to create a custom Python function or view variable.

@register.filter
def get_difficulty(recipe):
    """
    Determine recipe difficulty based on ingredient count:
    - Beginner: <= 3 ingredients
    - Easy: 4-6 ingredients
    - Medium: 7-8 ingredients
    - Hard: 9-12 ingredients
    - Insane: > 12 ingredients
    
    Uses the same counting method as the point system.
    """
    ingredient_count = 0
    
    #get recipe ingredients
    if hasattr(recipe, 'get_ingredients'):
        ingredients = recipe.get_ingredients()
    elif hasattr(recipe, 'ingredients_list') and recipe.ingredients_list:
        import json
        try:
            ingredients = json.loads(recipe.ingredients_list)
        except:
            ingredients = []
    elif hasattr(recipe, 'ingredients') and recipe.ingredients:
        try:
            if isinstance(recipe.ingredients, str):
                if recipe.ingredients.startswith('['):
                    import json
                    ingredients = json.loads(recipe.ingredients.replace("'", '"'))
                else:
                    ingredients = recipe.ingredients.split('\n')
            elif hasattr(recipe.ingredients, 'all'):
                ingredients = list(recipe.ingredients.all())
            else:
                ingredients = recipe.ingredients
        except:
            ingredients = []
    else:
        ingredients = []
    
    try:
        if hasattr(ingredients, 'all'):  
            ingredient_count = ingredients.count()
        else:
            ingredient_count = len([i for i in ingredients if i])
    except TypeError:
        ingredient_count = 0
    
    if hasattr(recipe, 'matching_ingredients') and hasattr(recipe, 'missing_ingredients'):
        if hasattr(recipe, 'total_ingredients'):
            ingredient_count = recipe.total_ingredients
    
    #determine difficulty level with updated thresholds
    if ingredient_count <= 3:
        return {'level': 'Beginner', 'class': 'info', 'icon': 'fa-baby'}
    elif ingredient_count <= 6:
        return {'level': 'Easy', 'class': 'success', 'icon': 'fa-smile'}
    elif ingredient_count <= 9:
        return {'level': 'Medium', 'class': 'primary', 'icon': 'fa-thumbs-up'}
    elif ingredient_count <= 12:
        return {'level': 'Hard', 'class': 'warning', 'icon': 'fa-fire'}
    else:
        return {'level': 'Insane', 'class': 'danger', 'icon': 'fa-bomb'}

@register.filter(name='add_class')
def add_class(field, css_class):
    #add a CSS class to a form field.
    try:
        return field.as_widget(attrs={"class": css_class})
    except AttributeError:
        return field
    
@register.filter
def parse_ingredients(ingredients_data):
    #parse ingredients from various formats into a list of strings
    if not ingredients_data:
        return []
    
    if isinstance(ingredients_data, list):
        return ingredients_data
    
    if isinstance(ingredients_data, str):
        try:
            if ingredients_data.startswith('['):
                parsed = json.loads(ingredients_data.replace("'", '"'))
                if isinstance(parsed, list):
                    return parsed
            
            # split by newlines or commas
            if '\n' in ingredients_data:
                return [line.strip() for line in ingredients_data.split('\n') if line.strip()]
            else:
                return [item.strip() for item in ingredients_data.split(',') if item.strip()]
        except:
            return [ingredients_data]
    
    return [str(ingredients_data)]


@register.filter
def startswith(text, starts):
    
    #check if a string starts with a given value
    
    if text is None:
        return False
    return str(text).startswith(str(starts))

@register.filter
def is_expiring_soon(item):
    #check if an item is expiring within 3 days.
    if not item.expiration_date:
        return False
    
    today = datetime.now().date()
    threshold = today + timedelta(days=3)
    return item.expiration_date <= threshold

@register.filter
def expiring_soon(items):
    #return a list of items that are expiring soon.
    expiring_items = []
    today = datetime.now().date()
    threshold = today + timedelta(days=3)
    
    for item in items:
        if item.expiration_date and item.expiration_date <= threshold:
            expiring_items.append(item)
    
    return expiring_items

@register.filter
def split(value, delimiter):
    #plit the value by delimiter
    return value.split(delimiter)

@register.filter
def strip(value):
    #Strip whitespace from the beginning and end of a string
    return value.strip() if value else value