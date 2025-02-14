from django.urls import path
from . import views

urlpatterns = [
    path('', views.RecipeListView.as_view(), name="recipes-home"),
    path('recipe/create/', views.RecipeCreateView.as_view(), name="recipes-create"),
    path('recipe/<int:pk>/', views.RecipeDetailView.as_view(), name="recipes-detail"),
    path('recipe/<int:pk>/update/', views.RecipeUpdateView.as_view(), name="recipes-update"),
    path('recipe/<int:pk>/delete/', views.RecipeDeleteView.as_view(), name="recipes-delete"),
    path('about/', views.about, name="recipes-about"),
    path('recipe/<int:pk>/save/', views.toggle_save_recipe, name="recipe-save"),
    path('profile/', views.profile, name='user-profile'),

    path('shopping-list/', views.shopping_list, name="shopping_list"),  
    path('add-item/', views.add_item, name="add_item"),  
    path('remove-item/<int:item_id>/', views.remove_item, name="remove_item"),
    path('track-ingredient/', views.track_ingredient, name="track_ingredient"),  
    path('remove-tracked-ingredient/<int:item_id>/', views.remove_tracked_ingredient, name="remove_tracked_ingredient"),  

    path('match-recipes/', views.match_ingredients_with_recipes, name="match_recipes"),  

    path('scrape-recipes/', views.scrape_recipes, name="scrape_recipes"),  
    path('ingredient-tracking/', views.ingredient_tracking, name="ingredient_tracking"),
    path('', views.home, name='recipes-home'),
    # urls.py
    path('dataset-recipe/<int:pk>/', views.dataset_recipe_detail, name='dataset-recipe-detail'),



]