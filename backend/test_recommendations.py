import requests

r = requests.get('http://localhost:5000/data/recommendations')
data = r.json()

print("=== RECOMMENDATIONS (First 10) ===")
for rec in data['recommendations'][:10]:
    print(f"\n{rec['region']} ({rec['priority']}):")
    print(f"  Action: {rec['action']}")
    print(f"  Cost: {rec['roi']}")
    print(f"  Impact: {rec['estimated_impact']}")
    print(f"  Capabilities: {rec['capability_needed'][:60]}...")

# Check KEEA specifically
keea_recs = [r for r in data['recommendations'] if 'KEEA' in r['region']]
if keea_recs:
    print("\n=== KEEA RECOMMENDATION ===")
    rec = keea_recs[0]
    print(f"Region: {rec['region']}")
    print(f"Action: {rec['action']}")
    print(f"Priority: {rec['priority']}")
    print(f"Cost: {rec['roi']}")
