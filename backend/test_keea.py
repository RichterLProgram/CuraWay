import requests

r = requests.get('http://localhost:5000/data/gap')
data = r.json()

# Find KEEA
keea_deserts = [d for d in data['deserts'] if 'KEEA' in d['region_name'] or 'Ankaful' in d['region_name']]
print(f"Found {len(keea_deserts)} KEEA deserts:")
for d in keea_deserts:
    print(f"  {d['region_name']}: lat={d['lat']}, lng={d['lng']}")

# Show all unique regions
all_regions = sorted(set([d['region_name'] for d in data['deserts']]))
print(f"\nTotal unique regions: {len(all_regions)}")
print(f"First 20: {all_regions[:20]}")

# Check for Unknown
unknown = [d for d in data['deserts'] if d['region_name'] == 'Unknown']
print(f"\nUnknown regions: {len(unknown)}")
if unknown:
    print(f"  First Unknown: lat={unknown[0]['lat']}, lng={unknown[0]['lng']}")
