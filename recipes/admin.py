from django.contrib import admin
from django.contrib import messages
from .models import Recipe, SavedRecipe, ShoppingListItem, TrackedIngredient, ScrapedRecipe, RecipeIngredient, ShopRecipe, PurchasedRecipe

# Register models
models_to_register = [SavedRecipe, ShoppingListItem, TrackedIngredient, ScrapedRecipe, RecipeIngredient]

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
    
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "recipe":
            kwargs["queryset"] = Recipe.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
        
    def remove_from_shop(self, request, queryset):
        #Remove selected recipes from the shop
        recipe_count = queryset.count()
        for shop_recipe in queryset:
            recipe_title = shop_recipe.recipe.title
            shop_recipe.delete()
            self.message_user(request, f"Removed '{recipe_title}' from shop", messages.SUCCESS)
        
        self.message_user(request, f"{recipe_count} recipes removed from shop", messages.SUCCESS)
    remove_from_shop.short_description = "Remove selected recipes from shop"
    
    def feature_recipes(self, request, queryset):
        #Mark selected recipes as featured
        queryset.update(featured=True)
        recipe_count = queryset.count()
        self.message_user(request, f"{recipe_count} recipes marked as featured", messages.SUCCESS)
    feature_recipes.short_description = "Mark selected recipes as featured"
    
    def unfeature_recipes(self, request, queryset):
        #Remove featured status from selected recipes
        queryset.update(featured=False)
        recipe_count = queryset.count()
        self.message_user(request, f"Featured status removed from {recipe_count} recipes", messages.SUCCESS)
    unfeature_recipes.short_description = "Remove featured status from selected recipes"
    
    
@admin.register(PurchasedRecipe)
class PurchasedRecipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe', 'purchased_at', 'points_spent')
    list_filter = ('purchased_at',)
    search_fields = ('user__username', 'recipe__title')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'created_by_user', 'is_premium', 'points_cost', 'created_at')
    list_filter = ('status', 'created_by_user', 'is_premium')
    search_fields = ('title', 'author__username')
    list_editable = ('status', 'is_premium', 'points_cost')
    actions = ['approve_recipes', 'reject_recipes', 'mark_as_premium', 'remove_premium_status']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'ingredients', 'instructions', 'image')
        }),
        ('Recipe Metadata', {
            'fields': ('prep_time', 'cook_time', 'servings', 'calories', 'fat', 'carbs', 'protein')
        }),
        ('Review Settings', {
            'fields': ('status', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Premium Settings', {
            'fields': ('is_premium', 'points_cost'),
            'classes': ('collapse',)
        }),
        ('Other Settings', {
            'fields': ('author', 'created_by_user'),
            'classes': ('collapse',)
        }),
    )
    
    def approve_recipes(self, request, queryset):
        queryset.update(status='approved')
        self.message_user(request, f"{queryset.count()} recipes have been approved.")
    approve_recipes.short_description = "Approve selected recipes"
    
    def reject_recipes(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} recipes have been rejected.")
    reject_recipes.short_description = "Reject selected recipes"
    
    def mark_as_premium(self, request, queryset):
        #Mark selected recipes as premium and award points to the authors
        for recipe in queryset:
            recipe.is_premium = True
            recipe.status = 'premium'
            recipe.save()
            
            #Award points to the author if available
            if recipe.author:
                from users.models import UserPoints, PointsTransaction, UserNotification
                
                #Check if points have already been awarded for this recipe
                premium_award_exists = PointsTransaction.objects.filter(
                    user=recipe.author,
                    description__contains=f"Recipe selected as premium: {recipe.title}",
                    transaction_type='recipe_premium'
                ).exists()
                
                if not premium_award_exists:
                    premium_points = 100
                    user_points = UserPoints.get_or_create_user_points(recipe.author)
                    user_points.total_points += premium_points
                    user_points.save()
                    
                    PointsTransaction.objects.create(
                        user=recipe.author,
                        points=premium_points,
                        description=f"Recipe selected as premium: {recipe.title}",
                        transaction_type='recipe_premium',
                        recipe=recipe
                    )
                    
                    UserNotification.objects.create(
                        user=recipe.author,
                        title="Your Recipe is now Premium!",
                        message=f"Congratulations! Your recipe '{recipe.title}' has been selected as a premium recipe and is now available in the Recipe Shop. You've earned {premium_points} points!",
                        notification_type='achievement'
                    )
                    
                    user_points.check_and_update_level()
                    
                    self.message_user(
                        request, 
                        f"Awarded {premium_points} points to {recipe.author.username} for premium recipe '{recipe.title}'", 
                        messages.SUCCESS
                    )
        
        self.message_user(request, f"{queryset.count()} recipes have been marked as premium.")
    mark_as_premium.short_description = "Mark selected recipes as premium"
    
    def remove_premium_status(self, request, queryset):
        queryset.update(is_premium=False, status='approved')
        self.message_user(request, f"{queryset.count()} recipes have been removed from premium status.")
    remove_premium_status.short_description = "Remove premium status from selected recipes"