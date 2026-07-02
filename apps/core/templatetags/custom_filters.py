from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def filter_no_category(queryset):
    return [item for item in queryset if not item.category]

@register.filter
def attribute(obj, attr):
    """Gets an attribute of an object dynamically from a string name.
    Supports dictionary lookup and Django Form field lookup.
    """
    if obj is None:
        return None
        
    # Try Django Form field lookup first if it's a form
    try:
        if hasattr(obj, '__getitem__') and not isinstance(obj, (list, tuple, str)):
            return obj[attr]
    except:
        pass
        
    if hasattr(obj, str(attr)):
        return getattr(obj, str(attr))
    elif isinstance(obj, dict):
        return obj.get(attr)
    return None
@register.filter
def split(value, arg):
    return value.split(arg)
