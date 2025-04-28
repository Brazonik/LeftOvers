from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    #lets the user retrieve values from a dictionary 
    return dictionary.get(key)


@register.filter
def has_new_unlocked_recipes(user):
    #check if a user has any unviewed unlocked recipes
    if not user or not user.is_authenticated:
        return False
    return user.unlocked_recipes.filter(viewed=False).exists()