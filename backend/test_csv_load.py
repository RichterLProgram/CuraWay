import requests

# Test if the CSV is being loaded
r = requests.get('http://localhost:5000/data/demand')
data = r.json()

print(f"Demand data received: {len(data.get('demand_by_region', {}))} regions")
print(f"First 3 regions: {list(data.get('demand_by_region', {}).keys())[:3]}")

# This endpoint uses virtue_rows
r2 = requests.get('http://localhost:5000/data/gap')
gap_data = r2.json()
print(f"\nGap data: {len(gap_data.get('deserts', []))} deserts")

# Test recommendations endpoint
r3 = requests.get('http://localhost:5000/data/recommendations')
rec_data = r3.json()
print(f"\nRecommendations: {len(rec_data.get('recommendations', []))}")
first_rec = rec_data['recommendations'][0] if rec_data['recommendations'] else {}
print(f"First recommendation:")
print(f"  Region: {first_rec.get('region')}")
print(f"  Action: {first_rec.get('action')}")
print(f"  Cost: {first_rec.get('roi')}")
print(f"  Impact: {first_rec.get('estimated_impact')}")
