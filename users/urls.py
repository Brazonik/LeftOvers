from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='user-register'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='user-login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='user-logout'),
    
    path('profile/', views.profile, name='profile'),  
    
    path('notifications/', views.notifications_view, name='notifications'),
    path('achievements/', views.achievements_view, name='achievements'),
    path('points-history/', views.points_history, name='points-history'),
    
    path('create-initial-achievements/', views.create_initial_achievements, name='create-initial-achievements'),
    
    path('mark-recipe-tried/<int:pk>/', views.mark_recipe_as_tried, name='mark-recipe-tried'),
    path('mark-dataset-recipe-tried/<int:pk>/', views.mark_dataset_recipe_as_tried, name='mark-dataset-recipe-tried'),
    path('leaderboards/', views.leaderboards, name='leaderboards'),
    path('unlocked-recipes/', views.unlocked_recipes, name='unlocked-recipes'),


]