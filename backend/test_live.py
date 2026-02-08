import sys
sys.path.insert(0, ".")

# Force reload of the module
import importlib
if 'api.server' in sys.modules:
    importlib.reload(sys.modules['api.server'])

from api.server import build_gap_analysis

# Test the function directly
gap = build_gap_analysis()
print("=== DIRECT CALL TO build_gap_analysis() ===")
for desert in gap['deserts'][:5]:
    print(f"  {desert['region_name']}: lat={desert['lat']}, lng={desert['lng']}")
