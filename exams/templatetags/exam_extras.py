from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Access dict item by key in templates: {{ mydict|get_item:key }}"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def percentage(value, total):
    """Calculate percentage: {{ value|percentage:total }}"""
    if not total:
        return 0
    return round(value / total * 100, 1)


@register.filter
def subtract(value, arg):
    """Subtract: {{ value|subtract:arg }}"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0
