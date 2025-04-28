# Add to users/models.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from recipes.models import Recipe, DatasetRecipe, TriedRecipe

# Chef Level Titles and Rewards
CHEF_LEVELS = [
    {
        'level': 1,
        'title': 'New',
        'points_required': 0,
        'reward': 'Welcome to the cooking community!',
        'reward_description': 'You\'ve taken your first steps into the world of cooking. Here is a free recipe',
    },
    {
        'level': 2,
        'title': 'Beginner',
        'points_required': 100,
        'reward': 'New Recipe',
        'reward_description': 'Enjoy a new recipe to try out!',
    },
    {
        'level': 3,
        'title': 'Home Cook',
        'points_required': 200,
        'reward': 'New recipe',
        'reward_description': 'New recipe to try out!',
    },
    {
        'level': 4,
        'title': 'Novice',
        'points_required': 300,
        'reward': 'New recipe',
        'reward_description': ' How about an extra recipe',
    },
    {
        'level': 5,
        'title': 'line cook',
        'points_required': 400,
        'reward': 'New recipe',
        'reward_description': 'You look like you want to try something new',
    },
    {
        'level': 6,
        'title': 'sous chef',
        'points_required': 500,
        'reward': 'New recipe',
        'reward_description': ' Here is something no one else gets to try',
    },
    {
        'level': 7,
        'title': 'Gourmet Chef',
        'points_required': 600,
        'reward': 'New recipe',
        'reward_description': ' Treat your family and friends',
    },
    {
        'level': 8,
        'title': 'Executive Chef',
        'points_required': 700,
        'reward': 'New recipe',
        'reward_description': ' You are now a pro chef, try this recipe',
    },
    {
        'level': 9,
        'title': 'expert',
        'points_required': 800,
        'reward': 'New recipe',
        'reward_description': ' You have improved a lot, here is another recipe',
    },
    {
        'level': 10,
        'title': 'Master Chef',
        'points_required': 900,
        'reward': 'New recipe',
        'reward_description': 'Maybe this will cleanse your hunger',
    },
    {
        'level': 11,
        'title': 'Executive Chef',
        'points_required': 1000,
        'reward': 'New recipe',
        'reward_description': ' You look like you could use something new, try this recipe'
    },
    {
        'level': 12,
        'title': 'Culinary Master',
        'points_required': 1500,
        'reward': 'New recipe',
        'reward_description': 'Just because we love you, try this recipe'
    },
    {
        'level': 13,
        'title': 'Legendary Chef',
        'points_required': 2000,
        'reward': 'New recipe',
        'reward_description': 'Here is your final challenge, try this recipe'
    },
]

class UserPoints(models.Model):
    #track total points for users
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points_profile')
    total_points = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    current_level = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.user.username}'s Points: {self.total_points}"
    
    @classmethod
    def get_or_create_user_points(cls, user):
        user_points, created = cls.objects.get_or_create(user=user)
        return user_points
    
    def get_level_data(self):
        #get the current level data for this user
        #find the highest level the user has reached
        current_level_data = CHEF_LEVELS[0]  # Default to first level
        next_level_data = None
        
        for i, level_data in enumerate(CHEF_LEVELS):
            if self.total_points >= level_data['points_required']:
                current_level_data = level_data
                if i < len(CHEF_LEVELS) - 1:
                    next_level_data = CHEF_LEVELS[i + 1]
            else:
                if next_level_data is None:
                    next_level_data = level_data
                break
        
        return {
            'current': current_level_data,
            'next': next_level_data
        }
    
    def calculate_progress(self):
        level_data = self.get_level_data()
        current = level_data['current']
        next_level = level_data['next']
        
        if next_level is None:  
            return 100
        
        points_in_current_level = self.total_points - current['points_required']
        points_needed_for_next = next_level['points_required'] - current['points_required']

        if points_needed_for_next == 0:
            return 100
        
        progress = (points_in_current_level / points_needed_for_next) * 100
        
        return min(round(progress), 100)  
    
    def check_and_update_level(self):
        
        #check if user has leveled up and update accordingly.
        #award a random scraped recipe as a reward.
        
        from recipes.models import ScrapedRecipe
        
        old_level = self.current_level
        level_data = self.get_level_data()
        new_level = level_data['current']['level']
        
        if new_level > old_level:
            #user has leveled up
            self.current_level = new_level
            self.save()
            
            #award a random recipe reward
            reward_recipe = None
            
            #get already unlocked recipe IDs for this user
            from users.models import UnlockedRecipeReward
            unlocked_recipe_ids = UnlockedRecipeReward.objects.filter(
                user=self.user
            ).values_list('recipe_id', flat=True)
            
            #get a random recipe that the user hasn't unlocked yet
            available_recipes = ScrapedRecipe.objects.exclude(id__in=unlocked_recipe_ids)
            
            if available_recipes.exists():
                #get a random recipe
                reward_recipe = available_recipes.order_by('?').first()
                
                #create the unlocked recipe record
                UnlockedRecipeReward.objects.create(
                    user=self.user,
                    recipe=reward_recipe,
                    for_level=new_level
                )
            
            #create notification message
            base_message = f"Congratulations! You've reached level {new_level} and earned: {level_data['current']['reward']}"
            
            if reward_recipe:
                base_message += f"\n\nAs a special bonus, you've unlocked a new recipe: '{reward_recipe.title}'! Check your profile to view it."
            
            #create notification
            UserNotification.objects.create(
                user=self.user,
                title=f"Level Up! You're now a {level_data['current']['title']}",
                message=base_message,
                notification_type='level_up'
            )
            
            return True, level_data['current']
        
        return False, None

class PointsTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.IntegerField()
    description = models.CharField(max_length=255)
    transaction_type = models.CharField(max_length=50)  
    created_at = models.DateTimeField(auto_now_add=True)
    recipe = models.ForeignKey('recipes.Recipe', null=True, blank=True, on_delete=models.SET_NULL)
    dataset_recipe = models.ForeignKey('recipes.DatasetRecipe', null=True, blank=True, on_delete=models.SET_NULL)
    scraped_recipe = models.ForeignKey('recipes.ScrapedRecipe', null=True, blank=True, on_delete=models.SET_NULL)  
    achievement = models.ForeignKey('Achievement', null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        ordering = ['-created_at']

#achievement/Badge system
class Achievement(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="CSS class for the icon")
    points_reward = models.IntegerField(default=0)
    achievement_type = models.CharField(
        max_length=50,
        choices=[
            ('recipes_tried', 'Recipes Tried'),
            ('recipe_category', 'Recipe Category'),
            ('points_milestone', 'Points Milestone'),
            ('consecutive_days', 'Consecutive Days'),
            ('other', 'Other')
        ]
    )
    requirement_count = models.IntegerField(default=1, help_text="Number required to earn this achievement")
    category = models.CharField(max_length=50, blank=True, null=True, help_text="Category for recipe_category type achievements")
    
    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    #tracks achievements earned by users
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
    
    def __str__(self):
        return f"{self.user.username} earned {self.achievement.name}"

class UserProgress(models.Model):
    #tracks user progress toward achievements
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievement_progress')
    achievement_type = models.CharField(max_length=50)
    category = models.CharField(max_length=50, blank=True, null=True)
    count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'achievement_type', 'category']
    
    def __str__(self):
        if self.category:
            return f"{self.user.username}'s progress: {self.count} {self.achievement_type} in {self.category}"
        return f"{self.user.username}'s progress: {self.count} {self.achievement_type}"

class UserNotification(models.Model):
    #model for storing user notifications
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='info')  
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"

#create UserPoints profile when a user is created
@receiver(post_save, sender=User)
def create_user_points(sender, instance, created, **kwargs):
    if created:
        UserPoints.objects.create(user=instance)


class UnlockedRecipeReward(models.Model):
    
    #tracks scraped recipes that users have unlocked as rewards for leveling up
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocked_recipes')
    recipe = models.ForeignKey('recipes.ScrapedRecipe', on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    for_level = models.IntegerField(help_text="The level this recipe was unlocked at")
    viewed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'recipe']
        ordering = ['-unlocked_at']
    
    def __str__(self):
        return f"{self.user.username} unlocked {self.recipe.title} at level {self.for_level}"