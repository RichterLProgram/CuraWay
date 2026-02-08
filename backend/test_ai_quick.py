import requests

print("Testing AI Agent with OpenAI...")

try:
    response = requests.post(
        "http://localhost:8000/agent/run",
        json={
            "query": "What are the healthcare gaps in KEEA region?",
            "provider": "openai",
            "top_k": 3,
            "enable_rag": True
        },
        timeout=30
    )
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n=== SUCCESS! AI IS WORKING ===")
        print(f"Answer: {data.get('answer', '')[:200]}...")
        print(f"Citations: {len(data.get('citations', []))}")
        print(f"Trace ID: {data.get('trace_id', 'N/A')}")
    else:
        print(f"\nError: {response.text}")
        
except Exception as e:
    print(f"\nException: {e}")
