from django import forms
from .models import Recipe
import json

# defines what the structure and what fields exist in the form
# converts the ingredients field to a JSON string
# connects the form to the Recipe model
# gets raw data from the form, splits it by newlines and trims empty space and converts it to a JSON string

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
    # method transforms the ingredients that users type into a format the website can use. 