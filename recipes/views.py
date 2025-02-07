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
        
        # Basic ingredient name cleaning
        ingredient_name = ingredient_name.replace(',', '')
        ingredient_name = ingredient_name.replace('fresh', '')
        ingredient_name = ingredient_name.replace('frozen', '')
        ingredient_name = ingredient_name.replace('raw', '')
        ingredient_name = ingredient_name.strip()
        
        # Check if ingredient already exists
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
    """Web scraper to fetch recipes from an external site."""
    url = "https://www.bbcgoodfood.com/recipes"  

    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        recipes = []
        for item in soup.select(".standard-card-new__article-title"):  
            recipes.append(item.get_text(strip=True))

        return JsonResponse({"success": True, "recipes": recipes})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
@login_required
def ingredient_tracking(request):
    """
    Displays the user's tracked ingredients and allows them to find recipes.
    """
    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user).order_by('expiration_date')

    # Fetch scraped recipes that match the user's tracked ingredients
    user_ingredient_names = set(item.ingredient_name.lower() for item in tracked_ingredients)

    matched_recipes = []
    for recipe in ScrapedRecipe.objects.all():
        recipe_ingredients = set(ingredient.name.lower() for ingredient in recipe.ingredients.all())

        if user_ingredient_names.intersection(recipe_ingredients):
            matched_recipes.append({
                "title": recipe.title,
                "url": recipe.url,
                "matching_ingredients": list(user_ingredient_names.intersection(recipe_ingredients)),
            })

    return render(request, "recipes/ingredient_tracking.html", {
        "tracked_ingredients": tracked_ingredients,
        "matched_recipes": matched_recipes
    })



@login_required
def fetch_recipes_by_ingredients(request):
    API_KEY = "5fd7a331048d4bd49ff39d237b270e91"
    base_url = "https://api.spoonacular.com/recipes/findByIngredients"

    # Get all user's tracked ingredients
    user_ingredients = TrackedIngredient.objects.filter(user=request.user)
    
    if not user_ingredients.exists():
        return JsonResponse({'error': 'No ingredients tracked yet!'}, status=400)

    ingredient_list = [ingredient.ingredient_name.strip().lower() for ingredient in user_ingredients]
    ingredients_query = ',+'.join(ingredient_list)

    print(f"Searching with these ingredients: {ingredient_list}")  # Debug log

    params = {
        'apiKey': API_KEY,
        'ingredients': ingredients_query,
        'number': 2,  # Increased number of recipes
        'ranking': 1,
        'ignorePantry': True,
        'limitLicense': False
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"Found {len(data)} initial recipes")  # Debug log
        
        recipes = []

        for recipe in data:
            used_ingredients = [ing['name'].lower() for ing in recipe.get('usedIngredients', [])]
            missed_ingredients = [ing['name'].lower() for ing in recipe.get('missedIngredients', [])]
            
            used_count = len(used_ingredients)
            total_tracked = len(ingredient_list)
            usage_percentage = (used_count / total_tracked) * 100

            print(f"\nAnalyzing recipe: {recipe['title']}")  # Debug log
            print(f"Uses {used_count} out of {total_tracked} ingredients ({usage_percentage:.1f}%)")
            print(f"Used ingredients: {used_ingredients}")
            
            # Lowered the threshold to 25%
            if usage_percentage >= 25:  # Changed from 50% to 25%
                recipe_id = recipe['id']

                # Get detailed recipe info
                nutrition_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
                nutrition_params = {'apiKey': API_KEY, 'includeNutrition': 'true'}
                nutrition_response = requests.get(nutrition_url, params=nutrition_params)
                nutrition_data = nutrition_response.json()

                recipes.append({
                    'id': recipe['id'],
                    'title': recipe['title'],
                    'image': recipe.get('image', ''),
                    'source_url': nutrition_data.get('sourceUrl', ''),
                    'used_ingredients': used_ingredients,
                    'missing_ingredients': missed_ingredients,
                    'unused_tracked_ingredients': list(set(ingredient_list) - set(used_ingredients)),
                    'ingredients_usage_percentage': round(usage_percentage, 1),
                    'total_ingredients_used': used_count,
                    'total_tracked_ingredients': total_tracked,
                    'nutrition': {
                        nutrient['name']: {
                            'amount': nutrient['amount'],
                            'unit': nutrient['unit']
                        }
                        for nutrient in nutrition_data.get('nutrition', {}).get('nutrients', [])
                        if nutrient['name'] in ['Calories', 'Protein', 'Fat', 'Carbohydrates']
                    },
                    'instructions': nutrition_data.get('instructions', ''),
                    'readyInMinutes': nutrition_data.get('readyInMinutes', 0),
                    'servings': nutrition_data.get('servings', 0)
                })

        # Sort recipes by percentage of ingredients used
        recipes.sort(key=lambda x: x['ingredients_usage_percentage'], reverse=True)

        print(f"Final number of recipes after filtering: {len(recipes)}")  # Debug log

        return JsonResponse({
            'recipes': recipes,
            'debug_info': {
                'tracked_ingredients': ingredient_list,
                'total_ingredients': len(ingredient_list),
                'recipes_found': len(recipes),
                'search_query': ingredients_query  # Added to see what's being sent to API
            }
        })

    except Exception as e:
        print(f"Error in recipe fetching: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)