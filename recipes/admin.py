from django.contrib import admin
from .models import Recipe, SavedRecipe, ShoppingListItem, TrackedIngredient, ScrapedRecipe, RecipeIngredient


models_to_register = [Recipe, SavedRecipe, ShoppingListItem, TrackedIngredient, ScrapedRecipe, RecipeIngredient]

for model in models_to_register:
    if model not in admin.site._registry:  
        admin.site.register(model)
