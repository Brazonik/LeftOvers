import html
from django import forms
from django.contrib import messages
from django.shortcuts import render, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy, reverse  
from django.core.cache import cache
import hashlib
import json

from recipes.forms import RecipeForm
from recipes.templatetags.recipe_filters import format_duration, get_difficulty
from recipes.utils import normalize_ingredient_name
from users.models import PointsTransaction, UnlockedRecipeReward, UserPoints

from . import models
from .models import DatasetRecipe, Recipe, RecipeIngredient, SavedRecipe, ScrapedRecipe, TrackedIngredient, TriedRecipe
from django.http import JsonResponse
from .models import ShoppingListItem
import json
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import requests
from recipes.models import Recipe
from django.core.paginator import Paginator
from recipes.forms import RecipeForm

from .models import DatasetRecipe
import sys
from django.shortcuts import render
from recipes.models import DatasetRecipe
from .utils import normalize_ingredient_name  
from django.db import transaction


@login_required
def dataset_recipe_detail(request, pk):
    #vew for displaying a dataset recipe in detail
    recipe = get_object_or_404(DatasetRecipe, pk=pk)
    
    is_saved = SavedDatasetRecipe.objects.filter(
        user=request.user, 
        recipe=recipe,
        saved=True
    ).exists() if request.user.is_authenticated else False
    
    context = {
        'recipe': recipe,
        'is_saved': is_saved,  
        'title': recipe.name
        
    }
    
    
    return render(request, 'recipes/dataset_recipe_detail.html', context)



def home(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    difficulty = request.GET.get("difficulty", "")  
    show_all = request.GET.get("show_all", "false") == "true"
    page_number = request.GET.get('page', 1)
    
    primary_recipes = []
    
    #process user recipes with images first 
    user_recipes_query = Recipe.objects.filter(
        author__isnull=False,
        status__in=['approved', 'premium'],  
        is_premium=False  
    )
    
    if query:
        user_recipes_query = user_recipes_query.filter(title__icontains=query)
    
    user_recipes_query = user_recipes_query.order_by('-created_at')[:100]
    
    for recipe in user_recipes_query:
        #only check has_image if not show_all
        if show_all or recipe.has_image():
            if category and category != 'all':
                if category not in recipe.get_categories():
                    continue
            
            recipe.recipe_type = "user"
            recipe.get_prep_time_display = lambda r=recipe: f"{r.prep_time} min" if r.prep_time else "Not specified"
            recipe.get_cook_time_display = lambda r=recipe: format_duration(r.cook_time) 
            recipe.get_clean_name = lambda r=recipe: r.name
            primary_recipes.append(recipe)
    
    #process BBC recipes with images(not working)
    bbc_recipes_query = Recipe.objects.filter(source='bbc')
    
    if query:
        bbc_recipes_query = bbc_recipes_query.filter(title__icontains=query)
    
    bbc_recipes_query = bbc_recipes_query.order_by('-created_at')[:100]
    
    for recipe in bbc_recipes_query:
        if show_all or recipe.has_image():
            if category and category != 'all':
                if category not in recipe.get_categories():
                    continue
            
            recipe.recipe_type = "bbc"
            recipe.get_prep_time_display = lambda r=recipe: f"{r.prep_time} min" if r.prep_time else "Not specified"
            recipe.get_cook_time_display = lambda: "Not specified"
            recipe.get_clean_name = lambda r=recipe: r.title
            primary_recipes.append(recipe)
    
    #process dataset recipes 
    dataset_query = DatasetRecipe.objects.all()
    
    if query:
        dataset_query = dataset_query.filter(name__icontains=query)
    
    if category and category != 'all':
        dataset_query = dataset_query.filter(category__icontains=category)
    
    dataset_recipes = dataset_query.order_by('name')[:60000]
    
    dataset_count = 0
    max_dataset_recipes = 100000  
    
    for recipe in dataset_recipes:
        if dataset_count >= max_dataset_recipes:
            break
            
        #check for image presence if not showing all
        if show_all or (hasattr(recipe, 'has_image') and callable(getattr(recipe, 'has_image')) and recipe.has_image()):
            recipe.recipe_type = "dataset"
            recipe.name = html.unescape(recipe.name)
            recipe.get_clean_name = lambda r=recipe: r.name
            primary_recipes.append(recipe)
            dataset_count += 1
    
    # ensure consistent properties on all recipes
    for recipe in primary_recipes:
        if not hasattr(recipe, 'calories'):
            recipe.calories = None
        if not hasattr(recipe, 'fat'):
            recipe.fat = None
        if not hasattr(recipe, 'carbs'):
            recipe.carbs = None
        if not hasattr(recipe, 'protein'):
            recipe.protein = None
            
        if not hasattr(recipe, 'recipe_type'):
            recipe.recipe_type = "user" if hasattr(recipe, 'author') else "dataset"
    
    if difficulty:
        filtered_recipes = []
        for recipe in primary_recipes:
            recipe_difficulty = get_difficulty(recipe)
            if recipe_difficulty['level'].lower() == difficulty.lower():
                filtered_recipes.append(recipe)
        primary_recipes = filtered_recipes
    
    #pagination
    per_page = 24
    paginator = Paginator(primary_recipes, per_page)
    page_obj = paginator.get_page(page_number)

    context = {
        "recipes": page_obj,
        "query": query,
        "total_results": len(primary_recipes),
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
        "selected_category": category,
        "selected_difficulty": difficulty,  
        "show_all": show_all,
        "has_image_recipes": any(recipe.has_image() if hasattr(recipe, 'has_image') else False for recipe in primary_recipes)
    }
    
    return render(request, "recipes/home.html", context)

def search_recipes(request):
    # Search view for recipes
    #comines datsaset and user recipes into one list and filters them based on the search query and category
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
    #list view for recipes that show information about each recipe
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
                #dislike is no loner used
            if dislike_filter and dislike_filter != 'all':
                if dislike_filter in categories:
                    continue
            
            recipe.categories = categories
            filtered_recipes.append(recipe)
            
        return filtered_recipes

class RecipeDetailView(DetailView):
    #detail view for a single recipe
    model = models.Recipe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['is_saved'] = self.object.is_saved_by(self.request.user)
        return context


@login_required
def toggle_save_recipe(request, pk):
    if request.method == 'POST':
        try:
            recipe = get_object_or_404(Recipe, pk=pk)
            
            # check if already saved
            existing_save = SavedRecipe.objects.filter(user=request.user, recipe=recipe)
            
            if existing_save.exists():
                #if already saved, remove it 
                existing_save.delete()
                return JsonResponse({'success': True, 'message': 'Recipe removed from saved recipes', 'saved': False})
            else:
                #if not saved, add it 
                saved_recipe = SavedRecipe(user=request.user, recipe=recipe)
                saved_recipe.save()
                return JsonResponse({'success': True, 'message': 'Recipe saved successfully!', 'saved': True})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

    

class RecipeCreateView(LoginRequiredMixin, CreateView):
    #create view for a new recipe
    model = models.Recipe

    form_class = RecipeForm  #
    template_name = 'recipes/recipe_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
class RecipeUpdateView(LoginRequiredMixin,UserPassesTestMixin, UpdateView):
    # update view for a recipe
    model = models.Recipe
    fields = ['title', 'description']

    def test_func(self):
        recipe = self.get_object()
        return self.request.user == recipe.author

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
    
class RecipeDeleteView(LoginRequiredMixin,UserPassesTestMixin, DeleteView):
    # delete view for a recipe
    model = models.Recipe
    success_url = reverse_lazy('recipes-home')

    def test_func(self):
        recipe = self.get_object()
        return self.request.user == recipe.author

    
    

def about(request):
    return render(request, "recipes/about.html", {'title': 'About us page'})





@login_required
def remove_item(request, item_id):
    #Remove an ingredient from the shopping list.
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

    #mark an ingredient as used, remove it and award points.
    if request.method == "POST":
        item = get_object_or_404(ShoppingListItem, id=item_id, user=request.user)
        item.delete()  
        return JsonResponse({"success": True})





@login_required
def remove_tracked_ingredient(request, item_id):
    
    #Allows users to remove ingredients from their tracking list.
    
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
    
    #Matches user's tracked ingredients with web-scraped recipes.
    
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
#not wokring
def scrape_recipes(request):
    
    #Scrapes recipes based on the user's tracked ingredients.
    
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
    #track an ingredient for the user and add it to the tracked list
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received data:", data)  
            
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
            print(f"Error adding ingredient: {str(e)}")  
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})

@login_required
def ingredient_tracking(request):

    def print_progress(message):
        print(f"Progress: {message}")
        
        log_key = f"ingredient_tracking_logs_{request.user.id}"
        log_entries = cache.get(log_key, [])
        log_entries.append({
            'message': f"Progress: {message}",
            'type': 'progress',
            'timestamp': datetime.now().isoformat()
        })
        #nly keep the most recent 100 entries
        log_entries = log_entries[-100:]
        cache.set(log_key, log_entries, 60 * 5)  

    def print_match(recipe_name, matched_count, missing_count):
        print(f"Match found: {recipe_name} with {matched_count} ingredients matched, {missing_count} missing")
        
        log_key = f"ingredient_tracking_logs_{request.user.id}"
        log_entries = cache.get(log_key, [])
        log_entries.append({
            'message': f"Match found: {recipe_name} with {matched_count} ingredients matched, {missing_count} missing",
            'type': 'match',
            'timestamp': datetime.now().isoformat()
        })
        log_entries = log_entries[-100:]
        cache.set(log_key, log_entries, 60 * 5)

    def print_perfect_match(recipe_name, matched_count):
        print(f"PERFECT MATCH: {recipe_name} - {matched_count} ingredients matched, 0 missing")
        
        log_key = f"ingredient_tracking_logs_{request.user.id}"
        log_entries = cache.get(log_key, [])
        log_entries.append({
            'message': f"PERFECT MATCH: {recipe_name} - {matched_count} ingredients matched, 0 missing",
            'type': 'perfect_match',
            'timestamp': datetime.now().isoformat()
        })
        log_entries = log_entries[-100:]
        cache.set(log_key, log_entries, 60 * 5)

    def print_stats(total_processed, matches_found, perfect_matches):
        print(f"Statistics: Processed {total_processed} recipes, Found {matches_found} matches, Perfect matches: {perfect_matches}")
        
        log_key = f"ingredient_tracking_logs_{request.user.id}"
        log_entries = cache.get(log_key, [])
        log_entries.append({
            'message': f"Statistics: Processed {total_processed} recipes, Found {matches_found} matches, Perfect matches: {perfect_matches}",
            'type': 'stats',
            'timestamp': datetime.now().isoformat()
        })
        log_entries = log_entries[-100:]
        cache.set(log_key, log_entries, 60 * 5)

    def print_highlight(message):
        print(f">>> {message}")
        
        log_key = f"ingredient_tracking_logs_{request.user.id}"
        log_entries = cache.get(log_key, [])
        log_entries.append({
            'message': f">>> {message}",
            'type': 'highlight',
            'timestamp': datetime.now().isoformat()
        })
        log_entries = log_entries[-100:]
        cache.set(log_key, log_entries, 60 * 5)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'progress_check' in request.GET:
        # Return the current progress info from cache
        progress_key = f"ingredient_tracking_progress_{request.user.id}"
        progress_data = cache.get(progress_key, {
            'status': 'Starting...',
            'progress': 0,
            'total_processed': 0,
            'matches_found': 0,
            'perfect_matches': 0,
            'step': 'initializing'
        })
        
        # Add recent log entries to the response
        log_key = f"ingredient_tracking_logs_{request.user.id}"
        log_entries = cache.get(log_key, [])
        progress_data['log_entries'] = log_entries
        
        return JsonResponse(progress_data)
        
    total_dataset_recipes = DatasetRecipe.objects.count()
    
    progress_key = f"ingredient_tracking_progress_{request.user.id}"
    
    progress_data = {
        'status': f"Starting recipe search across {total_dataset_recipes} recipes",
        'progress': 0,
        'total_processed': 0,
        'matches_found': 0,
        'perfect_matches': 0,
        'step': 'starting'
    }
    cache.set(progress_key, progress_data, 60*10)  #cache for 10 minutes
    
    print(f"Total dataset recipes in database: {total_dataset_recipes}")
    tracked_ingredients = TrackedIngredient.objects.filter(user=request.user).order_by('ingredient_name')
    
    # Get filter parameters( this festure is not working yet)
    show_all = request.GET.get('show_all', 'false') == 'true'
    cuisine_filter = request.GET.get('cuisine', '')
    meal_type = request.GET.get('meal_type', '')
    max_missing = request.GET.get('max_missing', '')
    sort_by = request.GET.get('sort_by', 'matched_count')  
    selected_difficulty = request.GET.get('difficulty', '')
    
    #update progress
    progress_data = {
        'status': f"Analyzing your {len(tracked_ingredients)} tracked ingredients",
        'progress': 5,
        'step': 'analyzing_ingredients'
    }
    cache.set(progress_key, progress_data, 60*10)
    
    print("==== INGREDIENT TRACKING DEBUG ====")
    print(f"Function called by user: {request.user.username}")
    print(f"Show all recipes (including those without images): {show_all}")
    print(f"Applied filters - Cuisine: '{cuisine_filter}', Meal Type: '{meal_type}', Max Missing: '{max_missing}', Sort By: '{sort_by}', Difficulty: '{selected_difficulty}'")
    
    print(f"User has {len(tracked_ingredients)} tracked ingredients:")
    for ing in tracked_ingredients:
        print(f"  - {ing.ingredient_name} (normalized: {normalize_ingredient_name(ing.ingredient_name)})")
    
    if not tracked_ingredients.exists():
        print("No tracked ingredients found. Returning empty result.")
        #clear progress data
        cache.delete(progress_key)
        return render(request, 'recipes/ingredient_tracking.html', {
            'tracked_ingredients': [],
            'matched_recipes': [],
            'total_matches': 0,
            'perfect_matches': 0
        })

    #generate a cache key based on the user's ingredients and filters
    ingredient_ids = sorted([str(ing.id) for ing in tracked_ingredients])
    ingredients_hash = hashlib.md5(json.dumps(ingredient_ids).encode()).hexdigest()
    filter_string = f"{show_all}-{cuisine_filter}-{meal_type}-{max_missing}-{selected_difficulty}"
    cache_key = f"ingredient_tracking_{request.user.id}_{ingredients_hash}_{filter_string}"
    
    #try to get results from cache
    cached_results = cache.get(cache_key)
    if cached_results:
        print("Using cached recipe matches")
        matched_recipes = cached_results
        
        progress_data = {
            'status': "Using cached results from previous search",
            'progress': 90,
            'step': 'using_cache'
        }
        cache.set(progress_key, progress_data, 60*10)
        
        all_cuisines = set()
        all_meal_types = set()
        for recipe_match in matched_recipes:
            if 'cuisine' in recipe_match and recipe_match['cuisine']:
                categories = [cat.strip().lower() for cat in recipe_match['cuisine'].split(',')]
                all_cuisines.update(categories)
                
                meal_keywords = ['breakfast', 'lunch', 'dinner', 'appetizer', 'dessert', 'snack', 'brunch']
                for cat in categories:
                    if cat in meal_keywords:
                        all_meal_types.add(cat)
    else:
        print("Cache miss - processing recipes")
        #ipdate progres
        progress_data = {
            'status': "Processing your ingredients to find the best recipes",
            'progress': 10,
            'step': 'normalizing_ingredients'
        }
        cache.set(progress_key, progress_data, 60*10)
        
        #normalize and prepare user ingredients
        user_ingredient_names = [normalize_ingredient_name(item.ingredient_name) for item in tracked_ingredients]
        user_ingredient_set = set(user_ingredient_names)
        print(f"Normalized user ingredients: {user_ingredient_set}")
        
        matched_recipes = []
        all_cuisines = set()
        all_meal_types = set()
        
        from django.db.models import Q
        filter_conditions = Q()
        
        for ingredient in tracked_ingredients:
            normalized_name = normalize_ingredient_name(ingredient.ingredient_name)
            #look for partial matches in ingredients_parts field
            filter_conditions |= Q(ingredients_parts__icontains=normalized_name)
        
        progress_data = {
            'status': "Searching database for recipes with your ingredients",
            'progress': 15,
            'step': 'querying_database'
        }
        cache.set(progress_key, progress_data, 60*10)
        
        # Apply cuisine filter if provided
        print("Building database query for dataset recipes...")
        if cuisine_filter:
            cuisine_q = Q(category__icontains=cuisine_filter)
            potential_matches = DatasetRecipe.objects.filter(filter_conditions & cuisine_q)[:150000]#tells how many recioes to analyse
            print(f"Query includes cuisine filter: {cuisine_filter}")
        else:
            potential_matches = DatasetRecipe.objects.filter(filter_conditions)[:150000]
        
        potential_count = potential_matches.count()
        print(f"Potential dataset recipe matches from DB: {potential_count}")
        
        progress_data = {
            'status': f"Found {potential_count} potential recipes - analyzing ingredients",
            'progress': 20,
            'step': 'analyzing_recipes'
        }
        cache.set(progress_key, progress_data, 60*10)
        
        total_recipes_processed = 0
        recipes_skipped_no_image = 0
        recipes_skipped_no_ingredients = 0
        recipes_skipped_meal_type = 0
        recipes_skipped_no_matches = 0
        recipes_skipped_too_many_missing = 0
        recipes_with_errors = 0
        recipes_below_threshold = 0
        perfect_matches_found = 0
        
        # all perfect matches for debugging
        all_perfect_matches = []
        
        print("\nProcessing dataset recipes...")
        progress_update_interval = max(1, potential_count // 20)  
        
        #process dataset recipes
        for count, recipe in enumerate(potential_matches):
            try:
                total_recipes_processed += 1
                
                if count % progress_update_interval == 0:
                    progress_percent = min(20 + int((count / potential_count) * 60), 80)
                    match_count = len(matched_recipes)
                    progress_data = {
                        'status': f"Processed {count}/{potential_count} recipes - Found {match_count} matches",
                        'progress': progress_percent,
                        'total_processed': count,
                        'matches_found': match_count,
                        'perfect_matches': perfect_matches_found,
                        'step': 'processing_dataset'
                    }
                    cache.set(progress_key, progress_data, 60*10)
                
                # skip recipes without images unless show_all is True
                if not show_all and not (hasattr(recipe, 'has_image') and callable(getattr(recipe, 'has_image')) and recipe.has_image()):
                    recipes_skipped_no_image += 1
                    if total_recipes_processed % 1000 == 0:
                        print(f"Progress: Processed {total_recipes_processed} recipes, skipped {recipes_skipped_no_image} without images")
                    continue
                    
                recipe_ingredients = recipe.get_ingredients()
                if not recipe_ingredients:
                    recipes_skipped_no_ingredients += 1
                    continue
                    
                if recipe.category:
                    categories = [cat.strip().lower() for cat in recipe.category.split(',')]
                    all_cuisines.update(categories)
                    
                    meal_keywords = ['breakfast', 'lunch', 'dinner', 'appetizer', 'dessert', 'snack', 'brunch']
                    for cat in categories:
                        if cat in meal_keywords:
                            all_meal_types.add(cat)
                
                if meal_type and (meal_type.lower() not in [cat.lower() for cat in recipe.category.split(',')] if recipe.category else True):
                    recipes_skipped_meal_type += 1
                    continue
                    
                normalized_recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe_ingredients]
                
                # find matching ingredients with more flexible matching
                matching_ings = set()
                
                for recipe_ing in normalized_recipe_ingredients:
                    for user_ing in user_ingredient_names:
                        if (user_ing in recipe_ing or recipe_ing in user_ing or 
                            user_ing.split()[0] in recipe_ing or recipe_ing.split()[0] in user_ing):
                            matching_ings.add(recipe_ing)
                            break
                
                # skip if we have no matches at all
                if not matching_ings:
                    recipes_skipped_no_matches += 1
                    continue
                    
                #calculate missing ingredients
                recipe_ingredient_set = set(normalized_recipe_ingredients)
                missing_ings = recipe_ingredient_set - matching_ings
                total_missing = len(missing_ings)
                
                #skip if too many missing ingredients when filter is applied
                if max_missing and total_missing > int(max_missing):
                    recipes_skipped_too_many_missing += 1
                    continue
                    
                total_recipe_ings = len(normalized_recipe_ingredients)
                match_percentage = (len(matching_ings) / total_recipe_ings) * 100
                
                #calculate weighted percentage (prioritizes recipes that use MORE of the users ingredients)
                #This gives higher scores to recipes that use more of what the user has
                weighted_percentage = match_percentage
                
                if match_percentage >= 5:
                    recipe_match = {
                        'is_dataset': True,
                        'recipe': recipe,
                        'name': recipe.name,
                        'prep_time': recipe.prep_time,
                        'cook_time': recipe.cook_time,
                        'cuisine': recipe.category,
                        'matching_ingredients': list(matching_ings),
                        'missing_ingredients': list(missing_ings),
                        'match_percentage': round(match_percentage, 1),
                        'matched_count': len(matching_ings),  
                        'weighted_percentage': round(weighted_percentage, 1),
                        'total_ingredients': total_recipe_ings,
                        'extra_ingredients_needed': total_missing,
                        'is_perfect_match': total_missing == 0 and len(matching_ings) > 0
                    }
                    
                    ingredient_count = 0
                    if hasattr(recipe, 'ingredients_parts') and recipe.ingredients_parts:
                        ingredient_count = len(recipe.ingredients_parts.split('\n'))
                    elif hasattr(recipe, 'ingredients') and recipe.ingredients:
                        if isinstance(recipe.ingredients, str):
                            ingredient_count = len(recipe.ingredients.split('\n'))
                        elif isinstance(recipe.ingredients, list):
                            ingredient_count = len(recipe.ingredients)
                    
                    # Add difficulty level to match dict with beginner level
                    if ingredient_count <= 3:
                        recipe_match['difficulty'] = 'beginner'
                    elif ingredient_count <= 6:
                        recipe_match['difficulty'] = 'easy'
                    elif ingredient_count <= 9:
                        recipe_match['difficulty'] = 'medium'
                    elif ingredient_count <= 12:
                        recipe_match['difficulty'] = 'hard'
                    else:
                        recipe_match['difficulty'] = 'insane'
                    
                    if total_missing == 0:
                        perfect_matches_found += 1
                        all_perfect_matches.append(recipe.name)
                        print(f"PERFECT MATCH: {recipe.name} - {len(matching_ings)} ingredients matched, {len(missing_ings)} missing")
                    
                    matched_recipes.append(recipe_match)
                else:
                    recipes_below_threshold += 1
            except Exception as e:
                recipes_with_errors += 1
                print(f"Error with dataset recipe {recipe.name}: {str(e)}")
                continue
        
        print(f"\nFinished processing dataset recipes.")
        print(f"Total processed: {total_recipes_processed}")
        print(f"Skipped due to no image: {recipes_skipped_no_image}")
        print(f"Skipped due to no ingredients: {recipes_skipped_no_ingredients}")
        print(f"Skipped due to meal type filter: {recipes_skipped_meal_type}")
        print(f"Skipped due to no matching ingredients: {recipes_skipped_no_matches}")
        print(f"Skipped due to too many missing ingredients: {recipes_skipped_too_many_missing}")
        print(f"Skipped due to match percentage below threshold: {recipes_below_threshold}")
        print(f"Recipes with errors: {recipes_with_errors}")
        print(f"Perfect matches found in dataset recipes: {perfect_matches_found}")
        
        progress_data = {
            'status': f"Found {len(matched_recipes)} dataset matches - Processing user recipes",
            'progress': 85,
            'matches_found': len(matched_recipes),
            'perfect_matches': perfect_matches_found,
            'step': 'processing_user_recipes'
        }
        cache.set(progress_key, progress_data, 60*10)
        
        # Process user recipes similarly
        print("\nProcessing user recipes...")
        user_recipes = Recipe.objects.all()[:500]
        user_perfect_matches = 0
        
        for recipe in user_recipes:
            try:
                if not show_all and not recipe.has_image():
                    continue
                    
                recipe_ingredients = recipe.get_ingredients()
                if not recipe_ingredients:
                    continue
                
                categories = recipe.get_categories()
                if meal_type and meal_type not in categories:
                    continue
                    
                for cat in categories:
                    if cat not in ['all', 'breakfast', 'lunch', 'dinner', 'dessert', 'vegetarian', 
                                 'spicy', 'quick', 'healthy']:
                        all_cuisines.add(cat)
                    if cat in ['breakfast', 'lunch', 'dinner', 'dessert']:
                        all_meal_types.add(cat)
                
                if cuisine_filter and cuisine_filter not in categories:
                    continue
                
                normalized_recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe_ingredients]
                
                matching_ings = set()
                
                for recipe_ing in normalized_recipe_ingredients:
                    for user_ing in user_ingredient_names:
                        if (user_ing in recipe_ing or recipe_ing in user_ing or 
                            user_ing.split()[0] in recipe_ing or recipe_ing.split()[0] in user_ing):
                            matching_ings.add(recipe_ing)
                            break
                
                if not matching_ings:
                    continue
                    
                recipe_ingredient_set = set(normalized_recipe_ingredients)
                missing_ings = recipe_ingredient_set - matching_ings
                total_missing = len(missing_ings)
                
                if max_missing and total_missing > int(max_missing):
                    continue
                    
                total_recipe_ings = len(normalized_recipe_ingredients)
                match_percentage = (len(matching_ings) / total_recipe_ings) * 100
                
                weighted_percentage = match_percentage
                
                if match_percentage >= 5:
                    user_recipe_match = {
                        'is_dataset': False,
                        'recipe': recipe,
                        'name': recipe.title,
                        'prep_time': recipe.prep_time,
                        'cook_time': recipe.cook_time,
                        'cuisine': recipe.category if hasattr(recipe, 'category') and recipe.category else None,
                        'matching_ingredients': list(matching_ings),
                        'missing_ingredients': list(missing_ings),
                        'match_percentage': round(match_percentage, 1),
                        'matched_count': len(matching_ings),  
                        'weighted_percentage': round(weighted_percentage, 1),
                        'total_ingredients': total_recipe_ings,
                        'extra_ingredients_needed': total_missing,
                        'is_perfect_match': total_missing == 0 and len(matching_ings) > 0
                    }
                    
                    ingredient_count = 0
                    if hasattr(recipe, 'ingredients_parts') and recipe.ingredients_parts:
                        ingredient_count = len(recipe.ingredients_parts.split('\n'))
                    elif hasattr(recipe, 'ingredients') and recipe.ingredients:
                        if isinstance(recipe.ingredients, str):
                            ingredient_count = len(recipe.ingredients.split('\n'))
                        elif isinstance(recipe.ingredients, list):
                            ingredient_count = len(recipe.ingredients)
                    
                    if ingredient_count <= 3:
                        user_recipe_match['difficulty'] = 'beginner'
                    elif ingredient_count <= 6:
                        user_recipe_match['difficulty'] = 'easy'
                    elif ingredient_count <= 9:
                        user_recipe_match['difficulty'] = 'medium'
                    elif ingredient_count <= 12:
                        user_recipe_match['difficulty'] = 'hard'
                    else:
                        user_recipe_match['difficulty'] = 'insane'
                    
                    if total_missing == 0:
                        user_perfect_matches += 1
                        all_perfect_matches.append(recipe.title)
                        print(f"PERFECT MATCH (User Recipe): {recipe.title} - {len(matching_ings)} ingredients matched, {len(missing_ings)} missing")
                    
                    matched_recipes.append(user_recipe_match)
            except Exception as e:
                print(f"Error with user recipe {recipe.title}: {str(e)}")
                continue
        
        print(f"Perfect matches found in user recipes: {user_perfect_matches}")
        print(f"Total perfect matches found: {perfect_matches_found + user_perfect_matches}")
        print(f"Perfect match recipes: {all_perfect_matches}")
        
        progress_data = {
            'status': "Finalizing results and preparing display",
            'progress': 90,
            'matches_found': len(matched_recipes),
            'perfect_matches': perfect_matches_found + user_perfect_matches,
            'step': 'finalizing'
        }
        cache.set(progress_key, progress_data, 60*10)
        
        #store results in cache for 1 hour
        cache.set(cache_key, matched_recipes, 60 * 60)
    
    if selected_difficulty:
        matched_recipes = [match for match in matched_recipes if match['difficulty'] == selected_difficulty]
    
    #filter out recipes with 2 or fewer ingredients
    print("\nFiltering out recipes with 2 or fewer ingredients...")
    initial_count = len(matched_recipes)
    matched_recipes = [match for match in matched_recipes if match['total_ingredients'] > 1]
    filtered_count = initial_count - len(matched_recipes)
    print(f"Filtered out {filtered_count} recipes with 2 or fewer ingredients")
    
    # sort the recipes by perfect matches first, then by fewest additional ingredients needed
    print("\nSorting recipes by perfect matches first, then by fewest additional ingredients needed...")

    #first separate perfect matches and non-perfect matches
    perfect_matches = [match for match in matched_recipes if match['is_perfect_match']]
    non_perfect_matches = [match for match in matched_recipes if not match['is_perfect_match']]

    # keep perfect matches sorted as before (by number of matching ingredients)
    perfect_matches.sort(key=lambda x: -len(x['matching_ingredients']))

    # sort non-perfect matches by fewest extra ingredients needed first
    non_perfect_matches.sort(key=lambda x: (
        x['extra_ingredients_needed'],  #fewest missing ingredients first
        -x['match_percentage']  #then by match percentage (higher is better)
    ))

    #combine together 
    matched_recipes = perfect_matches + non_perfect_matches

    print(f"Perfect matches at top: {len(perfect_matches)}")
    print(f"Then sorted by fewest additional ingredients needed: {len(non_perfect_matches)}")

    #show some examples from the sorted list
    if non_perfect_matches:
        print("\nExample non-perfect matches after sorting:")
        for i, match in enumerate(non_perfect_matches[:5]):
            print(f"  {i+1}. {match['name']} - Matched: {len(match['matching_ingredients'])}, Missing: {match['extra_ingredients_needed']}, Total ingredients: {match['total_ingredients']}")
    
    # limit to top 150 matches after sorting
    original_count = len(matched_recipes)
    matched_recipes = matched_recipes[:150]
    
    print(f"Limited from {original_count} matches to top 150")
    perfect_matches_count = sum(1 for r in matched_recipes if r['is_perfect_match'])
    print(f"Perfect matches in top 150: {perfect_matches_count}")
    
    progress_data = {
        'status': "Completed! Displaying results",
        'progress': 100,
        'matches_found': len(matched_recipes),
        'perfect_matches': perfect_matches_count,
        'step': 'completed'
    }
    cache.set(progress_key, progress_data, 60*10)
    
    per_page = 30
    paginator = Paginator(matched_recipes, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    print(f"Pagination: Page {page_number} of {paginator.num_pages}, showing {per_page} recipes per page")

    context = {
        'tracked_ingredients': tracked_ingredients,
        'matched_recipes': page_obj,
        'total_matches': len(matched_recipes),
        'perfect_matches': perfect_matches_count,
        'good_matches': sum(1 for r in matched_recipes if r['match_percentage'] >= 40),
        'show_all': show_all,
        'cuisines': sorted(all_cuisines),
        'meal_types': sorted(all_meal_types),
        'selected_cuisine': cuisine_filter,
        'selected_meal_type': meal_type,
        'selected_max_missing': max_missing,
        'selected_sort': sort_by,
        'selected_difficulty': selected_difficulty,
    }
    
    print("\nSummary:")
    print(f"Total matches: {context['total_matches']}")
    print(f"Perfect matches: {context['perfect_matches']}")
    print(f"Good matches: {context['good_matches']}")
    print("==== END INGREDIENT TRACKING DEBUG ====\n")

  
    
    return render(request, 'recipes/ingredient_tracking.html', context)

def search_recipes(request):
    #search view for recipes by query, category, and nutrtioan
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

def create_recipe(request):
    # Create a new recipe
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)  
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.author = request.user
            recipe.save()
            return redirect('recipe-detail', pk=recipe.pk)
    else:
        form = RecipeForm()
    return render(request, 'recipes/recipe_form.html', {'form': form})

@login_required
def remove_tracked_ingredient(request, item_id):
    
    #Allows users to remove ingredients from their tracking list.
    
    if request.method == "POST":
        try:
            item = TrackedIngredient.objects.get(id=item_id, user=request.user)
            item.delete()
            return JsonResponse({"success": True})
        except TrackedIngredient.DoesNotExist:
            return JsonResponse({
                "success": False,
                "error": "Ingredient not found"
            }, status=404)

    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def add_recipe_to_shopping_list(request, recipe_id):
    #add all ingredients from a recipe to the user's shopping list.
    if request.method == "POST":
        try:
            is_dataset = request.POST.get('is_dataset') == 'true'
            
            if is_dataset:
                recipe = get_object_or_404(DatasetRecipe, pk=recipe_id)
                ingredients = []
                
                full_ingredients = recipe.get_full_ingredients()
                if full_ingredients:
                    ingredients = [(item, '') for item in full_ingredients]
                else:
                    ingredients = [(item, '') for item in recipe.get_ingredients()]
            else:
                recipe = get_object_or_404(Recipe, pk=recipe_id)
                ingredients = [(item, '') for item in recipe.get_ingredients()]
            
            added_items = []
            for ingredient_text, quantity in ingredients:
                if not ingredient_text:
                    continue
                    
                item = ShoppingListItem.objects.create(
                    user=request.user,
                    ingredient_name=ingredient_text.strip(),
                    quantity=quantity.strip() if quantity else '',
                    expiration_date=None
                )
                added_items.append(item)
            
            return JsonResponse({
                "success": True, 
                "message": f"Added {len(added_items)} ingredients to your shopping list",
                "count": len(added_items)
            })
            
        except Exception as e:
            import traceback
            print(f"Error adding recipe to shopping list: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                "success": False, 
                "error": str(e)
            }, status=500)
    
    return JsonResponse({"error": "Invalid request"}, status=400)

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import DatasetRecipe, SavedDatasetRecipe

@login_required
def save_dataset_recipe(request, recipe_id):
    #save or unsave a dataset recipe for the current user
    if request.method == 'POST':
        try:
            recipe = DatasetRecipe.objects.get(id=recipe_id)
            
            saved_recipe_exists = SavedDatasetRecipe.objects.filter(
                user=request.user,
                recipe=recipe
            ).exists()
            
            if saved_recipe_exists:
                SavedDatasetRecipe.objects.filter(
                    user=request.user,
                    recipe=recipe
                ).delete()
                is_saved = False
                message = 'Recipe removed from saved recipes'
            else:
                SavedDatasetRecipe.objects.create(
                    user=request.user,
                    recipe=recipe,
                    saved=True
                )
                is_saved = True
                message = 'Recipe saved successfully!'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'is_saved': is_saved
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
            
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=400)


@login_required
def mark_recipe_as_tried(request, pk):
    
    #mark a recipe as tried by the current user
    recipe = get_object_or_404(Recipe, pk=pk)
    
    if not TriedRecipe.objects.filter(user=request.user, recipe=recipe).exists():
        TriedRecipe.objects.create(user=request.user, recipe=recipe)
        messages.success(request, f"You've marked '{recipe.title}' as tried!")  
    else:
        messages.info(request, "You've already tried this recipe!")  
    
    return redirect(request.META.get('HTTP_REFERER', reverse('recipes-detail', kwargs={'pk': pk})))

@login_required
def mark_dataset_recipe_as_tried(request, pk):
    #mark a dataset recipe as tried by the current user"""
    recipe = get_object_or_404(DatasetRecipe, pk=pk)
    
    if not TriedRecipe.objects.filter(user=request.user, dataset_recipe=recipe).exists():
        TriedRecipe.objects.create(
            user=request.user,
            dataset_recipe=recipe
        )
        messages.success(request, f"You've marked '{recipe.name}' as tried!")
    else:
        messages.info(request, "You've already tried this recipe!")
    
    return redirect(request.META.get('HTTP_REFERER', reverse('dataset-recipe-detail', kwargs={'pk': pk})))

@login_required
def scraped_recipe_detail(request, recipe_id):
    
    #View for displaying a scraped recipe in detail
    
    recipe = get_object_or_404(ScrapedRecipe, pk=recipe_id)
    
    from users.models import UnlockedRecipeReward
    is_unlocked = UnlockedRecipeReward.objects.filter(
        user=request.user,
        recipe=recipe
    ).exists()
    
    if not is_unlocked:
        messages.error(request, "You haven't unlocked this recipe yet! Level up to unlock more recipes.")
        return redirect('unlocked-recipes')
    
    # Get the recipe ingredients
    ingredients = recipe.ingredients.all()
    
    context = {
        'recipe': recipe,
        'ingredients': ingredients,
        'title': recipe.title
    }
    
    return render(request, 'recipes/scraped_recipe_detail.html', context)


@login_required
def mark_scraped_recipe_as_tried(request, recipe_id):
    #Mark a scraped recipe as tried by the current user
    recipe = get_object_or_404(ScrapedRecipe, pk=recipe_id)
    
    from users.models import UnlockedRecipeReward
    is_unlocked = UnlockedRecipeReward.objects.filter(
        user=request.user,
        recipe=recipe
    ).exists()
    
    if not is_unlocked:
        messages.error(request, "You haven't unlocked this recipe yet!")
        return redirect('unlocked-recipes')
    
    if TriedRecipe.objects.filter(user=request.user, scraped_recipe=recipe).exists():
        messages.info(request, "You've already tried this recipe!")
        return redirect('scraped-recipe-detail', recipe_id=recipe.id)
    
    from users.views import award_points_for_recipe
    success, points = award_points_for_recipe(request, recipe.id, is_scraped=True)
    
    if success:
        extra_message = "You tried an exclusive recipe! "
        messages.success(request, extra_message)
    
    return redirect('scraped-recipe-detail', recipe_id=recipe.id)

@login_required
def add_scraped_recipe_to_shopping_list(request, recipe_id):
    #Add all ingredients from a scraped recipe to the shopping list
    recipe = get_object_or_404(ScrapedRecipe, pk=recipe_id)
    
    from users.models import UnlockedRecipeReward
    is_unlocked = UnlockedRecipeReward.objects.filter(
        user=request.user,
        recipe=recipe
    ).exists()
    
    if not is_unlocked:
        messages.error(request, "You haven't unlocked this recipe yet!")
        return redirect('unlocked-recipes')
    
    ingredients = recipe.ingredients.all()
    
    added_count = 0
    for ingredient in ingredients:
        ingredient_name = ingredient.clean_text()
        quantity = f"{ingredient.amount} {ingredient.unit}" if ingredient.amount and ingredient.unit else ""
        
        ShoppingListItem.objects.create(
            user=request.user,
            ingredient_name=ingredient_name,
            quantity=quantity,
            expiration_date=None
        )
        added_count += 1
    
    messages.success(request, f"Added {added_count} ingredients to your shopping list!")
    return redirect('scraped-recipe-detail', recipe_id=recipe.id)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import ShopRecipe, PurchasedRecipe, ScrapedRecipe

@login_required
def recipe_shop(request):
    #fetch shop recipes from ShopRecipe model
    shop_recipes = ShopRecipe.objects.all().select_related('recipe')
    
    all_shop_items = []
    
    for shop_item in shop_recipes:
        all_shop_items.append({
            'is_shop_recipe': True,  
            'shop_recipe': shop_item,
            'recipe': shop_item.recipe,
            'title': shop_item.recipe.title,
            'points_cost': shop_item.points_cost,
            'featured': shop_item.featured,
            'image': shop_item.recipe.image
        })
    
    #add user-created premium recipes that aren't already in the shop
    shop_recipe_ids = shop_recipes.values_list('recipe_id', flat=True)
    premium_user_recipes = Recipe.objects.filter(
        is_premium=True,  # Only premium recipes
        created_by_user=True,  # Only user-created recipes
    ).exclude(id__in=shop_recipe_ids)  # Exclude those already in shop
    
    for user_recipe in premium_user_recipes:
        all_shop_items.append({
            'is_shop_recipe': False,  
            'shop_recipe': None,
            'recipe': user_recipe,
            'title': user_recipe.title,
            'points_cost': user_recipe.points_cost,
            'featured': False,  
            'image': user_recipe.image
        })
    
    from users.models import UserPoints
    user_points = UserPoints.get_or_create_user_points(request.user).total_points
    
    purchased_recipes = PurchasedRecipe.objects.filter(user=request.user).values_list('recipe_id', flat=True)

    context = {
        'shop_recipes': all_shop_items,  
        'user_points': user_points,
        'purchased_recipes': purchased_recipes,
    }
    return render(request, 'recipes/recipe_shop.html', context)


@login_required
def purchase_recipe(request, recipe_id):
    #View for purchasing a recipe
    try:
        # Convert recipe_id to integer
        recipe_id = int(recipe_id)
        
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        
        #get the shop recipe if it exists
        shop_recipe = ShopRecipe.objects.filter(recipe_id=recipe_id).first()
        
        # Check if the recipe is premium and not in the shop
        if not shop_recipe and recipe.is_premium:
            points_cost = recipe.points_cost
        elif shop_recipe:
            points_cost = shop_recipe.points_cost
        else:
            messages.error(request, "This recipe is not available for purchase.")
            return redirect('recipe-shop')
        
        #check if the user has already purchased this recipe
        if PurchasedRecipe.objects.filter(user=request.user, recipe_id=recipe_id).exists():
            messages.info(request, "You've already purchased this recipe.")
            return redirect('recipe-shop')
        
        #check if the user has enough points
        from users.models import UserPoints, PointsTransaction
        user_points = UserPoints.get_or_create_user_points(request.user)
        if user_points.total_points < points_cost:
            messages.error(request, f"You don't have enough points to purchase this recipe. You need {points_cost} points.")
            return redirect('recipe-shop')
        
        # Process the purchase
        from django.db import transaction
        with transaction.atomic():
            user_points.total_points -= points_cost
            user_points.save()
            
            purchase = PurchasedRecipe.objects.create(
                user=request.user,
                recipe=recipe,
                points_spent=points_cost
            )
            
            PointsTransaction.objects.create(
                user=request.user,
                points=-points_cost,  
                description=f"Purchased recipe: {recipe.title}",
                transaction_type="recipe_purchase",
                recipe=recipe
            )
        
        messages.success(request, f"You've successfully purchased '{recipe.title}' for {points_cost} points!")
        return redirect('purchased-recipe-detail', recipe_id=recipe.id)
        
    except ValueError as e:
        messages.error(request, f"Invalid recipe ID: {str(e)}")
        return redirect('recipe-shop')
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('recipe-shop')

@login_required
def purchased_recipes(request):
    #View to display user's purchased recipes
    purchases = PurchasedRecipe.objects.filter(user=request.user).select_related('recipe').order_by('-purchased_at')
    return render(request, 'recipes/purchased_recipes.html', {'purchases': purchases})

@login_required
def submit_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.created_by_user = True  
            recipe.save()
            return redirect('recipe_submission_success')
    else:
        form = RecipeForm()
    return render(request, 'recipes/submit_recipe.html', {'form': form})

class RecipeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = ['title', 'description', 'ingredients', 'instructions', 'prep_time', 
                 'cook_time', 'servings', 'image']
        widgets = {
            'ingredients': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter each ingredient on a new line'}),
            'instructions': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Enter detailed cooking instructions'}),
        }

@login_required
def submit_recipe_for_review(request):
    if request.method == 'POST':
        form = RecipeSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            recipe = form.save(commit=False)
            recipe.author = request.user
            recipe.created_by_user = True
            recipe.status = 'submitted'  
            
            ingredients_text = form.cleaned_data.get('ingredients')
            if ingredients_text and isinstance(ingredients_text, str):
                ingredients_list = [line.strip() for line in ingredients_text.split('\n') if line.strip()]
                recipe.ingredients = json.dumps(ingredients_list)
            
            recipe.calories = form.cleaned_data.get('calories')
            recipe.fat = form.cleaned_data.get('fat')
            recipe.carbs = form.cleaned_data.get('carbs')
            recipe.protein = form.cleaned_data.get('protein')
            
            if form.cleaned_data.get('prep_time') and form.cleaned_data.get('cook_time'):
                try:
                    prep_time = int(form.cleaned_data.get('prep_time', 0) or 0)
                    cook_time = int(form.cleaned_data.get('cook_time', 0) or 0)
                    recipe.ready_in_minutes = prep_time + cook_time
                except (ValueError, TypeError):
                    pass
            
            recipe.save()
            
            print(f"Recipe submitted: {recipe.title}")
            print(f"Nutrition info: Calories: {recipe.calories}, Fat: {recipe.fat}g, Carbs: {recipe.carbs}g, Protein: {recipe.protein}g")
            
            messages.success(request, "Your recipe has been submitted for review! Our team will evaluate it soon.")
            return redirect('user-submissions')
    else:
        form = RecipeSubmissionForm()
    
    return render(request, 'recipes/submit_recipe.html', {'form': form})

@login_required
def user_submissions(request):
    # Get user's submitted recipes
    submitted_recipes = Recipe.objects.filter(
        author=request.user,
        status__in=['submitted', 'approved', 'premium', 'rejected']
    ).order_by('-created_at')
    
    return render(request, 'recipes/user_submissions.html', {
        'submitted_recipes': submitted_recipes
    })




def mark_as_premium(self, request, queryset):
    for recipe in queryset:
        recipe.is_premium = True
        recipe.status = 'premium'
        recipe.save()
        
        #award points to the author if not already awarded
        if recipe.author:
            from users.models import UserPoints, PointsTransaction
            user_points = UserPoints.get_or_create_user_points(recipe.author)
            
            premium_award_exists = PointsTransaction.objects.filter(
                user=recipe.author,
                description__contains=f"Recipe selected as premium: {recipe.title}",
                transaction_type='recipe_premium'
            ).exists()
            
            if not premium_award_exists:
                # award points 
                premium_points = 100
                user_points.total_points += premium_points
                user_points.save()
                
                PointsTransaction.objects.create(
                    user=recipe.author,
                    points=premium_points,
                    description=f"Recipe selected as premium: {recipe.title}",
                    transaction_type='recipe_premium',
                    recipe=recipe
                )
                
                from users.models import UserNotification
                UserNotification.objects.create(
                    user=recipe.author,
                    title="Your Recipe is now Premium!",
                    message=f"Congratulations! Your recipe '{recipe.title}' has been selected as a premium recipe and is now available in the Recipe Shop. You've earned {premium_points} points!",
                    notification_type='achievement'
                )
    
    self.message_user(request, f"{queryset.count()} recipes have been marked as premium.")
mark_as_premium.short_description = "Mark selected recipes as premium"


@login_required
def purchased_recipe_detail(request, recipe_id):
    #View to display a purchased recipe in detail
    try:
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        
        print(f"Recipe loaded: {recipe.title} (ID: {recipe.id})")
        if hasattr(recipe, 'ingredients'):
            print(f"Raw ingredients: {recipe.ingredients}")
        
        purchase = get_object_or_404(PurchasedRecipe, 
                                    user=request.user, 
                                    recipe_id=recipe_id)
        
        ingredients = []
        if hasattr(recipe, 'ingredients') and recipe.ingredients:
            if isinstance(recipe.ingredients, str):
                try:
                    if recipe.ingredients.startswith('['):
                        try:
                            ingredients = json.loads(recipe.ingredients.replace("'", '"'))
                        except json.JSONDecodeError:
                            ingredients = [recipe.ingredients]
                    elif '\n' in recipe.ingredients:
                        ingredients = [line.strip() for line in recipe.ingredients.split('\n') if line.strip()]
                    else:
                        ingredients = [recipe.ingredients]
                except Exception as e:
                    print(f"Error parsing ingredients: {e}")
                    ingredients = [recipe.ingredients]
            elif isinstance(recipe.ingredients, list):
                ingredients = recipe.ingredients
        
        print(f"Processed ingredients: {ingredients}")
        
        instructions_list = None
        if hasattr(recipe, 'instructions') and recipe.instructions:
            if isinstance(recipe.instructions, str):
                if recipe.instructions.startswith('['):
                    try:
                        instructions_list = json.loads(recipe.instructions)
                    except:
                        instructions_list = [line.strip() for line in recipe.instructions.split('\n') if line.strip()]
                else:
                    instructions_list = [line.strip() for line in recipe.instructions.split('\n') if line.strip()]
        
        from recipes.models import TriedRecipe
        is_tried = TriedRecipe.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists()
        
        ready_in_minutes = None
        if hasattr(recipe, 'ready_in_minutes'):
            ready_in_minutes = recipe.ready_in_minutes
        elif recipe.prep_time and recipe.cook_time:
            try:
                prep_time = int(recipe.prep_time) if recipe.prep_time else 0
                cook_time = int(recipe.cook_time) if recipe.cook_time else 0
                ready_in_minutes = prep_time + cook_time
            except (ValueError, TypeError):
                ready_in_minutes = None
        
        context = {
            'recipe': recipe,
            'purchase': purchase,
            'ingredients': ingredients,
            'instructions_list': instructions_list,
            'is_tried': is_tried,
            'title': recipe.title,
            'calories': recipe.calories,
            'fat': recipe.fat,
            'carbs': recipe.carbs,
            'protein': recipe.protein,
            'prep_time': recipe.prep_time,
            'cook_time': recipe.cook_time,
            'ready_in_minutes': ready_in_minutes,
            'servings': recipe.servings
        }
        
        return render(request, 'recipes/purchased_recipe_detail.html', context)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error viewing recipe: {str(e)}")
        return redirect('purchased-recipes')
    
@login_required
def mark_recipe_tried(request, recipe_id):
    #Mark a user-created recipe as tried
    try:
        from recipes.models import Recipe, TriedRecipe
        from users.models import UserPoints, PointsTransaction
        from django.utils import timezone
        
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        
        tried_exists = TriedRecipe.objects.filter(
            user=request.user,
            recipe=recipe
        ).exists()
        
        if tried_exists:
            messages.info(request, f"You've already marked '{recipe.title}' as tried!")
        else:
            TriedRecipe.objects.create(
                user=request.user,
                recipe=recipe,
                tried_at=timezone.now()
            )
            
            user_points = UserPoints.get_or_create_user_points(request.user)
            points_awarded = 5
            
            today = timezone.now().date()
            tried_today = TriedRecipe.objects.filter(
                user=request.user,
                tried_at__date=today
            ).count()
            
            if tried_today <= 1:  
                user_points.total_points += points_awarded
                user_points.save()
                
                PointsTransaction.objects.create(
                    user=request.user,
                    points=points_awarded,
                    description=f"Tried recipe: {recipe.title}",
                    transaction_type='recipe_tried'
                )
                
                messages.success(request, 
                    f"You've marked '{recipe.title}' as tried! You earned {points_awarded} points.")
            else:
                messages.success(request, 
                    f"You've marked '{recipe.title}' as tried! (Daily limit for points reached)")
        
        return redirect('purchased-recipe-detail', recipe_id=recipe.id)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        messages.error(request, f"Error marking recipe as tried: {str(e)}")
        return redirect('purchased-recipe-detail', recipe_id=recipe_id)
    

@login_required
def purchase_random_recipe(request):
    
    #vew for purchasing a random recipe
    
    RANDOM_RECIPE_COST = 50
    
    difficulty = request.GET.get('difficulty', None)
    valid_difficulties = ['beginner', 'easy', 'medium', 'hard', 'insane']
    
    if difficulty and difficulty not in valid_difficulties:
        messages.error(request, f"Invalid difficulty level. Please choose from: {', '.join(valid_difficulties)}")
        return redirect('recipe-shop')  
    
    user_points = UserPoints.get_or_create_user_points(request.user)
    
    if user_points.total_points < RANDOM_RECIPE_COST:
        messages.error(request, f"You don't have enough points. You need {RANDOM_RECIPE_COST} points to purchase a random recipe.")
        return redirect('recipe-shop')  
    
    # get the IDs of recipes the user has already purchased
    purchased_recipe_ids = PurchasedRecipe.objects.filter(
        user=request.user
    ).values_list('recipe_id', flat=True)
    
    available_recipes = ScrapedRecipe.objects.all()
    
    filtered_recipes = []
    if difficulty and available_recipes:
        from recipes.templatetags.recipe_filters import get_difficulty
        
        for recipe in available_recipes:
            difficulty_info = get_difficulty(recipe)
            
            if difficulty_info['level'].lower() == difficulty.lower():
                filtered_recipes.append(recipe.id)
                
        if filtered_recipes:
            available_recipes = ScrapedRecipe.objects.filter(id__in=filtered_recipes)
    
    if not available_recipes.exists():
        messages.error(request, "No recipes available for random selection.")
        return redirect('recipe-shop')  
    
    import random
    random_scraped_recipe = random.choice(available_recipes)
    
    print(f"Random recipe: {random_scraped_recipe.title}")
    print(f"Image field value: {random_scraped_recipe.image}")
    print(f"Image field type: {type(random_scraped_recipe.image).__name__}")
    
    try:
        with transaction.atomic():
            new_recipe = Recipe()
            new_recipe.title = random_scraped_recipe.title
            new_recipe.description = random_scraped_recipe.description if hasattr(random_scraped_recipe, 'description') else ""
            
            # copy image field exactly as it appears in the original
            #this ensures the image will display in the purchased_recipes template
            new_recipe.image = random_scraped_recipe.image
            
            # copy other important fields
            new_recipe.instructions = random_scraped_recipe.instructions if hasattr(random_scraped_recipe, 'instructions') else ""
            new_recipe.servings = random_scraped_recipe.servings
            new_recipe.ready_in_minutes = random_scraped_recipe.ready_in_minutes if hasattr(random_scraped_recipe, 'ready_in_minutes') else None
            new_recipe.prep_time = random_scraped_recipe.prep_time if hasattr(random_scraped_recipe, 'prep_time') else None
            new_recipe.cook_time = random_scraped_recipe.cook_time if hasattr(random_scraped_recipe, 'cook_time') else None
            
            if hasattr(random_scraped_recipe, 'ingredients'):
                if hasattr(random_scraped_recipe.ingredients, 'all'):
                    ingredient_objs = list(random_scraped_recipe.ingredients.all())
                    ingredients_list = [obj.name for obj in ingredient_objs]
                    new_recipe.ingredients = json.dumps(ingredients_list)
                else:
                    new_recipe.ingredients = random_scraped_recipe.ingredients
            elif hasattr(random_scraped_recipe, 'ingredients_list'):
                new_recipe.ingredients = random_scraped_recipe.ingredients_list
                
            if hasattr(random_scraped_recipe, 'url'):
                new_recipe.url = random_scraped_recipe.url
                
            new_recipe.is_premium = True
            new_recipe.status = 'premium'
            
            new_recipe.save()
            
            user_points.total_points -= RANDOM_RECIPE_COST
            user_points.save()
            
            PointsTransaction.objects.create(
                user=request.user,
                points=-RANDOM_RECIPE_COST,
                description=f"Purchased random recipe: {new_recipe.title}",
                transaction_type="random_recipe_purchase"
            )
            
            purchased_recipe = PurchasedRecipe.objects.create(
                user=request.user,
                recipe=new_recipe,
                points_spent=RANDOM_RECIPE_COST
            )
            
            messages.success(request, f"Congratulations! You've purchased the recipe: '{new_recipe.title}'")
            
            print(f"New recipe: {new_recipe.title}")
            print(f"New recipe image field: {new_recipe.image}")
            print(f"New recipe image field type: {type(new_recipe.image).__name__}")
            
            return redirect('purchased-recipe-detail', recipe_id=new_recipe.id)
            
    except Exception as e:
        import traceback
        traceback.print_exc()  
        messages.error(request, f"An error occurred while processing your purchase: {str(e)}")
        return redirect('recipe-shop')  

@login_required
def shopping_list(request):
    #Display the user's shopping list with expired items appearing first
    items = ShoppingListItem.objects.filter(user=request.user).order_by('expiration_date')

    
    from datetime import datetime, timedelta
    today = datetime.now().date()
    expiry_threshold = today + timedelta(days=3)
    
    for item in items:
        if item.expiration_date and item.expiration_date <= expiry_threshold:
            item.is_expiring_soon = True
        else:
            item.is_expiring_soon = False

    return render(request, 'recipes/shopping_list.html', {'items': items})


@login_required
def add_item(request):
    #add an ingredient to the shopping list.
    if request.method == "POST":
        data = json.loads(request.body)
        ingredient_name = data.get("ingredient_name")
        quantity = data.get("quantity")
        expiration_date = data.get("expiration_date")

        if not ingredient_name:
            return JsonResponse({"success": False, "error": "Ingredient name is required"}, status=400)

        expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date() if expiration_date else None

        item = ShoppingListItem.objects.create(
            user=request.user,
            ingredient_name=ingredient_name,
            quantity=quantity,
            expiration_date=expiration_date
        )

        return JsonResponse({
            "success": True, 
            "id": item.id,
            "ingredient": item.ingredient_name, 
            "quantity": item.quantity, 
            "expiration_date": item.expiration_date.strftime("%Y-%m-%d") if item.expiration_date else None
        })

    return JsonResponse({"error": "Invalid request"}, status=400)








@login_required
def clear_shopping_list(request):
    #Clear all items from the shopping list.
    if request.method == "POST":
        try:
            count = ShoppingListItem.objects.filter(user=request.user).count()
            ShoppingListItem.objects.filter(user=request.user).delete()
            return JsonResponse({
                "success": True,
                "count": count,
                "message": f"Removed {count} items from your shopping list."
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
            
    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def track_shopping_list_items(request):
    #Move all shopping list items to ingredient tracking.
    if request.method == "POST":
        try:
            from recipes.models import TrackedIngredient
            
            shopping_items = ShoppingListItem.objects.filter(user=request.user)
            count = 0
            
            for item in shopping_items:
                TrackedIngredient.objects.create(
                    user=request.user,
                    ingredient_name=item.ingredient_name,
                    quantity=item.quantity,
                    expiration_date=item.expiration_date
                )
                
                item.delete()
                count += 1
            
            return JsonResponse({
                "success": True,
                "count": count,
                "message": f"Moved {count} items to ingredient tracking."
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
            
    return JsonResponse({"error": "Invalid request"}, status=400)