import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from recipes.models import Recipe, DatasetRecipe, SavedRecipe, ShoppingListItem, TrackedIngredient, TriedRecipe
from recipes.utils import normalize_ingredient_name
from users.models import (
    PointsTransaction, UserPoints, UserNotification, 
    Achievement, UserAchievement, UserProgress, CHEF_LEVELS
)

from . import forms


def register(request):
    #user registration view
    if request.method == "POST":
        form = forms.UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!, Please login.')
            return redirect('user-login')
    else:
        form = forms.UserRegisterForm()  
    return render(request, "users/register.html", {'form': form})

@login_required()
def profile(request):
    #uer profile view with recipes, saved recipes, tried recipes, and achievements
    recipes = Recipe.objects.filter(author=request.user).order_by('-created_at')
    
    saved_recipes = SavedRecipe.objects.filter(user=request.user).select_related('recipe').order_by('-saved_at')
    
    saved_dataset_recipes = DatasetRecipe.objects.filter(
        saveddatasetrecipe__user=request.user,
    )
    
    tried_recipes = TriedRecipe.objects.filter(user=request.user).order_by('-tried_at')
    
    from users.models import UnlockedRecipeReward
    unlocked_recipes = UnlockedRecipeReward.objects.filter(user=request.user).select_related('recipe').order_by('-unlocked_at')
    
    #get or create user points profile
    user_points = UserPoints.get_or_create_user_points(request.user)
    
    #get level data
    level_data = user_points.get_level_data()
    progress_percent = user_points.calculate_progress()
    
    #get user's earned achievements
    user_achievements = UserAchievement.objects.filter(user=request.user).order_by('-earned_at')
    
    # Get achievement progress data
    achievement_progress = []
    
    unearned_achievements = Achievement.objects.exclude(
        id__in=user_achievements.values_list('achievement_id', flat=True)
    )
    
    for achievement in unearned_achievements:
        #get progress for this achievement type
        if achievement.achievement_type == 'recipe_category' and achievement.category:
            progress_obj, created = UserProgress.objects.get_or_create(
                user=request.user,
                achievement_type=achievement.achievement_type,
                category=achievement.category
            )
        else:
            progress_obj, created = UserProgress.objects.get_or_create(
                user=request.user,
                achievement_type=achievement.achievement_type
            )
        
        if achievement.requirement_count > 0:
            percentage = min(round((progress_obj.count / achievement.requirement_count) * 100), 100)
        else:
            percentage = 0
        
        if achievement.achievement_type == 'recipes_tried':
            display_name = f"Try {achievement.requirement_count} Recipes"
        elif achievement.achievement_type == 'recipe_category':
            display_name = f"{achievement.name} ({achievement.category.capitalize()} recipes)"
        else:
            display_name = achievement.name
        
        achievement_progress.append({
            'display_name': display_name,
            'count': progress_obj.count,
            'requirement': achievement.requirement_count,
            'percentage': percentage
        })
    
    #sort progress by percentage (highest first)
    achievement_progress.sort(key=lambda x: x['percentage'], reverse=True)
    
    #get unread notification count
    unread_notification_count = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    context = {
        'created_recipes': recipes,
        'saved_recipes': saved_recipes,
        'saved_dataset_recipes': saved_dataset_recipes,
        'tried_recipes': tried_recipes,
        'unlocked_recipes': unlocked_recipes[:3],  
        'unlocked_recipes_count': unlocked_recipes.count(),  
        'recipes_count': recipes.count(),
        'saved_recipes_count': saved_recipes.count() + saved_dataset_recipes.count(),
        'tried_recipes_count': tried_recipes.count(),
        'user_points': user_points,
        'current_level': level_data['current'],
        'next_level': level_data['next'],
        'progress_percent': progress_percent,
        'user_achievements': user_achievements,
        'achievement_progress': achievement_progress[:3],  
        'unread_notification_count': unread_notification_count
    }
    
    return render(request, 'users/profile.html', context)


def calculate_recipe_points(recipe, user=None):
    
    #Calculate points for a recipe based on its complexity, number of ingredients,
    #and bonus points for tracked ingredients and those near expiration.
    
    #Args:
    #   recipe: The recipe object
    #  user: The current user 
    
    #Returns:
    #tuple: (total_points, ingredient_count, points_breakdown)
    
    # get recipe ingredients
    if hasattr(recipe, 'get_ingredients'):
        ingredients = recipe.get_ingredients()
    elif hasattr(recipe, 'ingredients_list') and recipe.ingredients_list:
        import json
        try:
            ingredients = json.loads(recipe.ingredients_list)
        except:
            ingredients = []
    elif hasattr(recipe, 'ingredients') and recipe.ingredients:
        try:
            ingredients = json.loads(recipe.ingredients)
        except:
            ingredients = []
    else:
        ingredients = []
    
    #count non-empty ingredients
    ingredient_count = len([i for i in ingredients if i])
    
    #base points + points per ingredient
    base_points = 10
    regular_points = ingredient_count * 2
    total_points = base_points + regular_points
    
    #initialize bonus points variables
    tracked_ingredient_bonus = 0
    expiration_bonus = 0
    tracked_count = 0
    expiring_ingredients = []
    
    # check for tracked ingredients if user is provided
    from datetime import datetime, timedelta
    from recipes.models import TrackedIngredient
    from recipes.utils import normalize_ingredient_name
    
    if user and ingredient_count > 0:
        # get user's tracked ingredients
        tracked_ingredients = TrackedIngredient.objects.filter(user=user)
        
        #if user has tracked ingredients, check for matches
        if tracked_ingredients.exists():
            #current date for expiration check
            today = datetime.now().date()
            
            #normalize recipe ingredients
            normalized_recipe_ingredients = [normalize_ingredient_name(ing) for ing in ingredients]
            
            #check each tracked ingredient against recipe ingredients
            for tracked in tracked_ingredients:
                normalized_tracked_name = normalize_ingredient_name(tracked.ingredient_name)
                
                #check for ingredient match with fuzzy matching
                for recipe_ing in normalized_recipe_ingredients:
                    if (normalized_tracked_name in recipe_ing or 
                        recipe_ing in normalized_tracked_name or
                        normalized_tracked_name.split()[0] in recipe_ing or 
                        recipe_ing.split()[0] in normalized_tracked_name):
                        
                        #count as a tracked ingredient match
                        tracked_count += 1
                        
                        # add extra points for tracked ingredients (2 extra points per ingredient)
                        tracked_ingredient_bonus += 2
                        
                        # check expiration date for bonus points
                        if tracked.expiration_date:
                            days_until_expiration = (tracked.expiration_date - today).days
                            
                            # expiration bonus based on days remaining
                            if days_until_expiration < 0:
                                bonus = 3
                                expiration_status = "expired"
                            elif days_until_expiration == 0:
                                bonus = 3
                                expiration_status = "expires today"
                            elif days_until_expiration == 1:
                                bonus = 2
                                expiration_status = "expires tomorrow"
                            elif days_until_expiration == 2:
                                #expires in 2 days
                                bonus = 1
                                expiration_status = "expires in 2 days"
                            else:
                                #not expiring soon
                                bonus = 0
                                expiration_status = None
                            
                            if bonus > 0:
                                expiration_bonus += bonus
                                expiring_ingredients.append({
                                    'name': tracked.ingredient_name,
                                    'status': expiration_status,
                                    'bonus': bonus
                                })
                        
                        break
    
    total_points = base_points + regular_points + tracked_ingredient_bonus + expiration_bonus
    
    #create a breakdown for display
    breakdown = {
        'base_points': base_points,
        'regular_points': regular_points,
        'tracked_count': tracked_count,
        'tracked_bonus': tracked_ingredient_bonus * 2,
        'expiration_bonus': expiration_bonus,
        'expiring_ingredients': expiring_ingredients
    }
    
    return total_points, ingredient_count, breakdown

# Modify the update_user_progress function to correctly track the recipe categories
# This will ensure consistent tracking of achievement progress
def update_user_progress(user, recipe=None, dataset_recipe=None, scraped_recipe=None):
    #Update user progress for various achievement types when a recipe is tried
    print(f"Updating progress for user {user.username}")
    
    # update general recipes tried counter
    recipes_tried_progress, created = UserProgress.objects.get_or_create(
        user=user,
        achievement_type='recipes_tried',
        defaults={'count': 1}  
    )
    
    if not created:
        #only increment if not newly created
        recipes_tried_progress.count += 1
        recipes_tried_progress.save()
        print(f"Updated recipes_tried progress to {recipes_tried_progress.count}")
    
    categories = []
    
    #check for categories in user-created recipes
    if recipe:
        if hasattr(recipe, 'category') and recipe.category:
            categories.append(recipe.category.lower())
        elif hasattr(recipe, 'meal_type') and recipe.meal_type:
            categories.append(recipe.meal_type.lower())
        elif hasattr(recipe, 'tags') and recipe.tags:
            try:
                if isinstance(recipe.tags, str):
                    categories.extend([tag.strip().lower() for tag in recipe.tags.split(',')])
                elif isinstance(recipe.tags, list):
                    categories.extend([tag.lower() for tag in recipe.tags])
            except:
                pass
    
    #check for categories in dataset recipes
    elif dataset_recipe:
        if hasattr(dataset_recipe, 'tags') and dataset_recipe.tags:
            try:
                categories = [tag.lower() for tag in dataset_recipe.tags.split(',') if tag.strip()]
            except:
                pass
        elif hasattr(dataset_recipe, 'meal_type') and dataset_recipe.meal_type:
            categories.append(dataset_recipe.meal_type.lower())
    
    print(f"Recipe categories: {categories}")
    
    # update progress for each category only once
    for category in set(categories):  #using set() to avoid duplicates
        if category in ['breakfast', 'lunch', 'dinner', 'dessert', 'healthy', 'vegetarian']:
            category_progress, created = UserProgress.objects.get_or_create(
                user=user,
                achievement_type='recipe_category',
                category=category,
                defaults={'count': 1} 
            )
            
            if not created:
                category_progress.count += 1
                category_progress.save()
                print(f"Updated {category} category progress to {category_progress.count}")
    
    #sfter updating progres check for any achievements earned
    check_for_achievements(user)



def check_for_achievements(user):
    #check if user has earned any achievements based on current progress
    # get all available achievements
    achievements = Achievement.objects.all()
    achievements_earned = []
    
    for achievement in achievements:
        # skip if user already has this achievement
        if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            continue
        
        if achievement.achievement_type == 'recipe_category' and achievement.category:
            progress = UserProgress.objects.filter(
                user=user, 
                achievement_type=achievement.achievement_type,
                category=achievement.category
            ).first()
        else:
            progress = UserProgress.objects.filter(
                user=user, 
                achievement_type=achievement.achievement_type
            ).first()
        
        #if no progress found or requirement not met, continue to next achievement
        if not progress or progress.count < achievement.requirement_count:
            continue
            
        UserAchievement.objects.create(
            user=user,
            achievement=achievement
        )
        
        #create notification
        UserNotification.objects.create(
            user=user,
            title=f"New Achievement: {achievement.name}",
            message=f"Congratulations! You've earned the {achievement.name} achievement. {achievement.description}",
            notification_type='achievement'
        )
        
        #award points if theres a points reward
        if achievement.points_reward > 0:
            user_points = UserPoints.get_or_create_user_points(user)
            user_points.total_points += achievement.points_reward
            user_points.save()
            
            PointsTransaction.objects.create(
                user=user,
                points=achievement.points_reward,
                description=f"Achievement: {achievement.name}",
                transaction_type='achievement'
            )
            
            user_points.check_and_update_level()
            
            achievements_earned.append({
                'name': achievement.name,
                'points': achievement.points_reward
            })
        else:
            achievements_earned.append({
                'name': achievement.name,
                'points': 0
            })
    
    return achievements_earned


@login_required
def award_points_for_recipe(request, recipe_id, is_dataset=False, is_scraped=False):
    #Award points to a user for trying a recipe and record the transaction
    
    if is_scraped:
        from recipes.models import ScrapedRecipe
        recipe = get_object_or_404(ScrapedRecipe, pk=recipe_id)
        recipe_name = recipe.title
        already_tried = TriedRecipe.objects.filter(
            user=request.user, 
            scraped_recipe=recipe
        ).exists()
    elif is_dataset:
        recipe = get_object_or_404(DatasetRecipe, pk=recipe_id)
        recipe_name = recipe.name
        already_tried = TriedRecipe.objects.filter(
            user=request.user, 
            dataset_recipe=recipe
        ).exists()
    else:
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        recipe_name = recipe.title
        already_tried = TriedRecipe.objects.filter(
            user=request.user, 
            recipe=recipe
        ).exists()
    
    if already_tried:
        messages.info(request, "You've already tried this recipe!")
        return False, 0
    
    points, ingredient_count, breakdown = calculate_recipe_points(recipe, user=request.user)
    
    
    if is_scraped:
        bonus_points = 15  
        points += bonus_points
    
    if is_scraped:
        TriedRecipe.objects.create(
            user=request.user,
            scraped_recipe=recipe,
            points_earned=points
        )
    elif is_dataset:
        TriedRecipe.objects.create(
            user=request.user,
            dataset_recipe=recipe,
            points_earned=points
        )
    else:
        TriedRecipe.objects.create(
            user=request.user,
            recipe=recipe,
            points_earned=points
        )
    
    #update user's progress
    if is_scraped:
        update_user_progress(request.user, scraped_recipe=recipe)
    elif is_dataset:
        update_user_progress(request.user, dataset_recipe=recipe)
    else:
        update_user_progress(request.user, recipe=recipe)
    
    user_points = UserPoints.get_or_create_user_points(request.user)
    
    user_points.total_points += points
    user_points.save()
    
    transaction = PointsTransaction.objects.create(
        user=request.user,
        points=points,
        description=f"Tried recipe: {recipe_name}",
        transaction_type='recipe_tried'
    )
    
    if is_scraped:
        transaction.scraped_recipe = recipe
    elif is_dataset:
        transaction.dataset_recipe = recipe
    else:
        transaction.recipe = recipe
    
    transaction.save()
    
    leveled_up, new_level_data = user_points.check_and_update_level()
    
    achievements_earned = check_for_achievements(request.user)
    
   
    base_message = (f"You've tried '{recipe_name}'! You earned {points} points!")
    
    if is_scraped:
        base_message += f" (Including a {bonus_points} point bonus for trying an exclusive recipe!)"
    else:
        base_message += f" ({ingredient_count} ingredients × 2 + 10 base points)"
    
    # add tracked ingredients bonus information
    if breakdown['tracked_count'] > 0:
        tracked_message = (f"<br><b>BONUS:</b> You used {breakdown['tracked_count']} tracked ingredients "
                          f"(+{breakdown['tracked_bonus']} bonus points)!")
        base_message += tracked_message
    
    # add expiring ingredients bonus information
    if breakdown['expiration_bonus'] > 0:
        expiration_message = f"<br><b>EXPIRATION BONUS:</b> "
        
        for i, ing in enumerate(breakdown['expiring_ingredients']):
            if i > 0:
                expiration_message += ", "
            expiration_message += f"{ing['name']} ({ing['status']}, +{ing['bonus']} points)"
            
        base_message += expiration_message
    
    if leveled_up:
        base_message += f"<br><b>LEVEL UP!</b> You're now a {new_level_data['title']} (Level {new_level_data['level']})!"
        base_message += f"<br>New reward: {new_level_data['reward']}"
    
    if achievements_earned:
        base_message += "<br><b>Achievements Unlocked:</b>"
        for achievement in achievements_earned:
            if achievement['points'] > 0:
                base_message += f"<br>• {achievement['name']} (+{achievement['points']} points)"
            else:
                base_message += f"<br>• {achievement['name']}"
    
    messages.success(request, base_message)
    
    return True, points




@login_required
def mark_recipe_as_tried(request, pk):
    try:
        recipe = Recipe.objects.get(pk=pk)

        print(f"Recipe: {recipe.title}")
        print(f"Ingredients raw: {recipe.ingredients}")
        try:
            ingredients_list = json.loads(recipe.ingredients) if isinstance(recipe.ingredients, str) else recipe.ingredients
            print(f"Parsed ingredients: {ingredients_list}")
            print(f"Ingredient count: {len(ingredients_list)}")
        except Exception as e:
            print(f"Error parsing ingredients: {str(e)}")
        
        # check if recipe is already marked as tried
        if TriedRecipe.objects.filter(user=request.user, recipe=recipe).exists():
            messages.info(request, "You've already marked this recipe as tried!")
            return redirect('recipes-detail', pk=pk)
        
        #check for matching tracked ingredients
        from recipes.models import TrackedIngredient
        from recipes.utils import normalize_ingredient_name
        
        recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe.get_ingredients()]
        tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)
        
        matched_ingredients = []
        for tracked in tracked_ingredients:
            normalized_tracked = normalize_ingredient_name(tracked.ingredient_name)
            for recipe_ing in recipe_ingredients:
                if (normalized_tracked in recipe_ing or recipe_ing in normalized_tracked or
                    normalized_tracked.split()[0] in recipe_ing or recipe_ing.split()[0] in normalized_tracked):
                    matched_ingredients.append(tracked)
                    break
        
        #if there are matching ingredients show confirmation dialog
        if matched_ingredients and request.method == 'GET':
            context = {
                'recipe': recipe,
                'matched_ingredients': matched_ingredients,
                'confirm_url': reverse('mark-recipe-tried', kwargs={'pk': pk})
            }
            return render(request, 'recipes/confirm_use_ingredients.html', context)
        
        points_to_award, ingredient_count, breakdown = calculate_recipe_points(recipe, user=request.user)
        
        if request.method == 'POST' and 'confirm' in request.POST and matched_ingredients:
            # remove matched ingredients from tracking
            for ingredient in matched_ingredients:
                ingredient.delete()
            
            ingredients_message = ", ".join([ing.ingredient_name for ing in matched_ingredients])
            messages.success(request, f"The following ingredients were used and removed from tracking: {ingredients_message}")
        
        TriedRecipe.objects.create(
            user=request.user,
            recipe=recipe,
            points_earned=points_to_award
        )
        
        update_user_progress(request.user, recipe=recipe)
        
        user_points = UserPoints.get_or_create_user_points(request.user)
        user_points.total_points += points_to_award
        user_points.save()
        
        PointsTransaction.objects.create(
            user=request.user,
            points=points_to_award,
            description=f"Tried recipe: {recipe.title} ({ingredient_count} ingredients)",
            transaction_type="recipe_tried",
            recipe=recipe
        )
        
        leveled_up, level_data = user_points.check_and_update_level()
        
        success_message = f"Recipe marked as tried! You earned {points_to_award} points! ({ingredient_count} ingredients × 2 + 10 base points)"

        if breakdown['tracked_count'] > 0:
            actual_bonus = breakdown['tracked_count'] * 2
            tracked_message = f"<br><b>BONUS:</b> You used {breakdown['tracked_count']} tracked ingredients (+{actual_bonus} bonus points)"
            success_message += tracked_message

        if breakdown['expiration_bonus'] > 0:
            expiration_message = "<br><b>EXPIRATION BONUS:</b> "
            expiring_items = []
            
            for ing in breakdown['expiring_ingredients']:
                expiring_items.append(f"{ing['name']} ({ing['status']}, +{ing['bonus']} points)")
            
            expiration_message += ", ".join(expiring_items)
            success_message += expiration_message
        
        if leveled_up:
            success_message += f"<br><br><b>LEVEL UP!</b> You're now a {level_data['title']} (Level {level_data['level']})!"
            if 'reward' in level_data:
                success_message += f"<br>New reward: {level_data['reward']}"
        
        achievements_earned = check_for_achievements(request.user)
        if achievements_earned:
            success_message += "<br><br><b>Achievements Unlocked:</b>"
            for achievement in achievements_earned:
                if achievement['points'] > 0:
                    success_message += f"<br>• {achievement['name']} (+{achievement['points']} points)"
                else:
                    success_message += f"<br>• {achievement['name']}"
        
        messages.success(request, success_message)
        return redirect('recipes-detail', pk=pk)
    
    except Recipe.DoesNotExist:
        messages.error(request, "Recipe not found!")
        return redirect('recipes-home')


@login_required
def mark_dataset_recipe_as_tried(request, pk):
    try:
        recipe = DatasetRecipe.objects.get(pk=pk)
        
        if TriedRecipe.objects.filter(user=request.user, dataset_recipe=recipe).exists():
            messages.info(request, "You've already marked this recipe as tried!")
            return redirect('dataset-recipe-detail', pk=pk)
        
        from recipes.models import TrackedIngredient
        from recipes.utils import normalize_ingredient_name
        
        recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe.get_ingredients()]
        tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)
        
        matched_ingredients = []
        for tracked in tracked_ingredients:
            normalized_tracked = normalize_ingredient_name(tracked.ingredient_name)
            for recipe_ing in recipe_ingredients:
                if (normalized_tracked in recipe_ing or recipe_ing in normalized_tracked or
                    normalized_tracked.split()[0] in recipe_ing or recipe_ing.split()[0] in normalized_tracked):
                    matched_ingredients.append(tracked)
                    break
        
        if matched_ingredients and request.method == 'GET':
            if hasattr(recipe, 'title'):
                recipe_name = recipe.title
            else:
                recipe_name = recipe.name
                
            recipe.title = recipe_name
            
            context = {
                'recipe': recipe,
                'matched_ingredients': matched_ingredients,
                'confirm_url': reverse('mark-dataset-recipe-tried', kwargs={'pk': pk})
            }
            return render(request, 'recipes/confirm_use_ingredients.html', context)
        
        points_to_award, ingredient_count, breakdown = calculate_recipe_points(recipe, user=request.user)
        
        if request.method == 'POST' and 'confirm' in request.POST and matched_ingredients:
            for ingredient in matched_ingredients:
                ingredient.delete()
            
            ingredients_message = ", ".join([ing.ingredient_name for ing in matched_ingredients])
            messages.success(request, f"The following ingredients were used and removed from tracking: {ingredients_message}")
        
        TriedRecipe.objects.create(
            user=request.user,
            dataset_recipe=recipe,
            points_earned=points_to_award
        )
        
        update_user_progress(request.user, dataset_recipe=recipe)
        
        user_points = UserPoints.get_or_create_user_points(request.user)
        user_points.total_points += points_to_award
        user_points.save()
        
        PointsTransaction.objects.create(
            user=request.user,
            points=points_to_award,
            description=f"Tried recipe: {recipe.name} ({ingredient_count} ingredients)",
            transaction_type="recipe_tried",
            dataset_recipe=recipe
        )
        
        leveled_up, level_data = user_points.check_and_update_level()
        
        success_message = f"Recipe marked as tried! You earned {points_to_award} points! ({ingredient_count} ingredients × 2 + 10 base points)"

        if breakdown['tracked_count'] > 0:
            actual_bonus = breakdown['tracked_count'] * 2
            tracked_message = f"<br><b>BONUS:</b> You used {breakdown['tracked_count']} tracked ingredients (+{actual_bonus} bonus points)"
            success_message += tracked_message

        if breakdown['expiration_bonus'] > 0:
            expiration_message = "<br><b>EXPIRATION BONUS:</b> "
            expiring_items = []
            
            for ing in breakdown['expiring_ingredients']:
                expiring_items.append(f"{ing['name']} ({ing['status']}, +{ing['bonus']} points)")
            
            expiration_message += ", ".join(expiring_items)
            success_message += expiration_message
        
        if leveled_up:
            success_message += f"<br><br><b>LEVEL UP!</b> You're now a {level_data['title']} (Level {level_data['level']})!"
            if 'reward' in level_data:
                success_message += f"<br>New reward: {level_data['reward']}"
        
        achievements_earned = check_for_achievements(request.user)
        if achievements_earned:
            success_message += "<br><br><b>Achievements Unlocked:</b>"
            for achievement in achievements_earned:
                if achievement['points'] > 0:
                    success_message += f"<br>• {achievement['name']} (+{achievement['points']} points)"
                else:
                    success_message += f"<br>• {achievement['name']}"
        
        messages.success(request, success_message)
        return redirect('dataset-recipe-detail', pk=pk)
    
    except DatasetRecipe.DoesNotExist:
        messages.error(request, "Recipe not found!")
        return redirect('recipes-home')

@login_required
def points_history(request):
    #view for displaying a user's points history
    transactions = PointsTransaction.objects.filter(user=request.user).order_by('-created_at')
    user_points = UserPoints.get_or_create_user_points(request.user)
    
    level_data = user_points.get_level_data()
    progress_percent = user_points.calculate_progress()
    
    context = {
        'transactions': transactions,
        'total_points': user_points.total_points,
        'current_level': level_data['current'],
        'next_level': level_data['next'],
        'progress_percent': progress_percent,
    }
    
    return render(request, 'users/points_history.html', context)

@login_required
def notifications_view(request):
    #view for user notifications
    
    if request.method == 'POST':
        if 'mark_all' in request.POST:
            UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read")
            return redirect('notifications')
            
        notification_id = request.POST.get('notification_id')
        if notification_id:
            try:
                notification = UserNotification.objects.get(id=notification_id, user=request.user)
                notification.is_read = True
                notification.save()
                messages.success(request, "Notification marked as read")
            except UserNotification.DoesNotExist:
                messages.error(request, "Notification not found")
            
            return redirect('notifications')
    
    unread_notifications = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')
    
    read_notifications = UserNotification.objects.filter(
        user=request.user,
        is_read=True
    ).order_by('-created_at')[:10]  
    
    context = {
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
        'title': 'Notifications'
    }
    
    return render(request, 'users/notifications.html', context)

@login_required
def create_initial_achievements(request):
    #Create initial achievements (admin only)
    if not request.user.is_superuser:
        messages.error(request, "You don't have permission to do this.")
        return redirect('profile')
    
    initial_achievements = [
        # Recipes tried achievements
        {
            'name': 'First Steps',
            'description': 'Try your first recipe',
            'icon': 'fa-utensils',
            'points_reward': 20,
            'achievement_type': 'recipes_tried',
            'requirement_count': 1,
        },
        {
            'name': 'Kitchen Explorer',
            'description': 'Try 5 different recipes',
            'icon': 'fa-compass',
            'points_reward': 30,
            'achievement_type': 'recipes_tried',
            'requirement_count': 5,
        },
        {
            'name': 'Cooking Enthusiast',
            'description': 'Try 10 different recipes',
            'icon': 'fa-fire',
            'points_reward': 50,
            'achievement_type': 'recipes_tried',
            'requirement_count': 10,
        },
        {
            'name': 'Recipe Master',
            'description': 'Try 25 different recipes',
            'icon': 'fa-award',
            'points_reward': 100,
            'achievement_type': 'recipes_tried',
            'requirement_count': 25,
        },
        
        {
            'name': 'Breakfast Champion',
            'description': 'Try 5 breakfast recipes',
            'icon': 'fa-sun',
            'points_reward': 40,
            'achievement_type': 'recipe_category',
            'requirement_count': 5,
            'category': 'breakfast',
        },
        {
            'name': 'Lunch Master',
            'description': 'Try 5 lunch recipes',
            'icon': 'fa-clock',
            'points_reward': 40,
            'achievement_type': 'recipe_category',
            'requirement_count': 5,
            'category': 'lunch',
        },
        {
            'name': 'Dinner Connoisseur',
            'description': 'Try 5 dinner recipes',
            'icon': 'fa-moon',
            'points_reward': 40,
            'achievement_type': 'recipe_category',
            'requirement_count': 5,
            'category': 'dinner',
        },
        {
            'name': 'Sweet Tooth',
            'description': 'Try 5 dessert recipes',
            'icon': 'fa-cookie',
            'points_reward': 40,
            'achievement_type': 'recipe_category',
            'requirement_count': 5,
            'category': 'dessert',
        },
        {
            'name': 'Health Enthusiast',
            'description': 'Try the first healthy recipe',
            'icon': 'fa-carrot',
            'points_reward': 25,
            'achievement_type': 'recipe_category',
            'requirement_count': 1,
            'category': 'healthy',
        },
        {
            'name': 'Veggie Lover',
            'description': 'Try 3 vegetarian recipes',
            'icon': 'fa-leaf',
            'points_reward': 35,
            'achievement_type': 'recipe_category',
            'requirement_count': 3,
            'category': 'vegetarian',
        },
    ]
    
    # Create achievements
    for achievement_data in initial_achievements:
        Achievement.objects.get_or_create(
            name=achievement_data['name'],
            defaults=achievement_data
        )
    
    messages.success(request, f"Created {len(initial_achievements)} achievements.")
    return redirect('admin:index')

@login_required
def achievements_view(request):
    #View for user achievements
    # Get user's earned achievements
    earned_achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement').order_by('-earned_at')
    
    # Get achievements the user hasn't earned yet
    remaining_achievements = Achievement.objects.exclude(
        id__in=earned_achievements.values_list('achievement_id', flat=True)
    ).order_by('name')
    
    achievement_progress = []
    
    for achievement in remaining_achievements:
        if achievement.achievement_type == 'recipe_category' and achievement.category:
            progress_obj, created = UserProgress.objects.get_or_create(
                user=request.user,
                achievement_type=achievement.achievement_type,
                category=achievement.category
            )
        else:
            progress_obj, created = UserProgress.objects.get_or_create(
                user=request.user,
                achievement_type=achievement.achievement_type,
                category=None
            )
        
        if achievement.requirement_count > 0:
            percent = min(round((progress_obj.count / achievement.requirement_count) * 100), 100)
        else:
            percent = 0
            
        achievement_progress.append({
            'achievement_id': achievement.id,  
            'current': progress_obj.count,
            'requirement': achievement.requirement_count,
            'percent': percent
        })
    
    print(f"Debug: {len(earned_achievements)} earned achievements")
    print(f"Debug: {len(remaining_achievements)} remaining achievements")
    print(f"Debug: {len(achievement_progress)} progress items")
    
    if achievement_progress:
        first_progress = achievement_progress[0]
        print(f"First progress item: achievement_id={first_progress['achievement_id']}, current={first_progress['current']}, percent={first_progress['percent']}")
    
    context = {
        'earned_achievements': earned_achievements,
        'remaining_achievements': remaining_achievements,
        'achievement_progress': achievement_progress,
        'title': 'My Achievements'
    }
    
    return render(request, 'users/achievements.html', context)


def leaderboards(request):
    #view for displaying various leaderboards
    #Get the leaderboard filter type
    leaderboard_type = request.GET.get('type', 'points')
    time_period = request.GET.get('period', 'all')
    
    user_points_query = UserPoints.objects.select_related('user').all()
    
    if leaderboard_type == 'achievements':
        from django.db.models import Count
        users_with_achievements = UserAchievement.objects.values('user__username', 'user_id') \
                                                    .annotate(achievement_count=Count('id')) \
                                                    .order_by('-achievement_count')[:50]
        
        #fetch UserPoints for these users to get levels
        user_ids = [entry['user_id'] for entry in users_with_achievements]
        user_points_map = {up.user_id: up for up in UserPoints.objects.filter(user_id__in=user_ids)}
        
        for entry in users_with_achievements:
            user_points = user_points_map.get(entry['user_id'])
            if user_points:
                entry['level'] = user_points.current_level
                entry['level_title'] = CHEF_LEVELS[user_points.current_level]['title']
            else:
                entry['level'] = 1
                entry['level_title'] = 'Novice Chef'
        
        context = {
            'leaderboard_type': 'achievements',
            'time_period': time_period,
            'leaderboard_entries': users_with_achievements,
            'user_rank': None, 
            'title': 'Achievement Leaderboard'
        }
        
        if request.user.is_authenticated:
            user_achievement_count = UserAchievement.objects.filter(user=request.user).count()
            user_rank = UserAchievement.objects.values('user') \
                                      .annotate(count=Count('id')) \
                                      .filter(count__gt=user_achievement_count).count() + 1
            context['user_rank'] = user_rank
            context['user_achievement_count'] = user_achievement_count
    
    elif leaderboard_type == 'recipes_tried':
        # count recipes tried per user
        from django.db.models import Count
        users_with_recipes = TriedRecipe.objects.values('user__username', 'user_id') \
                                             .annotate(recipes_count=Count('id')) \
                                             .order_by('-recipes_count')[:50]
        
        # fetch UserPoints for these users to get levels
        user_ids = [entry['user_id'] for entry in users_with_recipes]
        user_points_map = {up.user_id: up for up in UserPoints.objects.filter(user_id__in=user_ids)}
        
        # combine the data
        for entry in users_with_recipes:
            user_points = user_points_map.get(entry['user_id'])
            if user_points:
                entry['level'] = user_points.current_level
                entry['level_title'] = CHEF_LEVELS[user_points.current_level]['title']
            else:
                entry['level'] = 1
                entry['level_title'] = 'Novice Chef'
        
        context = {
            'leaderboard_type': 'recipes_tried',
            'time_period': time_period,
            'leaderboard_entries': users_with_recipes,
            'user_rank': None,  
            'title': 'Recipes Tried Leaderboard'
        }
        
        # find current user's rank if authenticated
        if request.user.is_authenticated:
            user_recipes_count = TriedRecipe.objects.filter(user=request.user).count()
            user_rank = TriedRecipe.objects.values('user') \
                                  .annotate(count=Count('id')) \
                                  .filter(count__gt=user_recipes_count).count() + 1
            context['user_rank'] = user_rank
            context['user_recipes_count'] = user_recipes_count
    
    else:
        #get top users by points
        top_users = user_points_query.order_by('-total_points')[:50]
        
        context = {
            'leaderboard_type': 'points',
            'time_period': time_period,
            'leaderboard_entries': top_users,
            'user_rank': None, 
            'title': 'Points Leaderboard'
        }
        
    if leaderboard_type == 'points':
        #get top users by points
        top_users = UserPoints.objects.select_related('user').order_by('-total_points')[:50]
        context['leaderboard_entries'] = top_users
        
        #find current users rank if authenticated
        if request.user.is_authenticated:
            try:
                user_points_obj = UserPoints.objects.get(user=request.user)
                context['user_points'] = user_points_obj.total_points  
                user_rank = UserPoints.objects.filter(total_points__gt=user_points_obj.total_points).count() + 1
                context['user_rank'] = user_rank
            except UserPoints.DoesNotExist:
                context['user_points'] = 0
                context['user_rank'] = None
    
    return render(request, 'users/leaderboards.html', context)


@login_required
def recipe_try_confirm(request, pk):
    #Show confirmation page for trying a recipe with tracked ingredients
    try:
        recipe = Recipe.objects.get(pk=pk)
        
        tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)
        
        recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe.get_ingredients()]
        
        matched_ingredients = []
        for tracked in tracked_ingredients:
            normalized_tracked = normalize_ingredient_name(tracked.ingredient_name)
            for recipe_ing in recipe_ingredients:
                if (normalized_tracked in recipe_ing or recipe_ing in normalized_tracked or
                    normalized_tracked.split()[0] in recipe_ing or recipe_ing.split()[0] in normalized_tracked):
                    matched_ingredients.append(tracked)
                    break
        
        if not matched_ingredients:
            return redirect('mark-recipe-tried', pk=pk)
        
        context = {
            'recipe': recipe,
            'matched_ingredients': matched_ingredients,
            'form_action': reverse('mark-recipe-tried', kwargs={'pk': pk}),
            'cancel_url': reverse('recipes-detail', kwargs={'pk': pk}),
            'replace_history': True  

        }
        return render(request, 'recipes/confirm_use_ingredients.html', context)
    
    except Recipe.DoesNotExist:
        messages.error(request, "Recipe not found!")
        return redirect('recipes-home')

@login_required
def dataset_recipe_try_confirm(request, pk):
    #Show confirmation page for trying a dataset recipe with tracked ingredients
    try:
        recipe = DatasetRecipe.objects.get(pk=pk)
        
        tracked_ingredients = TrackedIngredient.objects.filter(user=request.user)
        
        recipe_ingredients = [normalize_ingredient_name(ing) for ing in recipe.get_ingredients()]
        
        matched_ingredients = []
        for tracked in tracked_ingredients:
            normalized_tracked = normalize_ingredient_name(tracked.ingredient_name)
            for recipe_ing in recipe_ingredients:
                if (normalized_tracked in recipe_ing or recipe_ing in normalized_tracked or
                    normalized_tracked.split()[0] in recipe_ing or recipe_ing.split()[0] in normalized_tracked):
                    matched_ingredients.append(tracked)
                    break
        
        if not matched_ingredients:
            return redirect('mark-dataset-recipe-tried', pk=pk)
        
        if hasattr(recipe, 'title'):
            recipe_name = recipe.title
        else:
            recipe_name = recipe.name
            
        recipe.title = recipe_name
        
        context = {
            'recipe': recipe,
            'matched_ingredients': matched_ingredients,
            'form_action': reverse('mark-dataset-recipe-tried', kwargs={'pk': pk}),
            'cancel_url': reverse('dataset-recipe-detail', kwargs={'pk': pk}),
            'replace_history': True  

        }
        return render(request, 'recipes/confirm_use_ingredients.html', context)
    
    except DatasetRecipe.DoesNotExist:
        messages.error(request, "Recipe not found!")
        return redirect('recipes-home')
    

@login_required
def unlocked_recipes(request):
    #View for displaying a user's unlocked recipe rewards
    from users.models import UnlockedRecipeReward
    
    unlocked_recipes = UnlockedRecipeReward.objects.filter(
        user=request.user
    ).select_related('recipe').order_by('-unlocked_at')
    
    unviewed = unlocked_recipes.filter(viewed=False)
    for unviewed_recipe in unviewed:
        unviewed_recipe.viewed = True
        unviewed_recipe.save()
    
    user_points = UserPoints.get_or_create_user_points(request.user)
    level_data = user_points.get_level_data()
    
    context = {
        'unlocked_recipes': unlocked_recipes,
        'user_points': user_points,
        'current_level': level_data['current'],
        'next_level': level_data['next'],
        'title': 'My Unlocked Recipes'
    }
    
    return render(request, 'users/unlocked_recipes.html', context)
