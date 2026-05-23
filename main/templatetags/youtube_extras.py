import re
from django import template

register = template.Library()

@register.filter
def embed_url(value):
    if not value:
        return ""
    # Extract video ID
    match = re.search(r"(?:v=|be/)([a-zA-Z0-9_-]{11})", value)
    if match:
        video_id = match.group(1)
        return f"https://www.youtube.com/embed/{video_id}"
    return value
