from django.shortcuts import render, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from recipes.utils import normalize_ingredient_name

from . import models
from .models import DatasetRecipe, Recipe, RecipeIngredient, SavedRecipe, ScrapedRecipe, TrackedIngredient
from django.http import JsonResponse
from .models import ShoppingListItem
import json
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from recipes.models import Recipe
from django.core.paginator import Paginator

from .models import DatasetRecipe
import sys
from django.shortcuts import render
from recipes.models import DatasetRecipe
from .utils import normalize_ingredient_name  # Add this at the top

def dataset_recipe_detail(request, pk):
    try:
        recipe = get_object_or_404(DatasetRecipe, pk=pk)
        return render(request, 'recipes/dataset_recipe_detail.html', {'recipe': recipe})
    except Exception as e:
        print(f"Error retrieving recipe {pk}: {str(e)}")  # Debug print
        raise



def home(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    
    dataset_recipes = DatasetRecipe.objects.all().order_by('name')
    user_recipes = Recipe.objects.all().order_by('title')
    
    if query:
        dataset_recipes = dataset_recipes.filter(name__icontains=query)
        user_recipes = user_recipes.filter(title__icontains=query)
    
    if category and category != 'all':
        dataset_recipes = dataset_recipes.filter(category__icontains=category)
        if user_recipes:
            user_recipes = [recipe for recipe in user_recipes if category in recipe.get_categories()]

    dataset_list = list(dataset_recipes)
    user_list = list(user_recipes)
    
    combined_recipes = []
    
    for recipe in dataset_list:
        combined_recipes.append(recipe)
    
    for recipe in user_list:
        recipe.get_prep_time_display = lambda: f"{recipe.prep_time} min" if recipe.prep_time else "Not specified"
        recipe.get_cook_time_display = lambda: "Not specified"  # Since user recipes might not have this
        recipe.get_clean_name = lambda: recipe.title
        recipe.category = "User Created"  # Or you could use recipe.get_categories()[0] if categories exist
        recipe.is_user_recipe = True  # Add this flag to distinguish in template
        combined_recipes.append(recipe)

    per_page = 24
    paginator = Paginator(combined_recipes, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "recipes": page_obj,
        "query": query,
        "total_results": len(combined_recipes),
        "filter_options": [
            ("all", "All Recipes"),
            ("breakfast", "Breakfast"),
            ("lunch", "Lunch"),
            ("dinner", "Dinner"),
            ("dessert", "Dessert"),
            ("vegetarian", "Vegetarian"),
            ("spicy", "Spicy"),
            ("quick", "Quick & Easy"),
            ("healthy", "Healthy"),
        ],
        "selected_category": category
    }
    
    return render(request, "recipes/home.html", context)

def search_recipes(request):
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    max_calories = request.GET.get("max_calories", None)

    dataset_recipes = DatasetRecipe.objects.all()
    user_recipes = Recipe.objects.all()

    if query:
        dataset_recipes = dataset_recipes.filter(name__icontains=query)
        user_recipes = user_recipes.filter(title__icontains=query)
    
    if category:
        dataset_recipes = dataset_recipes.filter(category__icontains=category)
        if user_recipes:
            user_recipes = [recipe for recipe in user_recipes if category in recipe.get_categories()]
    
    if max_calories:
        dataset_recipes = dataset_recipes.filter(calories__lte=max_calories)

    combined_recipes = []
    for recipe in dataset_recipes:
        combined_recipes.append({
            'title': recipe.get_clean_name(),
            'type': 'dataset',
            'pk': recipe.pk,
            'category': recipe.category,
        })
    
    for recipe in user_recipes:
        combined_recipes.append({
            'title': recipe.title,
            'type': 'user',
            'pk': recipe.pk,
            'author': recipe.author.username,
        })

    return render(request, "recipes/search.html", {
        "recipes": combined_recipes, 
        "query": query, 
        "category": category
    })



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
    fields = ['title', 'description', 'ingredients', 'instructions', 'prep_time', 'servings']

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
    created_recipes = Recipe.objects.filter(author=request.user)
    saved_recipes = SavedRecipe.objects.filter(user=request.user)
    recipes_count = created_recipes.count()
    saved_recipes_count = saved_recipes.count() 
    shopping_list = ShoppingListItem.objects.filter(user=request.user).order_by('expiration_date')
    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)  

    context = {
        'created_recipes': created_recipes,
        'recipes_count': recipes_count,
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
def track_ingredient(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received data:", data)  # Debug print
            
            ingredient_name = data.get("ingredient_name")
            quantity = data.get("quantity")
            expiration_date = data.get("expiration_date")

            if not ingredient_name:
                return JsonResponse({"success": False, "error": "Ingredient name is required"})

            if expiration_date:
                expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()

            ingredient = TrackedIngredient.objects.create(
                user=request.user,
                ingredient_name=ingredient_name,
                quantity=quantity,
                expiration_date=expiration_date
            )

            return JsonResponse({
                "success": True,
                "ingredient": {
                    "name": ingredient.ingredient_name,
                    "quantity": ingredient.quantity,
                    "expiration_date": ingredient.expiration_date.strftime("%Y-%m-%d") if ingredient.expiration_date else None
                }
            })
        except Exception as e:
            print(f"Error adding ingredient: {str(e)}")  # Debug print
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})

@login_required
def ingredient_tracking(request):
    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user).order_by('expiration_date')
    print(f"Number of tracked ingredients: {tracked_ingredients.count()}")
    
    user_ingredients = {normalize_ingredient_name(item.ingredient_name): item 
                       for item in tracked_ingredients}
    print(f"Normalized user ingredients: {list(user_ingredients.keys())}")
    
    matched_recipes = []
    checked_recipes = 0
    
    for recipe in DatasetRecipe.objects.all():
        checked_recipes += 1
        try:
            recipe_ingredients = recipe.get_ingredients()
            if recipe_ingredients and len(recipe_ingredients) > 1:  # Only consider recipes with more than 1 ingredient
                recipe_ing_set = set(recipe_ingredients)
                user_ing_set = set(user_ingredients.keys())
                
                matching_ings = recipe_ing_set.intersection(user_ing_set)
                if matching_ings and len(matching_ings) >= 2:  # Only include if at least 2 ingredients match
                    missing_ings = recipe_ing_set - user_ing_set
                    match_percentage = (len(matching_ings) / len(recipe_ingredients)) * 100
                    
                    matched_recipes.append({
                        'is_dataset': True,
                        'recipe': recipe,
                        'name': recipe.name,
                        'prep_time': recipe.prep_time,
                        'cook_time': recipe.cook_time,
                        'matching_ingredients': list(matching_ings),
                        'missing_ingredients': list(missing_ings),
                        'match_percentage': round(match_percentage, 1),
                        'is_perfect_match': len(missing_ings) == 0,
                        'total_ingredients': len(recipe_ingredients),
                        'extra_ingredients_needed': len(missing_ings)
                    })
                    
        except Exception as e:
            print(f"Error with recipe {recipe.name}: {str(e)}")
            continue

    for recipe in Recipe.objects.all():
        try:
            recipe_ingredients = [normalize_ingredient_name(ing) 
                                for ing in json.loads(recipe.ingredients)]
            
            if recipe_ingredients and len(recipe_ingredients) > 1:
                recipe_ing_set = set(recipe_ingredients)
                user_ing_set = set(user_ingredients.keys())
                
                matching_ings = recipe_ing_set.intersection(user_ing_set)
                if matching_ings and len(matching_ings) >= 2:
                    missing_ings = recipe_ing_set - user_ing_set
                    match_percentage = (len(matching_ings) / len(recipe_ingredients)) * 100
                    
                    matched_recipes.append({
                        'is_dataset': False,
                        'recipe': recipe,
                        'name': recipe.title,
                        'prep_time': f"{recipe.prep_time} min" if recipe.prep_time else "Not specified",
                        'matching_ingredients': list(matching_ings),
                        'missing_ingredients': list(missing_ings),
                        'match_percentage': round(match_percentage, 1),
                        'is_perfect_match': len(missing_ings) == 0,
                        'total_ingredients': len(recipe_ingredients),
                        'extra_ingredients_needed': len(missing_ings)
                    })
                    
        except Exception as e:
            print(f"Error with user recipe {recipe.title}: {str(e)}")
            continue

    matched_recipes.sort(key=lambda x: (
        -x['is_perfect_match'],           # Perfect matches first (-True = -1, -False = 0)
        -x['match_percentage'],           # Higher percentage first
        -x['total_ingredients'],          # More ingredients first
        x['extra_ingredients_needed']     # Fewer missing ingredients first
    ))

    paginator = Paginator(matched_recipes, 20)  # Show 20 recipes per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    print(f"\nFinal stats:")
    print(f"Checked {checked_recipes} recipes")
    print(f"Found {len(matched_recipes)} matches")
    print(f"Perfect matches: {sum(1 for r in matched_recipes if r['is_perfect_match'])}")

    context = {
        'tracked_ingredients': tracked_ingredients,
        'matched_recipes': page_obj,  # Use paginated recipes
        'total_matches': len(matched_recipes),
        'perfect_matches': sum(1 for r in matched_recipes if r['is_perfect_match'])
    }

    return render(request, 'recipes/ingredient_tracking.html', context)

def search_recipes(request):
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    max_calories = request.GET.get("max_calories", None)

    recipes = DatasetRecipe.objects.all()

    if query:
        recipes = recipes.filter(name__icontains=query)
    if category:
        recipes = recipes.filter(category__icontains=category)
    if max_calories:
        recipes = recipes.filter(calories__lte=max_calories)

    return render(request, "recipes/search.html", {"recipes": recipes, "query": query, "category": category})
