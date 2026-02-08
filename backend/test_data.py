import requests
import json

# Test gap data
r = requests.get('http://localhost:5000/data/gap')
gap_data = r.json()
print("=== GAP DATA ===")
print(f"Total deserts: {len(gap_data['deserts'])}")
for desert in gap_data['deserts'][:5]:
    print(f"  {desert['region_name']}: lat={desert['lat']}, lng={desert['lng']}, gap_score={desert['gap_score']}")

print("\n=== RECOMMENDATIONS ===")
r = requests.get('http://localhost:5000/data/recommendations')
rec_data = r.json()
print(f"Total recommendations: {len(rec_data['recommendations'])}")
for rec in rec_data['recommendations'][:5]:
    print(f"  {rec['region']}: {rec['action']}")
