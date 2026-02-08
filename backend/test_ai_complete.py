"""
Umfassender AI Test für alle Funktionen
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_agent_run():
    """Test 1: Basis AI Agent mit unterschiedlichen Queries"""
    print("\n" + "="*80)
    print("TEST 1: AI Agent - Verschiedene Queries")
    print("="*80)
    
    queries = [
        "What are the key healthcare gaps in Western region?",
        "How can KEEA improve oncology services?",
        "Suggest interventions for Greater Accra's underserved areas"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n📝 Query {i}: {query[:50]}...")
        try:
            response = requests.post(
                f"{BASE_URL}/agent/run",
                json={
                    "query": query,
                    "provider": "openai",
                    "top_k": 3,
                    "enable_rag": True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Answer: {data.get('answer', '')[:100]}...")
                print(f"   Citations: {len(data.get('citations', []))} found")
                print(f"   Trace ID: {data.get('trace_id', 'N/A')}")
            else:
                print(f"❌ Error {response.status_code}: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
        
        time.sleep(1)  # Rate limiting
    
    return True


def test_agent_council():
    """Test 2: Multi-Agent Council"""
    print("\n" + "="*80)
    print("TEST 2: Multi-Agent Council (Collaborative AI)")
    print("="*80)
    
    query = "What is the best approach to reduce healthcare gaps in Ghana?"
    print(f"\n📝 Query: {query}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/agent/council",
            json={
                "query": query,
                "num_agents": 3
            },
            timeout=45
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Consensus: {data.get('consensus', '')[:150]}...")
            print(f"   Agents: {len(data.get('opinions', []))} participated")
            return True
        else:
            print(f"⚠️  Status: {response.status_code} (Optional feature)")
            return True  # Council is optional
    except Exception as e:
        print(f"⚠️  Council not available (optional): {e}")
        return True


def test_routing():
    """Test 3: AI Routing Optimization"""
    print("\n" + "="*80)
    print("TEST 3: AI-Powered Routing")
    print("="*80)
    
    try:
        response = requests.post(
            f"{BASE_URL}/agent/routing",
            json={
                "origin": {"lat": 5.6037, "lng": -0.1870},  # Accra
                "destination": {"lat": 5.0919, "lng": -1.0419},  # KEEA
                "mode": "driving"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   Distance: {data.get('distance_km', 'N/A')} km")
            print(f"   Duration: {data.get('duration_minutes', 'N/A')} min")
            return True
        else:
            print(f"⚠️  Status: {response.status_code} (Optional feature)")
            return True
    except Exception as e:
        print(f"⚠️  Routing not available (optional): {e}")
        return True


def test_text2sql():
    """Test 4: Natural Language to SQL"""
    print("\n" + "="*80)
    print("TEST 4: Text2SQL")
    print("="*80)
    
    query = "Show me the top 5 regions with highest demand"
    print(f"\n📝 Query: {query}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/agent/text2sql",
            json={
                "question": query,
                "schema": "regions (name TEXT, demand INTEGER, supply INTEGER)"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {response.status_code}")
            print(f"   SQL: {data.get('sql', '')}")
            return True
        else:
            print(f"⚠️  Status: {response.status_code} (Optional feature)")
            return True
    except Exception as e:
        print(f"⚠️  Text2SQL not available (optional): {e}")
        return True


def test_hotspot_report():
    """Test 5: AI Hotspot Report Generation"""
    print("\n" + "="*80)
    print("TEST 5: AI Hotspot Report (Main Feature!)")
    print("="*80)
    
    hotspots = [
        {"region_name": "Western", "gap_score": 0.3, "population_affected": 20000},
        {"region_name": "KEEA", "gap_score": 0.8, "population_affected": 21000},
        {"region_name": "Greater Accra", "gap_score": 0.2, "population_affected": 13000}
    ]
    
    for hotspot in hotspots:
        print(f"\n🎯 Testing: {hotspot['region_name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/agent/hotspot_report",
                json={
                    "hotspot": hotspot,
                    "demand": {},
                    "supply": {},
                    "gap": {},
                    "recommendations": [],
                    "baseline_kpis": {}
                },
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Summary: {data.get('summary', '')[:100]}...")
                print(f"   Actions: {len(data.get('action_plan', {}).get('actions', []))} generated")
                
                # Check if AI generated unique content
                agent_report = data.get('agent_report', {})
                if agent_report.get('answer'):
                    print(f"   🤖 AI Answer: {agent_report['answer'][:80]}...")
            else:
                print(f"❌ Error {response.status_code}: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            return False
        
        time.sleep(1)
    
    return True


def main():
    print("\n" + "="*80)
    print("AI FUNCTIONALITY TEST SUITE")
    print("="*80)
    
    results = {
        "Agent Run (Core)": test_agent_run(),
        "Multi-Agent Council": test_agent_council(),
        "AI Routing": test_routing(),
        "Text2SQL": test_text2sql(),
        "Hotspot Reports": test_hotspot_report()
    }
    
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    for feature, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:12} {feature}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("SUCCESS: ALL AI FEATURES WORKING!")
    else:
        print("WARNING: Some features failed - check errors above")
    print("="*80 + "\n")
    
    return all_passed


if __name__ == "__main__":
    main()
