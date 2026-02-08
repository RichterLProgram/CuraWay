import sys
sys.path.insert(0, 'C:\\Users\\Linus\\Desktop\\HACKNATION1STPLACE\\backend')

# Force reload
if 'api.server' in sys.modules:
    del sys.modules['api.server']

from api.server import build_recommendations

recs = build_recommendations()

print("=== DIRECT FUNCTION CALL ===")
for idx, rec in enumerate(recs['recommendations'][:10]):
    print(f"\n{idx+1}. {rec['region']} ({rec['priority']}):")
    print(f"   Action: {rec['action']}")
    print(f"   Cost: {rec['roi']}")
    print(f"   Impact: {rec['estimated_impact']}")
