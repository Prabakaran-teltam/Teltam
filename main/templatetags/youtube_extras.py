import re
from django import template

register = template.Library()

@register.filter
def youtube_id(value):
    """
    Extracts the YouTube video ID from a YouTube URL.
    """
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, value)
    if match:
        return match.group(1)
    return None
