import os
import sys
import io
import django
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import Client
from app.models import DocumentTranslationHistory

def generate_test_image(text, filename):
    """Creates a sample test image with rendered text for Vision OCR testing."""
    img = Image.new('RGB', (600, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((30, 80), text, fill=(0, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.name = filename
    buffer.seek(0)
    return buffer

def test_multi_image_upload():
    print("--- Starting Multi-Image Upload & Vision OCR Translation Test ---")
    client = Client()
    
    # 1. Create temporary test images
    img1 = generate_test_image("Welcome to Teltam AI multi-image OCR engine page one.", "page1.png")
    img2 = generate_test_image("Translating multiple document pages simultaneously page two.", "page2.png")
    
    # 2. Perform multi-image POST request
    response = client.post('/api/upload-document/', {
        'file': [img1, img2],
        'source_lang': 'en',
        'target_lang': 'ta', # Tamil
        'output_format': 'txt'
    })
    
    print("Upload API Response Status:", response.status_code)
    res_json = response.json()
    print("Upload API Response Payload:", res_json)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert 'task_id' in res_json, "Missing task_id in response"
    
    task_id = res_json['task_id']
    history_id = res_json['history_id']
    
    # 3. Poll task status until complete
    import time
    for attempt in range(30):
        status_res = client.get(f'/api/task-status/{task_id}/')
        status_json = status_res.json()
        print(f"[Attempt {attempt+1}] Status:", status_json.get('status'), "| Progress:", status_json.get('progress'))
        
        if status_json.get('status') == 'SUCCESS':
            result = status_json['result']
            print("\n--- OCR & Translation Completed Successfully! ---")
            print("Extracted Text:\n", result.get('extracted_text'))
            print("\nTranslated Text:\n", result.get('translated_text'))
            print("\nDownload URL:", result.get('download_url'))
            
            assert 'Image 1' in result['extracted_text']
            assert 'Image 2' in result['extracted_text']
            print("\nSUCCESS: Multi-Image Batch OCR & Translation verified cleanly!")
            return
            
        time.sleep(2)
        
    raise RuntimeError("Task status polling timed out!")

if __name__ == '__main__':
    test_multi_image_upload()
