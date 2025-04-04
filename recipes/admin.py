# Adds recipes to the shops and can remove them throguh admin


from django.contrib import admin
from django.contrib import messages
from .models import Recipe, SavedRecipe, ShoppingListItem, TrackedIngredient, ScrapedRecipe, RecipeIngredient, ShopRecipe, PurchasedRecipe

models_to_register = [Recipe, SavedRecipe, ShoppingListItem, TrackedIngredient, ScrapedRecipe, RecipeIngredient]

for model in models_to_register:
    if model not in admin.site._registry:  
        admin.site.register(model)



@admin.register(ShopRecipe)
class ShopRecipeAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'points_cost', 'featured', 'added_to_shop')
    list_filter = ('featured',)
    search_fields = ('recipe__title',)
    list_editable = ('points_cost', 'featured')
    actions = ['remove_from_shop', 'feature_recipes', 'unfeature_recipes']
    
    def remove_from_shop(self, request, queryset):
        """Remove selected recipes from the shop"""
        recipe_count = queryset.count()
        for shop_recipe in queryset:
            recipe_title = shop_recipe.recipe.title
            shop_recipe.delete()
            self.message_user(request, f"Removed '{recipe_title}' from shop", messages.SUCCESS)
        
        self.message_user(request, f"{recipe_count} recipes removed from shop", messages.SUCCESS)
    remove_from_shop.short_description = "Remove selected recipes from shop"
    
    
@admin.register(PurchasedRecipe)
class PurchasedRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'purchased_at', 'points_spent')
    list_filter = ('purchased_at',)
    search_fields = ('user__username', 'recipe__title')
