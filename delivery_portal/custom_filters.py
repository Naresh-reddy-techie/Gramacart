from django import template

register = template.Library()

@register.filter
def status_color(value):
    """
    Returns a CSS class or color based on status value.
    Example: 'pending' -> 'text-warning', 'completed' -> 'text-success'
    """
    mapping = {
        'pending': 'text-warning',
        'completed': 'text-success',
        'failed': 'text-danger',
    }
    return mapping.get(value.lower(), 'text-secondary')

