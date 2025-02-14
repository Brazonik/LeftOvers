import json
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date

class Recipe(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    source = models.CharField(max_length=50, choices=[('dataset', 'Dataset'), ('bbc', 'BBC Food')], default='dataset')
    url = models.URLField(null=True, blank=True)
    ingredients = models.TextField(null=True, blank=True, default='[]')
    instructions = models.TextField(null=True, blank=True, default='')  # Changed this line
    prep_time = models.IntegerField(null=True, blank=True)
    servings = models.IntegerField(null=True, blank=True)
    nutrition_info = models.JSONField(null=True, blank=True)


    def get_absolute_url(self):
        return reverse("recipes-detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.title
    
    def is_saved_by(self, user):
        return self.saved_by.filter(user=user).exists()
    
    def get_ingredient_list(self):
        return json.loads(self.ingredients)

    def get_categories(self):
        """Automatically determine categories based on recipe content"""
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
        """Check if the ingredient has expired"""
        return self.expiration_date and self.expiration_date < date.today()

    def __str__(self):
        return f"{self.quantity} of {self.ingredient_name} (Exp: {self.expiration_date})"   

class TrackedIngredient(models.Model):
    """
    Tracks ingredients that users currently have in their kitchen.
    Used for matching with web-scraped recipes.
    """
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
    """
    Stores recipes that were scraped from Spoonacular API.
    """
    title = models.CharField(max_length=255)
    url = models.URLField()
    image = models.URLField(blank=True, null=True)  # Store recipe image
    instructions = models.TextField()
    ready_in_minutes = models.IntegerField(default=0)
    servings = models.IntegerField(default=1)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    """
    Represents an ingredient that may or may not be linked to a recipe.
    Users can select standalone ingredients to generate a recipe.
    """
    recipe = models.ForeignKey(ScrapedRecipe, on_delete=models.CASCADE, related_name='ingredients', null=True, blank=True)
    name = models.CharField(max_length=255)
    amount = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.amount} {self.unit} {self.name}" if self.amount else self.name

class DatasetRecipe(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    cook_time = models.CharField(max_length=50, default='Unknown')
    prep_time = models.CharField(max_length=50, default='Unknown')
    category = models.CharField(max_length=100, default='Uncategorized', db_index=True)
    servings = models.IntegerField(default=4)
    
    # Nutrition info
    calories = models.FloatField(default=0, db_index=True)
    protein = models.FloatField(default=0)
    carbs = models.FloatField(default=0)
    fat = models.FloatField(default=0)
    
    # Recipe details
    instructions = models.TextField(default='')
    ingredients_list = models.TextField(default='[]')  # New field

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
            import json
            return json.loads(self.ingredients_list)
        except:
            return []

    def format_time(self, time_str):
        if not time_str or time_str == 'Unknown':
            return 'Not specified'
        try:
            # Remove "PT" prefix and "M" suffix
            time_str = time_str.replace('PT', '').replace('M', '')
            minutes = int(time_str)
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if hours > 0:
                return f"{hours}h {remaining_minutes}m" if remaining_minutes else f"{hours}h"
            return f"{minutes}m"
        except:
            return time_str

   

class DatasetIngredient(models.Model):
    recipe = models.ForeignKey(DatasetRecipe, related_name='dataset_ingredients', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} for {self.recipe.name}"

    class Meta:
        indexes = [
            models.Index(fields=['name'])
        ]