# template filters for the recipes app.


from django import template
import json
import re

register = template.Library()

@register.filter
def json_parse(value):
    # Convert a JSON string to a Python list
    try:
        # If it's already a Python object (list, dict, etc.), return as is
        if not isinstance(value, str):
            return value
            
        # If empty, return empty list
        if not value or value == '[]':
            return []
            
        # If it's a standard JSON string
        if value.startswith('[') or value.startswith('{'):
            try:
                # Replace single quotes with double quotes for valid JSON
                return json.loads(value.replace("'", '"'))
            except:
                pass
                
        # Handle the case where the string has bullets/dots (•) between chars
        if '•' in value:
            # First remove brackets
            clean_text = value.strip('[]')
                
            # Split by commas
            parts = clean_text.split(',')
                
            clean_parts = []
            for part in parts:
                # Remove special characters and get the actual text
                clean_part = re.sub(r'[^a-zA-Z0-9 ,]', '', part).strip()
                if clean_part:
                    clean_parts.append(clean_part)
                        
            return clean_parts
                
        # If it's a single ingredient, return as a list with one item
        if value:
            return [value]
                
        # Default case - empty list
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
        # First check for user-uploaded image
        if hasattr(recipe, 'image') and recipe.image:
            return recipe.image.url
            
        # Then looks for a method to get the image. Check if the object has the method directly
        if hasattr(recipe, 'get_primary_image_url') and callable(getattr(recipe, 'get_primary_image_url')):
            img_url = recipe.get_primary_image_url()
            if img_url:
                return img_url
                
        # Try to parse the images field
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
    #Check if a recipe has at least one image
    #shows a placeholder image if there isn't one
    try:
        # Check for user-uploaded image first
        if hasattr(recipe, 'image') and recipe.image:
            return True
            
        # Then check other image sources
        return get_primary_image(recipe) is not None
    except Exception as e:
        print(f"Error in has_image: {e}")
        return False

@register.filter
def get_title(recipe):
    #Get the title of a recipe, whether it's a Recipe or DatasetRecipe, returns "Untitled Recipe" if not found
    if hasattr(recipe, 'title'):
        return recipe.title
    elif hasattr(recipe, 'name'):
        return recipe.name
    return "Untitled Recipe"

@register.filter
def format_duration(value):
    # Displays prep and cook times in human-readable format
    #  Turns PT10M to human-readable format 10 min
    
    if not value:
        return "Not specified"
        
    try:
        # Convert to string if it's not already
        value_str = str(value)
        
        # Handle ISO 8601 durations
        if value_str.startswith('PT'):
            # Remove PT prefix
            value_str = value_str[2:]
            
            # Handle minutes
            if 'M' in value_str:
                minutes = value_str.split('M')[0]
                return f"{minutes} min"
            # Handle hours
            elif 'H' in value_str:
                hours = value_str.split('H')[0]
                return f"{hours} hr"
        
        # If not ISO format but has numeric value, assume it is minutes
        if value_str.isdigit():
            return f"{value_str} min"
            
        return value_str
    except:
        return str(value)

@register.filter
def has_tried(recipe, user):
    #Check if a user has tried a recipe
    #Allows showing different options for tried vs. untried recipes
    
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
    
    #This filter lets you perform subtraction directly in your templates without needing to create a custom Python function or view variable.
