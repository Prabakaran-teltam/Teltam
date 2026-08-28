import sys
import os
import csv
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

import django
django.setup()

from app.models import YoutubeVideo, extract_youtube_id
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.utils.text import slugify

CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'youtube_videos_data.csv')

def parse_bool(val):
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ('true', '1', 't', 'yes')

def parse_dt(val):
    if not val or str(val).strip().upper() in ('NULL', 'NONE', ''):
        return None
    try:
        dt = parse_datetime(str(val).strip())
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
        return dt
    except Exception:
        return None

def strip_tags(html_str):
    if not html_str:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', str(html_str))
    return ' '.join(clean.split())

def seed_youtube_videos():
    if not os.path.exists(CSV_FILE_PATH):
        print(f"Error: {CSV_FILE_PATH} not found!")
        return

    created_count = 0
    updated_count = 0
    
    print("Starting YoutubeVideo data import...")
    
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            vid_id = int(row['id'])
            title = row['title'].strip()
            description = row['description'].strip()
            youtube_url = row['youtube_url'].strip()
            thumbnail_image = row['thumbnail_image'].strip()
            is_published = parse_bool(row['is_active'])
            created_date = parse_dt(row['created_at']) or timezone.now()
            updated_date = parse_dt(row['updated_at']) or timezone.now()
            category = "AI & Technology"  # Default category

            # Extract YouTube Video ID from iframe or URL
            yt_video_id = extract_youtube_id(youtube_url)

            # Check if record exists strictly by ID
            video = YoutubeVideo.objects.filter(id=vid_id).first()

            is_new = False
            if not video:
                video = YoutubeVideo(id=vid_id)
                is_new = True

            video.title = title
            video.full_description = description
            
            # Clean text for short description
            plain_desc = strip_tags(description)
            video.short_description = plain_desc[:250] + "..." if len(plain_desc) > 250 else plain_desc
            
            video.youtube_video_url = youtube_url
            video.youtube_video_id = yt_video_id
            if thumbnail_image:
                video.thumbnail_image = thumbnail_image
            video.category = category
            video.is_published = is_published
            video.created_date = created_date
            video.updated_date = updated_date
            
            # Auto slugify if missing
            if not video.slug:
                video.slug = slugify(title)
                orig = video.slug
                count = 1
                while YoutubeVideo.objects.filter(slug=video.slug).exclude(id=video.id).exists():
                    video.slug = f"{orig}-{count}"
                    count += 1
                    
            if not video.meta_title:
                video.meta_title = title

            video.save()

            if is_new:
                created_count += 1
                print(f"[CREATED] ID: {video.id} | Title: {video.title[:45]}... | YT ID: {video.youtube_video_id}")
            else:
                updated_count += 1
                print(f"[UPDATED] ID: {video.id} | Title: {video.title[:45]}... | YT ID: {video.youtube_video_id}")

    print(f"\nImport Completed Successfully! Total Created: {created_count}, Total Updated: {updated_count}")

if __name__ == '__main__':
    seed_youtube_videos()
