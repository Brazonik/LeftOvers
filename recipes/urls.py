from django.shortcuts import redirect
from django.urls import path
from . import views
from users.views import recipe_try_confirm, dataset_recipe_try_confirm

urlpatterns = [
    path('recipe/create/', views.RecipeCreateView.as_view(), name="recipes-create"),
    path('recipe/<int:pk>/', views.RecipeDetailView.as_view(), name="recipes-detail"),
    path('recipe/<int:pk>/update/', views.RecipeUpdateView.as_view(), name="recipes-update"),
    path('recipe/<int:pk>/delete/', views.RecipeDeleteView.as_view(), name="recipes-delete"),
    path('about/', views.about, name="recipes-about"),
    path('recipe/<int:pk>/save/', views.toggle_save_recipe, name="recipe-save"),
    
    path('shopping-list/', views.shopping_list, name="shopping_list"),  
    path('add-item/', views.add_item, name="add_item"),  
    path('remove-item/<int:item_id>/', views.remove_item, name="remove_item"),
    path('track-ingredient/', views.track_ingredient, name="track_ingredient"),  

    path('match-recipes/', views.match_ingredients_with_recipes, name="match_recipes"),  
    path('scrape-recipes/', views.scrape_recipes, name="scrape_recipes"),  
    
    path('ingredient-tracking/', views.ingredient_tracking, name="ingredient_tracking"),
    path('', views.home, name='recipes-home'),  
    
    
    path('dataset-recipe/<int:pk>/', views.dataset_recipe_detail, name='dataset-recipe-detail'),
    path('remove-tracked-ingredient/<int:item_id>/', views.remove_tracked_ingredient, name='remove_tracked_ingredient'),
    path('add-recipe-to-shopping-list/<int:recipe_id>/', views.add_recipe_to_shopping_list, name='add_recipe_to_shopping_list'),
    path('save-dataset-recipe/<int:recipe_id>/', views.save_dataset_recipe, name='save_dataset_recipe'),
    path('recipe/<int:pk>/try/', lambda req, pk: redirect('mark-recipe-tried', pk=pk)),
    path('dataset-recipe/<int:pk>/try/', lambda req, pk: redirect('mark-dataset-recipe-tried', pk=pk)),
    path('recipe/<int:pk>/try/confirm/', recipe_try_confirm, name='recipe-try-confirm'),
    path('dataset-recipe/<int:pk>/try/confirm/', dataset_recipe_try_confirm, name='dataset-recipe-try-confirm'),
    path('scraped-recipe/<int:recipe_id>/', views.scraped_recipe_detail, name='scraped-recipe-detail'),
    path('scraped-recipe/<int:recipe_id>/', views.scraped_recipe_detail, name='scraped-recipe-detail'),
    path('mark-scraped-recipe-tried/<int:recipe_id>/', views.mark_scraped_recipe_as_tried, name='mark-scraped-recipe-tried'),
    path('add-scraped-recipe-to-shopping-list/<int:recipe_id>/', views.add_scraped_recipe_to_shopping_list, name='add-scraped-recipe-to-shopping-list'),

    path('recipe-shop/', views.recipe_shop, name='recipe-shop'),
    path('purchase-recipe/<int:recipe_id>/', views.purchase_recipe, name='purchase-recipe'),
    path('purchased-recipes/', views.purchased_recipes, name='purchased-recipes'),
    path('purchased-recipe/<int:recipe_id>/', views.purchased_recipe_detail, name='purchased-recipe-detail'),
    path('submit-recipe/', views.submit_recipe_for_review, name='submit-recipe-for-review'),
    path('my-submissions/', views.user_submissions, name='user-submissions'),
    path('add-recipe-to-shopping-list/<int:recipe_id>/', views.add_recipe_to_shopping_list, name='add-recipe-to-shopping-list'),
    path('mark-recipe-tried/<int:recipe_id>/', views.mark_recipe_tried, name='mark-recipe-tried'),
    path('purchase-random-recipe/', views.purchase_random_recipe, name='purchase-random-recipe'),
    path('purchase-random-recipe/<str:difficulty>/', views.purchase_random_recipe, name='purchase-random-recipe-difficulty'),
    path('purchase-random-recipe/', views.purchase_random_recipe, name='purchase-random-recipe'),
    path('clear-shopping-list/', views.clear_shopping_list, name='clear_shopping_list'),
    path('track-shopping-list-items/', views.track_shopping_list_items, name='track_shopping_list_items'),
    path('mark-used/<int:item_id>/', views.mark_used, name='mark_used'),
]