#!/usr/bin/env python3
"""
Test what the backend actually returns
"""
import requests
import json

# Test the chat endpoint
url = "http://localhost:8000/api/chat"
payload = {
    "session_id": "debug_test_123",
    "content": "How do I reset my password?",
    "user_email": "test@example.com",
    "customer_name": "Test User",
    "subject": "Test",
    "category": "General Question"
}

print("🔍 Testing backend response...\n")
print(f"Sending: {payload['content']}")
print(f"Category: {payload['category']}\n")

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n📦 Response:")
        print(json.dumps(data, indent=2))
        
        if 'related' in data:
            print(f"\n✅ Related questions found: {len(data['related'])}")
            for i, q in enumerate(data['related'], 1):
                print(f"   {i}. {q}")
        else:
            print("\n⚠️  No 'related' field in response!")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Make sure backend is running: docker compose ps")