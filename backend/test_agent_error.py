import requests
import json

url = "http://localhost:8000/agent/run"
payload = {
    "query": "Test query for KEEA region",
    "provider": "openai",
    "model": None,
    "top_k": 5,
    "enable_rag": True
}

try:
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
