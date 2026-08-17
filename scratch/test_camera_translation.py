import os
import sys

sys.path.insert(0, r'r:\Gowtham\Client side\Teltam_website\Trasnlater_django')

import json
import base64
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from app.models import DeveloperAPIKey, UserSubscription, PricingPlan, UserTranslationHistory

def test_camera_api():
    print("=== STARTING LIVE CAMERA TRANSLATION MODULE VERIFICATION ===")

    # 1. Ensure user and developer API key exists
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username="cameratestuser", email="camera@test.com", password="password123")

    plan = PricingPlan.objects.filter(slug="pro").first()
    if not plan:
        plan = PricingPlan.objects.first()
    sub, _ = UserSubscription.objects.get_or_create(user=user, defaults={'plan': plan, 'status': 'active'})
    sub.status = 'active'
    sub.save()

    api_key_obj = DeveloperAPIKey.objects.filter(user=user, is_active=True).first()
    if not api_key_obj:
        api_key_obj = DeveloperAPIKey.objects.create(user=user, name="Camera Test Key", api_key=DeveloperAPIKey.generate_key())

    client = Client()
    client.force_login(user)

    # 2. Test rendering User Dashboard Live Camera workspace
    res = client.get('/user/tools/camera/')
    print(f"[1/4] User Tool Camera Page GET status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"

    # 3. Create a valid 200x100 PNG image in base64 using PIL
    from PIL import Image, ImageDraw
    import io

    img = Image.new('RGB', (200, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 40), "HELLO WORLD TELTAM CAMERA OCR", fill=(0, 0, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    sample_jpeg_base64 = f"data:image/png;base64,{base64_str}"

    # 4. Test Internal Camera API endpoint /api/translate/camera/
    payload = {
        'image_data': sample_jpeg_base64,
        'target_lang': 'es',
        'source_lang': 'auto'
    }
    res_api = client.post('/api/translate/camera/', data=json.dumps(payload), content_type='application/json')
    print(f"[2/4] Live Camera API POST status: {res_api.status_code}")
    data = res_api.json()
    print(f"      API Response: {data}")
    assert res_api.status_code == 200, f"Expected 200, got {res_api.status_code}"
    assert data.get('status') == 'success', f"Expected success status, got {data}"

    # 5. Test Developer REST API v1 Endpoint /api/v1/translate/camera/
    res_v1 = client.post(
        '/api/v1/translate/camera/',
        data=json.dumps(payload),
        content_type='application/json',
        HTTP_X_API_KEY=api_key_obj.api_key
    )
    print(f"[3/4] Developer REST API v1 Camera POST status: {res_v1.status_code}")
    data_v1 = res_v1.json()
    print(f"      v1 Response: {data_v1}")
    assert res_v1.status_code == 200, f"Expected 200, got {res_v1.status_code}"
    assert data_v1.get('status') == 'success', f"Expected success status, got {data_v1}"

    # 6. Verify UserTranslationHistory count for camera tool
    cam_history_count = UserTranslationHistory.objects.filter(user=user, tool_type='camera').count()
    print(f"[4/4] Saved Camera Translation History entries: {cam_history_count}")

    print("\n[SUCCESS] LIVE CAMERA TRANSLATION MODULE VERIFICATION PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_camera_api()
