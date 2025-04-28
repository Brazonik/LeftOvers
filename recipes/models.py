import json
from django import forms
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date
import re
from django.db.models.signals import post_save
from django.dispatch import receiver

class Recipe(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    source = models.CharField(max_length=50, choices=[('dataset', 'Dataset'), ('bbc', 'BBC Food')], default='dataset')
    url = models.URLField(null=True, blank=True)
    ingredients = models.TextField(default='[]')
    instructions = models.TextField(null=True, blank=True, default='')
    prep_time = models.CharField(max_length=20, null=True, blank=True)
    cook_time = models.CharField(max_length=20, null=True, blank=True)
    servings = models.IntegerField(null=True, blank=True)
    nutrition_info = models.JSONField(null=True, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    
    ingredients_parts = models.TextField(default='[]')
    ingredients_quantities = models.TextField(default='[]')
    images = models.TextField(default='[]')  
    image = models.ImageField(upload_to='recipe_images/', null=True, blank=True)
    created_by_user = models.BooleanField(default=False) 
    is_premium = models.BooleanField(default=False)  
    points_cost = models.PositiveIntegerField(default=10) 
    calories = models.IntegerField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True, help_text="Fat in grams")
    carbs = models.FloatField(null=True, blank=True, help_text="Carbohydrates in grams")
    protein = models.FloatField(null=True, blank=True, help_text="Protein in grams")

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Approved'),
        ('premium', 'Premium'),
        ('rejected', 'Rejected')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    admin_notes = models.TextField(blank=True, null=True, help_text="Private notes for admins reviewing this recipe")

    def get_absolute_url(self):
        return reverse("recipes-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.title
    
    def is_saved_by(self, user):
        return self.saved_by.filter(user=user).exists()
    
    def get_ingredient_list(self):
        return json.loads(self.ingredients)
        
    def get_ingredients(self):
        try:
            if not self.ingredients:
                return []
                
            if isinstance(self.ingredients, list):
                return self.ingredients
                
            if self.ingredients_parts and self.ingredients_parts != '[]':
                if isinstance(self.ingredients_parts, str) and self.ingredients_parts.startswith('['):
                    try:
                        import json
                        return json.loads(self.ingredients_parts.replace("'", '"'))
                    except:
                        pass
                
            if isinstance(self.ingredients, str):
                if self.ingredients.startswith('['):
                    try:
                        import json
                        ingredients_list = json.loads(self.ingredients.replace("'", '"'))
                        return ingredients_list
                    except:
                        pass
                        
                if '•' in self.ingredients:
                    clean_text = self.ingredients.strip('[]')
                    parts = clean_text.split(',')
                    clean_parts = []
                    for part in parts:
                        clean_part = re.sub(r'[^a-zA-Z0-9 ,]', '', part).strip()
                        if clean_part:
                            clean_parts.append(clean_part)
                    return clean_parts
                
                if ',' in self.ingredients:
                    return [item.strip() for item in self.ingredients.split(',') if item.strip()]
                    
            try:
                return self.get_ingredient_list()
            except:
                pass
            
            return [self.ingredients] if self.ingredients else []
        except Exception as e:
            print(f"Error parsing ingredients for {self.title}: {str(e)}")
            return []
        
    
    
    def has_image(self):
        try:
            if self.image:
                return True
                
            if hasattr(self, 'images') and self.images:
                if self.images.startswith('['):
                    import json
                    images = json.loads(self.images)
                    return len(images) > 0
                return bool(self.images)
            return False
        except Exception as e:
            print(f"Error checking image for {self.title}: {str(e)}")
            return False
    
    def get_primary_image_url(self):
        try:
            if self.images and self.images != '[]':
                if isinstance(self.images, list) and len(self.images) > 0:
                    return self.images[0]
                
                if isinstance(self.images, str) and self.images.startswith('['):
                    import json
                    images_list = json.loads(self.images.replace("'", '"'))
                    if images_list and len(images_list) > 0:
                        return images_list[0]
            return None
        except Exception as e:
            print(f"Error getting image for {self.title}: {str(e)}")
            return None


    def get_categories(self):
        categories = []
        text_to_check = f"{self.title.lower()} {self.description.lower()}"
        
        category_keywords = {
            'breakfast': {
                'dishes': ['pancake', 'waffle', 'omelet', 'french toast', 'porridge', 'oatmeal', 'cereal', 
                          'granola', 'breakfast burrito', 'eggs benedict', 'hash brown', 'bagel', 'toast',
                          'croissant', 'muffin', 'smoothie bowl', 'crepe', 'breakfast sandwich'],
                'ingredients': ['egg', 'bacon', 'sausage', 'maple syrup', 'yogurt'],
                'context': ['breakfast', 'brunch', 'morning']
            },
            'lunch': {
                'dishes': ['sandwich', 'wrap', 'salad', 'soup', 'quiche', 'panini', 'burger', 'taco', 
                          'quesadilla', 'bowl', 'sushi roll', 'pita', 'sub', 'blt', 'club sandwich',
                          'lunch box', 'bento', 'pasta salad', 'chicken salad', 'tuna salad'],
                'context': ['lunch', 'midday', 'light meal', 'packed lunch']
            },
            'dinner': {
                'dishes': ['steak', 'roast', 'casserole', 'lasagna', 'curry', 'stir fry', 'pasta', 
                          'pizza', 'rice', 'chicken', 'fish', 'pork', 'beef', 'salmon', 'pot roast',
                          'meatloaf', 'enchilada', 'risotto', 'paella', 'ramen', 'pho', 'stew',
                          'chili', 'mashed potato', 'grilled', 'baked', 'braised'],
                'context': ['dinner', 'supper', 'main course', 'main dish', 'entree']
            },
            'dessert': {
                'dishes': ['cake', 'cookie', 'brownie', 'pie', 'ice cream', 'pudding', 'mousse', 
                          'cheesecake', 'cupcake', 'pastry', 'tart', 'cobbler', 'tiramisu',
                          'chocolate', 'candy', 'fudge', 'donut', 'eclair', 'creme brulee',
                          'sundae', 'parfait', 'truffle'],
                'ingredients': ['chocolate', 'caramel', 'vanilla', 'frosting', 'icing', 'sugar',
                              'sweet', 'cream', 'dessert', 'candy', 'sprinkles', 'ganache'],
                'context': ['dessert', 'sweet', 'treat', 'baked goods', 'confection']
            },
            'vegetarian': {
                'positive': ['vegetarian', 'vegan', 'plant-based', 'meatless', 'veggie'],
                'ingredients': ['tofu', 'tempeh', 'seitan', 'lentil', 'bean', 'chickpea', 
                              'mushroom', 'eggplant', 'cauliflower', 'quinoa', 'veggie'],
                'exclude': ['chicken', 'beef', 'pork', 'fish', 'shrimp', 'meat', 'turkey',
                           'bacon', 'sausage', 'seafood']
            },
            'spicy': {
                'ingredients': ['chili', 'jalapeno', 'sriracha', 'hot sauce', 'cayenne',
                              'spicy', 'hot', 'wasabi', 'pepper', 'buffalo', 'curry',
                              'chipotle', 'habanero', 'ghost pepper', 'tabasco'],
                'context': ['spicy', 'hot', 'fiery', 'burning', 'flaming', 'zesty', 'kick']
            },
            'quick': {
                'time_indicators': ['quick', 'easy', 'simple', 'fast', '15 minute', '20 minute',
                                  '30 minute', 'instant', 'no-cook', '5 ingredient',
                                  'one pot', 'one pan', 'sheet pan', 'minimal'],
                'context': ['weeknight', 'beginner', 'basic', 'lazy', 'busy', 'quick']
            },
            'healthy': {
                'indicators': ['healthy', 'nutritious', 'light', 'lean', 'low-fat', 'low-carb',
                             'keto', 'paleo', 'whole30', 'Mediterranean', 'balanced',
                             'protein', 'superfood', 'clean eating', 'wholesome'],
                'ingredients': ['quinoa', 'kale', 'spinach', 'avocado', 'salmon', 'greek yogurt',
                              'nuts', 'seeds', 'olive oil', 'green', 'lean', 'grilled',
                              'steamed', 'baked', 'roasted'],
                'exclude': ['fried', 'greasy', 'buttery', 'creamy', 'rich', 'decadent']
            }
        }

        for category, rules in category_keywords.items():
            if category in ['breakfast', 'lunch', 'dinner', 'dessert']:
                if any(dish in text_to_check for dish in rules['dishes']):
                    categories.append(category)
                    continue
                if any(context in text_to_check for context in rules['context']):
                    categories.append(category)
                    continue
                if category == 'breakfast' and any(ing in text_to_check for ing in rules['ingredients']):
                    if 'dessert' not in categories:
                        categories.append(category)
                    
            elif category == 'vegetarian':
                if any(term in text_to_check for term in rules['positive']):
                    categories.append(category)
                elif any(ing in text_to_check for ing in rules['ingredients']):
                    if not any(meat in text_to_check for meat in rules['exclude']):
                        categories.append(category)
                    
            elif category == 'spicy':
                if any(spice in text_to_check for spice in rules['ingredients']) or \
                   any(context in text_to_check for context in rules['context']):
                    categories.append(category)
                
            elif category == 'quick':
                if any(indicator in text_to_check for indicator in rules['time_indicators']) or \
                   any(context in text_to_check for context in rules['context']):
                    categories.append(category)
                
            elif category == 'healthy':
                if any(indicator in text_to_check for indicator in rules['indicators']):
                    categories.append(category)
                elif any(ing in text_to_check for ing in rules['ingredients']):
                    if not any(unhealthy in text_to_check for unhealthy in rules['exclude']):
                        categories.append(category)

        return categories
    
    
    
class SavedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_recipes')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'recipe']
        
    def __str__(self):
        return f"{self.user.username} saved {self.recipe.title}"
    
class ShoppingListItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  
    ingredient_name = models.CharField(max_length=255)
    quantity = models.CharField(max_length=50)  
    expiration_date = models.DateField(null=True, blank=True)  
    points = models.IntegerField(default=0)  
    added_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.expiration_date and self.expiration_date < date.today()

    def __str__(self):
        return f"{self.quantity} of {self.ingredient_name} (Exp: {self.expiration_date})"   

class TrackedIngredient(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient_name = models.CharField(max_length=255)
    quantity = models.CharField(max_length=50, blank=True, null=True)
    expiration_date = models.DateField(null=True, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return self.expiration_date and self.expiration_date < date.today()

    def __str__(self):
        return f"{self.ingredient_name} (Exp: {self.expiration_date})"


class ScrapedRecipe(models.Model):
    
    title = models.CharField(max_length=255)
    url = models.URLField()
    image = models.URLField(blank=True, null=True)  
    instructions = models.TextField()
    ready_in_minutes = models.IntegerField(default=0)
    servings = models.IntegerField(default=1)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    def clean_instructions(self):
        #Clean up encoding issues in instruction text
        if not self.instructions:
            return ""
        
        text = self.instructions
        text = text.replace("Â", "")  
        text = text.replace("â\x80\x93", "-")  
        text = text.replace("â\x80\x99", "'")  
        
        
        return text


class RecipeIngredient(models.Model):
    
    recipe = models.ForeignKey(ScrapedRecipe, on_delete=models.CASCADE, related_name='ingredients', null=True, blank=True)
    name = models.CharField(max_length=255)
    amount = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        clean_name = self.clean_text()
        return f"{self.amount} {self.unit} {clean_name}" if self.amount else clean_name
    
    def clean_text(self):
        #Clean up encoding issues in ingredient text
        if not self.name:
            return ""
        
        text = self.name
        text = text.replace("Â", "")  
        text = text.replace("â\x80\x93", "-")  
        text = text.replace("â\x80\x99", "'")  
        
        
        return text

"""class DatasetRecipe(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    cook_time = models.CharField(max_length=50, default='Unknown')
    prep_time = models.CharField(max_length=50, default='Unknown')
    category = models.CharField(max_length=100, default='Uncategorized', db_index=True)
    servings = models.IntegerField(default=4)
    ingredients_parts = models.TextField(default='[]')
    ingredients_quantities = models.TextField(default='[]')
    calories = models.FloatField(default=0, db_index=True)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)
    instructions = models.TextField(default='')
    ingredients_list = models.TextField(default='[]')
    
    calories = models.FloatField(default=0, db_index=True)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)
    
    instructions = models.TextField(default='')
    ingredients_list = models.TextField(default='[]')

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["calories"]),
        ]
        
    def __str__(self):
        return self.name"""
    
class DatasetRecipe(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    cook_time = models.CharField(max_length=50, default='Unknown')
    prep_time = models.CharField(max_length=50, default='Unknown')
    category = models.CharField(max_length=100, default='Uncategorized', db_index=True)
    servings = models.IntegerField(default=4)
    ingredients_parts = models.TextField(default='[]')
    ingredients_quantities = models.TextField(default='[]')
    calories = models.FloatField(default=0, db_index=True)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)
    instructions = models.TextField(default='')
    ingredients_list = models.TextField(default='[]')
    images = models.TextField(default='[]')  
    description = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["calories"]),
        ]
        
    def __str__(self):
        return self.name
    
    def get_ingredients(self):
        try:
            if not self.ingredients_parts:
                return []
                
            if isinstance(self.ingredients_parts, list):
                return [ing.lower() for ing in self.ingredients_parts if ing]
                
            if self.ingredients_parts.startswith('['):
                try:
                    import json
                    ingredients = json.loads(self.ingredients_parts)
                    return [ing.lower() for ing in ingredients if ing]
                except:
                    pass
            
            ingredients = []
            text = self.ingredients_parts.strip('[]')
            for ingredient in text.split(','):
                cleaned = ingredient.replace('"', '').strip("'").strip()
                if cleaned:
                    ingredients.append(cleaned.lower())
            return ingredients
        except Exception as e:
            print(f"Error parsing ingredients for {self.name}: {str(e)}")
            return []

    def get_full_ingredients(self):
        try:
            if isinstance(self.ingredients_quantities, list):
                quantities = self.ingredients_quantities
            elif self.ingredients_quantities and self.ingredients_quantities.startswith('['):
                try:
                    import ast
                    quantities = ast.literal_eval(self.ingredients_quantities)
                except:
                    quantities = []
            elif self.ingredients_quantities and self.ingredients_quantities.startswith('c('):
                text = self.ingredients_quantities[2:-1]
                quantities = [q.strip('"').strip() for q in text.split(',') if q.strip()]
            else:
                quantities = []

            if isinstance(self.ingredients_parts, list):
                parts = self.ingredients_parts
            elif self.ingredients_parts and self.ingredients_parts.startswith('['):
                try:
                    import ast
                    parts = ast.literal_eval(self.ingredients_parts)
                except:
                    parts = []
            elif self.ingredients_parts and self.ingredients_parts.startswith('c('):
                text = self.ingredients_parts[2:-1]
                parts = [p.strip('"').strip() for p in text.split(',') if p.strip()]
            else:
                parts = []

            min_length = min(len(quantities), len(parts))
            quantities = quantities[:min_length]
            parts = parts[:min_length]
            
            return [f"{q} {p}" for q, p in zip(quantities, parts)]
            
        except Exception as e:
            print(f"Error getting full ingredients for {self.name}: {str(e)}")
            return []

    def get_clean_name(self):
        import html
        return html.unescape(self.name)

    def get_prep_time_display(self):
        return self.format_time(self.prep_time)

    def get_cook_time_display(self):
        return self.format_time(self.cook_time)

    def format_time(self, time_str):
        if not time_str or time_str == 'Unknown':
            return 'Not specified'
        try:
            time_str = time_str.replace('PT', '')
            if 'M' in time_str:
                minutes = int(time_str.replace('M', ''))
                return f"{minutes} min"
            elif 'H' in time_str:
                hours = int(time_str.replace('H', ''))
                return f"{hours} hr"
            elif 'S' in time_str:
                return "< 1 min"
            return time_str
        except:
            return 'Not specified'
        
    def has_image(self):
        try:
            if self.images and self.images != '[]':
                if isinstance(self.images, list) and len(self.images) > 0:
                    return True
                
                if isinstance(self.images, str) and self.images.startswith('['):
                    import json
                    images_list = json.loads(self.images.replace("'", '"'))
                    if images_list and len(images_list) > 0:
                        return True
            return False
        except Exception as e:
            print(f"Error checking image for {self.name}: {str(e)}")
            return False
   

class DatasetIngredient(models.Model):
    recipe = models.ForeignKey(DatasetRecipe, related_name='dataset_ingredients', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} for {self.recipe.name}"

    class Meta:
        indexes = [
            models.Index(fields=['name'])
        ]


class SavedDatasetRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(DatasetRecipe, on_delete=models.CASCADE)
    saved = models.BooleanField(default=True)
    saved_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'recipe')
        
    def __str__(self):
        return f"{self.user.username} - {self.recipe.name}"


class TriedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True)
    dataset_recipe = models.ForeignKey(DatasetRecipe, on_delete=models.SET_NULL, null=True, blank=True)
    scraped_recipe = models.ForeignKey(ScrapedRecipe, on_delete=models.SET_NULL, null=True, blank=True)  
    tried_at = models.DateTimeField(auto_now_add=True)
    points_earned = models.IntegerField(default=10)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                condition=models.Q(recipe__isnull=False),
                name='unique_user_recipe'
            ),
            models.UniqueConstraint(
                fields=['user', 'dataset_recipe'],
                condition=models.Q(dataset_recipe__isnull=False),
                name='unique_user_dataset_recipe'
            ),
            models.UniqueConstraint(
                fields=['user', 'scraped_recipe'],
                condition=models.Q(scraped_recipe__isnull=False),
                name='unique_user_scraped_recipe'
            ),
        ]
    
    def __str__(self):
        if self.recipe:
            recipe_name = self.recipe.title
        elif self.dataset_recipe:
            recipe_name = self.dataset_recipe.name
        elif self.scraped_recipe:
            recipe_name = self.scraped_recipe.title
        else:
            recipe_name = "Unknown Recipe"
            
        return f"{self.user.username} tried {recipe_name}"
    
class ShopRecipe(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='shop_listing')
    points_cost = models.IntegerField(default=50)
    featured = models.BooleanField(default=False)
    added_to_shop = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.recipe.title} ({self.points_cost} points)"

class PurchasedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchased_recipes')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)
    points_spent = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['user', 'recipe']
        
    def __str__(self):
        return f"{self.user.username} purchased {self.recipe.title}"
    



