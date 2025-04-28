from django import forms
from .models import Recipe
import json

#recipe Form for normal recipe creation
class RecipeForm(forms.ModelForm):
    class Meta:
        model = Recipe
        fields = [
            'title',
            'description',
            'ingredients',
            'instructions',
            'prep_time',
            'cook_time',
            'servings',
            'calories',
            'fat',
            'carbs',
            'protein',
            'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe your recipe'}),
            'ingredients': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter ingredients, one per line'}),
            'instructions': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Enter step-by-step instructions'}),
            'prep_time': forms.TextInput(attrs={'placeholder': 'e.g., 15 (in minutes)'}),
            'cook_time': forms.TextInput(attrs={'placeholder': 'e.g., 30 (in minutes)'}),
            'calories': forms.NumberInput(attrs={'placeholder': 'e.g., 350'}),
            'fat': forms.NumberInput(attrs={'placeholder': 'e.g., 12', 'step': '0.1'}),
            'carbs': forms.NumberInput(attrs={'placeholder': 'e.g., 45', 'step': '0.1'}),
            'protein': forms.NumberInput(attrs={'placeholder': 'e.g., 18', 'step': '0.1'}),
        }
        labels = {
            'prep_time': 'Preparation Time (minutes)',
            'cook_time': 'Cooking Time (minutes)',
            'calories': 'Calories (kcal)',
            'fat': 'Fat (g)',
            'carbs': 'Carbohydrates (g)',
            'protein': 'Protein (g)',
        }
        
    def clean_ingredients(self):
        ingredients = self.cleaned_data.get('ingredients', '')
        if ingredients and isinstance(ingredients, str):
            ingredients_list = [line.strip() for line in ingredients.split('\n') if line.strip()]
            return json.dumps(ingredients_list)
        return ingredients


#separate form for recipe submission for review
class RecipeSubmissionForm(forms.ModelForm):
    ingredients = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Enter each ingredient on a new line'}),
        help_text='Enter each ingredient on a new line'
    )
    
    class Meta:
        model = Recipe
        fields = [
            'title', 
            'description', 
            'ingredients', 
            'instructions', 
            'prep_time', 
            'cook_time', 
            'servings',
            'calories',  
            'fat', 
            'carbs', 
            'protein',
            'image'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about your recipe'}),
            'instructions': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Enter detailed cooking instructions'}),
            'prep_time': forms.NumberInput(attrs={'placeholder': 'Minutes'}),
            'cook_time': forms.NumberInput(attrs={'placeholder': 'Minutes'}),
            'servings': forms.NumberInput(attrs={'placeholder': 'Number of servings'}),
            'calories': forms.NumberInput(attrs={'placeholder': 'Calories per serving'}),
            'fat': forms.NumberInput(attrs={'placeholder': 'Fat in grams', 'step': '0.1'}),
            'carbs': forms.NumberInput(attrs={'placeholder': 'Carbohydrates in grams', 'step': '0.1'}),
            'protein': forms.NumberInput(attrs={'placeholder': 'Protein in grams', 'step': '0.1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #if editing an existing recipe with JSON ingredients, convert to text
        if self.instance.pk and self.instance.ingredients:
            try:
                ingredients_list = json.loads(self.instance.ingredients)
                if isinstance(ingredients_list, list):
                    self.initial['ingredients'] = '\n'.join(ingredients_list)
            except:
                pass
                
    def clean_ingredients(self):
        ingredients = self.cleaned_data.get('ingredients', '')
        if ingredients and isinstance(ingredients, str):
            ingredients_list = [line.strip() for line in ingredients.split('\n') if line.strip()]
            return json.dumps(ingredients_list)
        return ingredients