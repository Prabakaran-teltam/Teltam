import requests

api_key="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"

headers = {
    "Authorization": f"Bearer {api_key}"
}

# OpenAI endpoint to get credit grant (remaining balance)
url = "https://api.openai.com/v1/dashboard/billing/credit_grants"

response = requests.get(url, headers=headers)

if response.status_code == 200:
    data = response.json()
    total = data['total_granted']
    used = data['total_used']
    remaining = data['total_available']
    
    print(f"✅ Total Credits Granted: ${total}")
    print(f"🟠 Total Credits Used: ${used}")
    print(f"🟢 Remaining Credits: ${remaining}")
else:
    print(f"❌ Failed to fetch usage info: {response.status_code}")
    print(response.text)
