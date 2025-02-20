import json
from django.core.management.base import BaseCommand
from recipes.models import Recipe

class Command(BaseCommand):
    help = 'Load recipes from a dataset into the database'

    def handle(self, *args, **kwargs):
        with open('recipes_dataset.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

            for item in data:
                Recipe.objects.create(
                    title=item['title'],
                    ingredients=json.dumps(item['ingredients']),  # Store as JSON
                    instructions=item.get('instructions', ''),
                    prep_time=item.get('prep_time', None),
                    servings=item.get('servings', None),
                    source='local',
                    url=item.get('url', '')
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded dataset recipes!'))
