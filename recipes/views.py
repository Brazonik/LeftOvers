from django.shortcuts import render, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from . import models
from .models import Recipe, RecipeIngredient, SavedRecipe, ScrapedRecipe, TrackedIngredient
from django.http import JsonResponse
from .models import ShoppingListItem
import json
from datetime import datetime
from bs4 import BeautifulSoup
import requests





def home(request):
    recipes = models.Recipe.objects.all()
    context = {
        'recipes': recipes
    }
    return render(request, "recipes/home.html", context)



class RecipeListView(ListView):
    model = models.Recipe
    template_name = 'recipes/home.html'
    context_object_name = 'recipes'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['filter_options'] = [
            ('all', 'All Recipes'),
            ('breakfast', 'Breakfast'),
            ('lunch', 'Lunch'),
            ('dinner', 'Dinner'),
            ('dessert', 'Dessert'),
            ('vegetarian', 'Vegetarian'),
            ('spicy', 'Spicy'),
            ('quick', 'Quick & Easy'),
            ('healthy', 'Healthy')
        ]
        
        context['selected_like'] = self.request.GET.get('like')
        context['selected_dislike'] = self.request.GET.get('dislike')
        
        return context

    def get_queryset(self):
        recipes = Recipe.objects.all()
        filtered_recipes = []
        
        like_filter = self.request.GET.get('like')
        dislike_filter = self.request.GET.get('dislike')
        
        for recipe in recipes:
            categories = recipe.get_categories()
            
            if like_filter and like_filter != 'all':
                if like_filter not in categories:
                    continue
            if dislike_filter and dislike_filter != 'all':
                if dislike_filter in categories:
                    continue
            
            recipe.categories = categories
            filtered_recipes.append(recipe)
            
        return filtered_recipes

class RecipeDetailView(DetailView):
    model = models.Recipe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['is_saved'] = self.object.is_saved_by(self.request.user)
        return context


@login_required
def toggle_save_recipe(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    saved_recipe = models.SavedRecipe.objects.filter(user=request.user, recipe=recipe)
    
    if saved_recipe.exists():
        saved_recipe.delete()
    else:
        models.SavedRecipe.objects.create(user=request.user, recipe=recipe)
    
    return redirect('recipes-detail', pk=pk)

    

class RecipeCreateView(LoginRequiredMixin, CreateView):
    model = models.Recipe
    fields = ['title', 'description']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
class RecipeUpdateView(LoginRequiredMixin,UserPassesTestMixin, UpdateView):
    model = models.Recipe
    fields = ['title', 'description']

    def test_func(self):
        recipe = self.get_object()
        return self.request.user == recipe.author

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
class RecipeDeleteView(LoginRequiredMixin,UserPassesTestMixin, DeleteView):
    model = models.Recipe
    success_url = reverse_lazy('recipes-home')

    def test_func(self):
        recipe = self.get_object()
        return self.request.user == recipe.author

    
    

def about(request):
    return render(request, "recipes/about.html", {'title': 'About us page'})

@login_required
def profile(request):
    saved_recipes = SavedRecipe.objects.filter(user=request.user)
    saved_recipes_count = saved_recipes.count()  
    shopping_list = ShoppingListItem.objects.filter(user=request.user).order_by('expiration_date')
    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)  

    context = {
        'saved_recipes': saved_recipes,
        'saved_recipes_count': saved_recipes_count,
        'shopping_list': shopping_list,  
        'tracked_ingredients': tracked_ingredients,  
    }

    return render(request, 'users/profile.html', context)



@login_required
def add_item(request):
    """Add an ingredient to the shopping list."""
    if request.method == "POST":
        data = json.loads(request.body)
        ingredient_name = data.get("ingredient_name")
        quantity = data.get("quantity")
        expiration_date = data.get("expiration_date")

        expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date() if expiration_date else None

        item = ShoppingListItem.objects.create(
            user=request.user,
            ingredient_name=ingredient_name,
            quantity=quantity,
            expiration_date=expiration_date
        )

        return JsonResponse({
            "success": True, 
            "ingredient": item.ingredient_name, 
            "quantity": item.quantity, 
            "expiration_date": item.expiration_date.strftime("%Y-%m-%d") if item.expiration_date else "No Expiration"
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def remove_item(request, item_id):
    """Remove an ingredient from the shopping list."""
    if request.method == "POST":
        try:
            item = ShoppingListItem.objects.get(id=item_id, user=request.user)
            item.delete()
            return JsonResponse({"success": True})
        except ShoppingListItem.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "error": "Item not found"
            }, status=404)

    return JsonResponse({"error": "Invalid request"}, status=400)



@login_required
def mark_used(request, item_id):
    """Mark an ingredient as used, remove it, and award points."""
    if request.method == "POST":
        item = get_object_or_404(ShoppingListItem, id=item_id, user=request.user)

        if hasattr(request.user, 'profile'):  
            request.user.profile.points += item.points
            request.user.profile.save()

        item.delete()  
        return JsonResponse({"success": True, "new_points": getattr(request.user.profile, 'points', 0)})

    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def shopping_list(request):
    """Display the user's shopping list with expired items appearing first."""
    items = ShoppingListItem.objects.filter(user=request.user).order_by('expiration_date')

    expired_items = [item for item in items if item.is_expired()]
    non_expired_items = [item for item in items if not item.is_expired()]

    sorted_items = expired_items + non_expired_items  
    return render(request, 'recipes/shopping_list.html', {'items': sorted_items})

@login_required
def track_ingredient(request):
    if request.method == "POST":
        data = json.loads(request.body)
        ingredient_name = data.get("ingredient_name", "").lower().strip()
        
        ingredient_name = ingredient_name.replace(',', '')
        ingredient_name = ingredient_name.replace('fresh', '')
        ingredient_name = ingredient_name.replace('frozen', '')
        ingredient_name = ingredient_name.replace('raw', '')
        ingredient_name = ingredient_name.strip()
        
        existing = TrackedIngredient.objects.filter(
            user=request.user, 
            ingredient_name=ingredient_name
        ).exists()
        
        if existing:
            return JsonResponse({
                "success": False,
                "error": "This ingredient is already being tracked"
            })

        item = TrackedIngredient.objects.create(
            user=request.user,
            ingredient_name=ingredient_name,
            quantity=data.get("quantity"),
            expiration_date=datetime.strptime(data.get("expiration_date"), "%Y-%m-%d").date() if data.get("expiration_date") else None
        )

        return JsonResponse({
            "success": True,
            "ingredient": item.ingredient_name,
            "quantity": item.quantity,
            "expiration_date": item.expiration_date.strftime("%Y-%m-%d") if item.expiration_date else "No Expiration"
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def remove_tracked_ingredient(request, item_id):
    """
    Allows users to remove ingredients from their tracking list.
    """
    if request.method == "POST":
        try:
            item = TrackedIngredient.objects.get(id=item_id, user=request.user)
            item.delete()
            return JsonResponse({"success": True})
        except TrackedIngredient.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Item not found"
            }, status=404)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def match_ingredients_with_recipes(request):
    """
    Matches user's tracked ingredients with web-scraped recipes.
    """
    user_ingredients = TrackedIngredient.objects.filter(user=request.user)
    user_ingredient_names = set(item.ingredient_name.lower() for item in user_ingredients)

    matched_recipes = []

    for recipe in ScrapedRecipe.objects.all():
        recipe_ingredients = set(ingredient.name.lower() for ingredient in recipe.ingredients.all())

        if user_ingredient_names.intersection(recipe_ingredients):
            matched_recipes.append({
                "title": recipe.title,
                "url": recipe.url,
                "matching_ingredients": list(user_ingredient_names.intersection(recipe_ingredients)),
            })

    return JsonResponse({"recipes": matched_recipes})

@login_required
def scrape_recipes(request):
    """
    Scrapes recipes based on the user's tracked ingredients.
    """
    from recipes.scraper import scrape_recipes_for_user

    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)
    
    if not tracked_ingredients.exists():
        return render(request, 'recipes/ingredient_tracking.html', {
            'tracked_ingredients': tracked_ingredients,
            'recipes': [],
            'error_message': "You haven't tracked any ingredients yet."
        })

    try:
        scraped_recipes = scrape_recipes_for_user(request.user)

        return render(request, 'recipes/ingredient_tracking.html', {
            'tracked_ingredients': tracked_ingredients,
            'recipes': scraped_recipes,
            'success_message': f"Found {len(scraped_recipes)} recipes!"
        })
    except Exception as e:
        print(f"Error scraping recipes: {str(e)}")
        return render(request, 'recipes/ingredient_tracking.html', {
            'tracked_ingredients': tracked_ingredients,
            'recipes': [],
            'error_message': "Error finding recipes. Please try again."
        })


    
@login_required
def ingredient_tracking(request):
    """
    Displays the user's tracked ingredients and allows them to find recipes.
    """
    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user).order_by('expiration_date')

    user_ingredient_names = set(item.ingredient_name.lower() for item in tracked_ingredients)

    matched_recipes = []
    for recipe in ScrapedRecipe.objects.all():
        recipe_ingredients = set(ingredient.name.lower() for ingredient in recipe.ingredients.all())

        used_ingredients = list(user_ingredient_names.intersection(recipe_ingredients))
        missing_ingredients = list(recipe_ingredients - user_ingredient_names)

        if not missing_ingredients:

            total_tracked = len(user_ingredient_names)
            used_count = len(used_ingredients)
            usage_percentage = round((used_count / total_tracked) * 100, 1) if total_tracked > 0 else 0

            matched_recipes.append({
                "title": recipe.title,
                "url": recipe.url,
                "used_ingredients": used_ingredients,
                "missing_ingredients": missing_ingredients,
                "usage_percentage": usage_percentage,
                "nutrition": recipe.nutrition if hasattr(recipe, "nutrition") and recipe.nutrition else {},
                "readyInMinutes": getattr(recipe, "readyInMinutes", "N/A"),
                "servings": getattr(recipe, "servings", "N/A"),
            })

    matched_recipes.sort(key=lambda x: x['usage_percentage'], reverse=True)

    if not matched_recipes:
        return render(request, "recipes/ingredient_tracking.html", {
            "tracked_ingredients": tracked_ingredients,
            "recipes": [],
            "error_message": "No recipes found that fully match your ingredients. Try adding more!"
        })

    return render(request, "recipes/ingredient_tracking.html", {
        "tracked_ingredients": tracked_ingredients,
        "recipes": matched_recipes
    })
