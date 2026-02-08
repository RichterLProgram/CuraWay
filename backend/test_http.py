import requests

r = requests.get('http://localhost:5000/data/gap')
data = r.json()
regions = [d['region_name'] for d in data['deserts'][:10]]
print('First 10 regions from HTTP:')
for region in regions:
    print(f'  - {region}')
